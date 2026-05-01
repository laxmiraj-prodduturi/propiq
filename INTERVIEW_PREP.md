# AI Engineer / Architect Interview Prep — PropIQ

## What You Built

A multi-agent AI system for property management with a LangGraph orchestrator, six specialist agents, RAG over lease documents, human-in-the-loop approval, role-based access control, and full session persistence.

---

## 1. The 2-Minute Pitch

> "I built PropIQ — a production-grade multi-agent AI backend for property management. A LangGraph orchestrator routes tenant or manager questions to one of six specialist agents: portfolio, maintenance, finance, lease, tenant, and document. Agents run in parallel using a thread pool. A RAG pipeline answers questions against uploaded lease PDFs via ChromaDB. For high-stakes actions like scheduling maintenance work orders, I built a human-in-the-loop approval gate — the agent proposes, a manager approves via a REST endpoint, then follow-up notifications fire automatically. The whole thing is role-aware: tenants only see their own data, managers see their portfolio, owners see everything. Session history persists across restarts via SQLite and MySQL."

---

## 2. Architecture Deep Dive

### System Diagram

```
User (tenant / manager / owner)
       │  POST /chat  (headers: user_id, role, tenant_id)
       ▼
  FastAPI  ──────────────────────────────────────────────
       │
  LangGraph Graph
  ┌────────────────────────────────────────────┐
  │  agent_node  (GPT-4.1-mini, temp=0.1)     │
  │    ↓ tool_calls (parallel)                 │
  │  tool_executor_node                        │
  │    ThreadPoolExecutor(max_workers=N)       │
  │    ├─ ask_portfolio_agent()                │
  │    ├─ ask_maintenance_agent()  ──────────► │  run_specialist()
  │    ├─ ask_finance_agent()      [ReAct, 5i] │    LLM + tools (up to 5 tool calls)
  │    ├─ ask_lease_agent()                    │
  │    ├─ ask_tenant_agent()                   │
  │    └─ ask_document_agent()  ──────────────►│  ChromaDB (cosine) + keyword fallback
  │    ↓                                       │
  │  agent_node  (synthesize)                  │
  └────────────────────────────────────────────┘
       │
  Detect propose_action → HITL gate
       │
  POST /approve/{action_id}
       │
  post-approval actions → notify tenants + manager
```

### Key Numbers to Remember
- **6** specialist agents, **19** tools total
- **2** LangGraph nodes (agent + tool_executor)
- **3** temperature presets (0.1 precise / 0.3 balanced / 0.5 creative)
- **5** max ReAct iterations per specialist
- **3** storage layers: SQLite (LangGraph), MySQL (backend), JSON (approval state)
- **3** user roles: tenant / manager / owner

---

## 3. Key Design Decisions — Be Ready to Defend These

### Why LangGraph over raw LangChain or CrewAI?

LangGraph gives you a **stateful graph** with explicit control flow — you can inspect and interrupt at any node. This was critical for HITL: I can detect `propose_action` in the agent node and pause before execution. CrewAI is higher-level but less controllable; raw LangChain chains have no built-in state machine.

### Why the orchestrator + specialist pattern instead of one big agent?

One agent with 19 tools would overwhelm the LLM's context and make it harder to enforce domain-specific rules (e.g., maintenance agent must confirm a work order ID before proposing action). Specialists let you give tighter, domain-specific system prompts and tool lists. The orchestrator handles routing, the specialists handle depth.

### Why parallel tool execution?

If the user asks "show me overdue payments and expiring leases," the orchestrator calls both `ask_finance_agent` and `ask_lease_agent` simultaneously via `ThreadPoolExecutor`. Each specialist does its own ReAct loop. Without parallelism this would be strictly sequential — slower for compound queries.

### Why ContextVar for user context instead of passing it as a parameter?

Tools are LangChain `@tool` decorated functions — their signatures are fixed by the schema exposed to the LLM. I can't add a `user` parameter without the LLM hallucinating a value for it. ContextVar lets me set context once at the start of a turn and read it from any tool call without it appearing in the LLM-facing schema. I also copy the context into `ThreadPoolExecutor` threads so it propagates correctly.

### Why fuzzy property matching in the tool, not the agent?

If the tool returns an error listing valid addresses, the agent can self-correct in the next ReAct step. If the agent had to do matching, it would require an extra LLM call and could hallucinate. Keeping matching in the tool keeps the agent's job as reasoning, not string matching.

### Why ChromaDB + keyword fallback?

Embedding API calls can fail or be slow. The keyword fallback ensures document search degrades gracefully instead of throwing an error. In practice, semantic search handles paraphrasing; keyword handles exact clause lookups.

### Why not resume the LangGraph graph after approval?

The approval endpoint fires side effects (notifications) and generates a confirmation message inline. Resuming the graph would re-run the agent node which risks re-proposing the action or hallucinating a different follow-up. Simpler and safer to handle post-approval outside the graph with explicit function calls.

---

## 4. RAG Pipeline

**Flow:**
1. `PyMuPDFLoader` extracts clean text from lease PDFs (better than pypdf for encoded/scanned docs)
2. `RecursiveCharacterTextSplitter` — 1000 char chunks, 150 overlap
3. `OpenAIEmbeddings` (`text-embedding-3-small`) creates vectors
4. Stored in ChromaDB with `cosine` metric, `property_documents` collection
5. At query time: semantic search with distance threshold 0.8, top-3 results
6. Keyword fallback if embedding unavailable
7. Multi-tenant isolation: filtered by `tenant_id` at retrieval

**Why text-embedding-3-small?** Good quality/cost tradeoff for document retrieval. For a production upgrade, `text-embedding-3-large` or a fine-tuned model would improve recall on legal language.

**Chunk strategy rationale:** 1000 chars with 150 overlap keeps lease clauses intact (most clauses are < 800 chars) while giving overlap to avoid splitting mid-clause.

---

## 5. Human-In-The-Loop (HITL) — Walk Through This End to End

1. User: *"Schedule a plumber for 4008 Gunnar Dr"*
2. Orchestrator calls `ask_maintenance_agent`
3. Maintenance agent ReAct loop: `find_vendor` → `create_maintenance_work_order` → receives `"Work order created (ID: WO-1234)"`
4. Agent calls `propose_action(title, description)` with confirmed ID
5. `agent_node` detects `propose_action` in tool_calls, sets `approval_required=True`, builds `ProposedAction` with `action_id`
6. Response returned to user with `AIActionCard` (status: pending) — no action has fired yet
7. Manager clicks Approve → `POST /approve/WO-1234?approved=true`
8. API validates: correct user, role is manager/owner
9. `_run_post_approval_actions()`: send notification to tenant + send confirmation to manager
10. LLM generates a human-friendly confirmation message
11. Follow-up stored in session, approval cleaned from store

**Safety rails:**
- Agent cannot call `propose_action` before confirmed work order ID — enforced in system prompt
- If user types "yes" while approval is pending, the chat endpoint detects it and redirects instead of creating a duplicate proposal
- Only manager/owner roles can approve

---

## 6. Role-Based Access Control

| Role | Sees |
|------|------|
| tenant | Only their own unit, lease, payments |
| manager | All properties and tenants in their org (`tenant_id`) |
| owner | All properties they own (`owner_id`) |

**Implementation:** `UserContext` stored in a `ContextVar`, read by every tool → passed to `backend_bridge` → applied as SQL `WHERE` clauses. No tool bypasses this — the ContextVar raises `RuntimeError` if not set.

**Interview angle:** This is a security boundary, not a UX nicety. Tenants cannot enumerate other tenants' data even if they craft a question designed to extract it.

---

## 7. Session & State Persistence

| Layer | What | Technology |
|-------|------|-----------|
| LangGraph checkpoint | Graph state per turn | SQLite (`agent_memory.db`) |
| Session messages | Chat history displayed to user | In-memory dict + JSON |
| Approval state | Pending approvals across restarts | `_PersistentDict` (JSON) |
| Backend history | Long-term message log | MySQL |

On startup, if the in-memory session cache is empty, messages are rehydrated from MySQL. This means a service restart doesn't lose conversation context.

---

## 8. Anticipated Interview Questions

**Q: How do you prevent the agent from hallucinating tool arguments?**
Tool schemas are strict Pydantic models. Fuzzy matching is in the tool, not the LLM. If a property address doesn't match, the tool returns an error listing valid options — the LLM self-corrects in the next ReAct step.

**Q: How do you handle the case where an agent calls the wrong specialist?**
The orchestrator prompt has explicit routing rules. But I also designed specialists to be narrowly scoped — a finance agent has no maintenance tools, so even if routed incorrectly, it can't create a work order. Defense in depth.

**Q: How would you scale this to 10,000 tenants?**
- Replace in-memory session store with Redis
- Replace `ThreadPoolExecutor` with a proper async task queue (Celery/ARQ)
- Add ChromaDB collection sharding by `tenant_id`
- Rate-limit per-user LLM calls
- Add a caching layer for repeated portfolio queries (they're read-heavy)

**Q: How do you evaluate RAG quality?**
Currently I rely on the distance threshold (0.8) to filter low-relevance results and keyword fallback as a safety net. For production I'd add: (1) a retrieval eval set of question/expected-chunk pairs, (2) track citation rate (did the response cite a document?), (3) LLM-as-judge scoring on answer faithfulness.

**Q: Why not use a fully managed solution like LangSmith + hosted agents?**
Good question — for a real production system I would integrate LangSmith for tracing. The current setup has structured logging with rotating file handlers, but LangSmith would give step-level visibility into every agent hop, which is much more debuggable.

**Q: How do you handle token limits in long sessions?**
The chat endpoint sends the last 20 messages as history. Beyond that, the LangGraph checkpointer has the full graph state, but the LLM context is intentionally bounded. In a v2 I'd add a summarization step that compresses old turns before they're passed to the LLM.

**Q: What's the hardest bug you fixed?**
ContextVar propagation into `ThreadPoolExecutor` threads — Python threads don't inherit the calling thread's context by default. I had to explicitly call `contextvars.copy_context().run(tool_func, args)` to carry `_user_ctx` into each worker thread. Without this, every parallel tool call would fail with "user context not set."

---

## 9. What to Prepare to Show (Live Demo Checklist)

- [ ] Start the AI service: `uvicorn app.main:app --reload`
- [ ] Hit `/health` — show LangGraph available, OpenAI configured
- [ ] Tenant chat: *"What are the pet rules in my lease?"* → RAG retrieval + citation
- [ ] Manager chat: *"Show me expiring leases in the next 90 days"* → lease agent
- [ ] Manager chat: *"Schedule a plumber for 4008 Gunnar"* → full HITL flow → approve → confirmation
- [ ] Show `rag1.py` — PDF ingestion pipeline with PyMuPDFLoader
- [ ] Show `graph.py` — 2-node LangGraph with parallel tool executor
- [ ] Show `agent_tools.py` — ContextVar pattern + fuzzy matching

---

## 10. Concepts to Brush Up On

| Topic | Why It Matters |
|-------|---------------|
| LangGraph state machines | Core orchestration — explain nodes, edges, conditional routing |
| ReAct pattern | How each specialist loops: Thought → Action → Observation |
| RAG fundamentals | Chunking, embeddings, vector similarity, retrieval eval |
| ContextVar / threading | Your parallel execution solution |
| HITL patterns | Interrupt-and-resume vs. side-channel approval (your approach) |
| Pydantic v2 | Validation, settings, schema generation for tool definitions |
| Multi-tenant data isolation | SQL-level filtering, not app-level |
| LLM temperature | Why 0.1 for tool decisions, 0.5 for letters |
| Token budgeting | Why max_tokens=2048, why 20-turn history window |
| Vector similarity metrics | Cosine vs dot product vs L2 — when to use each |
