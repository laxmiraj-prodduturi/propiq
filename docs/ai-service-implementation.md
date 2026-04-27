# AI Service — Implementation Reference

## Overview

PropIQ AI is a **multi-agent property management assistant** built on LangGraph and OpenAI. It uses a supervisor pattern: one orchestrator agent receives every user request and delegates work to 6 domain-specific specialist agents, each with real-data tools. The system is role-aware (tenant / manager / owner), conversation-aware across turns, and supports human-in-the-loop (HITL) approval for high-impact actions.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (React)                                               │
│  Chat UI  →  Approve / Reject card  →  Follow-up message       │
└─────────────────┬───────────────────────────────────────────────┘
                  │ REST (JWT auth)
┌─────────────────▼───────────────────────────────────────────────┐
│  Backend (FastAPI :8000)                                        │
│  /api/v1/ai/chat  →  /api/v1/ai/approve/{id}                   │
│  Proxy + DB persistence (MySQL via SQLAlchemy)                  │
└─────────────────┬───────────────────────────────────────────────┘
                  │ HTTP + x-user-* headers
┌─────────────────▼───────────────────────────────────────────────┐
│  AI Service (FastAPI :8100)                                     │
│                                                                 │
│   LangGraph Orchestrator Graph                                  │
│   ┌──────────┐   tool_calls?   ┌──────────────────┐            │
│   │ agent    │ ─────────────→  │ tool_executor    │            │
│   │ node     │ ←────────────── │ node             │            │
│   └──────────┘   ToolMessages  └──────────────────┘            │
│        │ no tool_calls → END                                    │
│                                                                 │
│   Each orchestrator tool wraps a specialist mini-agent          │
│   (its own LLM + tools ReAct loop)                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Component | Technology | Version |
|---|---|---|
| Agent framework | LangGraph | 1.1.9 |
| LLM | OpenAI GPT-4.1-mini | — |
| Orchestration | LangChain | 1.2.15 |
| Agent memory | LangGraph SQLite checkpointer | 3.0.3 |
| Vector search | ChromaDB + OpenAI embeddings | 0.5.5 |
| AI service API | FastAPI + Uvicorn | 0.111.0 |
| Backend API | FastAPI + SQLAlchemy | — |
| Database | MySQL | — |
| Logging | Python `logging` + RotatingFileHandler | — |

---

## File Map

```
ai_service/
├── app/
│   ├── main.py               # FastAPI app: /chat, /approve, /support/chat
│   ├── graph.py              # LangGraph graph, nodes, routing, confirmation generator
│   ├── state.py              # AgentState (extends MessagesState)
│   ├── schemas.py            # Pydantic models for API I/O
│   ├── config.py             # Settings (OpenAI key, model, paths)
│   ├── checkpointer.py       # SQLite-backed persistent memory
│   ├── store.py              # In-memory + file-persisted session/approval state
│   ├── logging_config.py     # Rotating file logger + console logger
│   ├── backend_bridge.py     # Write operations: work orders, notifications
│   ├── agents/
│   │   ├── base.py           # run_specialist() — shared ReAct loop for specialists
│   │   ├── orchestrator.py   # 7 orchestrator tools + system prompt
│   │   ├── portfolio_agent.py
│   │   ├── maintenance_agent.py
│   │   ├── finance_agent.py
│   │   ├── lease_agent.py
│   │   ├── tenant_agent.py
│   │   └── document_agent.py
│   └── services/
│       ├── agent_tools.py    # 16 @tool functions backed by real DB queries
│       ├── data_access.py    # Read-only DB accessors (properties, leases, payments, tenants)
│       ├── rag.py            # ChromaDB vector store + OpenAI embeddings
│       └── openai_client.py  # Support chat (lightweight Q&A, no tools)
└── logs/
    └── ai_service.log        # Rotating log file (10 MB × 5 backups)
```

---

## LangGraph Graph

### State — `AgentState`

Extends LangGraph's `MessagesState` which provides `messages: Annotated[list, add_messages]` with automatic message accumulation.

```python
class AgentState(MessagesState):
    session_id: str
    user_id: str
    role: str                          # tenant | manager | owner
    tenant_id: str
    citations: Annotated[list[str], add]
    approval_required: bool
    approval_status: str | None        # None | "approved" | "rejected"
    proposed_actions: list[dict]
    debug_steps: Annotated[list[str], add]
```

### Nodes

| Node | Function | Responsibility |
|---|---|---|
| `agent` | `agent_node` | Calls orchestrator LLM; detects `propose_action` calls; sets `approval_required` |
| `tools` | `tool_executor_node` | Executes all tool calls in the last message; appends `ToolMessage` results |

### Routing — `_route_agent`

```python
def _route_agent(state):
    last = state["messages"][-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"   # keep looping
    return END           # LLM is done
```

The graph runs until the LLM produces a response with no tool calls.

### Execution Loop (single turn)

```
agent_node → (tool_calls?) → tool_executor_node → agent_node → ...
                                                       ↓ (no tool_calls)
                                                      END
```

State messages accumulate every pass — the LLM always sees the full conversation history.

---

## Supervisor Pattern — Orchestrator + Specialists

### Orchestrator Tools

The orchestrator LLM has 7 tools. Six wrap specialist agents; one triggers HITL.

```python
ORCHESTRATOR_TOOLS = [
    ask_portfolio_agent,    # occupancy, vacancy, portfolio overview
    ask_maintenance_agent,  # work orders, vendors, urgency triage
    ask_finance_agent,      # payments, rent roll, late fees, revenue
    ask_lease_agent,        # expiring leases, renewal offers
    ask_tenant_agent,       # contacts, payment history, notifications
    ask_document_agent,     # policy search, lease clause lookup
    propose_action,         # HITL trigger for high-impact actions
]
```

Each `ask_*_agent` tool is:

```python
@tool
def ask_maintenance_agent(query: str) -> str:
    return maintenance_agent.run(query)   # runs a full specialist LLM loop
```

### Specialist Mini-Agent Loop — `run_specialist()`

```python
def run_specialist(*, name, system_prompt, tools, query, max_iterations=5):
    llm = ChatOpenAI(...).bind_tools(tools)
    messages = [SystemMessage(system_prompt), HumanMessage(query)]
    for _ in range(max_iterations):
        response = llm.invoke(messages)
        messages.append(response)
        if not response.tool_calls:
            return response.content        # final answer as plain string
        for tc in response.tool_calls:
            result = tool_map[tc["name"]].invoke(tc["args"])
            messages.append(ToolMessage(result, tc["id"]))
```

Each specialist has its own system prompt and tool set. It runs an independent ReAct loop and returns a plain-text summary back to the orchestrator.

---

## Domain Agents & Tools

### Portfolio Agent
| Tool | What it does |
|---|---|
| `get_portfolio_summary` | Properties, occupancy, maintenance summary, payment summary |

### Maintenance Agent
| Tool | What it does |
|---|---|
| `list_properties` | All properties with addresses (used for address validation) |
| `get_maintenance_requests` | Open work orders with urgency and category |
| `find_vendor` | Vendors filtered by trade, ranked by rating |
| `create_maintenance_work_order` | Inserts new work order into DB (fuzzy address match) |
| `propose_action` | Signals orchestrator that HITL approval is needed |

**Property matching** — `_fuzzy_match_property()` uses word-prefix overlap scoring so partial inputs like "4053 Penny ter" reliably match "4053 Penny Terrace, Fremont" without LLM guessing.

### Finance Agent
| Tool | What it does |
|---|---|
| `get_payment_status` | Overdue, pending, recent payment summary |
| `generate_rent_roll` | All active leases with rent amounts and status |
| `calculate_late_fees` | Outstanding late fees by tenant |
| `project_revenue` | N-month revenue projection from active leases |

### Lease Agent
| Tool | What it does |
|---|---|
| `get_expiring_leases` | Leases expiring within N days |
| `generate_renewal_offer` | Draft renewal letter for a tenant |

### Tenant Agent
| Tool | What it does |
|---|---|
| `list_tenants` | All tenants with phone, email, **and property address** (joined from active lease) |
| `get_tenant_payment_history` | Payment records for a named tenant |
| `send_tenant_notification` | In-app notification to a specific tenant |
| `send_bulk_notification` | In-app notification to all tenants in scope |

### Document Agent
| Tool | What it does |
|---|---|
| `search_documents` | ChromaDB semantic search over lease documents and policies |
| `get_expiring_leases` | Used to cross-reference lease document context |

---

## Human-in-the-Loop (HITL) Approval

When the maintenance agent calls `propose_action`, the orchestrator detects it in `agent_node` and sets `approval_required = True` and records the action in `proposed_actions`. The graph ends normally — no interrupt.

The action card is returned to the frontend via `AIMessageOut.action_card`. The user sees Approve / Reject buttons.

### Approve Flow (single call, no resume)

```
Frontend: POST /ai/approve/{action_id}?approved=true
    │
    ▼ Backend (routers/ai.py)
    Updates DB record (AIApproval)
    Proxies to AI service /approve
    │
    ▼ AI Service (main.py)
    Calls _run_post_approval_actions():
      - Sends in-app notification to all tenants on the property
      - Sends confirmation notification to the approver (manager)
    Calls generate_approval_confirmation():
      - Direct LLM call (no graph state needed)
      - Generates professional dispatch confirmation text
    Returns AIApprovalResponse { status, follow_up: AIMessageOut }
    │
    ▼ Backend
    Saves follow_up message to session DB
    Returns to frontend
    │
    ▼ Frontend
    Adds follow_up to chat — done
```

No `/resume` endpoint, no paused graph state. The confirmation is generated directly in the approve call.

---

## Conversation Continuity

Each chat request passes the last 20 session messages as LangChain message objects into the new graph run's initial state:

```python
history = []
for msg in session_store.get(session_id, [])[-20:]:
    if msg.role == "user":
        history.append(HumanMessage(content=msg.content))
    elif msg.role == "assistant":
        history.append(AIMessage(content=msg.content))

initial_state["messages"] = history + [HumanMessage(content=new_message)]
```

This gives the LLM full context without needing the LangGraph checkpointer for turn-to-turn memory.

---

## Persistent Storage

| Store | Type | Contents |
|---|---|---|
| `agent_memory.db` | SQLite (LangGraph checkpointer) | Full graph state per thread_id |
| `action_thread_map.json` | JSON file (`_PersistentThreadMap`) | action_id → turn_id mapping |
| MySQL | Relational DB | All domain data + session/approval records |
| `chroma_db/` | ChromaDB | Document embeddings for semantic search |
| `logs/ai_service.log` | Rotating file (10 MB × 5) | Request, tool call, reply, error logs |

---

## User Context Propagation

User identity flows from JWT → backend → AI service as HTTP headers:

```
x-user-id: u2
x-user-role: manager
x-tenant-id: t1
```

Inside the AI service, `UserContext` is stored in a `contextvars.ContextVar` before each graph run and consumed inside tool functions — no threading through parameters:

```python
_user_ctx: ContextVar[UserContext] = ContextVar("user_ctx", default=None)

def set_user_context(user: UserContext): _user_ctx.set(user)
def _user() -> UserContext: return _user_ctx.get()  # used inside every @tool
```

---

## Role-Based Access

| Role | Scope |
|---|---|
| `tenant` | Own lease, own property, own payments only |
| `manager` | All properties within their `tenant_id` org |
| `owner` | All properties where `owner_id` matches their user ID |

Every DB query in `backend_bridge.py` and `data_access.py` applies role filters. The orchestrator prompt also receives the role and adjusts its framing (investment metrics for owner, operations focus for manager).

---

## Logging

Configured in `logging_config.py`, initialized at FastAPI startup.

```
ai_service/logs/ai_service.log   ← 10 MB rotating, 5 backups
```

| Level | What is logged |
|---|---|
| `INFO` | Every chat request (user, role, session, first 120 chars) |
| `INFO` | Every chat reply (first 200 chars, action_card bool) |
| `INFO` | Every tool call name + args |
| `INFO` | Every approve action |
| `DEBUG` | Tool result (first 300 chars) |
| `DEBUG` | Registered orchestrator tools at startup |
| `ERROR` | Tool exceptions with full traceback |

Third-party loggers (`openai`, `langchain`, `httpx`, `chromadb`) are silenced to WARNING.

---

## API Endpoints

### AI Service (port 8100)

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness check, reports OpenAI + LangGraph status |
| `POST` | `/chat` | Run one agent turn; returns message + optional action_card |
| `GET` | `/chat/history` | Return session message history |
| `POST` | `/approve/{action_id}` | Record approval decision + generate confirmation |
| `POST` | `/support/chat` | Lightweight LLM Q&A, no tools or user context |

### Backend Proxy (port 8000 → 8100)

| Method | Path | Auth |
|---|---|---|
| `POST` | `/api/v1/ai/chat` | JWT required |
| `GET` | `/api/v1/ai/chat/history` | JWT required |
| `POST` | `/api/v1/ai/approve/{action_id}` | JWT, manager/owner only |

---

## Key Design Decisions

**Supervisor pattern over flat multi-agent** — the orchestrator delegates via tool calls rather than a peer graph. Adding a new domain agent is one new file + one new orchestrator tool, with no graph changes.

**Manual specialist loop instead of nested LangGraph subgraphs** — specialists return a plain string to the orchestrator. This avoids nested graph complexity while still giving each specialist its own LLM+tools reasoning loop.

**Approve-and-confirm in one call** — the original interrupt/resume pattern required preserving paused graph state across service restarts. Replacing it with a direct LLM call in `/approve` eliminates in-memory state dependency and makes the flow reliable across restarts.

**Fuzzy property matching in the tool, not the LLM** — word-prefix overlap scoring in `_fuzzy_match_property()` resolves partial addresses deterministically. The specialist prompt tells the LLM to trust the tool rather than validate addresses in its own reasoning, preventing the "please confirm the address" loop.

**Property field in tenant listing** — each tenant record is joined to their active lease and property address at the data layer. This prevents the LLM from hallucinating property associations when the data is unambiguous.
