from __future__ import annotations

import uuid
from datetime import datetime, timezone

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from .schemas import AIActionCard, AIMessageOut, ProposedAction, UserContext
from .services import tools
from .services.data_access import (
    get_active_leases,
    get_open_maintenance,
    get_payment_history,
    list_properties,
    summarize_leases,
    summarize_maintenance,
    summarize_payments,
    summarize_property_portfolio,
)
from .services.openai_client import classify_intent, compose_answer
from .services.rag import init_vector_store, retrieve_documents
from .state import AgentState


# ---------------------------------------------------------------------------
# Node functions — each returns a partial-state dict
# ---------------------------------------------------------------------------

def intake_node(_state: AgentState) -> dict:
    return {"debug_steps": ["intake"]}


def route_intent_node(state: AgentState) -> dict:
    intent = classify_intent(state["user_message"], state["role"])
    return {"intent": intent, "debug_steps": ["route_intent"]}


def retrieve_context_node(state: AgentState) -> dict:
    user = UserContext(user_id=state["user_id"], role=state["role"], tenant_id=state["tenant_id"])
    retrieved = retrieve_documents(state["user_message"], user)
    return {
        "retrieved_docs": [doc.model_dump() for doc in retrieved],
        "citations": [doc.title for doc in retrieved],
        "debug_steps": ["retrieve_context"],
    }


def plan_node(state: AgentState) -> dict:
    updates: dict = {"debug_steps": ["plan"]}
    if state["intent"] == "maintenance_workflow" and state["role"] in {"owner", "manager"}:
        action = ProposedAction(
            action_id=f"act_{uuid.uuid4().hex[:10]}",
            type="approve_maintenance_followup",
            title="Approve Maintenance Follow-up",
            description=(
                "Authorize a resident update and vendor dispatch plan. "
                "Review the open maintenance requests above before approving."
            ),
        )
        updates["approval_required"] = True
        updates["proposed_actions"] = [action.model_dump()]
    return updates


def tool_execution_node(state: AgentState) -> dict:
    user = UserContext(user_id=state["user_id"], role=state["role"], tenant_id=state["tenant_id"])
    intent = state["intent"]
    new_tool_calls: list[dict] = []
    structured: dict = {}

    if intent == "portfolio_summary":
        properties = list_properties(user)
        maintenance_items = get_open_maintenance(user)
        payments = get_payment_history(user)
        leases = get_active_leases(user)
        filtered_props = tools.filter_records_by_query(
            properties, state["user_message"], ["address", "city", "name", "status"]
        )
        prop_summary = summarize_property_portfolio(filtered_props)
        maint_summary = summarize_maintenance(maintenance_items)
        pay_summary = summarize_payments(payments, leases, state["role"])
        structured["summary"] = " ".join([prop_summary, maint_summary, pay_summary])
        new_tool_calls.extend([
            {"name": "list_properties", "input": {}, "output_summary": prop_summary},
            {"name": "get_open_maintenance", "input": {}, "output_summary": maint_summary},
            {"name": "get_payment_history", "input": {}, "output_summary": pay_summary},
        ])

    elif intent == "payment_workflow":
        leases = get_active_leases(user)
        payments = get_payment_history(user)
        filtered_pays = tools.filter_records_by_query(
            payments, state["user_message"], ["property_name", "tenant_name", "status", "due_date"]
        )
        pay_summary = summarize_payments(filtered_pays, leases, state["role"])
        lease_summary = summarize_leases(leases)
        structured["summary"] = " ".join([pay_summary, lease_summary])
        new_tool_calls.extend([
            {"name": "get_payment_history", "input": {"role": state["role"]}, "output_summary": pay_summary},
            {"name": "get_active_leases", "input": {}, "output_summary": lease_summary},
        ])

    elif intent == "maintenance_workflow":
        requests = get_open_maintenance(user)
        properties = list_properties(user)
        filtered_reqs = tools.filter_records_by_query(
            requests, state["user_message"], ["property_name", "category", "description", "urgency", "status"]
        )
        maint_summary = summarize_maintenance(filtered_reqs)
        prop_summary = summarize_property_portfolio(properties)
        structured["summary"] = " ".join([maint_summary, prop_summary])
        new_tool_calls.extend([
            {"name": "get_open_maintenance", "input": {}, "output_summary": maint_summary},
            {"name": "list_properties", "input": {}, "output_summary": prop_summary},
        ])

    else:  # document_lookup or general_qa
        leases = get_active_leases(user)
        doc_summary = " ".join(d.get("snippet", "") for d in state["retrieved_docs"])
        lease_summary = summarize_leases(leases)
        parts = [p for p in [doc_summary, lease_summary] if p]
        structured["summary"] = " ".join(parts) if parts else "No matching records found."
        if state["retrieved_docs"]:
            new_tool_calls.append({
                "name": "search_documents",
                "input": {"query": state["user_message"]},
                "output_summary": doc_summary,
            })
        if leases:
            new_tool_calls.append({
                "name": "get_active_leases",
                "input": {},
                "output_summary": lease_summary,
            })

    return {
        "structured_context": structured,
        "tool_calls": new_tool_calls,
        "debug_steps": ["tool_execution"],
    }


def policy_check_node(state: AgentState) -> dict:
    updates: dict = {"debug_steps": ["policy_check"]}
    if state.get("approval_required") and state["role"] not in {"owner", "manager"}:
        updates["approval_required"] = False
        updates["proposed_actions"] = []
    return updates


def respond_node(state: AgentState) -> dict:
    tool_summary = ""
    if state["tool_calls"]:
        names = ", ".join(call["name"] for call in state["tool_calls"])
        tool_summary = f"Tools used: {names}."

    answer = compose_answer(
        role=state["role"],
        user_message=state["user_message"],
        context_summary=state["structured_context"].get("summary", ""),
        citations=state["citations"],
        tool_summary=tool_summary,
    )
    return {"final_response": answer, "debug_steps": ["respond"]}


def approval_gate_node(state: AgentState) -> dict:
    """Runs after the user approves or rejects the proposed action."""
    tool_summary = ""
    if state["tool_calls"]:
        names = ", ".join(call["name"] for call in state["tool_calls"])
        tool_summary = f"Tools used: {names}."

    answer = compose_answer(
        role=state["role"],
        user_message=state["user_message"],
        context_summary=state["structured_context"].get("summary", ""),
        citations=state["citations"],
        tool_summary=tool_summary,
        approval_status=state.get("approval_status"),
    )
    return {"final_response": answer, "debug_steps": ["approval_gate"]}


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def _route_after_respond(state: AgentState) -> str:
    if state.get("approval_required"):
        return "approval_gate"
    return END


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def _build_graph() -> StateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node("intake", intake_node)
    workflow.add_node("route_intent", route_intent_node)
    workflow.add_node("retrieve_context", retrieve_context_node)
    workflow.add_node("plan", plan_node)
    workflow.add_node("tool_execution", tool_execution_node)
    workflow.add_node("policy_check", policy_check_node)
    workflow.add_node("respond", respond_node)
    workflow.add_node("approval_gate", approval_gate_node)

    workflow.set_entry_point("intake")
    workflow.add_edge("intake", "route_intent")
    workflow.add_edge("route_intent", "retrieve_context")
    workflow.add_edge("retrieve_context", "plan")
    workflow.add_edge("plan", "tool_execution")
    workflow.add_edge("tool_execution", "policy_check")
    workflow.add_edge("policy_check", "respond")
    workflow.add_conditional_edges(
        "respond",
        _route_after_respond,
        {"approval_gate": "approval_gate", END: END},
    )
    workflow.add_edge("approval_gate", END)

    return workflow


_checkpointer = MemorySaver()
graph = _build_graph().compile(
    checkpointer=_checkpointer,
    interrupt_before=["approval_gate"],
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_agent_turn(
    *, session_id: str, message: str, user: UserContext, turn_id: str
) -> tuple[dict, bool]:
    """
    Execute a fresh agent turn.

    Returns (state_values, was_interrupted).
    was_interrupted=True means the graph paused before approval_gate and is
    waiting for the user to approve/reject the proposed action.
    """
    init_vector_store()

    initial_state: AgentState = {
        "session_id": session_id,
        "user_id": user.user_id,
        "role": user.role,
        "tenant_id": user.tenant_id,
        "user_message": message,
        "intent": "general_qa",
        "retrieved_docs": [],
        "structured_context": {},
        "tool_calls": [],
        "proposed_actions": [],
        "approval_required": False,
        "approval_status": None,
        "final_response": "",
        "citations": [],
        "debug_steps": [],
    }

    thread_config = {"configurable": {"thread_id": turn_id}}
    for _ in graph.stream(initial_state, config=thread_config):
        pass

    snapshot = graph.get_state(thread_config)
    was_interrupted = bool(snapshot.next)
    return dict(snapshot.values), was_interrupted


def resume_agent_turn(*, turn_id: str, approval_status: str) -> dict:
    """
    Resume a paused graph after an approval decision.

    Returns the updated state containing the follow-up final_response.
    """
    thread_config = {"configurable": {"thread_id": turn_id}}
    graph.update_state(thread_config, {"approval_status": approval_status})

    for _ in graph.stream(None, config=thread_config):
        pass

    return dict(graph.get_state(thread_config).values)


def build_assistant_message(state: dict) -> AIMessageOut:
    action_card = None
    proposed = state.get("proposed_actions", [])
    if proposed and state.get("approval_required"):
        proposal = proposed[0]
        action_card = AIActionCard(
            action_id=proposal["action_id"],
            type=proposal["type"],
            title=proposal["title"],
            description=proposal["description"],
            status="pending",
        )

    return AIMessageOut(
        id=f"msg_{uuid.uuid4().hex[:10]}",
        role="assistant",
        content=state.get("final_response", ""),
        created_at=datetime.now(timezone.utc),
        action_card=action_card,
    )
