from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class AIChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class AIActionCard(BaseModel):
    action_id: str
    type: str
    title: str
    description: str
    status: Literal["pending", "approved", "rejected"]


class AIDebugInfo(BaseModel):
    intent: str = ""
    tools_called: list[str] = Field(default_factory=list)
    citations: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)


class AIMessageOut(BaseModel):
    id: str
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime
    action_card: Optional[AIActionCard] = None
    debug_info: Optional[AIDebugInfo] = None


class AIChatResponse(BaseModel):
    session_id: str
    message: AIMessageOut


class AIChatHistoryResponse(BaseModel):
    session_id: Optional[str]
    messages: list[AIMessageOut]


class AIApprovalResponse(BaseModel):
    action_id: str
    status: Literal["approved", "rejected"]
    message: str


class SupportMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class SupportChatRequest(BaseModel):
    message: str
    history: list[SupportMessage] = []


class SupportChatResponse(BaseModel):
    response: str
