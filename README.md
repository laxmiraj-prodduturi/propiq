# PropIQ — AI-Powered Property Management

A full-stack property management platform with a multi-agent AI backend. Tenants, managers, and owners each get a role-aware chat interface backed by specialized AI agents that can answer lease questions, track maintenance, manage payments, and execute approved actions.

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────────────────────┐
│  Frontend   │────▶│   Backend    │     │         AI Service              │
│  React/TS   │     │  FastAPI +   │────▶│  LangGraph Orchestrator         │
│  Vite       │     │  SQLAlchemy  │     │  ├─ Portfolio Agent             │
│  :3000      │     │  MySQL       │     │  ├─ Maintenance Agent (HITL)    │
└─────────────┘     │  :8000       │     │  ├─ Finance Agent               │
                    └──────────────┘     │  ├─ Lease Agent                 │
                           │             │  ├─ Tenant Agent                │
                           └────────────▶│  └─ Document Agent (RAG)        │
                                         │  :8100                          │
                                         └─────────────────────────────────┘
```

### Services

| Service | Stack | Port |
|---------|-------|------|
| Frontend | React, TypeScript, Vite | 3000 |
| Backend | FastAPI, SQLAlchemy, Alembic, MySQL | 8000 |
| AI Service | FastAPI, LangGraph, LangChain, ChromaDB | 8100 |

---

## AI Service — How It Works

### Multi-Agent Orchestration (LangGraph)

A two-node LangGraph graph handles every chat turn:

1. **`agent_node`** — GPT-4.1-mini orchestrator decides which specialists to call
2. **`tool_executor_node`** — runs specialist agents in parallel via `ThreadPoolExecutor`

Each specialist runs its own ReAct loop (max 5 iterations) with a scoped tool set:

| Agent | Responsibility | Tools |
|-------|---------------|-------|
| Portfolio | Occupancy, vacancy, rent collection overview | 1 |
| Maintenance | Work orders, vendor lookup, HITL approval | 5 |
| Finance | Payments, late fees, revenue projection | 4 |
| Lease | Expiry tracking, renewal letters | 3 |
| Tenant | Directory, payment history, notifications | 4 |
| Document | Lease clause lookup via RAG | 2 |

### RAG Pipeline

Lease PDFs are ingested with `PyMuPDFLoader`, chunked (1000 chars / 150 overlap), embedded with `text-embedding-3-small`, and stored in ChromaDB. Retrieval uses cosine similarity (threshold 0.8) with a keyword fallback.

```
PDF → PyMuPDFLoader → RecursiveCharacterTextSplitter → OpenAIEmbeddings → ChromaDB
Query → semantic search (top 3) → cited answer
```

### Human-In-The-Loop (HITL)

High-stakes actions (scheduling work orders) require manager approval:

1. Maintenance agent creates work order → receives confirmed ID
2. Agent calls `propose_action` → response includes an approval card
3. Manager approves via `POST /approve/{action_id}`
4. Post-approval actions fire: tenant + manager notifications

### Role-Based Access Control

User role flows from login → JWT → request headers → `ContextVar` → every tool call → SQL `WHERE` clause. No tool can bypass this.

| Role | Data Scope |
|------|-----------|
| tenant | Own unit, lease, and payment history |
| manager | All properties in their organization |
| owner | All properties they own |

---

## Getting Started

### Prerequisites

- Python 3.10
- Node.js 18+
- MySQL running locally

### Quick Start

```bash
# Start MySQL first
brew services start mysql

# Start all three services
./dev-up.sh
```

Services start at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- AI Service: http://localhost:8100

### Manual Setup

**Backend**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in DB credentials
alembic upgrade head
python run.py
```

**AI Service**
```bash
cd ai_service
python -m venv venv && source venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env   # fill in OPENAI_API_KEY
python run.py
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```

### Environment Variables

**`ai_service/.env`**
```
OPENAI_API_KEY=sk-...
DATABASE_URL=mysql+pymysql://user:password@localhost/quantum_quest_properties
SECRET_KEY=your-secret-key
```

**`backend/.env`**
```
DATABASE_URL=mysql+pymysql://user:password@localhost/quantum_quest_properties
SECRET_KEY=your-secret-key
```

### Ingest Lease Documents

```bash
cd ai_service
source venv/bin/activate
python3 app/services/rag1.py   # indexes PDFs into ChromaDB
```

---

## Demo Logins

| Role | Email | Password |
|------|-------|----------|
| Owner | alex.thompson@example.com | demo1234 |
| Manager | sarah.chen@example.com | demo1234 |
| Tenant | marcus.johnson@example.com | demo1234 |

---

## Project Structure

```
propery-management/
├── frontend/               # React + TypeScript UI
│   └── src/
│       ├── pages/          # Route-level components
│       ├── components/     # Shared UI components
│       └── api/            # API client
├── backend/                # FastAPI REST API
│   ├── app/
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── routers/        # API route handlers
│   │   ├── schemas/        # Pydantic request/response models
│   │   └── services/       # Business logic
│   └── alembic/            # Database migrations
├── ai_service/             # LangGraph AI backend
│   └── app/
│       ├── agents/         # Specialist agent implementations
│       ├── services/       # Tools, RAG, LLM factory, intent registry
│       ├── graph.py        # LangGraph state machine
│       ├── main.py         # FastAPI endpoints (/chat, /approve, /health)
│       ├── state.py        # AgentState schema
│       └── store.py        # Session + approval persistence
├── documents/leases/       # Source lease documents (txt + JSON)
├── scripts/                # Deploy, seed, and migration scripts
└── dev-up.sh               # Start all services locally
```

---

## API Reference

### AI Service

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Service health + config status |
| POST | `/chat` | Send a message, get an AI response |
| GET | `/chat/history` | Retrieve session message history |
| POST | `/approve/{action_id}` | Approve or reject a proposed action |
| POST | `/support/chat` | Lightweight support Q&A (no agents) |

**Chat request headers:** `x-user-id`, `x-user-role`, `x-tenant-id`

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| LLM | OpenAI GPT-4.1-mini |
| Embeddings | OpenAI text-embedding-3-small |
| Orchestration | LangGraph + LangChain |
| Vector store | ChromaDB (cosine metric) |
| Graph persistence | SQLite (LangGraph checkpointer) |
| Web framework | FastAPI + Pydantic v2 |
| Database | MySQL + SQLAlchemy + Alembic |
| PDF extraction | PyMuPDF |
| Frontend | React + TypeScript + Vite |
