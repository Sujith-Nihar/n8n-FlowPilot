"""
agents/parameter_filler.py
---------------------------
Fills node parameters based on real schema fields and user intent.

KEY RULES:
- Trigger nodes do NOT get resource/operation — they have their own parameter structure
- Logic nodes (IF, Set, Code) get their own specific parameter structure
- Never put 'name' inside parameters — that belongs to the node object itself
- Only use parameter names that exist in the actual node schema
"""

from agents.state import WorkflowState
from services.gemini_client import call_llm_json
import json

# Node types that ARE triggers — don't inject resource/operation into them
TRIGGER_NODE_TYPES = {
    "n8n-nodes-base.gmailTrigger",
    "n8n-nodes-base.googleSheetsTrigger",
    "n8n-nodes-base.slackTrigger",
    "n8n-nodes-base.webhookTrigger",
    "n8n-nodes-base.scheduleTrigger",
    "n8n-nodes-base.manualTrigger",
    "n8n-nodes-base.webhook",
    "n8n-nodes-base.cron",
    "n8n-nodes-base.emailReadImap",
}

# Built-in logic nodes — fixed parameter templates
LOGIC_NODE_PARAMS = {
    "n8n-nodes-base.if": {
        "conditions": {
            "options": {
                "caseSensitive": True,
                "leftValue": "",
                "typeValidation": "strict"
            },
            "conditions": [
                {
                    "id": "condition_1",
                    "leftValue": "={{ $json.from }}",
                    "rightValue": "recruiter",
                    "operator": {
                        "type": "string",
                        "operation": "contains"
                    }
                }
            ],
            "combinator": "and"
        }
    },
    "n8n-nodes-base.filter": {
        "conditions": {
            "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict"},
            "conditions": [],
            "combinator": "and"
        }
    },
    "n8n-nodes-base.set": {
        "mode": "manual",
        "duplicateItem": False,
        "assignments": {"assignments": []},
        "options": {}
    },
    "n8n-nodes-base.code": {
        "jsCode": "// Your code here\nreturn items;"
    },
    "n8n-nodes-base.switch": {
        "mode": "rules",
        "output": "single",
        "rules": {"rules": []},
        "options": {}
    },
    "n8n-nodes-base.merge": {
        "mode": "combine",
        "combinationMode": "multiplex",
        "options": {}
    },
}

FILLER_PROMPT = """You are an expert n8n workflow parameter specialist.

For each node, fill parameters based on the user's intent and node schema.

CRITICAL RULES:
1. NEVER include 'name' as a parameter — name is a node-level field, not a parameter
2. NEVER include 'resource' or 'operation' for trigger nodes (gmailTrigger, webhookTrigger, etc.)
3. For action nodes (googleSheets, slack, etc.) — DO include resource and operation
4. Only use parameter names that exist in the schema
5. For missing user-specific values (spreadsheetId, credentials) — omit them entirely, don't use placeholders
6. Logic nodes (IF, Set, Code) parameters are handled separately — skip them

For Gmail Trigger — correct parameters look like:
{
  "filters": {},
  "options": {}
}

For Google Sheets append — correct parameters look like:
{
  "resource": "sheet",
  "operation": "append",
  "documentId": {"__rl": true, "value": "", "mode": "list"},
  "sheetName": {"__rl": true, "value": "gid=0", "mode": "list"},
  "columns": {"mappingMode": "autoMapInputData", "value": {}, "matchingColumns": [], "schema": []},
  "options": {}
}

Return JSON:
{
  "filled_parameters": {
    "Gmail Trigger": {
      "filters": {},
      "options": {}
    },
    "Google Sheets": {
      "resource": "sheet",
      "operation": "append",
      "documentId": {"__rl": true, "value": "", "mode": "list"},
      "sheetName": {"__rl": true, "value": "gid=0", "mode": "list"},
      "columns": {"mappingMode": "autoMapInputData", "value": {}, "matchingColumns": [], "schema": []},
      "options": {}
    }
  }
}

Only include nodes that are NOT logic nodes (not IF, Set, Code, Filter, Switch).
"""


def parameter_filler_node(state: WorkflowState) -> dict:
    """
    LangGraph node: Fill parameters for each node based on schema and intent.
    """
    intent = state.get("intent", {})
    workflow_plan = state.get("workflow_plan", {})
    node_schemas = state.get("node_schemas", {})
    selected_nodes = state.get("selected_nodes", [])

    nodes_plan = workflow_plan.get("nodes_plan", [])
    print(f"[ParameterFiller] Filling parameters for {len(nodes_plan)} nodes...")

    # ── Separate logic nodes from service nodes ────────────────────────────────
    service_nodes = []
    logic_node_params = {}

    for node in nodes_plan:
        node_type = node.get("node_type", "")

        # Logic nodes — use fixed templates
        if node_type in LOGIC_NODE_PARAMS:
            logic_node_params[node.get("display_name", node_type)] = LOGIC_NODE_PARAMS[node_type].copy()
            continue

        service_nodes.append(node)

    # ── Build schema summaries for service nodes ───────────────────────────────
    schema_summaries = {}
    for node in service_nodes:
        node_type = node.get("node_type")
        schema = node_schemas.get(node_type, {})

        props = schema.get("properties", [])
        if isinstance(props, str):
            try:
                props = json.loads(props)
            except Exception:
                props = []

        is_trigger = node_type in TRIGGER_NODE_TYPES or "trigger" in node_type.lower()

        summary_fields = []
        for p in (props if isinstance(props, list) else [])[:20]:
            if isinstance(p, dict) and p.get("name") != "name":
                summary_fields.append({
                    "name": p.get("name"),
                    "type": p.get("type"),
                    "required": p.get("required", False),
                    "default": p.get("default"),
                })

        schema_summaries[node.get("display_name", node_type)] = {
            "node_type": node_type,
            "is_trigger": is_trigger,
            "role": node.get("role"),
            "resource": None if is_trigger else node.get("resource"),
            "operation": None if is_trigger else node.get("operation"),
            "properties_sample": summary_fields[:15],
        }

    # ── Ask Gemini to fill service node parameters ────────────────────────────
    filled_parameters = {}

    if service_nodes:
        user_message = f"""
User intent: {intent.get('goal', '')}

Service nodes to fill parameters for:
{json.dumps(schema_summaries, indent=2)}

Nodes plan context:
{json.dumps([{
    'display_name': n.get('display_name'),
    'node_type': n.get('node_type'),
    'role': n.get('role'),
    'purpose': n.get('purpose'),
} for n in service_nodes], indent=2)}

Fill clean, valid parameters for each service node.
Remember: NO 'name' field in parameters. Trigger nodes get NO resource/operation.
"""
        try:
            result = call_llm_json(FILLER_PROMPT, user_message)
            filled_parameters = result.get("filled_parameters", {})
        except Exception as e:
            print(f"[ParameterFiller] LLM error: {e}")
            # Fallback: minimal safe parameters per node
            for node in service_nodes:
                node_type = node.get("node_type", "")
                display_name = node.get("display_name", "")
                is_trigger = node_type in TRIGGER_NODE_TYPES or "trigger" in node_type.lower()
                if is_trigger:
                    filled_parameters[display_name] = {"filters": {}, "options": {}}
                else:
                    filled_parameters[display_name] = {
                        "resource": node.get("resource") or "default",
                        "operation": node.get("operation") or "default",
                        "options": {}
                    }

    # ── Merge logic node params ────────────────────────────────────────────────
    filled_parameters.update(logic_node_params)

    # ── Log results ───────────────────────────────────────────────────────────
    print(f"[ParameterFiller] Filled parameters for {len(filled_parameters)} nodes")
    for node_name, params in filled_parameters.items():
        param_keys = list(params.keys())
        print(f"  → {node_name}: {param_keys}")

    return {
        "filled_parameters": filled_parameters,
        "messages": [f"[ParameterFiller] Filled {len(filled_parameters)} nodes"],
    }