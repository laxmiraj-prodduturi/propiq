# PropIQ — AI Service Technical Specification

> Learning reference for the `ai_service/` module. Covers architecture, data flow, every component, and how to extend the system.

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Request Lifecycle — End to End](#request-lifecycle--end-to-end)
4. [LangGraph State Machine](#langgraph-state-machine)
5. [Intent Classification Pipeline](#intent-classification-pipeline)
6. [Intent Registry](#intent-registry)
7. [Tool Execution & Intent Handlers](#tool-execution--intent-handlers)
8. [Data Access Layer](#data-access-layer)
9. [RAG — Retrieval-Augmented Generation](#rag--retrieval-augmented-generation)
10. [Human-in-the-Loop (HITL) Approval](#human-in-the-loop-hitl-approval)
11. [Response Generation](#response-generation)
12. [API Endpoints](#api-endpoints)
13. [State Object Reference](#state-object-reference)
14. [Schema Reference](#schema-reference)
15. [In-Memory Stores](#in-memory-stores)
16. [Configuration](#configuration)
17. [Adding a New Intent — Step-by-Step](#adding-a-new-intent--step-by-step)
18. [Fallback Behavior](#fallback-behavior)
19. [Multi-Tenancy & Role-Based Access](#multi-tenancy--role-based-access)
20. [Deployment Topology](#deployment-topology)

---

## Overview

The AI service is a standalone **FastAPI** application that acts as a conversational intelligence layer for the PropIQ property management platform. It receives a user message, classifies intent via OpenAI, retrieves relevant structured data and documents, runs a LangGraph state machine, and returns a grounded natural-language answer.

**Key design goals:**
- **Scalable intent pipeline** — adding a new capability requires touching exactly 3 places
- **Grounded answers** — LLM never makes up data; it only summarizes real DB records
- **Role-aware** — owners, managers, and tenants see different data scopes
- **Graceful degradation** — every LLM call has a keyword/template fallback

**Tech stack:**

| Component | Technology |
|---|---|
| Web framework | FastAPI |
| AI orchestration | LangGraph 0.2 |
| LLM + embeddings | OpenAI gpt-4.1-mini + text-embedding-3-small |
| Vector store | ChromaDB (persistent, cosine similarity) |
| State checkpointing | LangGraph MemorySaver (in-memory) |
| Database access | SQLAlchemy (shared models with backend) |
| Config | pydantic-settings |

---

## System Architecture

```
Browser / Frontend (React)
        │
        │  POST /api/ai/chat
        ▼
Backend (FastAPI :8000)
  - Authenticates JWT
  - Injects headers: x-user-id, x-user-role, x-tenant-id
  - Proxies to AI service
        │
        │  POST /chat   (headers carry user context)
        ▼
AI Service (FastAPI :8001)
  ┌─────────────────────────────────────────────────┐
  │  main.py — API endpoints                        │
  │  graph.py — LangGraph state machine             │
  │  services/                                      │
  │    intent_registry.py — intent definitions      │
  │    openai_client.py   — LLM calls               │
  │    data_access.py     — structured data helpers │
  │    rag.py             — ChromaDB vector search  │
  │    tools.py           — filter utilities        │
  │  backend_bridge.py    — DB queries (SQLAlchemy) │
  └─────────────────────────────────────────────────┘
        │
        ▼
  MySQL (shared with backend)
  ChromaDB (local persistent store)
```

The AI service shares the backend's SQLAlchemy models directly by inserting the repo root into `sys.path`. There is no REST call between the two services for data — it's a direct DB connection.

---

## Request Lifecycle — End to End

```
1. User types a message in the chat UI
2. Frontend  →  POST /api/ai/chat  { message, session_id }
3. Backend   →  validates JWT, injects x-user-id / x-user-role / x-tenant-id headers
4. Backend   →  POST http://ai-service:8001/chat  (same payload + headers)
5. AI service main.py:chat()
   a. Parse user context from headers → UserContext
   b. Create a new turn_id (UUID) for LangGraph threading
   c. Call run_agent_turn(session_id, message, user, turn_id)
      └─ LangGraph executes the graph nodes in order:
         intake → route_intent → retrieve_context → plan
         → tool_execution → policy_check → respond
         (if approval required: pauses before approval_gate)
   d. build_assistant_message(state) → AIMessageOut (with debug_info)
   e. Store messages in session_store
6. Response flows back:  AI service → Backend → Frontend
7. Frontend renders the message + agent steps panel (intent badge, tools, citations)
```

---

## LangGraph State Machine

The graph is the central orchestration mechanism. Each **node** is a pure function that receives the current `AgentState` and returns a partial dict of updates.

### Graph Topology

```
intake
  │
  ▼
route_intent          ← classify_intent() — OpenAI or keyword fallback
  │
  ▼
retrieve_context      ← ChromaDB semantic search (or keyword fallback)
  │
  ▼
plan                  ← decides if approval_required (maintenance + owner/manager)
  │
  ▼
tool_execution        ← dispatches to intent handler, fetches DB data
  │
  ▼
policy_check          ← strips approval if caller lacks permission
  │
  ▼
respond               ← compose_answer() — OpenAI or template fallback
  │
  ├── [approval_required=True]  → PAUSE (interrupt_before=approval_gate)
  │                               user calls /approve/{action_id}
  │                               then /resume/{action_id}
  │                               resumes → approval_gate → END
  │
  └── [approval_required=False] → END
```

### Node Descriptions

| Node | File | What it does |
|---|---|---|
| `intake` | `graph.py` | No-op entry point; adds "intake" to debug_steps |
| `route_intent` | `graph.py` | Calls `classify_intent()`, writes `intent` to state |
| `retrieve_context` | `graph.py` | Calls `retrieve_documents()`, writes `retrieved_docs` + `citations` |
| `plan` | `graph.py` | For `maintenance_workflow` + owner/manager role: sets `approval_required=True` and creates a `ProposedAction` |
| `tool_execution` | `graph.py` | Dispatches to the correct intent handler via `_INTENT_HANDLERS` dict |
| `policy_check` | `graph.py` | Removes approval gate if the user's role doesn't qualify |
| `respond` | `graph.py` | Calls `compose_answer()` to generate the final LLM response |
| `approval_gate` | `graph.py` | Re-runs `compose_answer()` with `approval_status` included in context |

### State Accumulation

Two state fields use `Annotated[list, add]` — they **accumulate** across nodes instead of being replaced:

```python
tool_calls:   Annotated[list[dict], add]   # each handler appends its calls
debug_steps:  Annotated[list[str], add]    # each node appends its name
```

All other fields are replaced on each node update.

### Checkpointing & Interrupts

```python
graph = _build_graph().compile(
    checkpointer=MemorySaver(),
    interrupt_before=["approval_gate"],
)
```

`MemorySaver` stores the full graph state in memory keyed by `thread_id` (= `turn_id`). When `approval_required=True`, the graph pauses **before** executing `approval_gate`. The paused state persists until `resume_agent_turn()` injects `approval_status` and resumes streaming.

---

## Intent Classification Pipeline

```
User message
     │
     ▼
classify_intent(message, role)
     │
     ├── [OPENAI_API_KEY present]
     │    └── OpenAI gpt-4.1-mini
     │         system: build_classifier_prompt()  ← auto-generated from registry
     │         user:   "Role: {role}\nMessage: {message}"
     │         temp=0, max_tokens=20
     │         → returns one intent name (e.g. "lease_workflow")
     │         → if unknown name returned → fall through to keyword fallback
     │
     └── [no API key / LLM error]
          └── keyword_fallback(message)
               → scan message.lower() for each intent's keywords tuple
               → first match wins; default = "general_qa"
```

**Why temperature=0?** Classification is a deterministic lookup — there's no value in variation. The model should always return the same intent for the same message.

**Why max_tokens=20?** The response is a single intent name (longest is `maintenance_workflow` = 20 chars). Short cap prevents rambling.

---

## Intent Registry

`ai_service/app/services/intent_registry.py` — **single source of truth** for all intents.

```python
@dataclass(frozen=True)
class Intent:
    name: str           # used as key in handler dict and returned by LLM
    description: str    # shown verbatim in the classifier system prompt
    keywords: tuple     # used by keyword_fallback when LLM is unavailable
```

### Registered Intents

| Intent | What triggers it | Data retrieved |
|---|---|---|
| `portfolio_summary` | "show my portfolio", "vacancy rate", "occupancy" | Properties, maintenance, payments, leases |
| `maintenance_workflow` | "maintenance", "repair", "work order" | Open maintenance requests, properties |
| `payment_workflow` | "rent", "payment", "late fee", "overdue" | Payment history, active leases |
| `lease_workflow` | "expiring", "renew", "quarter", "ending soon" | Expiring leases, all active leases |
| `tenant_directory` | "tenant names", "phone numbers", "list tenants" | User records via `tenants_for_user()` |
| `document_lookup` | "pet policy", "lease clause", "notice", "document" | ChromaDB RAG + active leases |
| `general_qa` | everything else | Same as `document_lookup` |

### Auto-generated Classifier Prompt

`build_classifier_prompt()` produces a prompt like:

```
You are an intent classifier for a residential property management AI assistant.
Classify the user message into exactly one of these intents:

- portfolio_summary: questions about overall property portfolio, vacancies, occupancy...
- maintenance_workflow: maintenance requests, repairs, work orders...
- payment_workflow: rent payments, payment history, rent due dates...
- lease_workflow: leases expiring soon, upcoming renewals...
- tenant_directory: list tenants, tenant names, tenant contacts...
- document_lookup: specific lease terms, pet policy, lease clauses...
- general_qa: any other question not covered by the above intents

Respond with ONLY the intent name — no explanation, no punctuation.
```

This is rebuilt at module import time, so it's always in sync with the registry.

---

## Tool Execution & Intent Handlers

`tool_execution_node` dispatches to a handler via a simple dict:

```python
_INTENT_HANDLERS = {
    "portfolio_summary":    _handle_portfolio_summary,
    "payment_workflow":     _handle_payment_workflow,
    "maintenance_workflow": _handle_maintenance_workflow,
    "tenant_directory":     _handle_tenant_directory,
    "lease_workflow":       _handle_lease_workflow,
    "document_lookup":      _handle_document_lookup,
    "general_qa":           _handle_document_lookup,
}
```

Each handler signature:
```python
def _handle_X(state: AgentState, user: UserContext) -> tuple[dict, list[dict]]:
    # Returns: (structured_context dict, list of tool_call records)
```

### Handler Details

**`_handle_lease_workflow`** — smart window detection:
```python
days = 30 if any(t in msg_lower for t in ("month", "30 day")) else 90
```
Parses "this month" → 30 days, otherwise defaults to 90 days (one quarter).

**`_handle_portfolio_summary`** — broadest query:
Runs `list_properties`, `get_open_maintenance`, `get_payment_history`, `get_active_leases` simultaneously and concatenates their summaries.

**`_handle_document_lookup`** — uses both RAG and DB:
Combines ChromaDB retrieved doc snippets with active lease summaries. Falls back gracefully if no docs found.

---

## Data Access Layer

### Two-layer architecture

```
Intent Handler
     │
     ▼
data_access.py          — domain functions returning plain dicts
     │                    (list_properties, get_active_leases, etc.)
     ▼
backend_bridge.py       — SQLAlchemy queries returning ORM model instances
                          (properties_for_user, leases_for_user, etc.)
     │
     ▼
MySQL (shared database)
```

**Why two layers?**  
`backend_bridge.py` owns the DB session and returns ORM objects. `data_access.py` converts them to plain dicts and adds domain logic (filtering, summarization). The handlers in `graph.py` only see dicts — no SQLAlchemy leakage.

### Summarizer Functions

Each `summarize_*` function converts a list of records into a compact English paragraph that gets passed directly to the LLM as context:

| Function | Output example |
|---|---|
| `summarize_property_portfolio` | "5 homes found. 3 occupied, 1 vacant, 1 in maintenance. Average asking rent is $2,400." |
| `summarize_payments` | "12 payment records found. 2 late and 1 pending. Most recent: 123 Main St due 2025-05-01 with status pending." |
| `summarize_expiring_leases` | "3 lease(s) expiring within the next 90 days:\n  • Alice Smith — ends 2025-06-15, rent $1,800/mo" |
| `summarize_tenants` | "4 tenant(s):\n  • Alice Smith — 555-0101 — alice@example.com" |
| `summarize_maintenance` | "3 open maintenance requests found. Top priority is plumbing at 123 Main St with high urgency." |

---

## RAG — Retrieval-Augmented Generation

RAG (Retrieval-Augmented Generation) is the technique of fetching relevant documents before calling the LLM, so answers are grounded in real data rather than hallucinated.

### Indexing (startup)

`init_vector_store()` runs once on the first call to `run_agent_turn()`:

```
all_documents() — fetches ALL documents from DB (no user filter)
     │
     ▼
For each document:
  text = document_type + file_name + related_entity + snippet
     │
     ▼
_embed(texts) — OpenAI text-embedding-3-small → 1536-dim float vectors
     │
     ▼
ChromaDB.upsert(ids, embeddings, documents, metadatas)
  metadata includes: tenant_id, document_type, related_entity, file_name
```

If OpenAI embeddings are unavailable, ChromaDB falls back to its built-in embedding (keyword-based).

### Retrieval (per query)

```
retrieve_documents(query, user)
     │
     ▼
_embed([query]) → query embedding
     │
     ▼
ChromaDB.query(
  query_embeddings=[...],
  n_results=3,
  where={"tenant_id": user.tenant_id}    ← tenant isolation
)
     │
     ▼
Filter: distance > 0.8 → skip (low relevance)
     │
     ▼
Returns list[RetrievedDocument] with title, snippet, metadata
     │
(fallback if ChromaDB fails or returns nothing)
     ▼
_keyword_search() → data_access.search_documents()
  → tokenizes query, checks file_name + document_type + related_entity
```

**Cosine distance** ranges 0–2. A distance of 0 = identical, 2 = opposite. The `> 0.8` threshold keeps only reasonably relevant results.

**Tenant isolation** is enforced at the ChromaDB query level via `where={"tenant_id": ...}`, so one tenant can never retrieve another tenant's documents through the vector store.

---

## Human-in-the-Loop (HITL) Approval

Certain actions require a human decision before the agent can proceed. The implementation uses LangGraph's `interrupt_before` mechanism.

### Flow

```
1. plan_node detects: intent=maintenance_workflow AND role in {owner, manager}
   → sets approval_required=True, creates ProposedAction with action_id

2. graph runs to respond_node, then PAUSES before approval_gate
   (graph.stream() returns, snapshot.next is non-empty)

3. main.py stores:
   approval_store[action_id] = {status: "pending", user_id, action_card}
   action_thread_map[action_id] = turn_id

4. Frontend receives the message with action_card (status="pending")
   → renders Approve / Reject buttons

5. User clicks Approve → POST /approve/{action_id}?approved=true
   → approval_store[action_id].status = "approved"

6. User (or frontend) calls POST /resume/{action_id}
   → graph.update_state({approval_status: "approved"})
   → graph.stream(None, ...) resumes from approval_gate
   → approval_gate_node re-runs compose_answer() with approval context
   → returns follow-up message

7. action_thread_map entry is cleaned up
```

### Why `interrupt_before` not `interrupt_after`?

`interrupt_before=["approval_gate"]` pauses the graph **before** the node runs. This means the node function has not been called yet. When resumed, it runs `approval_gate_node` with the updated `approval_status` injected via `update_state`. If we used `interrupt_after`, the node would have already run without the approval context.

---

## Response Generation

`compose_answer()` in `openai_client.py` assembles the final user-facing response.

### Input assembly

```python
user_parts = [
    f"User question: {user_message}",
    f"\nRetrieved data context:\n{context_summary}",   # from tool handlers
    f"\n{tool_summary}",                                # "Tools used: X, Y"
    f"\nNote: the requested action was {approval_status}.",  # if HITL
]
```

### System prompt (role-aware)

```
You are a helpful AI assistant for a residential property management platform.
Real property data has been retrieved and is provided below. Ground your answer in that data.
The user's role is: {role}.

Guidelines:
- Be concise and specific; cite actual figures from the context when available.
- Tenant: focus on their specific lease, payments, and property.
- Manager: focus on portfolio oversight and operational data.
- Owner: focus on investment metrics and portfolio performance.
- Do not fabricate data not present in the context.
```

**`temperature=0.3`** — slightly creative for readable prose, but still factual. Lower than typical chat (0.7) because we want the model to stay close to the provided data.

**`max_tokens=500`** — enough for a detailed answer with a list, not so long it becomes a report.

### Citations appended post-LLM

```python
if citation_text:
    answer += f"\n\n{citation_text}"
```

Citations are document titles from the RAG retrieval step, formatted as "Sources: lease_2024.pdf, pet_policy.pdf." They are appended after the LLM call, not injected into the prompt, to keep the model focused on the data summary.

---

## API Endpoints

All endpoints are in `ai_service/app/main.py`.

### `POST /chat`

Main conversational endpoint.

**Headers (injected by backend, not frontend):**
```
x-user-id:    <user UUID>
x-user-role:  owner | manager | tenant
x-tenant-id:  <tenant org UUID>
```

**Request:**
```json
{ "message": "what leases expire this quarter?", "session_id": "session_abc123" }
```

**Response:** `AIChatResponse`
```json
{
  "session_id": "session_abc123",
  "message": {
    "id": "msg_3f2a1b",
    "role": "assistant",
    "content": "3 leases expire in the next 90 days...",
    "created_at": "2025-04-21T10:00:00Z",
    "action_card": null,
    "debug_info": {
      "intent": "lease_workflow",
      "tools_called": ["get_expiring_leases", "get_active_leases"],
      "citations": [],
      "steps": ["intake", "route_intent", "retrieve_context", "plan",
                "tool_execution", "policy_check", "respond"]
    }
  }
}
```

### `GET /chat/history`

Returns all messages in a session, ordered by insertion.

**Query param:** `?session_id=session_abc123` (optional — defaults to user's last session)

### `POST /approve/{action_id}?approved=true|false`

Records the user's decision on a pending action. Does not resume the graph — only updates `approval_store`.

### `POST /resume/{action_id}`

Resumes the paused LangGraph thread. Returns the follow-up `AIChatResponse`.

Raises `409 Conflict` if the action is still `pending` (not yet approved or rejected).

### `POST /support/chat`

Lightweight help-desk chatbot. No user context headers required, no DB access, no RAG. Uses `_SUPPORT_SYSTEM_PROMPT` via OpenAI. Maintains last 10 turns of context window.

### `GET /health`

```json
{
  "status": "ok",
  "demo_mode": false,
  "openai_configured": true,
  "langgraph_installed": true
}
```

---

## State Object Reference

`ai_service/app/state.py` — `AgentState` is a `TypedDict`.

| Field | Type | Set by | Description |
|---|---|---|---|
| `session_id` | `str` | `main.py` | Conversation session identifier |
| `user_id` | `str` | `main.py` | Authenticated user UUID |
| `role` | `str` | `main.py` | `owner`, `manager`, or `tenant` |
| `tenant_id` | `str` | `main.py` | Tenant org UUID for multi-tenancy |
| `user_message` | `str` | `main.py` | Raw user input |
| `intent` | `str` | `route_intent_node` | Classified intent name |
| `retrieved_docs` | `list[dict]` | `retrieve_context_node` | RAG results |
| `structured_context` | `dict` | `tool_execution_node` | `{"summary": "..."}` from handler |
| `tool_calls` | `list[dict]` *(append)* | `tool_execution_node` | Log of tools called with summaries |
| `proposed_actions` | `list[dict]` | `plan_node` | HITL action proposals |
| `approval_required` | `bool` | `plan_node` / `policy_check_node` | Whether to pause for approval |
| `approval_status` | `str \| None` | `resume_agent_turn()` | `"approved"` or `"rejected"` |
| `final_response` | `str` | `respond_node` / `approval_gate_node` | LLM-generated answer |
| `citations` | `list[str]` | `retrieve_context_node` | Document titles |
| `debug_steps` | `list[str]` *(append)* | Every node | Execution trace |

---

## Schema Reference

`ai_service/app/schemas.py`

```
AIChatRequest          → { message, session_id? }
AIChatResponse         → { session_id, message: AIMessageOut }
AIMessageOut           → { id, role, content, created_at, action_card?, debug_info? }
AIActionCard           → { action_id, type, title, description, status }
AIDebugInfo            → { intent, tools_called[], citations[], steps[] }
AIChatHistoryResponse  → { session_id?, messages[] }
AIApprovalResponse     → { action_id, status, message }
UserContext            → { user_id, role, tenant_id }
RetrievedDocument      → { document_id, title, snippet, metadata{} }
ProposedAction         → { action_id, type, title, description, requires_approval }
SupportChatRequest     → { message, history: SupportMessage[] }
SupportChatResponse    → { response }
```

---

## In-Memory Stores

`ai_service/app/store.py` — all stores are plain Python `defaultdict` / `dict` objects. They do not persist across service restarts.

| Store | Type | Purpose |
|---|---|---|
| `session_store` | `defaultdict(list)` | `session_id → list[AIMessageOut]` — chat history |
| `session_owner` | `dict` | `session_id → user_id` — ownership check for history access |
| `user_last_session` | `dict` | `user_id → session_id` — default session lookup |
| `approval_store` | `dict` | `action_id → {status, user_id, action_card}` — pending HITL approvals |
| `action_thread_map` | `dict` | `action_id → turn_id` — links approval to LangGraph thread |

**Production note:** For multi-instance deployments, these would need to be replaced with Redis or a database-backed store.

---

## Configuration

`ai_service/app/config.py` — all values from `.env` file.

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | `None` | Required for LLM calls and embeddings; service degrades gracefully without it |
| `OPENAI_MODEL` | `gpt-4.1-mini` | Model for both intent classification and response generation |
| `OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Model for RAG vector embeddings |
| `DEMO_MODE` | `True` | Surfaced in `/health` response |
| `CHROMA_DB_PATH` | `ai_service/chroma_db` | Where ChromaDB persists its index |

---

## Adding a New Intent — Step-by-Step

This is the **3-place rule**:

### Step 1 — Register the intent

`ai_service/app/services/intent_registry.py`:
```python
Intent(
    name="financial_report",
    description="annual income summary, revenue by property, financial performance overview",
    keywords=("revenue", "income", "annual", "financial report"),
),
```

The classifier system prompt and `INTENT_NAMES` set both update automatically.

### Step 2 — Write the handler

`ai_service/app/graph.py`:
```python
def _handle_financial_report(state: AgentState, user: UserContext) -> tuple[dict, list[dict]]:
    properties = list_properties(user)
    payments = get_payment_history(user)
    leases = get_active_leases(user)
    # build a summary string
    total_rent = sum(float(l["rent_amount"]) for l in leases)
    summary = f"Annual projected rent income: ${total_rent * 12:,.0f} across {len(properties)} properties."
    return (
        {"summary": summary},
        [{"name": "financial_summary", "input": {}, "output_summary": summary}],
    )
```

### Step 3 — Register in the dispatch dict

`ai_service/app/graph.py`:
```python
_INTENT_HANDLERS = {
    ...
    "financial_report": _handle_financial_report,
}
```

That's it. No changes to the API, graph topology, state, or schemas.

---

## Fallback Behavior

The service is designed to work at every level of degradation:

| Condition | Fallback |
|---|---|
| No `OPENAI_API_KEY` | `classify_intent` → keyword scan; `compose_answer` → template string |
| OpenAI API error | Same as above — `try/except` wraps every LLM call |
| ChromaDB unavailable | `retrieve_documents` → `_keyword_search` → `data_access.search_documents` |
| DB query error | Every `backend_bridge.py` function catches all exceptions and returns `[]` |
| Unknown intent returned by LLM | Falls through to `keyword_fallback`, defaults to `general_qa` |
| No documents in ChromaDB | `retrieve_documents` returns `[]`, handlers skip citations gracefully |

---

## Multi-Tenancy & Role-Based Access

Every DB query in `backend_bridge.py` is scoped by `(user_id, role, tenant_id)`:

| Role | Properties visible | Leases visible | Payments visible | Tenants visible |
|---|---|---|---|---|
| `owner` | Only properties where `owner_id = user_id` | Leases on own properties | Payments on own properties | Tenants with active leases on own properties |
| `manager` | All properties in `tenant_id` org | All leases in org | All payments in org | All users with role=tenant in org |
| `tenant` | Only properties with their active lease | Only own lease | Only own payments | Only themselves |

The AI service never receives scoped data by accident — `UserContext` is required for every tool call, and all bridge functions enforce scoping before querying MySQL.

---

## Deployment Topology

```
EC2 t4g.medium (ARM / Ubuntu 24.04)
  ├── Nginx :80         — serves built React app, proxies /api/* to :8000
  ├── propiq-backend    — FastAPI :8000 (systemd, uvicorn)
  ├── propiq-ai         — FastAPI :8001 (systemd, uvicorn)
  ├── MySQL :3306       — shared database
  ├── Redis :6379       — (reserved for future use)
  └── propiq-idle-shutdown.timer
        — runs every 5 min starting 10 min after boot
        — checks last Nginx access log timestamp
        — shuts down instance after 60 min of no HTTP traffic
```

**Scripts:**
- `scripts/setup-instance.sh` — provision EC2 once (key, SG, packages, venvs, systemd)
- `scripts/deploy.sh` — sync code, restart services (auto-starts stopped instance)
- `scripts/db-migrate.sh` — alembic migrations, seeding, rollback
