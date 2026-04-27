from __future__ import annotations

import contextvars
from datetime import date

from langchain_core.tools import tool

from . import data_access
from ..backend_bridge import (
    create_work_order,
    notifications_for_user,
    send_notification,
    vendors_for_tenant,
)
from ..schemas import UserContext
from ..services.rag import retrieve_documents

# ---------------------------------------------------------------------------
# User context — set once before each graph run, consumed inside every tool
# ---------------------------------------------------------------------------

_user_ctx: contextvars.ContextVar[UserContext | None] = contextvars.ContextVar(
    "user_ctx", default=None
)


def set_user_context(user: UserContext) -> None:
    _user_ctx.set(user)


def _user() -> UserContext:
    user = _user_ctx.get()
    if user is None:
        raise RuntimeError("User context not set before tool call")
    return user


# ---------------------------------------------------------------------------
# Portfolio tools
# ---------------------------------------------------------------------------

@tool
def get_portfolio_summary() -> str:
    """
    Get a complete overview of the property portfolio.
    Returns occupancy breakdown, vacancy count, open maintenance, and rent collection summary.
    Use for broad questions like 'how is my portfolio?', 'show me an overview', or 'what is the occupancy rate?'.
    """
    user = _user()
    properties = data_access.list_properties(user)
    maintenance = data_access.get_open_maintenance(user)
    payments = data_access.get_payment_history(user)
    leases = data_access.get_active_leases(user)
    return " ".join([
        data_access.summarize_property_portfolio(properties),
        data_access.summarize_maintenance(maintenance),
        data_access.summarize_payments(payments, leases, user.role),
    ])


# ---------------------------------------------------------------------------
# Lease tools
# ---------------------------------------------------------------------------

@tool
def get_expiring_leases(days: int = 90) -> str:
    """
    Get leases expiring within the specified number of days.
    Use 30 for 'this month', 90 for 'this quarter', 180 for 'next 6 months', 365 for 'this year'.
    Returns expiring leases sorted by end date plus a full active-lease summary.
    """
    user = _user()
    expiring = data_access.get_expiring_leases(user, days=days)
    all_leases = data_access.get_active_leases(user)
    return "\n".join([
        data_access.summarize_expiring_leases(expiring, days=days),
        data_access.summarize_leases(all_leases),
    ])


@tool
def generate_renewal_offer(tenant_name: str, new_monthly_rent: float, lease_end_date: str, property_address: str = "") -> str:
    """
    Draft a lease renewal offer letter for a tenant.
    tenant_name: Full name of the tenant.
    new_monthly_rent: Proposed new monthly rent amount in dollars.
    lease_end_date: Current lease end date in YYYY-MM-DD format.
    property_address: Address of the property (include for a complete letter).
    """
    property_line = f" at {property_address}" if property_address else ""
    return (
        f"LEASE RENEWAL OFFER\n"
        f"Dear {tenant_name},\n\n"
        f"Your current lease{property_line} expires on {lease_end_date}. We would like to offer you a renewal "
        f"at the updated monthly rent of ${new_monthly_rent:,.0f}/month.\n\n"
        f"Please respond by {lease_end_date} to secure your renewal. "
        f"Contact your property manager to sign the updated agreement.\n\n"
        f"Thank you for being a valued resident."
    )


# ---------------------------------------------------------------------------
# Shared property listing tool
# ---------------------------------------------------------------------------

@tool
def list_properties() -> str:
    """
    List all properties in scope with their addresses and current status.
    Use this FIRST whenever you need a property address — never guess an address.
    """
    user = _user()
    properties = data_access.list_properties(user)
    if not properties:
        return "No properties found in scope."
    lines = [
        f"  • {p.get('address')}, {p.get('city')} — status: {p.get('status')} — rent: ${float(p.get('rent_amount', 0)):,.0f}/mo"
        for p in properties
    ]
    return f"{len(properties)} properties:\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# Maintenance tools
# ---------------------------------------------------------------------------

@tool
def get_maintenance_requests() -> str:
    """
    Get all open maintenance requests with urgency levels, categories, and property locations.
    Use for questions about repairs, work orders, what issues need attention, or maintenance status.
    """
    user = _user()
    requests = data_access.get_open_maintenance(user)
    return data_access.summarize_maintenance(requests)


@tool
def find_vendor(trade: str) -> str:
    """
    Find available vendors by their trade specialty.
    trade options: plumbing, electrical, hvac, general, cleaning, locksmith, pest_control, painting.
    Returns vendors ranked by rating with contact info.
    """
    user = _user()
    vendors = vendors_for_tenant(tenant_id=user.tenant_id, trade=trade)
    if not vendors:
        all_vendors = vendors_for_tenant(tenant_id=user.tenant_id)
        if not all_vendors:
            return f"No vendors found for trade '{trade}'."
        vendors = all_vendors[:3]

    lines = [
        f"  • {v.name} ({v.trade}) — rating: {v.rating}/5.0 — response: {v.response_time} — {v.phone} — {v.email}"
        for v in vendors
    ]
    return f"{len(vendors)} vendor(s) for '{trade}':\n" + "\n".join(lines)


def _fuzzy_match_property(query: str, properties: list[dict]) -> dict | None:
    """Match a user's partial/abbreviated property input to the best property."""
    q = query.lower().strip()

    # 1. Exact substring match
    for p in properties:
        full = f"{p.get('address', '')} {p.get('city', '')}".lower()
        if q in full:
            return p

    # 2. Word-prefix overlap: each query word must be a prefix of some address word
    q_words = q.split()
    best, best_score = None, 0
    for p in properties:
        full = f"{p.get('address', '')} {p.get('city', '')}".lower()
        a_words = full.split()
        score = sum(1 for qw in q_words if any(aw.startswith(qw) for aw in a_words))
        if score > best_score:
            best_score, best = score, p

    # Accept if we matched at least (n-1) of the query words (allows one typo/extra word)
    if best and best_score >= max(1, len(q_words) - 1):
        return best
    return None


@tool
def create_maintenance_work_order(
    property_name: str,
    category: str,
    description: str,
    urgency: str,
    assigned_vendor_name: str = "",
    estimated_cost: float = 0.0,
) -> str:
    """
    Create a new maintenance work order in the system.
    property_name: Any part of the property address — fuzzy matching is applied automatically.
    category: Type of issue — plumbing, electrical, hvac, general, appliance, structural, pest, cleaning.
    description: Detailed description of the issue.
    urgency: One of — low, medium, high, emergency.
    assigned_vendor_name: Name of the vendor to assign (optional).
    estimated_cost: Estimated repair cost in dollars (optional).
    """
    user = _user()
    properties = data_access.list_properties(user)
    matched = _fuzzy_match_property(property_name, properties)

    if not matched:
        available = [str(p.get("address", "")) for p in properties]
        return (
            f"ERROR: Property '{property_name}' not found. Work order NOT created. "
            f"You MUST ask the user to choose from the actual properties: {available}"
        )

    work_order_id = create_work_order(
        property_id=str(matched["id"]),
        tenant_user_id=user.user_id,
        property_name=str(matched.get("address", property_name)),
        tenant_name="",
        category=category,
        description=description,
        urgency=urgency,
        assigned_vendor=assigned_vendor_name,
        estimated_cost=estimated_cost,
    )

    return (
        f"Work order created (ID: {work_order_id}).\n"
        f"Property: {matched.get('address')}\n"
        f"Category: {category} | Urgency: {urgency}\n"
        f"Vendor: {assigned_vendor_name or 'unassigned'} | Est. cost: ${estimated_cost:,.0f}"
    )


# ---------------------------------------------------------------------------
# Finance tools
# ---------------------------------------------------------------------------

@tool
def get_payment_status() -> str:
    """
    Get the current rent payment status across all leases.
    Returns overdue payments, pending amounts, and recent payment history.
    Use for questions about rent collection, late payments, outstanding balances, or payment history.
    """
    user = _user()
    payments = data_access.get_payment_history(user)
    leases = data_access.get_active_leases(user)
    return data_access.summarize_payments(payments, leases, user.role)


@tool
def generate_rent_roll() -> str:
    """
    Generate a full rent roll — a table of all active leases with tenant, rent amount, and payment status.
    Use for 'show me the rent roll', 'what is total monthly rent income?', or revenue overview questions.
    """
    user = _user()
    leases = data_access.get_active_leases(user)
    payments = data_access.get_payment_history(user)

    if not leases:
        return "No active leases found."

    total_rent = sum(float(l["rent_amount"]) for l in leases)
    paid_this_month = sum(
        float(p["amount"]) for p in payments
        if p["status"] == "paid" and str(p["due_date"]).startswith(str(date.today())[:7])
    )
    late_count = sum(1 for p in payments if p["status"] == "late")

    lines = [
        f"  • {l['tenant_name']} — ${float(l['rent_amount']):,.0f}/mo — ends {l['end_date']} — status: {l['status']}"
        for l in leases
    ]
    header = (
        f"RENT ROLL — {len(leases)} active leases\n"
        f"Total monthly rent: ${total_rent:,.0f} | Paid this month: ${paid_this_month:,.0f} | Late: {late_count}\n"
    )
    return header + "\n".join(lines)


@tool
def calculate_late_fees() -> str:
    """
    Calculate outstanding late fees across all late payments.
    Returns a breakdown of which tenants owe late fees and the total amount outstanding.
    """
    user = _user()
    payments = data_access.get_payment_history(user)
    late = [p for p in payments if p["status"] == "late"]

    if not late:
        return "No outstanding late fees found."

    total_fees = sum(float(p.get("late_fee") or 0) for p in late)
    lines = [
        f"  • {p['tenant_name']} at {p['property_name']} — due {p['due_date']} — late fee: ${float(p.get('late_fee') or 0):,.0f}"
        for p in late
    ]
    return f"Outstanding late fees: ${total_fees:,.0f} across {len(late)} payment(s):\n" + "\n".join(lines)


@tool
def project_revenue(months: int = 12) -> str:
    """
    Project rental revenue for the next N months based on current active leases.
    months: Number of months to project (default 12).
    Accounts for leases that expire before the projection window ends.
    """
    user = _user()
    leases = data_access.get_active_leases(user)

    if not leases:
        return "No active leases to project revenue from."

    today = date.today()
    total_projected = 0.0
    monthly_run_rate = 0.0
    expiring_before_end = []

    for l in leases:
        rent = float(l["rent_amount"])
        end = date.fromisoformat(l["end_date"])
        months_remaining = max(0, (end.year - today.year) * 12 + (end.month - today.month))
        contributing_months = min(months, months_remaining)
        total_projected += rent * contributing_months
        monthly_run_rate += rent
        if months_remaining < months:
            expiring_before_end.append(f"{l['tenant_name']} (ends {l['end_date']})")

    return (
        f"{months}-month revenue projection: ${total_projected:,.0f}\n"
        f"Current monthly run-rate: ${monthly_run_rate:,.0f} from {len(leases)} leases.\n"
        + (f"Note: {len(expiring_before_end)} lease(s) expire before end of window: {', '.join(expiring_before_end)}" if expiring_before_end else "All leases are active for the full projection window.")
    )


# ---------------------------------------------------------------------------
# Tenant tools
# ---------------------------------------------------------------------------

@tool
def list_tenants() -> str:
    """
    List all tenants with their contact information: name, phone number, and email address.
    Use for 'who are my tenants?', 'show tenant directory', or contact lookup questions.
    """
    user = _user()
    tenants = data_access.list_tenants(user)
    return data_access.summarize_tenants(tenants, user.role)


@tool
def get_tenant_payment_history(tenant_name: str) -> str:
    """
    Get payment history for a specific tenant by name.
    tenant_name: Full or partial name of the tenant to look up.
    """
    user = _user()
    payments = data_access.get_payment_history(user)
    matched = [p for p in payments if tenant_name.lower() in p["tenant_name"].lower()]
    if not matched:
        return f"No payment records found for tenant matching '{tenant_name}'."
    late = sum(1 for p in matched if p["status"] == "late")
    paid = sum(1 for p in matched if p["status"] == "paid")
    lines = [
        f"  • {p['due_date']} — ${float(p['amount']):,.0f} — {p['status']}"
        + (f" (late fee: ${float(p.get('late_fee') or 0):,.0f})" if p.get("late_fee") else "")
        for p in matched[:10]
    ]
    return (
        f"Payment history for {tenant_name}: {len(matched)} records — {paid} paid, {late} late.\n"
        + "\n".join(lines)
    )


# ---------------------------------------------------------------------------
# Notification tools
# ---------------------------------------------------------------------------

@tool
def send_tenant_notification(tenant_name: str, subject: str, message: str) -> str:
    """
    Send an in-app notification to a specific tenant.
    tenant_name: Full or partial name of the tenant.
    subject: Short notification title (e.g. 'Rent Reminder', 'Maintenance Update').
    message: Body of the notification message.
    """
    user = _user()
    tenants = data_access.list_tenants(user)
    matched = [t for t in tenants if tenant_name.lower() in t["name"].lower()]
    if not matched:
        return f"No tenant found matching '{tenant_name}'."

    results = []
    for t in matched:
        notif_id = send_notification(
            user_id=str(t["id"]),
            type="ai",
            title=subject,
            body=message,
        )
        results.append(f"Notification sent to {t['name']} (ID: {notif_id})")
    return "\n".join(results)


@tool
def send_bulk_notification(subject: str, message: str, filter_role: str = "tenant") -> str:
    """
    Send an in-app notification to all tenants or all users in scope.
    subject: Notification title.
    message: Notification body.
    filter_role: Who to send to — 'tenant' (default) sends to all tenants in scope. Only 'tenant' is supported.
    """
    if filter_role != "tenant":
        return f"Unsupported filter_role '{filter_role}'. Only 'tenant' is supported for bulk notifications."

    user = _user()
    tenants = data_access.list_tenants(user)
    if not tenants:
        return "No recipients found."

    count = 0
    for t in tenants:
        send_notification(user_id=str(t["id"]), type="ai", title=subject, body=message)
        count += 1

    return f"Notification sent to {count} tenant(s): '{subject}'"


# ---------------------------------------------------------------------------
# Document tools
# ---------------------------------------------------------------------------

@tool
def search_documents(query: str) -> str:
    """
    Search lease documents, property policies, and notices for specific terms or clauses.
    Use for 'what does my lease say about pets?', 'find the late fee policy', or document lookup questions.
    query: The specific term or topic to search for.
    """
    user = _user()
    docs = retrieve_documents(query, user)
    if not docs:
        return "No matching documents found."
    return "\n".join(f"[{doc.title}]: {doc.snippet}" for doc in docs)


# ---------------------------------------------------------------------------
# HITL trigger tool
# ---------------------------------------------------------------------------

@tool
def propose_action(title: str, description: str) -> str:
    """
    Propose a high-impact action that requires manager or owner approval before execution.
    Use when recommending: vendor dispatch, mass tenant notifications, lease modifications, or
    any action with financial or legal consequences.
    title: Short action name (e.g. 'Dispatch Plumber to 456 Oak Ave').
    description: What will happen if approved, including any cost or impact.
    """
    return f"Proposed: {title}. {description} — awaiting approval."


# ---------------------------------------------------------------------------
# Tool registries — grouped by specialist agent
# ---------------------------------------------------------------------------

PORTFOLIO_TOOLS = [get_portfolio_summary]

MAINTENANCE_TOOLS = [
    list_properties,
    get_maintenance_requests,
    find_vendor,
    create_maintenance_work_order,
    propose_action,
]

FINANCE_TOOLS = [
    get_payment_status,
    generate_rent_roll,
    calculate_late_fees,
    project_revenue,
]

LEASE_TOOLS = [
    get_expiring_leases,
    generate_renewal_offer,
    list_tenants,
]

TENANT_TOOLS = [
    list_tenants,
    get_tenant_payment_history,
    send_tenant_notification,
    send_bulk_notification,
]

DOCUMENT_TOOLS = [
    search_documents,
    get_expiring_leases,
]

ALL_TOOLS = list({t.name: t for t in (
    PORTFOLIO_TOOLS
    + MAINTENANCE_TOOLS
    + FINANCE_TOOLS
    + LEASE_TOOLS
    + TENANT_TOOLS
    + DOCUMENT_TOOLS
)}.values())
