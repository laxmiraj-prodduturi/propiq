from __future__ import annotations

import logging

from langchain_core.tools import tool
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from . import (
    document_agent,
    finance_agent,
    lease_agent,
    maintenance_agent,
    portfolio_agent,
    tenant_agent,
)
from ..services.agent_tools import propose_action, set_user_context
from ..schemas import UserContext

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Orchestrator tools — each wraps a specialist agent as a callable tool
# ---------------------------------------------------------------------------

@tool
def ask_portfolio_agent(query: str) -> str:
    """
    Delegate to the Portfolio Agent for questions about:
    property occupancy, vacancy rates, portfolio overview, property count, overall health.
    query: The specific portfolio question to answer.
    """
    return portfolio_agent.run(query)


@tool
def ask_maintenance_agent(query: str) -> str:
    """
    Delegate to the Maintenance Agent for questions about:
    open maintenance requests, repairs, work orders, vendor selection, emergency issues,
    maintenance urgency triage, creating work orders, dispatching vendors.
    query: The specific maintenance question or task.
    """
    return maintenance_agent.run(query)


@tool
def ask_finance_agent(query: str) -> str:
    """
    Delegate to the Finance Agent for questions about:
    rent payments, overdue balances, late fees, rent roll, revenue projections,
    payment history, total monthly income, financial performance.
    query: The specific finance question to answer.
    """
    return finance_agent.run(query)


@tool
def ask_lease_agent(query: str) -> str:
    """
    Delegate to the Lease Agent for questions about:
    leases expiring soon, renewal planning, renewal offer drafting,
    lease end dates, upcoming renewals, which leases expire this quarter/month/year.
    query: The specific lease question or task.
    """
    return lease_agent.run(query)


@tool
def ask_tenant_agent(query: str) -> str:
    """
    Delegate to the Tenant Agent for questions about:
    tenant names and contacts, tenant directory, sending notifications to tenants,
    tenant payment reliability, bulk announcements to tenants.
    query: The specific tenant question or communication task.
    """
    return tenant_agent.run(query)


@tool
def ask_document_agent(query: str) -> str:
    """
    Delegate to the Document Agent for questions about:
    lease clauses, pet policies, specific policy terms, what a lease document says,
    late fee policies, notices, and document search.
    query: The specific document or policy question.
    """
    return document_agent.run(query)


ORCHESTRATOR_TOOLS = [
    ask_portfolio_agent,
    ask_maintenance_agent,
    ask_finance_agent,
    ask_lease_agent,
    ask_tenant_agent,
    ask_document_agent,
    propose_action,          # orchestrator can propose high-impact actions for HITL approval
]

# ---------------------------------------------------------------------------
# Orchestrator system prompt
# ---------------------------------------------------------------------------

_ORCHESTRATOR_SYSTEM_PROMPT = """\
You are the PropIQ Orchestrator — the primary AI assistant for a residential property management platform.
You coordinate a team of 6 specialist agents. Your job is to:
1. Understand the user's question
2. Route it to the right specialist agent(s) by calling their tools
3. Synthesize the results into a single, clear, grounded answer

The user's role is: {role}
- tenant: answer only about their own lease, payments, property
- manager: full portfolio access — operations, tenants, maintenance
- owner: investment focus — revenue, occupancy, portfolio performance

Routing rules:
- Property overview / occupancy → ask_portfolio_agent
- Repairs / vendors / work orders → ask_maintenance_agent
- Payments / late fees / revenue / rent roll → ask_finance_agent
- Lease renewals / expiry → ask_lease_agent
- Tenant contacts / notifications / payment reliability → ask_tenant_agent
- Policy documents / lease clauses → ask_document_agent
- Cross-domain questions → call MULTIPLE agents and synthesize their answers

After collecting specialist results, synthesize into ONE clear answer.
Cite actual figures. Do not repeat raw tool output — distill it.
If a specialist returned an error or no data, say so clearly.

propose_action rules (CRITICAL):
- ONLY call propose_action if the maintenance agent's response explicitly contains "Work order created (ID:" — meaning the work order was actually committed to the system
- NEVER call propose_action based on a recommendation, a description of what might happen, or an unconfirmed address
- If the maintenance agent returned an ERROR or said the property was not found, relay that to the user — do NOT propose an action"""


def get_orchestrator_prompt(role: str) -> str:
    return _ORCHESTRATOR_SYSTEM_PROMPT.format(role=role)
