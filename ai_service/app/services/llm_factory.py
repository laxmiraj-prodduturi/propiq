from __future__ import annotations

from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI

from ..config import settings
from ..logging_config import get_logger

logger = get_logger("llm_factory")

# ---------------------------------------------------------------------------
# Temperature presets — use the right one per call-site
# ---------------------------------------------------------------------------

TEMP_PRECISE  = 0.1   # deterministic extraction: intent classification, tool routing
TEMP_BALANCED = 0.3   # default: orchestrator synthesis, approval confirmations
TEMP_CREATIVE = 0.5   # generative: renewal letters, tenant notifications

# ---------------------------------------------------------------------------
# Shared OpenAI client settings
# ---------------------------------------------------------------------------

_MAX_RETRIES     = 3          # retried automatically by the OpenAI SDK (exp backoff)
_REQUEST_TIMEOUT = 60.0       # seconds per API call before raising TimeoutError
_MAX_TOKENS      = 2048       # cap to avoid runaway completions on specialist loops


def build_llm(
    *,
    temperature: float = TEMP_BALANCED,
    tools: list[BaseTool] | None = None,
    max_tokens: int = _MAX_TOKENS,
) -> ChatOpenAI | None:
    """
    Return a configured ChatOpenAI instance, or None if the API key is absent.

    Args:
        temperature: Sampling temperature. Use module-level TEMP_* constants.
        tools: If provided, the returned LLM has these tools bound via .bind_tools().
        max_tokens: Maximum completion tokens. Prevents runaway long responses.

    Caller is responsible for checking None before use:
        llm = build_llm(temperature=TEMP_BALANCED, tools=MY_TOOLS)
        if not llm:
            return "OpenAI not configured"
    """
    if not settings.OPENAI_API_KEY:
        return None

    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        temperature=temperature,
        api_key=settings.OPENAI_API_KEY,
        max_retries=_MAX_RETRIES,
        request_timeout=_REQUEST_TIMEOUT,
        max_tokens=max_tokens,
    )

    if tools:
        return llm.bind_tools(tools)
    return llm
