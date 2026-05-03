"""
agents/node_discovery.py
-------------------------
Discovers the correct n8n node for EVERY step in the workflow plan —
including trigger nodes, logic nodes (IF, Filter, Set, Code),
and action nodes. Works for any use case without hardcoding.
"""

from agents.state import WorkflowState
from services.supabase_service import search_operations_multi, get_node_schema, search_nodes
from services.gemini_client import call_llm_json
import json

# Mapping of logic step types to known n8n node types
# These are always available in n8n — no registry search needed
BUILT_IN_LOGIC_NODES = {
    "n8n-nodes-base.if": {
        "node_type": "n8n-nodes-base.if",
        "node_name": "if",
        "display_name": "IF",
        "description": "Branch workflow based on a condition — true path and false path",
        "default_version": 2,
        "resource": None,
        "operation": None,
        "credentials": [],
        "required_fields": [],
        "search_text": "IF condition branch filter check boolean logic",
    },
    "n8n-nodes-base.filter": {
        "node_type": "n8n-nodes-base.filter",
        "node_name": "filter",
        "display_name": "Filter",
        "description": "Keep only items that match a condition",
        "default_version": 2,
        "resource": None,
        "operation": None,
        "credentials": [],
        "required_fields": [],
        "search_text": "filter keep remove items condition match",
    },
    "n8n-nodes-base.set": {
        "node_type": "n8n-nodes-base.set",
        "node_name": "set",
        "display_name": "Set",
        "description": "Set, map or transform data fields",
        "default_version": 3,
        "resource": None,
        "operation": None,
        "credentials": [],
        "required_fields": [],
        "search_text": "set map transform data fields edit",
    },
    "n8n-nodes-base.code": {
        "node_type": "n8n-nodes-base.code",
        "node_name": "code",
        "display_name": "Code",
        "description": "Run custom JavaScript or Python code",
        "default_version": 2,
        "resource": None,
        "operation": None,
        "credentials": [],
        "required_fields": [],
        "search_text": "code javascript python custom logic function",
    },
    "n8n-nodes-base.switch": {
        "node_type": "n8n-nodes-base.switch",
        "node_name": "switch",
        "display_name": "Switch",
        "description": "Route items to different branches based on multiple conditions",
        "default_version": 3,
        "resource": None,
        "operation": None,
        "credentials": [],
        "required_fields": [],
        "search_text": "switch route multiple conditions branches",
    },
    "n8n-nodes-base.merge": {
        "node_type": "n8n-nodes-base.merge",
        "node_name": "merge",
        "display_name": "Merge",
        "description": "Merge data from multiple branches",
        "default_version": 3,
        "resource": None,
        "operation": None,
        "credentials": [],
        "required_fields": [],
        "search_text": "merge combine join branches data",
    },
    "n8n-nodes-base.httpRequest": {
        "node_type": "n8n-nodes-base.httpRequest",
        "node_name": "httpRequest",
        "display_name": "HTTP Request",
        "description": "Make HTTP requests to any API",
        "default_version": 4,
        "resource": None,
        "operation": None,
        "credentials": [],
        "required_fields": [{"name": "url", "displayName": "URL", "type": "string"}],
        "search_text": "http request api call webhook post get rest",
    },
}

SELECTION_PROMPT = """You are an expert n8n workflow architect.

Given a complete workflow plan with logic steps, select the BEST n8n node for each step.

RULES:
- For trigger steps: find the best trigger node from the candidates
- For logic steps (IF, Filter, Set, Code): use the built-in logic nodes provided
- For action steps: find the best action node from the candidates
- Never invent node types — only use what is in the candidates or built-in list
- Preserve the exact execution order from logic_steps
- For each step, pick the most appropriate resource+operation if applicable

Return JSON:
{
  "selected_nodes": [
    {
      "order": 1,
      "node_type": "n8n-nodes-base.gmailTrigger",
      "display_name": "Gmail Trigger",
      "resource": null,
      "operation": null,
      "role": "trigger",
      "purpose": "Watch for new incoming emails",
      "required_fields": [],
      "credentials": ["gmailOAuth2"]
    },
    {
      "order": 2,
      "node_type": "n8n-nodes-base.if",
      "display_name": "IF",
      "resource": null,
      "operation": null,
      "role": "logic",
      "purpose": "Check if email is from a recruiter based on sender and subject",
      "required_fields": [],
      "credentials": []
    },
    {
      "order": 3,
      "node_type": "n8n-nodes-base.googleSheets",
      "display_name": "Google Sheets",
      "resource": "spreadsheet",
      "operation": "append",
      "role": "action",
      "purpose": "Append recruiter email details to spreadsheet",
      "required_fields": ["spreadsheetId"],
      "credentials": ["googleSheetsOAuth2Api"]
    }
  ]
}
"""


def node_discovery_node(state: WorkflowState) -> dict:
    """
    LangGraph node: Discover the best n8n node for EVERY step in the plan.
    Handles trigger, logic, and action nodes for any use case.
    """
    intent = state.get("intent", {})
    logic_steps = intent.get("logic_steps", [])
    integrations = intent.get("integrations", [])

    print(f"[NodeDiscovery] Finding nodes for {len(logic_steps)} steps...")

    # ── Step 1: Search registry for external service nodes ────────────────────
    service_steps = [
        s for s in logic_steps
        if not s.get("requires_logic_node") and s.get("service") not in BUILT_IN_LOGIC_NODES
    ]
    service_keywords = []
    for step in service_steps:
        service = step.get("service", "")
        if service:
            service_keywords.append(service.lower())
            # Add common variants
            variants = {
                "google sheets": ["sheets", "googlesheets"],
                "gmail": ["gmail"],
                "slack": ["slack"],
                "notion": ["notion"],
                "airtable": ["airtable"],
                "openai": ["openai", "gpt"],
                "gemini": ["gemini"],
            }
            for k, v in variants.items():
                if k in service.lower():
                    service_keywords.extend(v)

    # Deduplicate
    service_keywords = list(set(service_keywords))

    # Search registry
    registry_candidates = search_operations_multi(service_keywords, limit=6) if service_keywords else []
    print(f"[NodeDiscovery] Found {len(registry_candidates)} registry candidates for services")

    # ── Step 2: Collect built-in logic nodes needed ───────────────────────────
    logic_step_data = [s for s in logic_steps if s.get("requires_logic_node")]
    built_in_candidates = []

    for step in logic_step_data:
        suggested = step.get("suggested_n8n_node")
        step_type = step.get("type", "").lower()
        service = step.get("service", "").lower()

        # Match to built-in node
        if suggested and suggested in BUILT_IN_LOGIC_NODES:
            built_in_candidates.append(BUILT_IN_LOGIC_NODES[suggested])
        elif "if" in service or "condition" in step_type or "filter" in step_type:
            built_in_candidates.append(BUILT_IN_LOGIC_NODES["n8n-nodes-base.if"])
        elif "set" in service or "transform" in step_type or "map" in step_type:
            built_in_candidates.append(BUILT_IN_LOGIC_NODES["n8n-nodes-base.set"])
        elif "code" in service or "code" in step_type:
            built_in_candidates.append(BUILT_IN_LOGIC_NODES["n8n-nodes-base.code"])
        elif "switch" in service or "route" in step_type:
            built_in_candidates.append(BUILT_IN_LOGIC_NODES["n8n-nodes-base.switch"])
        elif "http" in service or "api" in step_type:
            built_in_candidates.append(BUILT_IN_LOGIC_NODES["n8n-nodes-base.httpRequest"])
        else:
            # Default to IF for any filter/condition step
            built_in_candidates.append(BUILT_IN_LOGIC_NODES["n8n-nodes-base.if"])

    print(f"[NodeDiscovery] Built-in logic nodes needed: {[n['display_name'] for n in built_in_candidates]}")

    # ── Step 3: Add HTTP Request fallback for missing services ────────────────
    found_services = set()
    for c in registry_candidates:
        display = (c.get("display_name") or "").lower()
        node_type = (c.get("node_type") or "").lower()
        for integ in integrations:
            if integ.lower() in display or integ.lower() in node_type:
                found_services.add(integ.lower())

    http_node = BUILT_IN_LOGIC_NODES["n8n-nodes-base.httpRequest"]
    for integ in integrations:
        if integ.lower() not in found_services:
            print(f"[NodeDiscovery] No native node for '{integ}' → HTTP Request fallback")
            fallback = {
                **http_node,
                "display_name": f"HTTP Request ({integ})",
                "_fallback_for": integ,
            }
            registry_candidates.append(fallback)

    # ── Step 4: Ask Gemini to select best node for each step ──────────────────
    all_candidates = registry_candidates + built_in_candidates

    user_message = f"""
Complete workflow plan:
{json.dumps(logic_steps, indent=2)}

Goal: {intent.get('goal', '')}

Available registry nodes (for external services):
{json.dumps(registry_candidates, indent=2)}

Available built-in logic nodes:
{json.dumps(list(BUILT_IN_LOGIC_NODES.keys()), indent=2)}

Select the best n8n node for EACH step in order.
For logic steps (requires_logic_node=true), use the built-in logic nodes.
For service steps, use the registry candidates.
"""

    try:
        result = call_llm_json(SELECTION_PROMPT, user_message)
        selected_nodes = result.get("selected_nodes", [])

        # Sort by order
        selected_nodes.sort(key=lambda x: x.get("order", 0))

        print(f"[NodeDiscovery] Selected {len(selected_nodes)} nodes:")
        for n in selected_nodes:
            print(f"  {n.get('order')}. [{n.get('role')}] {n.get('display_name')} — {n.get('purpose', '')[:60]}")

        return {
            "selected_nodes": selected_nodes,
            "messages": [
                f"[NodeDiscovery] {len(selected_nodes)} nodes selected: "
                f"{[n.get('display_name') for n in selected_nodes]}"
            ],
        }

    except Exception as e:
        print(f"[NodeDiscovery] LLM error: {e}")
        return {
            "error": f"Node discovery failed: {str(e)}",
            "messages": [f"[NodeDiscovery] ERROR: {e}"],
        }