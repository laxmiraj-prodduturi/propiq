from __future__ import annotations

import logging

from ..config import settings

logger = logging.getLogger(__name__)

_INTENT_SYSTEM_PROMPT = """\
You are an intent classifier for a residential property management AI assistant.
Classify the user message into exactly one of these intents:

- portfolio_summary: questions about overall property portfolio, vacancies, occupancy, portfolio overview, rent summary
- maintenance_workflow: maintenance requests, repairs, work orders, property issues, follow-up plans
- payment_workflow: rent payments, payment history, rent due dates, late fees, payment status
- document_lookup: lease terms, policies, pet policy, lease documents, notices, what my lease says
- general_qa: any other question

Respond with ONLY the intent name — no explanation, no punctuation."""

_SYSTEM_PROMPT_TEMPLATE = """\
You are a helpful AI assistant for a residential property management platform.
Real property data has been retrieved and is provided below. Ground your answer in that data.
The user's role is: {role}.

Guidelines:
- Be concise and specific; cite actual figures from the context when available.
- Tenant: focus on their specific lease, payments, and property.
- Manager: focus on portfolio oversight and operational data.
- Owner: focus on investment metrics and portfolio performance.
- Do not fabricate data not present in the context."""


def _openai_client():
    """Return an OpenAI client if an API key is configured, otherwise None."""
    if not settings.OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=settings.OPENAI_API_KEY)
    except Exception as exc:
        logger.warning("OpenAI client init failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------

_VALID_INTENTS = frozenset(
    {"portfolio_summary", "maintenance_workflow", "payment_workflow", "document_lookup", "general_qa"}
)


def classify_intent(message: str, role: str) -> str:
    """Classify user intent via LLM, falling back to keyword matching."""
    client = _openai_client()
    if client:
        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": _INTENT_SYSTEM_PROMPT},
                    {"role": "user", "content": f"Role: {role}\nMessage: {message}"},
                ],
                temperature=0,
                max_tokens=20,
            )
            intent = response.choices[0].message.content.strip().lower()
            if intent in _VALID_INTENTS:
                return intent
        except Exception as exc:
            logger.warning("Intent classification LLM call failed: %s", exc)

    return _keyword_intent(message)


def _keyword_intent(message: str) -> str:
    lowered = message.lower()
    if any(t in lowered for t in ("portfolio", "vacant", "vacancy", "report", "occupancy")):
        return "portfolio_summary"
    if "maintenance" in lowered or "repair" in lowered or "work order" in lowered:
        return "maintenance_workflow"
    if any(t in lowered for t in ("payment", "rent", "late fee", "due")):
        return "payment_workflow"
    if any(t in lowered for t in ("lease", "pet", "policy", "notice", "document")):
        return "document_lookup"
    return "general_qa"


# ---------------------------------------------------------------------------
# Response generation
# ---------------------------------------------------------------------------

def compose_answer(
    *,
    role: str,
    user_message: str,
    context_summary: str,
    citations: list[str],
    tool_summary: str,
    approval_status: str | None = None,
) -> str:
    """Generate a grounded response via LLM, falling back to a template."""
    from .rag import format_citations

    client = _openai_client()
    citation_text = format_citations(citations)

    if client:
        try:
            user_parts: list[str] = [f"User question: {user_message}"]
            if context_summary:
                user_parts.append(f"\nRetrieved data context:\n{context_summary}")
            if tool_summary:
                user_parts.append(f"\n{tool_summary}")
            if approval_status:
                user_parts.append(f"\nNote: the requested action was {approval_status}.")

            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT_TEMPLATE.format(role=role)},
                    {"role": "user", "content": "\n".join(user_parts)},
                ],
                temperature=0.3,
                max_tokens=500,
            )
            answer = response.choices[0].message.content.strip()
            if citation_text:
                answer += f"\n\n{citation_text}"
            return answer
        except Exception as exc:
            logger.warning("Response generation LLM call failed: %s", exc)

    return _template_answer(
        role=role,
        user_message=user_message,
        context_summary=context_summary,
        tool_summary=tool_summary,
        citation_text=citation_text,
        approval_status=approval_status,
    )


def _template_answer(
    *,
    role: str,
    user_message: str,
    context_summary: str,
    tool_summary: str,
    citation_text: str,
    approval_status: str | None,
) -> str:
    if approval_status == "approved":
        preface = "The requested action has been approved and queued for execution."
    elif approval_status == "rejected":
        preface = "The requested action has been rejected. No changes will be made."
    else:
        preface = "Demo agent response (OpenAI not configured)."

    body = context_summary or _static_fallback(role=role, user_message=user_message)
    parts = [p for p in [preface, body, tool_summary.strip(), citation_text] if p]
    return " ".join(parts).strip()


_SUPPORT_SYSTEM_PROMPT = """\
You are a friendly support assistant for QuantumQuest Properties, a residential property management platform.
You help property owners, managers, and tenants with:
- How to use platform features (payments, leases, maintenance requests, documents)
- General property management concepts and best practices
- Explaining rental and lease terminology
- Answering general real estate and landlord/tenant questions

Keep answers concise (2-4 sentences unless more detail is needed).
For questions about specific account data (their payments, lease details, maintenance status),
advise them to use the main AI Assistant which has live access to their property data.
Do not fabricate specific figures or personal details."""


def support_answer(message: str, history: list[dict]) -> str:
    """
    Generate a support agent reply for a general question.
    history is a list of {"role": "user"|"assistant", "content": "..."} dicts.
    Falls back to a keyword-based reply if OpenAI is unavailable.
    """
    client = _openai_client()
    if client:
        try:
            messages: list[dict] = [{"role": "system", "content": _SUPPORT_SYSTEM_PROMPT}]
            for h in history[-10:]:  # keep last 10 turns for context window
                messages.append({"role": h["role"], "content": h["content"]})
            messages.append({"role": "user", "content": message})

            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=messages,
                temperature=0.4,
                max_tokens=300,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            logger.warning("Support chat LLM call failed: %s", exc)

    return _support_fallback(message)


def _support_fallback(message: str) -> str:
    lowered = message.lower()
    if any(t in lowered for t in ("payment", "rent", "pay", "due")):
        return "You can view and make payments in the Payments section. For specific payment status on your account, use the main AI Assistant which has live access to your data."
    if any(t in lowered for t in ("maintenance", "repair", "issue", "broken", "fix")):
        return "To submit a maintenance request, go to the Maintenance section and click '+ New Request'. You can track request status there too."
    if any(t in lowered for t in ("lease", "agreement", "contract", "term")):
        return "Your lease details are available in the Leases section. The AI Assistant can also answer specific questions about your lease terms."
    if any(t in lowered for t in ("document", "upload", "file")):
        return "Documents can be uploaded and viewed in the Documents section. Supported formats include PDF and common image formats."
    if any(t in lowered for t in ("login", "password", "account", "reset")):
        return "If you're having trouble logging in, use the forgot password option on the login page or contact your property manager."
    return "I'm here to help with platform navigation and general property questions. For account-specific data, use the main AI Assistant on the AI Assistant page."


def _static_fallback(*, role: str, user_message: str) -> str:
    lowered = user_message.lower()
    if "lease" in lowered:
        return "I can summarize lease clauses by combining stored lease records with matching uploaded lease documents."
    if "payment" in lowered or "rent" in lowered:
        return "I can combine payment history with rent status and explain follow-up actions for the property in question."
    if "maintenance" in lowered:
        return "I can triage maintenance requests, draft replies, and prepare approval-gated follow-up actions."
    if role == "owner":
        return "I can summarize occupancy, rent posture, and operational risks across your portfolio."
    return "I can answer property, lease, payment, and maintenance questions using tool calls and grounded document retrieval."
