from __future__ import annotations

import logging

from ..config import settings

logger = logging.getLogger(__name__)


def _openai_client():
    if not settings.OPENAI_API_KEY:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=settings.OPENAI_API_KEY)
    except Exception as exc:
        logger.warning("OpenAI client init failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Support chat — lightweight help-desk Q&A, no user context or RAG required
# ---------------------------------------------------------------------------

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
    Generate a support agent reply. Falls back to keywords if OpenAI is unavailable.
    history: list of {"role": "user"|"assistant", "content": "..."} dicts.
    """
    client = _openai_client()
    if client:
        try:
            messages: list[dict] = [{"role": "system", "content": _SUPPORT_SYSTEM_PROMPT}]
            for h in history[-10:]:
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
