from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Intent:
    name: str
    description: str          # shown verbatim in the LLM classifier prompt
    keywords: tuple[str, ...] = field(default_factory=tuple)  # fallback keyword matching


# ---------------------------------------------------------------------------
# Single source of truth — add a new intent here only
# ---------------------------------------------------------------------------

INTENTS: list[Intent] = [
    Intent(
        name="portfolio_summary",
        description="questions about overall property portfolio, vacancies, occupancy, portfolio overview, rent summary",
        keywords=("portfolio", "vacant", "vacancy", "occupancy"),
    ),
    Intent(
        name="maintenance_workflow",
        description="maintenance requests, repairs, work orders, property issues, follow-up plans",
        keywords=("maintenance", "repair", "work order", "fix", "broken"),
    ),
    Intent(
        name="payment_workflow",
        description="rent payments, payment history, rent due dates, late fees, overdue balances, payment status",
        keywords=("payment", "rent", "late fee", "overdue", "due date"),
    ),
    Intent(
        name="lease_workflow",
        description="leases expiring soon, upcoming renewals, which leases expire this quarter/month/year, renewal planning",
        keywords=("expir", "renew", "upcoming lease", "quarter", "ending soon", "lease end"),
    ),
    Intent(
        name="tenant_directory",
        description="list tenants, tenant names, tenant contacts, tenant phone numbers, tenant emails, who are my tenants",
        keywords=("tenant name", "tenant contact", "tenant phone", "tenant email",
                  "list tenant", "all tenant", "who are my tenant", "phone number"),
    ),
    Intent(
        name="document_lookup",
        description="specific lease terms, pet policy, lease clauses, policy documents, notices, what my lease says about X",
        keywords=("lease", "pet policy", "policy", "notice", "document", "clause"),
    ),
    Intent(
        name="general_qa",
        description="any other question not covered by the above intents",
        keywords=(),
    ),
]

# ---------------------------------------------------------------------------
# Derived helpers — consumed by openai_client and graph
# ---------------------------------------------------------------------------

INTENT_NAMES: frozenset[str] = frozenset(i.name for i in INTENTS)

DEFAULT_INTENT = "general_qa"


def build_classifier_prompt() -> str:
    lines = "\n".join(f"- {i.name}: {i.description}" for i in INTENTS)
    return (
        "You are an intent classifier for a residential property management AI assistant.\n"
        "Classify the user message into exactly one of these intents:\n\n"
        f"{lines}\n\n"
        "Respond with ONLY the intent name — no explanation, no punctuation."
    )


def keyword_fallback(message: str) -> str:
    """Last-resort keyword matching when the LLM is unavailable."""
    lowered = message.lower()
    for intent in INTENTS:
        if intent.name == DEFAULT_INTENT:
            continue
        if any(kw in lowered for kw in intent.keywords):
            return intent.name
    return DEFAULT_INTENT
