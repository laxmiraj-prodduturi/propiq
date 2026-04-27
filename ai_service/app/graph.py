from __future__ import annotations

import contextvars
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph

from .agents.orchestrator import ORCHESTRATOR_TOOLS, get_orchestrator_prompt
from .checkpointer import get_checkpointer
from .config import settings
from .logging_config import get_logger
from .schemas import AIActionCard, AIDebugInfo, AIMessageOut, ProposedAction, UserContext
from .services.agent_tools import set_user_context
from .services.rag import init_vector_store
from .state import AgentState

logger = get_logger("graph")


# ---------------------------------------------------------------------------
# LLM factory
# ---------------------------------------------------------------------------

def _get_llm():
    if not settings.OPENAI_API_KEY:
        return None
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=0.3,
        api_key=settings.OPENAI_API_KEY,
    )
    return llm.bind_tools(ORCHESTRATOR_TOOLS)


# ---------------------------------------------------------------------------
# Node: orchestrator agent — routes to specialists, synthesizes answer
# ---------------------------------------------------------------------------

def agent_node(state: AgentState) -> dict:
    updates: dict = {"debug_steps": ["orchestrator"]}

    llm = _get_llm()
    if not llm:
        updates["messages"] = [
            AIMessage(content="OpenAI is not configured. Please set OPENAI_API_KEY in the .env file.")
        ]
        return updates

    system = SystemMessage(content=get_orchestrator_prompt(state["role"]))
    response = llm.invoke([system] + state["messages"])
    updates["messages"] = [response]
    logger.info("response", response)
    # Detect propose_action inside any specialist's result → HITL
    if hasattr(response, "tool_calls"):
        for tc in response.tool_calls:
            # The orchestrator itself can also trigger approval directly
            if tc["name"] == "propose_action" and state["role"] in {"owner", "manager"}:
                action = ProposedAction(
                    action_id=f"act_{uuid.uuid4().hex[:10]}",
                    type="approve_agent_action",
                    title=tc["args"].get("title", "Proposed Action"),
                    description=tc["args"].get("description", ""),
                )
                updates["approval_required"] = True
                updates["proposed_actions"] = [action.model_dump()]

    return updates


# ---------------------------------------------------------------------------
# Node: approval gate — generates follow-up after human decision
# ---------------------------------------------------------------------------

def approval_gate_node(state: AgentState) -> dict:
    updates: dict = {"debug_steps": ["approval_gate"]}
    approval_status = state.get("approval_status", "pending")
    proposed = state.get("proposed_actions", [])
    action = proposed[0] if proposed else {}

    # Execute real post-approval side-effects
    post_actions: list[str] = []
    if approval_status == "approved" and action:
        post_actions = _run_post_approval_actions(action, state)

    llm = _get_llm()
    if llm:
        if approval_status == "approved":
            instruction = (
                f"The action '{action.get('title', 'the requested action')}' was APPROVED.\n"
                + (f"Post-approval steps completed:\n" + "\n".join(f"- {s}" for s in post_actions) if post_actions else "")
                + "\n\nGenerate a professional dispatch confirmation that includes:\n"
                "1. What was dispatched and to which property\n"
                "2. Vendor name, trade, and expected response window\n"
                "3. What the tenant should expect (notification sent, technician incoming)\n"
                "4. Work order reference or tracking context\n"
                "5. Suggested next step for the manager (e.g. follow up in X hours if no vendor contact)"
            )
        else:
            instruction = (
                f"The action '{action.get('title', 'the requested action')}' was REJECTED.\n"
                "Acknowledge the rejection professionally, summarize what will NOT happen, "
                "and suggest alternative next steps the manager could take."
            )

        system = SystemMessage(content=get_orchestrator_prompt(state["role"]))
        note = HumanMessage(content=instruction)
        response = llm.invoke([system] + state["messages"] + [note])
        updates["messages"] = [response]
    else:
        text = (
            f"Dispatch confirmed. {' | '.join(post_actions)}"
            if approval_status == "approved"
            else "Action rejected. No changes have been made."
        )
        updates["messages"] = [AIMessage(content=text)]

    return updates


def _run_post_approval_actions(action: dict, state: AgentState) -> list[str]:
    """
    Execute real side-effects when an action is approved:
    - Send in-app notification to all tenants on the affected property
    - Send confirmation notification to the approver
    Returns a list of human-readable completion summaries.
    """
    from .backend_bridge import send_notification, tenants_for_user

    completed: list[str] = []
    title = action.get("title", "Maintenance action")
    description = action.get("description", "")

    # Notify tenants on the property about incoming work
    try:
        tenants = tenants_for_user(
            user_id=state["user_id"],
            role=state["role"],
            tenant_id=state["tenant_id"],
        )
        for tenant in tenants:
            send_notification(
                user_id=tenant.id,
                type="maintenance",
                title=f"Maintenance Scheduled: {title}",
                body=(
                    f"A technician has been dispatched to your property. {description} "
                    "Please ensure access is available. Contact your property manager with any questions."
                ),
            )
        if tenants:
            completed.append(f"Tenant notification sent to {len(tenants)} resident(s)")
    except Exception as exc:
        completed.append(f"Tenant notification attempted (error: {exc})")

    # Confirmation notification to the approver (manager/owner)
    try:
        send_notification(
            user_id=state["user_id"],
            type="ai",
            title=f"Dispatch Confirmed: {title}",
            body=f"You approved: {description} The vendor has been queued for dispatch.",
        )
        completed.append("Dispatch confirmation sent to your notifications")
    except Exception:
        pass

    return completed


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------

def _route_agent(state: AgentState) -> str:
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END



# ---------------------------------------------------------------------------
# Tool executor node — replaces ToolNode, executes all tool calls in the last message
# ---------------------------------------------------------------------------

_TOOL_MAP = {t.name: t for t in ORCHESTRATOR_TOOLS}
logger.info("Registered orchestrator tools: %s", list(_TOOL_MAP))


def tool_executor_node(state: AgentState) -> dict:
    last = state["messages"][-1]
    tool_calls = getattr(last, "tool_calls", [])
    if not tool_calls:
        return {"messages": [], "debug_steps": ["tools"]}

    # Copy the current context so ContextVar values (user_ctx) propagate into threads
    ctx = contextvars.copy_context()

    def _invoke_one(tc: dict) -> tuple[dict, str]:
        tool_fn = _TOOL_MAP.get(tc["name"])
        logger.info("Tool call: %s | args: %s", tc["name"], tc["args"])
        if tool_fn:
            try:
                result = ctx.run(tool_fn.invoke, tc["args"])
                logger.debug("Tool result [%s]: %s", tc["name"], str(result)[:300])
            except Exception as exc:
                logger.exception("Tool error [%s]: %s", tc["name"], exc)
                result = f"Tool error ({tc['name']}): {exc}"
        else:
            result = f"Unknown tool: {tc['name']}"
        return tc, str(result)

    results: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=len(tool_calls)) as executor:
        futures = {executor.submit(_invoke_one, tc): tc["id"] for tc in tool_calls}
        for future in as_completed(futures):
            tc, result = future.result()
            results[tc["id"]] = result

    # Preserve the original tool_call order in the output messages
    tool_messages = [
        ToolMessage(content=results[tc["id"]], tool_call_id=tc["id"], name=tc["name"])
        for tc in tool_calls
    ]
    return {"messages": tool_messages, "debug_steps": ["tools"]}


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def _build_graph() -> StateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tool_executor_node)

    workflow.set_entry_point("agent")
    workflow.add_conditional_edges(
        "agent",
        _route_agent,
        {"tools": "tools", END: END},
    )
    workflow.add_edge("tools", "agent")

    return workflow


_checkpointer = get_checkpointer()
graph = _build_graph().compile(checkpointer=_checkpointer)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def run_agent_turn(
    *,
    session_id: str,
    message: str,
    user: UserContext,
    turn_id: str,
    history: list | None = None,
) -> tuple[dict, bool]:
    """
    Execute one agent turn. Pass history (list of HumanMessage/AIMessage) from
    the session store so the agent maintains conversation continuity across turns.
    Returns (state_values, was_interrupted).
    """
    init_vector_store()
    set_user_context(user)

    # Build message list: prior conversation + new user message
    prior = [m for m in (history or []) if getattr(m, "content", "")]
    messages = prior + [HumanMessage(content=message)]

    initial_state: AgentState = {
        "session_id": session_id,
        "user_id": user.user_id,
        "role": user.role,
        "tenant_id": user.tenant_id,
        "messages": messages,
        "citations": [],
        "approval_required": False,
        "approval_status": None,
        "proposed_actions": [],
        "debug_steps": [],
    }

    thread_config = {"configurable": {"thread_id": turn_id}}
    for _ in graph.stream(initial_state, config=thread_config):
        pass

    snapshot = graph.get_state(thread_config)
    was_interrupted = bool(snapshot.next)
    return dict(snapshot.values), was_interrupted


def generate_approval_confirmation(
    *,
    action: dict,
    approval_status: str,
    user_id: str,
    role: str,
    tenant_id: str,
) -> str:
    """
    Generate a post-approval confirmation message without needing the graph state.
    Called directly from the /approve endpoint.
    """
    title = action.get("title", "the requested action")

    post_actions: list[str] = []
    if approval_status == "approved":
        post_actions = _run_post_approval_actions(
            action,
            {"user_id": user_id, "role": role, "tenant_id": tenant_id},
        )

    llm_obj = _get_llm()
    if llm_obj:
        from langchain_openai import ChatOpenAI
        simple_llm = ChatOpenAI(
            model=settings.OPENAI_MODEL,
            temperature=0.3,
            api_key=settings.OPENAI_API_KEY,
        )
        if approval_status == "approved":
            prompt = (
                f"The action '{title}' was APPROVED.\n"
                + (f"Steps completed:\n" + "\n".join(f"- {s}" for s in post_actions) + "\n\n" if post_actions else "\n")
                + "Generate a concise professional dispatch confirmation (3-4 sentences) covering:\n"
                "1. What was dispatched and to which property\n"
                "2. Expected vendor response window\n"
                "3. What the tenant should expect\n"
                "4. Suggested next step for the manager"
            )
        else:
            prompt = (
                f"The action '{title}' was REJECTED.\n"
                "Acknowledge the rejection professionally in 2-3 sentences and suggest an alternative next step."
            )
        try:
            resp = simple_llm.invoke([
                SystemMessage(content="You are a professional property management assistant."),
                HumanMessage(content=prompt),
            ])
            return resp.content
        except Exception:
            pass

    if approval_status == "approved":
        base = f"Dispatch confirmed for '{title}'."
        if post_actions:
            base += " " + " | ".join(post_actions) + "."
        return base
    return f"'{title}' was rejected. No changes have been made."


def resume_agent_turn(*, turn_id: str, approval_status: str) -> dict:
    """Resume a paused graph after an approval decision."""
    thread_config = {"configurable": {"thread_id": turn_id}}
    graph.update_state(thread_config, {"approval_status": approval_status})

    for _ in graph.stream(None, config=thread_config):
        pass

    return dict(graph.get_state(thread_config).values)


def build_assistant_message(state: dict) -> AIMessageOut:
    messages = state.get("messages", [])

    # Final answer = last AIMessage that has non-empty text content
    # (prefer messages without pending tool_calls, but fall back to any with content)
    final_content = ""
    for msg in reversed(messages):
        if isinstance(msg, AIMessage) and msg.content:
            final_content = msg.content
            break

    # Which specialist agents were called
    agents_called: list[str] = []
    for msg in messages:
        if isinstance(msg, AIMessage) and hasattr(msg, "tool_calls"):
            for tc in msg.tool_calls:
                agents_called.append(tc["name"])

    # Citations from document agent tool outputs
    citations: list[str] = []
    for msg in messages:
        if isinstance(msg, ToolMessage) and getattr(msg, "name", "") in (
            "ask_document_agent", "search_documents"
        ):
            for line in msg.content.split("\n"):
                if line.startswith("[") and "]:" in line:
                    citations.append(line[1: line.index("]")])

    action_card = None
    proposed = state.get("proposed_actions", [])
    # Only show action card when approval is still pending (not yet decided)
    if proposed and state.get("approval_required") and state.get("approval_status") is None:
        p = proposed[0]
        action_card = AIActionCard(
            action_id=p["action_id"],
            type=p["type"],
            title=p["title"],
            description=p["description"],
            status="pending",
        )

    debug_info = AIDebugInfo(
        intent=_infer_intent(agents_called),
        tools_called=agents_called,
        citations=citations or state.get("citations", []),
        steps=state.get("debug_steps", []),
    )

    return AIMessageOut(
        id=f"msg_{uuid.uuid4().hex[:10]}",
        role="assistant",
        content=final_content,
        created_at=datetime.now(timezone.utc),
        action_card=action_card,
        debug_info=debug_info,
    )


def _infer_intent(agents_called: list[str]) -> str:
    if "ask_portfolio_agent" in agents_called:
        return "portfolio_summary"
    if "ask_lease_agent" in agents_called:
        return "lease_workflow"
    if "ask_tenant_agent" in agents_called:
        return "tenant_directory"
    if "ask_finance_agent" in agents_called:
        return "payment_workflow"
    if "ask_maintenance_agent" in agents_called:
        return "maintenance_workflow"
    if "ask_document_agent" in agents_called:
        return "document_lookup"
    return "general_qa"
