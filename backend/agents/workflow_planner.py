"""
agents/workflow_planner.py
--------------------------
Plans the complete n8n workflow structure for any use case.
Reasons about data flow between ALL nodes including logic nodes.
Never hardcodes use cases — uses the intent and selected nodes to plan.
"""

from agents.state import WorkflowState
from services.gemini_client import call_llm_json
import json

PLANNER_PROMPT = """You are an expert n8n workflow architect.

Plan the COMPLETE workflow structure from the selected nodes.
Think carefully about how DATA FLOWS between each node.

CRITICAL RULES:
1. Preserve the exact node order from selected_nodes
2. Every node connects to the next via main output → main input
3. IF nodes have TWO outputs: output 0 = true branch, output 1 = false branch
   - true branch connects to the next action node
   - false branch connects to nothing (end) unless specified
4. Filter nodes have ONE output — items that passed the filter
5. Position nodes left to right: x starts at 250, increases by 280 per node
6. y position: 300 for main flow, 500 for false/alternative branches
7. Use exact node_type values from selected_nodes — never modify them

For IF nodes — think about what condition to set:
- Analyze the PURPOSE of the IF node from the intent
- The condition should use n8n expression syntax: {{$json.fieldName}}
- Example: {{$json.from}} contains "recruiter" 
- Example: {{$json.amount}} > 1000

Return JSON:
{
  "name": "Gmail Recruiter Filter to Sheets",
  "nodes_plan": [
    {
      "order": 1,
      "node_type": "n8n-nodes-base.gmailTrigger",
      "display_name": "Gmail Trigger",
      "role": "trigger",
      "resource": null,
      "operation": null,
      "position_x": 250,
      "position_y": 300,
      "purpose": "Watch for new incoming emails",
      "data_output": "email fields: from, subject, body, date",
      "params_to_fill": {}
    },
    {
      "order": 2,
      "node_type": "n8n-nodes-base.if",
      "display_name": "IF",
      "role": "logic",
      "resource": null,
      "operation": null,
      "position_x": 530,
      "position_y": 300,
      "purpose": "Check if email is from a recruiter",
      "condition_field": "from",
      "condition_type": "contains",
      "condition_value": "recruiter",
      "data_output": "same email data — only passes if condition is true",
      "params_to_fill": {
        "conditions": {
          "options": {"caseSensitive": false},
          "conditions": [
            {
              "id": "condition1",
              "leftValue": "={{$json.from}}",
              "rightValue": "recruiter",
              "operator": {"type": "string", "operation": "contains"}
            }
          ],
          "combinator": "or"
        }
      }
    },
    {
      "order": 3,
      "node_type": "n8n-nodes-base.googleSheets",
      "display_name": "Google Sheets",
      "role": "action",
      "resource": "spreadsheet",
      "operation": "append",
      "position_x": 810,
      "position_y": 300,
      "purpose": "Append recruiter email to spreadsheet",
      "data_output": "confirmation of appended row",
      "params_to_fill": {
        "resource": "spreadsheet",
        "operation": "append"
      }
    }
  ],
  "connections": [
    {
      "from_node": "Gmail Trigger",
      "from_output": 0,
      "to_node": "IF",
      "to_input": 0
    },
    {
      "from_node": "IF",
      "from_output": 0,
      "to_node": "Google Sheets",
      "to_input": 0
    }
  ]
}

IMPORTANT for connections:
- IF node: output 0 = true branch, output 1 = false branch
- Most nodes: output 0 is the only output
- Only connect false branch if there's something to do on false path
- Think carefully about which output connects to which node
"""


def workflow_planner_node(state: WorkflowState) -> dict:
    """
    LangGraph node: Plan the complete workflow with all nodes and connections.
    """
    intent = state.get("intent", {})
    selected_nodes = state.get("selected_nodes", [])
    node_schemas = state.get("node_schemas", {})

    workflow_name = intent.get("workflow_name", "Generated Workflow")
    print(f"[WorkflowPlanner] Planning: {workflow_name} ({len(selected_nodes)} nodes)")

    user_message = f"""
Workflow goal: {intent.get('goal', '')}
Workflow name: {workflow_name}
Complexity: {intent.get('complexity', 'medium')}

Selected nodes in order:
{json.dumps(selected_nodes, indent=2)}

Original logic steps from intent:
{json.dumps(intent.get('logic_steps', []), indent=2)}

Plan the complete workflow:
1. Set correct position for each node (left to right, 280px apart)
2. Define the params_to_fill for each node based on its purpose
3. For IF nodes: define the actual condition using n8n expression syntax
4. Define all connections including which output (0=true, 1=false for IF)
5. Think about what data flows from each node to the next

The workflow must solve: "{intent.get('goal', '')}"
"""

    try:
        plan = call_llm_json(PLANNER_PROMPT, user_message)

        nodes_plan = plan.get("nodes_plan", [])
        connections = plan.get("connections", [])

        print(f"[WorkflowPlanner] Plan: {len(nodes_plan)} nodes, {len(connections)} connections")
        for node in nodes_plan:
            print(f"  {node.get('order')}. {node.get('display_name')} [{node.get('role')}] — {node.get('purpose', '')[:60]}")

        return {
            "workflow_plan": plan,
            "messages": [
                f"[WorkflowPlanner] Planned '{plan.get('name')}': "
                f"{len(nodes_plan)} nodes, {len(connections)} connections"
            ],
        }

    except Exception as e:
        print(f"[WorkflowPlanner] Error: {e}")
        return {
            "error": f"Workflow planning failed: {str(e)}",
            "messages": [f"[WorkflowPlanner] ERROR: {e}"],
        }