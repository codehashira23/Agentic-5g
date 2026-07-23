"""Workflow request/response schemas."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CreateWorkflowRequest(BaseModel):
    goal: str = Field(..., min_length=1, max_length=2000)
    metadata: dict[str, Any] = Field(default_factory=dict)


class WorkflowResponse(BaseModel):
    id: str
    goal: str
    status: str
    stage: str
    created_at: str
    correlation_id: str
    trigger: str = "user"


class WorkflowControlRequest(BaseModel):
    action: str  # pause | resume | interrupt | retry_step | confirm
    confirmation_token: str | None = None


class TraceEntryResponse(BaseModel):
    stage: str
    agent_role: str
    rationale: str = ""
    ts: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: float = 0.0
