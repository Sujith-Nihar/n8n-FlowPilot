"""
api/models.py
-------------
Pydantic request/response models for the FastAPI endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional
import uuid


class ChatRequest(BaseModel):
    message: str = Field(..., description="User's natural language automation request")
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Chat session ID")
    mode: str = Field(default="create", description="'create' or 'update'")
    credential_hints: Optional[list[str]] = Field(default=None, description="Existing n8n credential names to attach")
    workflow_id: Optional[str] = Field(default=None, description="n8n workflow ID (required for update mode)")


class ChatResponse(BaseModel):
    session_id: str
    response: str
    workflow_name: Optional[str] = None
    workflow_id: Optional[str] = None
    n8n_url: Optional[str] = None
    nodes: Optional[list[str]] = None
    missing_credentials: Optional[list[str]] = None
    reflection_score: Optional[int] = None
    validation_passed: Optional[bool] = None
    status: str = "success"
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    n8n_connected: bool
    supabase_connected: bool
    registry_stats: dict
