# Property Management Platform — System Design Specification

---

## 1. Overview

This document defines the system design for a multi-tenant property management platform serving three personas — **Owners**, **Tenants**, and **Property Managers** — with an AI-powered agent orchestration layer built on LangGraph. The platform is composed of three independently deployable services: a React frontend, a FastAPI backend, and a Python-based AI agent service.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Client Layer                                  │
│                    React SPA (Browser)                               │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTPS / REST + WebSocket
          ┌──────────────────┴──────────────────┐
          │                                      │
┌─────────▼────────────┐            ┌────────────▼──────────────────┐
│  FastAPI Backend      │◄──────────►  AI Agent Service (LangGraph)  │
│  (Python)             │  Internal  │  (Python)                     │
│  - REST API           │  HTTP/gRPC │  - LangGraph Orchestration    │
│  - Auth & RBAC        │            │  - RAG Pipeline               │
│  - Business Logic     │            │  - Claude API Integration     │
│  - Data Access Layer  │            │  - Tool Executors             │
└─────────┬────────────┘            └───────────────────────────────┘
          │ SQLAlchemy ORM
┌─────────▼────────────┐
│   MySQL Database      │
│  - Multi-tenant data  │
│  - Leases, Payments   │
│  - Maintenance        │
│  - Users, Properties  │
└──────────────────────┘
```

---

## 3. Service Breakdown

### 3.1 React Frontend

**Purpose:** Single-page application providing role-differentiated views for Owners, Tenants, and Property Managers.

**Tech Stack:**
- React 18+ with TypeScript
- React Router for client-side routing
- React Query (TanStack Query) for server state management and caching
- Zustand or Redux Toolkit for client state (auth, UI preferences)
- Tailwind CSS for styling
- Socket.IO client for real-time notifications

**Key Modules:**

| Module | Description |
|---|---|
| Auth Module | Login, registration, password reset, JWT token management |
| Dashboard | Role-specific landing page with KPIs and quick actions |
| Property Management | Property listing, unit management, lease tracking |
| Tenant Portal | Rent payment, maintenance requests, document access, chat |
| Maintenance Module | Work order creation, status tracking, vendor assignment |
| Financial Module | Payment history, invoices, owner financial reports |
| Document Vault | Upload, view, and sign documents |
| AI Chat Interface | Conversational UI for the AI copilot with message streaming |
| Notification Center | Real-time alerts and in-app notification history |

**Role-Based UI Routing:**

```
/owner/*         → Owner dashboard, reports, approvals
/manager/*       → Full operational views, all properties
/tenant/*        → Tenant-scoped portal
/admin/*         → Platform-level super admin
```

**AI Chat Interface Specifics:**
- Streaming message display (token-by-token via SSE or WebSocket)
- Message history per session
- Structured action cards rendered from AI responses (e.g., "Approve work order?" with approve/reject buttons)
- Human-in-the-loop approval modals when the agent requests authorization

---

### 3.2 FastAPI Backend

**Purpose:** Core API server handling authentication, business logic, data persistence, and acting as the orchestration entry point between the frontend and the AI agent service.

**Tech Stack:**
- Python 3.11+
- FastAPI with async/await
- SQLAlchemy 2.0 (async ORM) with Alembic for migrations
- PyMySQL or aiomysql as the MySQL driver
- Pydantic v2 for request/response validation
- python-jose or PyJWT for JWT token handling
- Celery + Redis for background task processing
- Redis for caching and session storage
- Socket.IO (python-socketio) for real-time notifications

**API Structure:**

```
/api/v1/
├── auth/
│   ├── POST /login
│   ├── POST /register
│   ├── POST /refresh
│   └── POST /logout
├── users/
│   ├── GET  /me
│   └── PUT  /me
├── properties/
│   ├── GET  /
│   ├── POST /
│   ├── GET  /{id}
│   ├── PUT  /{id}
│   └── DELETE /{id}
├── units/
│   ├── GET  /{property_id}/units
│   └── POST /{property_id}/units
├── leases/
│   ├── GET  /
│   ├── POST /
│   ├── GET  /{id}
│   └── PUT  /{id}/renew
├── payments/
│   ├── GET  /
│   ├── POST /initiate
│   └── GET  /history
├── maintenance/
│   ├── GET  /requests
│   ├── POST /requests
│   ├── GET  /requests/{id}
│   └── PUT  /requests/{id}/status
├── documents/
│   ├── POST /upload
│   ├── GET  /
│   └── GET  /{id}/download
├── notifications/
│   └── GET  /
└── ai/
    ├── POST /chat          → Forward to AI Agent Service
    ├── GET  /chat/history
    └── POST /approve/{action_id}  → Human-in-the-loop approval
```

**Core Backend Services:**

| Service | Responsibilities |
|---|---|
| AuthService | JWT issuance, refresh, role validation, tenant resolution |
| PropertyService | CRUD for properties and units, occupancy tracking |
| LeaseService | Lease creation, renewals, expiry monitoring, clause storage |
| PaymentService | Rent tracking, late fee calculation, payment gateway integration |
| MaintenanceService | Work order lifecycle, vendor assignment, priority classification |
| DocumentService | File upload to S3/object storage, metadata persistence, access control |
| NotificationService | In-app and email notification dispatch, event subscriptions |
| AiProxyService | Request routing to AI Agent Service, response streaming, approval state management |

**Multi-Tenancy Strategy:**
- Each request carries a `tenant_id` derived from the authenticated user's JWT
- All database queries are scoped by `tenant_id` at the repository layer
- Middleware validates tenant context on every protected route

**Background Jobs (Celery):**
- Rent due reminders (daily cron)
- Lease expiry notifications (weekly cron)
- Late fee auto-calculation
- Maintenance escalation alerts
- Report generation jobs for owners

---

### 3.3 AI Agent Service (LangGraph)

**Purpose:** Standalone Python service that receives intent-bearing requests from the backend, orchestrates multi-step agentic workflows using LangGraph, and returns structured responses. This service is never called directly by the frontend.

**Tech Stack:**
- Python 3.11+
- LangGraph for agent state machine orchestration
- LangChain for LLM integration and tool abstractions
- Anthropic Claude API (`claude-opus-4-6`) as the primary LLM
- FastAPI or Flask as the internal HTTP server
- ChromaDB or pgvector (MySQL-adjacent) for the RAG vector store
- Redis for agent state persistence and session resumption
- Celery for async agent task execution on long-running workflows

**Core Agent Workflow (LangGraph State Machine):**

```
                    ┌─────────┐
                    │  Intake │
                    │  Node   │
                    └────┬────┘
                         │ classify intent
                    ┌────▼──────────┐
                    │ Context       │
                    │ Retrieval Node│◄── RAG (documents, leases)
                    │               │◄── DB Tool (payments, history)
                    └────┬──────────┘
                         │
                    ┌────▼──────────┐
                    │ Policy        │
                    │ Evaluation    │◄── Business rules engine
                    │ Node          │
                    └────┬──────────┘
                         │
                    ┌────▼──────────┐
                    │ Decision Node │
                    └──┬────────┬───┘
                       │        │
              auto-    │        │  requires human
              execute  │        │  approval
                       │   ┌────▼──────────┐
                       │   │ Approval Node  │──► Pause, notify backend
                       │   │ (HITL)        │◄── Resume on approval
                       │   └───────────────┘
                  ┌────▼──────────┐
                  │ Action Plan   │
                  │ Node          │
                  └────┬──────────┘
                       │
                  ┌────▼──────────┐
                  │ Execution     │◄── System API Tools
                  │ Node          │
                  └────┬──────────┘
                       │
                  ┌────▼──────────┐
                  │ Response      │
                  │ Generation    │
                  └───────────────┘
```

**Specialized Agent Workflows:**

| Agent | Trigger | Key Steps |
|---|---|---|
| MaintenanceTriageAgent | New maintenance request | Classify urgency → Retrieve vendor history → Check budget threshold → Create work order → Notify stakeholders |
| LeaseQAAgent | Lease-related question | Retrieve lease documents via RAG → Extract relevant clauses → Generate contextual answer with citations |
| PaymentHandlingAgent | Payment issue detected | Check payment history → Calculate outstanding fees → Identify resolution options → Guide tenant |
| OwnerReportAgent | Report request | Query financial data → Aggregate metrics → Generate narrative summary → Format for delivery |
| RenewalAgent | Lease nearing expiry | Fetch lease terms → Draft renewal offer → Route for manager approval → Send to tenant |

**Tool Registry (callable by agents):**

| Tool Name | Purpose | Calls |
|---|---|---|
| `get_lease_details` | Fetch structured lease data | FastAPI Backend |
| `get_payment_history` | Retrieve payment records | FastAPI Backend |
| `get_maintenance_history` | Fetch prior work orders | FastAPI Backend |
| `create_work_order` | Create a new maintenance work order | FastAPI Backend |
| `send_notification` | Dispatch notification to a user | FastAPI Backend |
| `search_documents` | Semantic search over uploaded documents | RAG Vector Store |
| `calculate_late_fee` | Deterministic fee calculation | Internal Rule Engine |
| `check_lease_compliance` | Validate action against lease terms | Internal Rule Engine |
| `request_human_approval` | Pause workflow, send approval request | FastAPI Backend |
| `generate_report` | Compile financial/operational report | FastAPI Backend + LLM |

**Human-in-the-Loop (HITL) Design:**
- The `request_human_approval` tool pauses the LangGraph state and persists the state to Redis with a unique `action_id`
- FastAPI receives the pending approval, stores it in MySQL, and notifies the manager/owner via WebSocket
- The approver sees a structured approval card in the React UI
- On approve/reject, FastAPI calls the AI Agent Service's `/resume/{action_id}` endpoint
- LangGraph resumes from the persisted checkpoint and either executes or cancels the planned action

**RAG System Design:**
- Documents (leases, policies, notices) are chunked and embedded on upload
- Embeddings stored in a vector store (ChromaDB for dev, pgvector for production)
- Retrieval uses hybrid search: semantic similarity + keyword filtering by `tenant_id` and `document_type`
- Retrieved chunks are passed as context into the Claude API call with prompt caching applied for repeated large-document queries

**LLM Integration Specifics:**
- Model: `claude-opus-4-6` with `thinking: {type: "adaptive"}`
- Streaming enabled for all user-facing response generation
- Deterministic logic (fee calculations, compliance checks) is handled by Python functions, not the LLM
- LLM used exclusively for: intent classification, natural language responses, summarization, clause interpretation, report narrative generation
- Prompt caching applied to stable system prompts and frequently-accessed lease documents

---

## 4. Database Design (MySQL)

### 4.1 Multi-Tenancy Approach
Every domain table includes a `tenant_id` foreign key. Row-level isolation is enforced at the ORM/repository layer. A separate `tenants` table holds platform-level configuration per organization.

### 4.2 Core Tables

**tenants**
- id, name, plan, created_at, settings_json

**users**
- id, tenant_id, email, password_hash, role (ENUM: owner/manager/tenant), first_name, last_name, phone, created_at, is_active

**properties**
- id, tenant_id, owner_id, name, address, city, state, zip, country, property_type, created_at

**units**
- id, property_id, tenant_id, unit_number, floor, bedrooms, bathrooms, sqft, status (ENUM: vacant/occupied/maintenance)

**leases**
- id, unit_id, tenant_user_id, tenant_id, start_date, end_date, rent_amount, security_deposit, status (ENUM: active/expired/terminated), lease_document_id, terms_json, created_at

**payments**
- id, lease_id, tenant_id, amount, due_date, paid_date, payment_method, status (ENUM: pending/paid/late/failed), late_fee, transaction_ref, created_at

**maintenance_requests**
- id, unit_id, tenant_user_id, tenant_id, category, description, urgency (ENUM: low/medium/high/emergency), status (ENUM: submitted/assigned/in_progress/resolved/closed), assigned_vendor_id, estimated_cost, resolution_notes, created_at, resolved_at

**documents**
- id, tenant_id, uploaded_by, document_type (ENUM: lease/notice/invoice/policy/other), file_name, storage_path, mime_type, file_size, related_entity_type, related_entity_id, created_at

**notifications**
- id, tenant_id, user_id, type, title, body, is_read, metadata_json, created_at

**ai_sessions**
- id, tenant_id, user_id, session_id, created_at, last_active_at

**ai_messages**
- id, session_id, role (ENUM: user/assistant/system), content, created_at

**ai_approval_requests**
- id, tenant_id, session_id, action_type, action_payload_json, requested_by_agent, status (ENUM: pending/approved/rejected), approver_user_id, created_at, resolved_at

**vendors**
- id, tenant_id, name, trade, email, phone, rating, is_active

---

## 5. Authentication & Authorization

**Authentication Flow:**
- Email/password login returns a short-lived JWT access token (15 min) and a long-lived refresh token (7 days)
- Refresh tokens stored in HttpOnly cookies; access tokens in memory (not localStorage)
- All API requests include `Authorization: Bearer <token>` header

**RBAC Model:**

| Permission | Owner | Manager | Tenant |
|---|:---:|:---:|:---:|
| View own properties | ✓ | ✓ | — |
| View all properties | — | ✓ | — |
| Create/edit lease | — | ✓ | — |
| Pay rent | — | — | ✓ |
| Submit maintenance | — | ✓ | ✓ |
| Approve work orders | ✓ | ✓ | — |
| Approve financial adjustments | ✓ | — | — |
| View owner reports | ✓ | — | — |
| Manage vendors | — | ✓ | — |
| Access AI chat | ✓ | ✓ | ✓ |
| Approve AI actions | ✓ | ✓ | — |

**AI Agent Authorization:**
- The AI Agent Service acts with a service-to-service API key, not a user JWT
- All tool calls from the agent include `acting_on_behalf_of: user_id` for audit logging
- The backend enforces that the agent cannot bypass RBAC — e.g., a tenant-initiated agent session cannot trigger owner-level approvals

---

## 6. Integration Layer

**Payment Gateway:**
- Integration with Stripe (or equivalent) for rent collection
- Webhook endpoint on FastAPI for payment event callbacks
- Idempotency keys on all payment initiation calls

**Email Notifications:**
- SendGrid or AWS SES for transactional emails
- Templates for: rent reminders, lease renewals, maintenance updates, AI-generated reports

**SMS Notifications (optional):**
- Twilio for urgent maintenance and overdue payment alerts

**File Storage:**
- AWS S3 or compatible object storage for documents
- Pre-signed URLs for secure, time-limited document access
- Metadata stored in MySQL; file content never in MySQL

**Real-Time Communication:**
- WebSocket server (Socket.IO) on the FastAPI backend
- Events: new notification, AI message stream, approval request, maintenance status update

---

## 7. Communication Patterns Between Services

### Frontend ↔ FastAPI Backend
- **REST** for all CRUD operations and data fetching
- **WebSocket** for real-time notifications and AI message streaming
- **SSE (Server-Sent Events)** as fallback for AI response streaming

### FastAPI Backend ↔ AI Agent Service
- **Synchronous HTTP** for short agent queries (lease Q&A, simple classification)
- **Async task queue (Celery)** for long-running agent workflows (report generation, multi-step maintenance triage)
- **Callback/webhook pattern**: Agent service calls back to FastAPI with results when async tasks complete
- **Redis** as shared state store for HITL approval workflow coordination

### FastAPI Backend ↔ MySQL
- Async SQLAlchemy with connection pooling
- All queries scoped by `tenant_id`
- Read replicas for reporting queries (optional for scale)

### AI Agent Service ↔ External APIs
- Claude API (Anthropic) for LLM inference
- Vector store for RAG retrieval
- FastAPI Backend tools via internal HTTP calls

---

## 8. Deployment Architecture

**Services:**

| Service | Runtime | Deployment Unit |
|---|---|---|
| React Frontend | Node.js build → static files | CDN / S3 + CloudFront |
| FastAPI Backend | Python 3.11 Uvicorn/Gunicorn | Docker container, auto-scaling |
| AI Agent Service | Python 3.11 Uvicorn | Docker container, auto-scaling |
| MySQL | Managed RDS (MySQL 8.0) | AWS RDS or equivalent |
| Redis | Managed ElastiCache | AWS ElastiCache or equivalent |
| Celery Workers | Python | Docker container workers |
| Vector Store | ChromaDB (dev) / pgvector (prod) | Sidecar or dedicated container |

**Environment Separation:**
- `development` — local Docker Compose stack with all services
- `staging` — mirrors production with reduced capacity
- `production` — full cloud deployment with auto-scaling, backups, monitoring

**Secrets Management:**
- Environment variables injected at runtime (never committed to source)
- AWS Secrets Manager or HashiCorp Vault for production credentials

---

## 9. Observability

**Logging:**
- Structured JSON logs from all services
- Every AI agent decision and tool call logged with: session_id, action, input summary, output summary, latency, model_used
- All HITL approval requests and outcomes logged for audit trail

**Metrics:**
- Request latency per endpoint
- AI agent turn count and cost per session
- Maintenance resolution time
- Rent collection rate
- Payment failure rate

**Tracing:**
- Distributed tracing (OpenTelemetry) across FastAPI ↔ AI Agent Service calls
- LangGraph workflow trace stored per session in `ai_messages` table

**Alerting:**
- Alert on: elevated payment failure rate, agent error rate, API latency p99 breach, pending HITL approvals exceeding SLA

---

## 10. Security Considerations

- All service-to-service communication over TLS on internal VPC
- AI Agent Service not exposed to the public internet; only callable from FastAPI Backend
- Input sanitization on all natural language inputs before passing to LLM (prompt injection mitigation)
- LLM responses validated before executing any action tools
- Document access enforced by signed URLs with expiry; no public document URLs
- Rate limiting on AI chat endpoint per user per hour
- PII fields (SSN, bank info) never stored in plain text; encrypted at rest
- HITL required for all financial mutations above configurable threshold

---

## 11. Key Design Decisions

| Decision | Rationale |
|---|---|
| Separate AI Agent Service from FastAPI Backend | Allows independent scaling of AI workloads; keeps business logic isolated from LLM orchestration complexity; enables versioning of agent workflows independently |
| LangGraph for orchestration | Provides explicit state machine with checkpointing, which is essential for HITL workflows and long-running processes |
| Claude as sole LLM | Consistent API surface; adaptive thinking for complex reasoning; strong instruction-following for tool use |
| Deterministic rules for calculations | Fee calculations and compliance checks are deterministic by design; LLM used only for language tasks, not arithmetic |
| MySQL over NoSQL | Relational integrity critical for financial and lease data; multi-tenancy with row-level isolation maps well to relational model |
| Redis for agent state | Fast read/write for transient HITL checkpoints; TTL-based expiry for abandoned approval flows |
| Celery for async jobs | Decouples long-running agent workflows from HTTP request lifecycle; enables retry and monitoring |

---

## 12. Success Metrics Mapping to Architecture

| Metric | How Measured | Owner |
|---|---|---|
| Rent collection rate | `payments` table: paid / due within period | FastAPI + Reporting |
| Maintenance resolution time | `resolved_at - created_at` in `maintenance_requests` | FastAPI + Agent |
| Tenant satisfaction | Post-interaction rating stored in DB | Frontend + FastAPI |
| Operational efficiency | Work orders auto-triaged / total work orders | AI Agent + Reporting |
| AI accuracy | HITL override rate on AI-proposed actions | AI Agent + HITL logs |
