"""
agents/validator.py
--------------------
Validates the generated n8n workflow JSON before deployment.

Fixes:
1. Built-in logic nodes (IF, Set, Code, Filter, etc.) are always valid
   — they don't need to be in the registry
2. Required field validation is smarter — only validates external service nodes
3. Skips user-config fields (spreadsheetId, sheetId, etc.) — those are expected
"""

from agents.state import WorkflowState
from services.supabase_service import get_node_schema
import json

# These built-in n8n nodes are ALWAYS valid — skip registry check
BUILT_IN_NODES = {
    "n8n-nodes-base.if",
    "n8n-nodes-base.filter",
    "n8n-nodes-base.set",
    "n8n-nodes-base.code",
    "n8n-nodes-base.switch",
    "n8n-nodes-base.merge",
    "n8n-nodes-base.httpRequest",
    "n8n-nodes-base.noOp",
    "n8n-nodes-base.wait",
    "n8n-nodes-base.splitInBatches",
    "n8n-nodes-base.manualTrigger",
    "n8n-nodes-base.scheduleTrigger",
    "n8n-nodes-base.webhook",
    "n8n-nodes-base.respondToWebhook",
    "n8n-nodes-base.stickyNote",
    "n8n-nodes-base.start",
}

# Fields that are user-config gaps — NOT structural errors
# These require user input and should not fail validation
USER_CONFIG_FIELDS = {
    "spreadsheetId", "sheetId", "sheetName", "range",
    "lookupColumn", "lookupValue", "id", "documentId",
    "databaseId", "boardId", "listId", "workspaceId",
    "projectId", "tableId", "formId", "calendarId",
    "channelId", "teamId", "userId", "groupId",
    "folderId", "fileId", "messageId", "threadId",
    "webhookId", "apiKey", "token", "secret",
}


def validator_node(state: WorkflowState) -> dict:
    """
    LangGraph node: Validate the generated workflow JSON.
    """
    workflow_json = state.get("generated_workflow_json", {})
    print("[Validator] Validating workflow JSON...")

    errors = []

    # ── 1. Top-level structure ────────────────────────────────────────────────
    if not workflow_json:
        return {
            "validation_errors": ["Workflow JSON is empty"],
            "validation_passed": False,
            "messages": ["[Validator] FAILED: Empty workflow JSON"],
        }

    if not workflow_json.get("name"):
        errors.append("Workflow is missing a name")

    nodes = workflow_json.get("nodes", [])
    if not nodes:
        errors.append("Workflow has no nodes")

    connections = workflow_json.get("connections", {})

    # ── 2. Node validation ────────────────────────────────────────────────────
    node_names = set()
    for i, node in enumerate(nodes):
        node_name = node.get("name", f"Node_{i}")
        node_type = node.get("type", "")
        node_names.add(node_name)

        # Required node fields
        if not node_type:
            errors.append(f"Node '{node_name}' is missing 'type'")
            continue

        if not node.get("typeVersion"):
            errors.append(f"Node '{node_name}' is missing 'typeVersion'")

        if not node.get("position"):
            errors.append(f"Node '{node_name}' is missing 'position'")

        # ── Built-in nodes are always valid — skip registry check ──
        if node_type in BUILT_IN_NODES:
            continue

        # ── External service nodes — validate against registry ──
        schema = get_node_schema(node_type)
        if not schema:
            errors.append(
                f"Node '{node_name}' has unknown type '{node_type}' — not in registry"
            )
            continue

        # Check required fields — but skip user-config fields
        params = node.get("parameters", {})
        resource = params.get("resource")
        operation = params.get("operation")

        raw_required = schema.get("required_fields", [])
        if isinstance(raw_required, str):
            try:
                raw_required = json.loads(raw_required)
            except Exception:
                raw_required = []

        for field in raw_required:
            field_name = field.get("name") if isinstance(field, dict) else field
            if not field_name:
                continue

            # Skip user-config fields — these are expected to be missing
            if field_name in USER_CONFIG_FIELDS:
                continue

            # Skip resource and operation themselves
            if field_name in ("resource", "operation"):
                continue

            # Check if field is present in parameters
            if field_name not in params:
                errors.append(
                    f"Node '{node_name}' ({resource}/{operation}) "
                    f"missing required field: '{field_name}'"
                )

    # ── 3. Connection validation ──────────────────────────────────────────────
    for from_node, conn_data in connections.items():
        if from_node not in node_names:
            errors.append(f"Connection references unknown source node: '{from_node}'")
            continue

        main_outputs = conn_data.get("main", [])
        for output_group in main_outputs:
            for conn in output_group:
                to_node = conn.get("node")
                if to_node and to_node not in node_names:
                    errors.append(
                        f"Connection from '{from_node}' references unknown target: '{to_node}'"
                    )

    # ── 4. Active flag ────────────────────────────────────────────────────────
    if workflow_json.get("active") is True:
        errors.append("Workflow active flag must be False for draft creation")

    # ── Result ────────────────────────────────────────────────────────────────
    passed = len(errors) == 0

    if passed:
        print(f"[Validator] ✔ PASSED — {len(nodes)} nodes, {len(connections)} connections")
    else:
        print(f"[Validator] ✘ FAILED — {len(errors)} error(s):")
        for e in errors:
            print(f"  → {e}")

    return {
        "validation_errors": errors,
        "validation_passed": passed,
        "messages": [
            f"[Validator] {'PASSED' if passed else 'FAILED'}: {len(errors)} error(s)"
        ],
    }