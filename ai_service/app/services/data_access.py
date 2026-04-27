from __future__ import annotations

from datetime import date, timedelta

from ..backend_bridge import documents_for_user, leases_for_user, maintenance_for_user, payments_for_user, properties_for_user, tenants_for_user
from ..schemas import RetrievedDocument, UserContext


def _property_payload(property_item) -> dict[str, object]:
    return {
        "id": property_item.id,
        "name": property_item.name,
        "address": property_item.address,
        "city": property_item.city,
        "state": property_item.state,
        "zip": property_item.zip,
        "status": property_item.status,
        "bedrooms": property_item.bedrooms,
        "bathrooms": property_item.bathrooms,
        "rent_amount": property_item.rent_amount,
    }


def list_properties(user: UserContext) -> list[dict[str, object]]:
    properties = properties_for_user(user_id=user.user_id, role=user.role, tenant_id=user.tenant_id)
    return [_property_payload(property_item) for property_item in properties]


def get_active_leases(user: UserContext) -> list[dict[str, object]]:
    leases = leases_for_user(user_id=user.user_id, role=user.role, tenant_id=user.tenant_id)
    return [
        {
            "id": lease.id,
            "property_id": lease.property_id,
            "tenant_user_id": lease.tenant_user_id,
            "tenant_name": lease.tenant_name,
            "start_date": lease.start_date.isoformat(),
            "end_date": lease.end_date.isoformat(),
            "rent_amount": lease.rent_amount,
            "security_deposit": lease.security_deposit,
            "status": lease.status,
        }
        for lease in leases
        if lease.status == "active"
    ]


def get_payment_history(user: UserContext) -> list[dict[str, object]]:
    payments = payments_for_user(user_id=user.user_id, role=user.role, tenant_id=user.tenant_id)
    return [
        {
            "id": payment.id,
            "lease_id": payment.lease_id,
            "tenant_name": payment.tenant_name,
            "property_name": payment.property_name,
            "amount": payment.amount,
            "due_date": payment.due_date.isoformat(),
            "paid_date": payment.paid_date.isoformat() if payment.paid_date else None,
            "status": payment.status,
            "late_fee": payment.late_fee,
            "payment_method": payment.payment_method,
        }
        for payment in payments
    ]


def get_open_maintenance(user: UserContext) -> list[dict[str, object]]:
    requests = maintenance_for_user(user_id=user.user_id, role=user.role, tenant_id=user.tenant_id)
    return [
        {
            "id": request.id,
            "property_id": request.property_id,
            "property_name": request.property_name,
            "tenant_name": request.tenant_name,
            "category": request.category,
            "description": request.description,
            "urgency": request.urgency,
            "status": request.status,
            "assigned_vendor": request.assigned_vendor,
            "estimated_cost": request.estimated_cost,
            "created_at": request.created_at.isoformat() if request.created_at else "",
        }
        for request in requests
        if request.status not in {"resolved", "closed"}
    ]


def search_documents(query: str, user: UserContext) -> list[RetrievedDocument]:
    docs = documents_for_user(user_id=user.user_id, role=user.role, tenant_id=user.tenant_id)
    lowered = query.lower()
    keywords = []
    for token in lowered.split():
        normalized = token.strip(".,?!").rstrip("s")
        if len(normalized) >= 3 and normalized not in {"what", "when", "show", "with", "that", "this", "from", "have", "your"}:
            keywords.append(normalized)
    matches: list[RetrievedDocument] = []

    for doc in docs:
        haystack = " ".join(
            [
                doc.file_name or "",
                doc.document_type or "",
                doc.related_entity or "",
            ]
        ).lower()
        if lowered in haystack or any(token in haystack for token in keywords):
            matches.append(
                RetrievedDocument(
                    document_id=doc.id,
                    title=doc.file_name,
                    snippet=_document_snippet(doc.file_name, doc.document_type, doc.related_entity),
                    metadata={
                        "document_type": doc.document_type,
                        "related_entity": doc.related_entity,
                        "created_at": doc.created_at.isoformat() if doc.created_at else "",
                    },
                )
            )

    if matches:
        return matches[:3]

    if not any(term in lowered for term in ["lease", "pet", "policy", "document", "notice", "maintenance"]):
        return []

    return [
        RetrievedDocument(
            document_id=doc.id,
            title=doc.file_name,
            snippet=_document_snippet(doc.file_name, doc.document_type, doc.related_entity),
            metadata={
                "document_type": doc.document_type,
                "related_entity": doc.related_entity,
                "created_at": doc.created_at.isoformat() if doc.created_at else "",
            },
        )
        for doc in docs[:2]
    ]


def summarize_property_portfolio(properties: list[dict[str, object]]) -> str:
    if not properties:
        return "No residential homes were found for this user."
    occupied = sum(1 for property_item in properties if property_item["status"] == "occupied")
    vacant = sum(1 for property_item in properties if property_item["status"] == "vacant")
    maintenance = sum(1 for property_item in properties if property_item["status"] == "maintenance")
    average_rent = round(sum(float(property_item["rent_amount"]) for property_item in properties) / len(properties))
    addresses = ", ".join(str(property_item["address"]) for property_item in properties[:3])
    return (
        f"{len(properties)} homes found. {occupied} occupied, {vacant} vacant, {maintenance} in maintenance status. "
        f"Average asking rent is ${average_rent}. Sample homes: {addresses}."
    )


def summarize_payments(payments: list[dict[str, object]], leases: list[dict[str, object]], role: str) -> str:
    if role == "tenant" and leases:
        active_lease = leases[0]
        current_month_due = date.today().replace(day=1).isoformat()
        next_due_payment = next(
            (
                payment
                for payment in payments
                if payment["status"] in {"pending", "late"} or payment["due_date"] >= current_month_due
            ),
            None,
        )
        if next_due_payment:
            if next_due_payment["status"] == "late":
                return (
                    f"Your rent for {next_due_payment['property_name']} was due on {next_due_payment['due_date']} and is currently marked late. "
                    f"The current late fee on record is ${next_due_payment['late_fee']:.0f}."
                )
            return (
                f"Your active lease rent is ${active_lease['rent_amount']:.0f}. "
                f"The next recorded payment due date is {next_due_payment['due_date']} for {next_due_payment['property_name']}."
            )
        return (
            f"Your active lease rent is ${active_lease['rent_amount']:.0f}. "
            "No upcoming payment record was found, so rent should be treated as due under the lease schedule."
        )

    if not payments:
        return "No payment records were found for the current portfolio scope."

    overdue = [payment for payment in payments if payment["status"] == "late"]
    pending = [payment for payment in payments if payment["status"] == "pending"]
    return (
        f"{len(payments)} payment records found. {len(overdue)} late and {len(pending)} pending. "
        f"Most recent payment record: {payments[0]['property_name']} due {payments[0]['due_date']} with status {payments[0]['status']}."
    )


def list_tenants(user: UserContext) -> list[dict[str, object]]:
    users = tenants_for_user(user_id=user.user_id, role=user.role, tenant_id=user.tenant_id)

    # Build a map of tenant_user_id → property address via active leases
    leases = leases_for_user(user_id=user.user_id, role=user.role, tenant_id=user.tenant_id)
    properties = properties_for_user(user_id=user.user_id, role=user.role, tenant_id=user.tenant_id)
    prop_map = {p.id: f"{p.address}, {p.city}" for p in properties}
    tenant_property: dict[str, str] = {}
    for lease in leases:
        if lease.status == "active" and lease.tenant_user_id not in tenant_property:
            tenant_property[lease.tenant_user_id] = prop_map.get(lease.property_id, "Unknown property")

    return [
        {
            "id": u.id,
            "name": f"{u.first_name} {u.last_name}".strip(),
            "email": u.email,
            "phone": u.phone or "—",
            "property": tenant_property.get(u.id, "No active lease"),
        }
        for u in users
    ]


def summarize_tenants(tenants: list[dict[str, object]], role: str) -> str:
    if not tenants:
        return "No tenant records found in scope."
    if role == "tenant":
        t = tenants[0]
        return f"Your contact on file: {t['name']}, {t['email']}, {t['phone']}."
    lines = [
        f"  • {t['name']} — {t['phone']} — {t['email']} — property: {t.get('property', '—')}"
        for t in tenants
    ]
    return f"{len(tenants)} tenant(s):\n" + "\n".join(lines)


def get_expiring_leases(user: UserContext, days: int = 90) -> list[dict[str, object]]:
    all_leases = get_active_leases(user)
    cutoff = (date.today() + timedelta(days=days)).isoformat()
    today = date.today().isoformat()
    return [
        lease for lease in all_leases
        if lease["end_date"] <= cutoff and lease["end_date"] >= today
    ]


def summarize_leases(leases: list[dict[str, object]]) -> str:
    if not leases:
        return "No active lease records were found in scope."
    next_expiring = sorted(leases, key=lambda lease: lease["end_date"])[0]
    return (
        f"{len(leases)} active lease records found. "
        f"The earliest lease end date is {next_expiring['end_date']} for tenant {next_expiring['tenant_name']}."
    )


def summarize_expiring_leases(leases: list[dict[str, object]], days: int = 90) -> str:
    if not leases:
        return f"No active leases are expiring within the next {days} days."
    sorted_leases = sorted(leases, key=lambda lease: lease["end_date"])
    lines = [
        f"  • {lease['tenant_name']} — ends {lease['end_date']}, rent ${float(lease['rent_amount']):.0f}/mo"
        for lease in sorted_leases
    ]
    return (
        f"{len(leases)} lease(s) expiring within the next {days} days:\n"
        + "\n".join(lines)
    )


def summarize_maintenance(requests: list[dict[str, object]]) -> str:
    if not requests:
        return "No open maintenance requests were found."
    highest_urgency = sorted(
        requests,
        key=lambda request: ["low", "medium", "high", "emergency"].index(request["urgency"]),
        reverse=True,
    )[0]
    return (
        f"{len(requests)} open maintenance requests found. "
        f"Top priority is {highest_urgency['category']} at {highest_urgency['property_name']} with {highest_urgency['urgency']} urgency and status {highest_urgency['status']}."
    )


def _document_snippet(file_name: str, document_type: str, related_entity: str) -> str:
    lowered_name = file_name.lower()
    if "pet" in lowered_name:
        return "Pets require written owner approval and compliance with the lease addendum before occupancy with animals."
    if "lease" in lowered_name:
        return "Recurring rent is due on the first of each month and standard residential occupancy terms apply through the lease end date."
    if "maintenance" in lowered_name or document_type == "policy":
        return "Urgent issues should be triaged quickly, documented clearly, and routed through an approval step before external dispatch."
    return f"{document_type.title()} document related to {related_entity or 'the residential portfolio'}."
