"""
agents/state.py
---------------
Central LangGraph state shared across all agents.
Every agent reads from and writes to this state.
"""

from typing import TypedDict, Optional, Annotated
import operator


class WorkflowState(TypedDict):
    # ─── Input ───────────────────────────────────────────────
    user_prompt: str                        # Raw user message
    session_id: str                         # Chat session ID
    mode: str                               # "create" or "update"
    credential_hints: Optional[list]        # User-provided credential names

    # ─── Fetched for updates ──────────────────────────────────
    current_workflow_json: Optional[dict]   # Fetched from n8n for updates

    # ─── Intent ───────────────────────────────────────────────
    intent: Optional[dict]
    # {
    #   "goal": "Check Gmail for recruiter emails...",
    #   "integrations": ["Gmail", "Gemini", "Slack", "Google Sheets"],
    #   "trigger": "gmail",
    #   "actions": ["summarize", "send_slack", "store_sheets"],
    #   "mode": "create"
    # }

    # ─── Node Discovery ───────────────────────────────────────
    selected_nodes: Optional[list]
    # [
    #   {
    #     "node_type": "n8n-nodes-base.gmail",
    #     "display_name": "Gmail",
    #     "resource": "message",
    #     "operation": "getAll",
    #     "role": "trigger",
    #     "required_fields": [...],
    #     "credentials": [...]
    #   }
    # ]

    # ─── Schema Retrieval ─────────────────────────────────────
    node_schemas: Optional[dict]
    # { "n8n-nodes-base.gmail": { full node schema } }

    # ─── Workflow Plan ────────────────────────────────────────
    workflow_plan: Optional[dict]
    # {
    #   "name": "Gmail Recruiter Summary",
    #   "nodes": [ { node_type, role, position, params } ],
    #   "connections": [ { from, to } ]
    # }

    # ─── Parameter Filling ────────────────────────────────────
    filled_parameters: Optional[dict]
    # { "Gmail": { "operation": "getAll", "filters": {...} } }

    # ─── Workflow JSON ────────────────────────────────────────
    generated_workflow_json: Optional[dict]   # Final n8n workflow JSON

    # ─── Credentials ─────────────────────────────────────────
    required_credentials: Optional[list]      # List of missing credential names
    credential_mapping: Optional[dict]        # name → { id, name } if provided

    # ─── Validation ───────────────────────────────────────────
    validation_errors: Optional[list]         # List of validation error strings
    validation_passed: bool                   # True if workflow passed validation

    # ─── Reflection ───────────────────────────────────────────
    reflection_feedback: Optional[str]        # Reflection agent feedback
    reflection_score: Optional[int]           # 1-10 quality score
    reflection_attempts: int                  # How many reflection loops ran
    repair_attempts: int                      # How many repair loops ran

    # ─── Deployment ───────────────────────────────────────────
    deployment_result: Optional[dict]
    # {
    #   "workflow_id": "abc123",
    #   "workflow_name": "Gmail Recruiter Summary",
    #   "status": "inactive",
    #   "n8n_url": "http://localhost:5678/workflow/abc123"
    # }

    # ─── Final Response ───────────────────────────────────────
    final_response: Optional[str]             # Human-readable response to user
    error: Optional[str]                      # Error message if something failed

    # ─── Message History ──────────────────────────────────────
    messages: Annotated[list, operator.add]   # Accumulated agent messages/logs
