"""
agents/workflow_builder.py
---------------------------
Builds the final valid n8n workflow JSON.

KEY FIXES:
- Correct typeVersion per node type (n8n is strict about this)
- Never put 'name' field inside parameters
- Clean parameters before building (remove invalid fields)
- Correct position format ([x, y] not {x, y})
- Valid connections structure
- Always active: false
"""

from agents.state import WorkflowState
import uuid
import json

# Correct typeVersion for known node types
# n8n will silently fail to render nodes with wrong typeVersion
NODE_TYPE_VERSIONS = {
    # Gmail
    "n8n-nodes-base.gmail":                 2,
    "n8n-nodes-base.gmailTrigger":          1,
    # Google
    "n8n-nodes-base.googleSheets":          4,
    "n8n-nodes-base.googleSheetsTrigger":   1,
    "n8n-nodes-base.googleDrive":           3,
    "n8n-nodes-base.googleCalendar":        2,
    "n8n-nodes-base.gmail":                 2,
    # Logic/core
    "n8n-nodes-base.if":                    2,
    "n8n-nodes-base.filter":               2,
    "n8n-nodes-base.set":                   3,
    "n8n-nodes-base.code":                  2,
    "n8n-nodes-base.switch":               3,
    "n8n-nodes-base.merge":                3,
    "n8n-nodes-base.httpRequest":           4,
    "n8n-nodes-base.webhook":              2,
    "n8n-nodes-base.scheduleTrigger":       1,
    "n8n-nodes-base.manualTrigger":         1,
    "n8n-nodes-base.noOp":                 1,
    "n8n-nodes-base.wait":                  1,
    "n8n-nodes-base.splitInBatches":        3,
    "n8n-nodes-base.respondToWebhook":      1,
    # Comm
    "n8n-nodes-base.slack":                 2,
    "n8n-nodes-base.slackTrigger":          1,
    "n8n-nodes-base.telegram":             1,
    "n8n-nodes-base.discord":              2,
    # CRM / PM
    "n8n-nodes-base.notion":               2,
    "n8n-nodes-base.airtable":             3,
    "n8n-nodes-base.hubspot":              2,
    "n8n-nodes-base.asana":               1,
    "n8n-nodes-base.trello":              1,
    "n8n-nodes-base.jira":               1,
    "n8n-nodes-base.linear":             1,
    # AI
    "n8n-nodes-base.openAi":              1,
    # DB
    "n8n-nodes-base.postgres":            2,
    "n8n-nodes-base.mysql":              2,
    "n8n-nodes-base.mongoDb":            1,
    # Files
    "n8n-nodes-base.readBinaryFile":     1,
    "n8n-nodes-base.writeBinaryFile":    1,
}

# Fields that must NEVER appear inside node parameters
INVALID_PARAM_FIELDS = {
    "name",           # belongs to node object, not parameters
    "_missing",       # internal tracking field
    "_is_fallback",   # internal tracking field
    "_fallback_for",  # internal tracking field
}


def get_type_version(node_type: str, schema_version=None) -> int:
    """Get the correct typeVersion for a node type."""
    # Check our whitelist first
    if node_type in NODE_TYPE_VERSIONS:
        return NODE_TYPE_VERSIONS[node_type]

    # Try schema version
    if schema_version:
        try:
            v = float(schema_version)
            return max(1, int(v))
        except (ValueError, TypeError):
            pass

    return 1  # Default safe fallback


def clean_parameters(params: dict) -> dict:
    """
    Remove invalid fields from parameters.
    """
    if not isinstance(params, dict):
        return {}

    cleaned = {}
    for k, v in params.items():
        # Skip invalid fields
        if k in INVALID_PARAM_FIELDS:
            continue
        # Skip None values for cleanliness
        if v is None:
            continue
        cleaned[k] = v

    return cleaned


def build_node(node_plan: dict, filled_params: dict, node_schemas: dict, idx: int) -> dict:
    """
    Build a single clean n8n node object.
    """
    node_type = node_plan.get("node_type", "n8n-nodes-base.noOp")
    display_name = node_plan.get("display_name", f"Node {idx + 1}")
    position_x = node_plan.get("position_x", 250 + idx * 280)
    position_y = node_plan.get("position_y", 300)

    # Get schema for this node
    schema = node_schemas.get(node_type, {})

    # Get schema defaults safely
    schema_defaults = {}
    raw_defaults = schema.get("defaults", {})
    if isinstance(raw_defaults, str):
        try:
            schema_defaults = json.loads(raw_defaults)
        except Exception:
            schema_defaults = {}
    elif isinstance(raw_defaults, dict):
        schema_defaults = raw_defaults

    # Get correct typeVersion
    schema_version = schema.get("default_version") or node_plan.get("default_version")
    type_version = get_type_version(node_type, schema_version)

    # Get filled parameters for this node
    params = filled_params.get(display_name, {})

    # Clean parameters — remove invalid fields
    clean_params = clean_parameters(params)

    # Apply schema defaults for any unset optional fields
    for k, v in schema_defaults.items():
        if k not in clean_params and k not in INVALID_PARAM_FIELDS and v is not None:
            clean_params[k] = v

    # Build the node object — matches n8n's exact format
    node_obj = {
        "id": str(uuid.uuid4()),
        "name": display_name,
        "type": node_type,
        "typeVersion": type_version,
        "position": [position_x, position_y],
        "parameters": clean_params,
    }

    return node_obj


def build_connections(connections_plan: list, nodes: list) -> dict:
    """
    Build n8n connections object.
    Format: { "NodeName": { "main": [[{ "node": "NextNode", "type": "main", "index": 0 }]] } }
    """
    connections = {}
    node_names = {n["name"] for n in nodes}

    for conn in connections_plan:
        from_node = conn.get("from_node")
        to_node = conn.get("to_node")
        from_output = conn.get("from_output", 0)
        to_input = conn.get("to_input", 0)

        if not from_node or not to_node:
            continue
        if from_node not in node_names or to_node not in node_names:
            print(f"  [Builder] Skipping invalid connection: {from_node} → {to_node}")
            continue

        if from_node not in connections:
            connections[from_node] = {"main": []}

        # Extend output array to needed size
        while len(connections[from_node]["main"]) <= from_output:
            connections[from_node]["main"].append([])

        connections[from_node]["main"][from_output].append({
            "node": to_node,
            "type": "main",
            "index": to_input,
        })

    return connections


def workflow_builder_node(state: WorkflowState) -> dict:
    """
    LangGraph node: Build the final n8n workflow JSON.
    """
    intent = state.get("intent", {})
    workflow_plan = state.get("workflow_plan", {})
    filled_parameters = state.get("filled_parameters", {})
    node_schemas = state.get("node_schemas", {})

    workflow_name = (
        workflow_plan.get("name")
        or intent.get("workflow_name")
        or "Generated Workflow"
    )
    nodes_plan = workflow_plan.get("nodes_plan", [])
    connections_plan = workflow_plan.get("connections", [])

    print(f"[WorkflowBuilder] Building: '{workflow_name}' ({len(nodes_plan)} nodes)")

    # ── Build nodes ───────────────────────────────────────────────────────────
    nodes = []
    for idx, node_plan in enumerate(nodes_plan):
        try:
            node_obj = build_node(node_plan, filled_parameters, node_schemas, idx)
            nodes.append(node_obj)
            print(
                f"  → {node_obj['name']} | type: {node_obj['type']} "
                f"| v{node_obj['typeVersion']} | params: {list(node_obj['parameters'].keys())}"
            )
        except Exception as e:
            print(f"  → ERROR building {node_plan.get('display_name')}: {e}")

    # ── Build connections ─────────────────────────────────────────────────────
    connections = build_connections(connections_plan, nodes)

    # ── Build final workflow JSON ─────────────────────────────────────────────
    workflow_json = {
        "name": workflow_name,
        "nodes": nodes,
        "connections": connections,
        "active": False,
        "settings": {
            "executionOrder": "v1",
            "saveManualExecutions": True,
            "callerPolicy": "workflowsFromSameOwner",
            "errorWorkflow": "",
        },
        "staticData": None,
    }

    # ── Print full JSON for verification ─────────────────────────────────────
    print(f"\n[WorkflowBuilder] ── WORKFLOW JSON PREVIEW ──")
    for node in nodes:
        print(f"  Node: {node['name']}")
        print(f"    type:        {node['type']}")
        print(f"    typeVersion: {node['typeVersion']}")
        print(f"    position:    {node['position']}")
        print(f"    parameters:  {json.dumps(node['parameters'])[:200]}")
    print(f"  Connections: {json.dumps(connections)[:300]}")
    print(f"[WorkflowBuilder] ─────────────────────────────\n")

    return {
        "generated_workflow_json": workflow_json,
        "messages": [
            f"[WorkflowBuilder] Built '{workflow_name}': "
            f"{len(nodes)} nodes, {len(connections)} connections"
        ],
    }