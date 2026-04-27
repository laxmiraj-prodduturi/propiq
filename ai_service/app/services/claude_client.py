from __future__ import annotations

import logging
from collections.abc import Iterator

from ..config import settings

logger = logging.getLogger(__name__)

# Intent values the classifier may return
_VALID_INTENTS = frozenset(
    {"portfolio_summary", "maintenance_workflow", "payment_workflow", "document_lookup", "general_qa"}
)

# ---------------------------------------------------------------------------
# Stable prompts — marked for prompt caching (ephemeral, 5-min TTL)
# ---------------------------------------------------------------------------

_INTENT_SYSTEM_PROMPT = """\
You are an intent classifier for a residential property management AI assistant.
Classify the user message into exactly one of these intents:

- portfolio_summary: questions about overall property portfolio, vacancies, occupancy, portfolio overview, rent summary
- maintenance_workflow: maintenance requests, repairs, work orders, property issues, follow-up plans
- payment_workflow: rent payments, payment history, rent due dates, late fees, payment status
- document_lookup: lease terms, policies, pet policy, lease documents, notices, what my lease says
- general_qa: any other question

Respond with ONLY the intent name — no explanation, no punctuation."""

_ANSWER_SYSTEM_PROMPT = """\
You are a helpful AI assistant for a residential property management platform.
Real property data has been retrieved and is provided below. Ground your answer in that data.

Guidelines:
- Be concise and specific; cite actual figures from the context when available.
- Tenant: focus on their specific lease, payments, and property.
- Manager: focus on portfolio oversight and operational data.
- Owner: focus on investment metrics and portfolio performance.
- Do not fabricate data not present in the context.
- When relevant, include actionable next steps for the user."""

_SUPPORT_SYSTEM_PROMPT = """\
You are a friendly support assistant for a residential property management platform.
You help property owners, managers, and tenants with:
- How to use platform features (payments, leases, maintenance requests, documents)
- General property management concepts and best practices
- Explaining rental and lease terminology
- Answering general real estate and landlord/tenant questions

Keep answers concise (2-4 sentences unless more detail is needed).
For questions about specific account data (their payments, lease details, maintenance status),
advise them to use the main AI Assistant which has live access to their property data.
Do not fabricate specific figures or personal details."""


# ---------------------------------------------------------------------------
# Client factory
# ---------------------------------------------------------------------------

def _client():
    if not settings.ANTHROPIC_API_KEY:
        return None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    except Exception as exc:
        logger.warning("Anthropic client init failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Intent classification — no thinking needed, fast and cheap
# ---------------------------------------------------------------------------

def classify_intent(message: str, role: str) -> str:
    client = _client()
    if client:
        try:
            response = client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=20,
                system=[
                    {
                        "type": "text",
                        "text": _INTENT_SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[
                    {"role": "user", "content": f"Role: {role}\nMessage: {message}"}
                ],
            )
            intent = response.content[0].text.strip().lower()
            if intent in _VALID_INTENTS:
                return intent
        except Exception as exc:
            logger.warning("Claude intent classification failed: %s", exc)

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
# Grounded response generation — with extended thinking for complex queries
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
    from .rag import format_citations

    client = _client()
    citation_text = format_citations(citations)

    if client:
        try:
            user_parts: list[str] = [f"User role: {role}\nUser question: {user_message}"]
            if context_summary:
                user_parts.append(f"\nRetrieved data context:\n{context_summary}")
            if tool_summary:
                user_parts.append(f"\n{tool_summary}")
            if approval_status:
                user_parts.append(f"\nNote: the requested action was {approval_status}.")

            response = client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=8000,
                thinking={
                    "type": "enabled",
                    "budget_tokens": 5000,
                },
                system=[
                    {
                        "type": "text",
                        "text": _ANSWER_SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[
                    {"role": "user", "content": "\n".join(user_parts)}
                ],
            )

            # Extract text blocks only (skip thinking blocks)
            answer = "\n".join(
                block.text
                for block in response.content
                if block.type == "text"
            ).strip()

            if citation_text:
                answer += f"\n\n{citation_text}"
            return answer
        except Exception as exc:
            logger.warning("Claude response generation failed: %s", exc)

    return _template_answer(
        role=role,
        user_message=user_message,
        context_summary=context_summary,
        tool_summary=tool_summary,
        citation_text=citation_text,
        approval_status=approval_status,
    )


def compose_answer_stream(
    *,
    role: str,
    user_message: str,
    context_summary: str,
    citations: list[str],
    tool_summary: str,
    approval_status: str | None = None,
) -> Iterator[str]:
    """Yield text chunks via streaming. Falls back to a single-shot response."""
    from .rag import format_citations

    client = _client()
    citation_text = format_citations(citations)

    if client:
        try:
            user_parts: list[str] = [f"User role: {role}\nUser question: {user_message}"]
            if context_summary:
                user_parts.append(f"\nRetrieved data context:\n{context_summary}")
            if tool_summary:
                user_parts.append(f"\n{tool_summary}")
            if approval_status:
                user_parts.append(f"\nNote: the requested action was {approval_status}.")

            # Extended thinking blocks are not streamable in all SDK versions;
            # we stream text only and collect thinking internally.
            with client.messages.stream(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=8000,
                thinking={
                    "type": "enabled",
                    "budget_tokens": 5000,
                },
                system=[
                    {
                        "type": "text",
                        "text": _ANSWER_SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[
                    {"role": "user", "content": "\n".join(user_parts)}
                ],
            ) as stream:
                for text in stream.text_stream:
                    yield text

            if citation_text:
                yield f"\n\n{citation_text}"
            return
        except Exception as exc:
            logger.warning("Claude streaming failed, falling back: %s", exc)

    # Fallback: yield the full template answer as one chunk
    yield _template_answer(
        role=role,
        user_message=user_message,
        context_summary=context_summary,
        tool_summary=tool_summary,
        citation_text=citation_text,
        approval_status=approval_status,
    )


# ---------------------------------------------------------------------------
# Support chat — general platform Q&A, no property data context
# ---------------------------------------------------------------------------

def support_answer(message: str, history: list[dict]) -> str:
    client = _client()
    if client:
        try:
            messages: list[dict] = []
            for h in history[-10:]:
                messages.append({"role": h["role"], "content": h["content"]})
            messages.append({"role": "user", "content": message})

            response = client.messages.create(
                model=settings.ANTHROPIC_MODEL,
                max_tokens=1024,
                system=[
                    {
                        "type": "text",
                        "text": _SUPPORT_SYSTEM_PROMPT,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=messages,
            )
            return response.content[0].text.strip()
        except Exception as exc:
            logger.warning("Claude support chat failed: %s", exc)

    return _support_fallback(message)


# ---------------------------------------------------------------------------
# Fallbacks
# ---------------------------------------------------------------------------

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
        preface = "Demo agent response (Claude API not configured)."

    body = context_summary or _static_fallback(role=role, user_message=user_message)
    parts = [p for p in [preface, body, tool_summary.strip(), citation_text] if p]
    return " ".join(parts).strip()


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
