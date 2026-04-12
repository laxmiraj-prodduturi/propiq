from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class AIChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class AIActionCard(BaseModel):
    action_id: str
    type: str
    title: str
    description: str
    status: Literal["pending", "approved", "rejected"]


class AIMessageOut(BaseModel):
    id: str
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime
    action_card: AIActionCard | None = None


class AIChatResponse(BaseModel):
    session_id: str
    message: AIMessageOut


class AIChatHistoryResponse(BaseModel):
    session_id: str | None
    messages: list[AIMessageOut]


class AIApprovalResponse(BaseModel):
    action_id: str
    status: Literal["approved", "rejected"]
    message: str


class UserContext(BaseModel):
    user_id: str
    role: str
    tenant_id: str


class RetrievedDocument(BaseModel):
    document_id: str
    title: str
    snippet: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolCallRecord(BaseModel):
    name: str
    input: dict[str, Any] = Field(default_factory=dict)
    output_summary: str


class ProposedAction(BaseModel):
    action_id: str
    type: str
    title: str
    description: str
    requires_approval: bool = True


class SupportMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class SupportChatRequest(BaseModel):
    message: str
    history: list[SupportMessage] = []


class SupportChatResponse(BaseModel):
    response: str
