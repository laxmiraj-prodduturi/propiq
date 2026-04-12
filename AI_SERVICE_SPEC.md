# AI Service Specification — QuantumQuest Properties

## 1. Purpose

The AI service is an LLM-powered agent embedded in the property management platform. It answers questions and executes actions on behalf of three user roles:

- **Owner** — portfolio performance, financials, approvals
- **Manager** — day-to-day operations, tenant issues, maintenance triage
- **Tenant** — their own lease, payments, and maintenance requests

The service is intentionally role-scoped: a tenant never sees data belonging to another tenant, and an owner's portfolio data is never visible to tenants. Every response is grounded in real data — either from the live database or from indexed property documents.

---

## 2. Data Sources

The agent draws from two pools of data:

### 2a. Structured (Live Database)

Queried at request time through the backend bridge.

| Table | What the AI uses it for |
|-------|------------------------|
| `properties` | Portfolio overview, occupancy rates, rent amounts |
| `leases` | Lease term dates, rent amounts, which tenant occupies which unit |
| `payments` | Overdue balances, late fees, rent history |
| `maintenance_requests` | Open work orders, urgency, assigned vendors, estimated cost |
| `documents` | Document metadata — file name, type, which lease/tenant it belongs to |
| `users` | Tenant name resolution |
| `vendors` | Vendor name, trade, contact details for maintenance dispatch |

### 2b. Unstructured (Document Content — RAG)

Documents stored offline (PDFs, Word files, scanned leases) that contain the actual text of agreements and policies. These are indexed into ChromaDB and retrieved semantically at query time.

**Documents you have offline today:**
- Lease agreements (per-tenant PDF files)
- Tenant information packets (move-in checklists, house rules)
- Policy documents (pet policy, maintenance response SLA, late fee schedule)
- Notice templates (lease renewal, non-renewal, entry notice)

These are currently **not** loaded into the vector store because only document metadata (file name, type) is indexed, not the file content. See Section 6 for the ingestion pipeline needed to fix this.

---

## 3. Agent Capabilities

### Owner

| Question type | Data source | Example |
|--------------|-------------|---------|
| Portfolio summary | DB: properties, leases, payments | "How many vacant units do I have?" |
| Revenue & late payments | DB: payments, leases | "Which tenants are overdue this month?" |
| Maintenance approval | DB: maintenance_requests | "Approve the HVAC dispatch for Oak Ridge" |
| Lease expiry calendar | DB: leases | "Which leases expire in the next 90 days?" |
| Vendor costs | DB: vendors, maintenance_requests | "What have I spent on plumbing this year?" |
| Document Q&A | RAG: lease PDFs | "What does the Oak Ridge lease say about subletting?" |

### Manager

| Question type | Data source | Example |
|--------------|-------------|---------|
| Maintenance triage | DB: maintenance_requests | "Prioritize open work orders by urgency" |
| Tenant status | DB: leases, payments, users | "Is Marcus Johnson current on rent?" |
| Lease renewals | DB: leases | "Which leases need renewal decisions this month?" |
| Vendor dispatch | DB: vendors, maintenance_requests | "Who should I send for the plumbing issue at Unit 4?" |
| Document lookup | RAG: policies, notices | "What's our late fee policy?" |

### Tenant

| Question type | Data source | Example |
|--------------|-------------|---------|
| Rent status | DB: payments, leases | "When is my next rent due?" |
| Lease terms | RAG: their lease PDF | "What does my lease say about guests?" |
| Maintenance submit/track | DB: maintenance_requests | "I have a water leak — can you help me submit a request?" |
| Move-out info | RAG: tenant info packet | "What do I need to do before moving out?" |
| Pet policy | RAG: pet policy doc | "Can I have a dog in my unit?" |

---

## 4. Intent Taxonomy

Every user message is classified into one intent before tools are invoked. This determines which data to fetch.

| Intent | Triggers | Tools called |
|--------|----------|-------------|
| `portfolio_summary` | "overview", "occupancy", "portfolio", "report", "vacant", "revenue" | list_properties, get_payment_history, get_open_maintenance |
| `maintenance_workflow` | "maintenance", "repair", "broken", "leak", "HVAC", "work order" | get_open_maintenance, list_properties, (vendors if dispatch) |
| `payment_workflow` | "rent", "payment", "overdue", "late fee", "due date", "balance" | get_payment_history, get_active_leases |
| `lease_query` | "lease", "agreement", "term", "clause", "subletting", "pet", "guest" | get_active_leases + RAG retrieve |
| `document_lookup` | "policy", "document", "notice", "what does it say", "rules", "addendum" | RAG retrieve |
| `general_qa` | Everything else | RAG retrieve (light) |

---

## 5. LangGraph Architecture

The agent runs as a LangGraph `StateGraph` with a `MemorySaver` checkpointer for within-session continuity and human-in-the-loop approval interrupts.

```
[intake] → [route_intent] → [retrieve_context] → [plan]
                                                      ↓
                                              [tool_execution]
                                                      ↓
                                              [policy_check]
                                                      ↓
                                                [respond]
                                                /        \
                                       (approval          (no approval
                                        required)          required)
                                             ↓                ↓
                                     [approval_gate]        [END]
                                    (interrupt here —
                                     wait for user)
                                             ↓
                                           [END]
```

### Node responsibilities

**intake** — validates user context, resets ephemeral state fields.

**route_intent** — calls `gpt-4.1-mini` with the intent taxonomy prompt. Falls back to keyword matching if OpenAI is unavailable. Result: one of the 6 intents above.

**retrieve_context** — queries ChromaDB using the user's message embedding and `tenant_id` filter. Returns up to 3 relevant document chunks. Falls back to keyword search against document metadata.

**plan** — examines the intent and role to decide whether an approval action is required. For `maintenance_workflow` on owner/manager, proposes an `approve_maintenance_followup` action card.

**tool_execution** — calls the appropriate DB tools and builds a `structured_context` summary. No LLM calls here; this is pure data assembly.

**policy_check** — enforces role restrictions. Strips approval-required flags from intents where the user's role does not have approval authority.

**respond** — calls `gpt-4.1-mini` with the system prompt, structured data context, and any retrieved document citations to compose the final answer.

**approval_gate** — runs *after* the user approves or rejects an action card. The graph is interrupted before this node and only resumes once `/resume/{action_id}` is called. Composes a follow-up response confirming what was approved/rejected.

---

## 6. Document Ingestion Pipeline (Current Gap)

**The most important missing piece.** Today, the RAG index only contains document metadata (file name, type, entity name). It cannot answer "what does my lease say about pets?" because the actual text of the lease PDF has never been loaded.

### What needs to be built

#### 6a. File storage

Lease agreements and tenant documents need to be stored somewhere the AI service can read them. Options:

- **Local filesystem** (simplest for now) — documents stored in a known path, e.g., `documents/{tenant_id}/{file_name}.pdf`
- **S3 / object storage** — for production; the ingestion job downloads and parses on demand
- **Already uploaded via the Documents page** — the current `Document` DB record stores `file_path` (where the file lives) but the content is never extracted

#### 6b. Text extraction

PDF and Word files must be parsed into plain text before embedding:

```
PDF file  →  pdfplumber / PyMuPDF  →  raw text
Word file →  python-docx           →  raw text
```

Each document is then split into overlapping chunks (400–600 tokens, 100-token overlap) to stay within embedding model limits and preserve context at retrieval time.

#### 6c. Chunking and metadata

Every chunk stored in ChromaDB must carry:

| Metadata field | Value | Used for |
|---------------|-------|----------|
| `tenant_id` | owner of the document | isolates results per tenant |
| `document_id` | FK to the `documents` table | links back to source |
| `document_type` | "lease", "policy", "notice", etc. | filtering |
| `related_entity` | tenant name / property name | display in citations |
| `chunk_index` | position in document | ordering multi-chunk answers |
| `file_name` | original file name | citation display |

#### 6d. Ingestion trigger options

| Trigger | When to use |
|---------|------------|
| On upload | Document uploaded via the Documents page → immediately ingest |
| On startup | AI service starts → re-index any unindexed documents |
| Manual CLI | `python ingest.py --file lease_oak_ridge.pdf --tenant-id t1` |
| Nightly cron | Catch any files that arrived outside normal upload flow |

**Recommended for your offline documents:** a one-time CLI ingestion script that walks a folder, extracts text, chunks, embeds, and upserts into ChromaDB. After that, hook into the upload endpoint so new documents are indexed automatically.

#### 6e. Retrieval improvement

Once real document text is in ChromaDB, the `retrieve_context` node should:

1. Embed the user query with `text-embedding-3-small`
2. Query ChromaDB filtered by `{"tenant_id": user.tenant_id}`
3. Filter out chunks with cosine distance > 0.75 (tighter than the current 0.8)
4. Return the top 3–5 chunks as context to the `respond` node
5. Surface the source document name as a citation in the response

---

## 7. System Prompt Design

### Grounded response prompt (respond node)

```
You are a helpful AI assistant for QuantumQuest Properties, a residential property management platform.
The user's role is: {role}.

Live data retrieved from the database and relevant document excerpts are provided below.
Ground every answer in that data. Do not fabricate figures, names, or dates.

Role guidelines:
- Tenant: answer only about their own lease, payments, and maintenance. Never expose other tenants' data.
- Manager: focus on operational data — maintenance, lease status, payment posture.
- Owner: focus on portfolio-level metrics, financial performance, and approval decisions.

If the data provided does not contain enough information to answer the question,
say so clearly and suggest the user check the relevant section of the platform.
```

### Intent classifier prompt

```
Classify the user message into exactly one intent:
portfolio_summary | maintenance_workflow | payment_workflow | lease_query | document_lookup | general_qa

Respond with ONLY the intent name. No explanation, no punctuation.
```

### Support agent prompt (floating widget)

```
You are a friendly support assistant for QuantumQuest Properties.
Help users navigate platform features and answer general property management questions.
For account-specific data (their payments, lease clauses, maintenance status),
tell them to use the main AI Assistant which has live access to their data.
Be concise — 2 to 4 sentences unless more detail is clearly needed.
```

---

## 8. Action / Approval Workflow

Some agent responses include an **action card** — a structured proposal requiring explicit user approval before any external action is taken.

### Action types (current + planned)

| Action type | Triggered when | What happens after approval |
|-------------|---------------|----------------------------|
| `approve_maintenance_followup` | Owner/manager asks about maintenance | Confirms authorization to dispatch vendor; logs the decision |
| `approve_lease_renewal` | (Planned) Lease expiry Q&A | Sends renewal offer to tenant (email/notification) |
| `approve_vendor_dispatch` | (Planned) Specific work order selected | Creates vendor assignment in the maintenance record |
| `waive_late_fee` | (Planned) Owner requests to waive a fee | Updates payment record late fee to $0 |

### Workflow steps

1. Agent proposes an action → `action_card` included in the response, graph interrupted
2. User sees the card in the chat UI with **Approve** / **Reject** buttons
3. User clicks → `POST /api/v1/ai/approve/{action_id}?approved=true`
4. Backend updates the `ai_approvals` table (status: approved/rejected)
5. Frontend calls `POST /api/v1/ai/resume/{action_id}`
6. Backend proxies to AI service `/resume/{action_id}`
7. LangGraph resumes from the `approval_gate` node
8. Agent composes a follow-up confirmation message
9. Follow-up message appended to chat

---

## 9. API Contract

### AI Service (port 8100) — internal only

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Service health + config flags |
| POST | `/chat` | Main agent turn. Headers: `x-user-id`, `x-user-role`, `x-tenant-id` |
| GET | `/chat/history` | Retrieve session messages |
| POST | `/approve/{action_id}` | Record approval decision |
| POST | `/resume/{action_id}` | Resume paused LangGraph, get follow-up |
| POST | `/support/chat` | Support assistant — no context headers needed |

### Backend (port 8000) — public API, JWT auth required

All routes under `/api/v1/ai/` proxy to the AI service with user context injected from the JWT token.

| Method | Path |
|--------|------|
| POST | `/api/v1/ai/chat` |
| GET | `/api/v1/ai/chat/history` |
| POST | `/api/v1/ai/approve/{action_id}` |
| POST | `/api/v1/ai/resume/{action_id}` |
| POST | `/api/v1/ai/support/chat` |

---

## 10. What Is Built vs. What Needs Work

### Built and working

- LangGraph StateGraph with 8 nodes, interrupt/resume for approvals
- OpenAI intent classification with keyword fallback
- LLM response generation with role-aware system prompt
- ChromaDB vector store with tenant-scoped retrieval
- Structured DB tools: properties, leases, payments, maintenance
- AI session + message persistence to MySQL
- Support chat agent (floating widget)
- Backend proxy routes with JWT auth and local fallbacks
- Rate limiting on chat endpoint (20/hour per IP)

### Gaps to close (priority order)

| Gap | Priority | Effort |
|-----|----------|--------|
| **Document text extraction and chunking** | High | Medium — needs pdfplumber/PyMuPDF + chunking logic |
| **Ingestion script for offline lease PDFs** | High | Low — one-time CLI job |
| **Auto-ingest on document upload** | Medium | Low — hook into the upload endpoint |
| **Lease-specific retrieval improvement** | Medium | Low — tighter distance threshold once real text is indexed |
| **`lease_query` intent** | Medium | Low — add to intent taxonomy, route to RAG-first |
| **Concrete action execution** (vendor dispatch, renewal emails) | Medium | High — requires integration with notifications / email |
| **Conversation memory across sessions** | Low | Medium — pass previous turns to LLM context window |
| **Vendor dispatch action type** | Low | Medium |

---

## 11. Document Ingestion — Step-by-Step Plan for Your Offline Files

Given that you have lease agreements and tenant information offline today, here is the recommended path:

**Step 1 — Organize files**

Place documents in a structured folder:
```
documents/
  t1/                         ← tenant_id
    lease_oak_ridge.pdf
    tenant_info_packet.pdf
  t2/
    lease_maple_street.pdf
  shared/
    pet_policy.pdf
    maintenance_sla.pdf
    late_fee_schedule.pdf
```

**Step 2 — Build the ingestion script**

File: `ai_service/scripts/ingest_documents.py`

- Walk the folder structure
- Extract text from each PDF using `pdfplumber`
- Split into 500-token chunks with 100-token overlap using `langchain_text_splitters.RecursiveCharacterTextSplitter`
- Embed each chunk with `text-embedding-3-small`
- Upsert into ChromaDB with metadata: `tenant_id`, `file_name`, `document_type` (inferred from file name), `chunk_index`

**Step 3 — Add packages**

```
# ai_service/requirements.txt
pdfplumber>=0.10.0
python-docx>=1.1.0
langchain-text-splitters>=0.2.0
```

**Step 4 — Run once**

```bash
cd ai_service
venv/bin/python scripts/ingest_documents.py --docs-dir ../documents/
```

**Step 5 — Hook into upload**

When a document is uploaded via the Documents page, trigger a background call to ingest the file content. This keeps the vector store current as new leases are signed.

---

## 12. Configuration Reference

| Setting | Where | Purpose |
|---------|-------|---------|
| `OPENAI_API_KEY` | `.env` | LLM + embeddings. Required for real answers. |
| `OPENAI_MODEL` | `ai_service/app/config.py` | Currently `gpt-4.1-mini`. Can switch to `gpt-4.1` for higher accuracy. |
| `OPENAI_EMBEDDING_MODEL` | `ai_service/app/config.py` | `text-embedding-3-small`. Switch to `text-embedding-3-large` for better retrieval at higher cost. |
| `CHROMA_DB_PATH` | `ai_service/app/config.py` | Local path for ChromaDB persistence. |
| `AI_SERVICE_URL` | `backend/.env` | Backend uses this to proxy requests. Default: `http://localhost:8100`. |
| `AI_SERVICE_TIMEOUT_SECONDS` | `backend/.env` | Request timeout. Default: 30s. |
| `DEMO_MODE` | `ai_service/app/config.py` | When true, suppresses real LLM calls (for demos without API key). |
