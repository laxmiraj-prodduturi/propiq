# AI Agent Spec

## Overview

This document defines the AI chatbot and agent orchestration layer for the residential property management platform. The goal is to showcase a credible agentic AI implementation using LangGraph, RAG, and OpenAI integration on top of the existing frontend and backend.

The chatbot should do more than answer free-form questions. It should retrieve grounded context, call tools, plan multi-step actions, and pause for approval before proposing any write-like operation.

## Objectives

The AI implementation should demonstrate:

- LangGraph-based multi-step orchestration
- RAG over property and lease documents
- OpenAI-powered reasoning, planning, and answer generation
- Tool use against operational property-management data
- Human-in-the-loop approval for action proposals
- Role-aware behavior for owner, manager, and tenant personas

## Product Scope

The AI copilot should support:

- conversational Q&A
- lease and policy interpretation
- payment and rent-status questions
- maintenance triage and follow-up planning
- property portfolio summaries
- structured action proposals with approval gating
- session memory
- citations for retrieved documents

The first version should not support:

- autonomous irreversible actions
- external vendor or messaging integrations
- direct mutation execution without approval
- large-scale multi-tenant infrastructure optimizations

## Demo Scenarios

The implementation should support at least these demo prompts:

- Tenant: "When is my rent due and what happens if I pay late?"
- Tenant: "What does my lease say about pets?"
- Manager: "Show me homes needing attention this week."
- Manager: "Draft a reply to a maintenance complaint."
- Manager: "Create a maintenance follow-up plan for 4053 Penny Terrace."
- Owner: "Summarize portfolio rent and vacancy risk."
- Owner: "Which homes are currently vacant and what is the asking rent?"

## Architecture

The AI system should be split into three layers:

1. Frontend chat UI
2. Backend application API
3. AI service

The AI service should be a separate Python service from the main backend to make the agentic architecture explicit and easier to evolve independently.

### Service Layout

- `frontend`
- `backend`
- `ai_service`

### Responsibilities

#### Frontend

- chat interface
- message history display
- streaming response rendering
- source/citation panel
- approval action cards
- optional agent-step debug panel

#### Backend

- authentication and RBAC
- operational data access
- internal read/write tool endpoints
- session persistence support
- approval state persistence

#### AI Service

- LangGraph orchestration
- intent routing
- RAG retrieval
- OpenAI model integration
- tool execution planning
- approval pause/resume logic

## LangGraph Design

The graph should be explicit and inspectable.

### Nodes

1. `intake`
   - normalize user input
   - attach user/session/role context

2. `route_intent`
   - classify into one of:
   - `qa`
   - `portfolio_summary`
   - `maintenance_workflow`
   - `payment_workflow`
   - `document_lookup`
   - `action_request`

3. `retrieve_context`
   - fetch structured records from backend
   - perform vector retrieval for relevant documents
   - assemble working context

4. `plan`
   - decide whether more tools are needed
   - produce bounded next actions

5. `tool_execution`
   - execute read tools
   - build action proposals for write-like tools

6. `policy_check`
   - enforce RBAC and approval requirements

7. `approval_gate`
   - pause workflow if approval is required
   - emit approval payload to backend/frontend

8. `respond`
   - generate final grounded response
   - attach citations and action cards when relevant

9. `resume_action`
   - continue after approval or rejection

### Graph State

The state object should include:

- `session_id`
- `user_id`
- `role`
- `tenant_id`
- `user_message`
- `intent`
- `retrieved_docs`
- `structured_context`
- `tool_calls`
- `proposed_actions`
- `approval_required`
- `approval_status`
- `final_response`
- `citations`

## RAG Specification

The RAG layer should index:

- lease documents
- notices
- policy documents
- uploaded reports
- maintenance-related files

### RAG Pipeline

1. document ingestion
2. text extraction
3. chunking
4. embedding generation
5. vector storage
6. filtered retrieval
7. answer grounding

### Chunk Metadata

Each chunk should store:

- `document_id`
- `document_type`
- `property_id` when available
- `tenant_id`
- `file_name`
- `chunk_index`

### Vector Store

Recommended:

- local/dev: Chroma
- later/prod option: pgvector

## OpenAI Integration

OpenAI should be used for:

- intent classification
- plan generation
- tool-selection reasoning
- grounded response generation
- summarization
- draft generation

OpenAI should not be used for:

- permission checks
- deterministic calculations
- approval enforcement
- business-rule validation

Those should remain application logic.

### Model Roles

Recommended split:

- chat/reasoning model for orchestration and final answers
- embedding model for document retrieval

## Tool Contract

The agent should call explicit tools rather than access the database directly.

### Read Tools

- `list_properties()`
- `get_property_overview(property_id?)`
- `get_active_leases(property_id?)`
- `get_payment_history(property_id?)`
- `get_open_maintenance(property_id?)`
- `search_documents(query, filters)`

### Proposal Tools

- `draft_maintenance_response(property_id, issue_summary)`
- `propose_maintenance_followup(property_id)`
- `request_human_approval(action_payload)`

Initial write-like behavior should be proposal-only.

## Approval Workflow

Human approval is required for:

- maintenance follow-up actions
- outbound drafted responses if treated as send-ready
- any future mutations

Approval flow:

1. agent produces action proposal
2. backend persists approval request
3. frontend renders approval card
4. user approves or rejects
5. backend calls AI service resume endpoint
6. graph continues from paused state

## Frontend Chat UX

The chat UI should include:

- threaded messages
- loading and streaming states
- suggested prompts by role
- citations panel
- approval cards
- optional "Agent Steps" panel for demo mode

### Demo Mode Panel

Expose:

- selected intent
- tools called
- retrieved documents
- approval decision point

This is important to visibly demonstrate agentic behavior.

## Backend API Requirements

The main backend should expose internal data endpoints the AI service can use.

Examples:

- `GET /api/v1/properties`
- `GET /api/v1/leases`
- `GET /api/v1/payments`
- `GET /api/v1/maintenance/requests`
- `GET /api/v1/documents`

The AI service should expose:

- `POST /ai/chat`
- `GET /ai/chat/history`
- `POST /ai/approve/{action_id}`
- `POST /ai/resume/{action_id}`

## Session and Memory

The AI layer should support short-term memory:

- per-session message history
- previous property references
- previous retrieved context
- pending approval state

Suggested persistence:

- `ai_sessions`
- `ai_messages`
- `ai_approval_requests`

Redis can be used later for checkpointing and resume state, but local DB-backed persistence is enough for the first demo.

## Security and Guardrails

- enforce RBAC in backend code, not only prompts
- filter retrieval by tenant and role
- require approval for proposed actions
- log every tool call
- limit tool inputs to known schemas
- avoid exposing unnecessary PII to prompts

## Observability

Track:

- request id
- session id
- graph node transitions
- tool calls
- retrieved document ids
- model latency
- approval events

These logs should support both debugging and demo narration.

## Recommended Implementation Phases

### Phase 1

- AI service scaffold
- plain OpenAI chat endpoint
- frontend wiring to separate AI service

### Phase 2

- LangGraph orchestration
- intent routing
- backend read tools

### Phase 3

- document ingestion
- embeddings
- vector retrieval
- citations

### Phase 4

- approval-gated action proposals
- pause/resume flow
- approval cards in frontend

### Phase 5

- session persistence
- debug panel for agent steps
- richer summaries and portfolio workflows

## Acceptance Criteria

The first strong demo should satisfy:

- chatbot answers lease, payment, maintenance, and property questions
- at least one scenario uses multiple backend tools
- at least one scenario uses document retrieval with citations
- at least one scenario pauses for approval
- role-aware behavior is enforced
- the UI visibly demonstrates agent orchestration

## Deliverables

- AI service scaffold
- LangGraph workflow implementation
- RAG ingestion pipeline
- OpenAI integration
- frontend AI chat with citations and approvals
- backend tool endpoints and approval persistence

