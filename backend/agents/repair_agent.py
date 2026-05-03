"""
agents/repair_agent.py
-----------------------
Attempts to fix validation errors in the generated workflow JSON.
Uses Gemini to understand and repair each error.
"""

from agents.state import WorkflowState
from services.gemini_client import call_llm_json
import json

REPAIR_PROMPT = """You are an expert n8n workflow repair specialist.

A generated workflow JSON has validation errors. Fix them.

Rules:
- Only fix what the errors specify
- Keep all node types exactly as they are — do not change node_type values
- Keep all node names exactly as they are
- If a required field is missing, add a reasonable placeholder value
- If active=true, set it to false
- If a connection references a non-existent node, remove that connection
- Return the complete fixed workflow JSON

Return the corrected workflow JSON object directly.
"""


def repair_agent_node(state: WorkflowState) -> dict:
    """
    LangGraph node: Attempt to repair validation errors in the workflow JSON.
    """
    workflow_json = state.get("generated_workflow_json", {})
    validation_errors = state.get("validation_errors", [])
    repair_attempts = state.get("repair_attempts", 0)

    print(f"[RepairAgent] Repair attempt {repair_attempts + 1} — {len(validation_errors)} errors to fix")

    user_message = f"""
Validation errors found:
{json.dumps(validation_errors, indent=2)}

Current workflow JSON with errors:
{json.dumps(workflow_json, indent=2)}

Fix all validation errors and return the corrected workflow JSON.
"""

    try:
        repaired = call_llm_json(REPAIR_PROMPT, user_message)

        # Ensure active is always False
        repaired["active"] = False

        print(f"[RepairAgent] Repair complete — {len(repaired.get('nodes', []))} nodes")

        return {
            "generated_workflow_json": repaired,
            "repair_attempts": repair_attempts + 1,
            "messages": [f"[RepairAgent] Repair attempt {repair_attempts + 1} complete"],
        }

    except Exception as e:
        print(f"[RepairAgent] Error: {e}")
        return {
            "repair_attempts": repair_attempts + 1,
            "messages": [f"[RepairAgent] ERROR on attempt {repair_attempts + 1}: {e}"],
        }
