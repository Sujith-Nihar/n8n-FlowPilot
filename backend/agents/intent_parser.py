"""
agents/intent_parser.py
------------------------
Parses the user's natural language prompt into a structured intent.
Reasons about the FULL solution — including filters, conditions,
transformations, and intermediate logic — for ANY use case.
"""

from agents.state import WorkflowState
from services.gemini_client import call_llm_json

SYSTEM_PROMPT = """You are an expert automation solutions architect who deeply understands n8n.

Your job is to analyze a user's automation request and think like a senior developer
solving the actual problem end-to-end.

CRITICAL THINKING PROCESS:
1. What starts the workflow? (trigger)
2. What data comes in from the trigger?
3. Does anything need to be FILTERED or CHECKED before proceeding?
4. Does data need to be TRANSFORMED or ENRICHED?
5. What CONDITIONS determine different paths?
6. What are the final OUTPUT actions?

For every step ask: "Is there implicit logic the user didn't explicitly state
but clearly needs?" For example:
- "recruiter emails" → needs a filter/condition to check if email is from recruiter
- "high priority tickets" → needs a filter on ticket priority
- "new customers only" → needs a condition to check if customer is new
- "large orders" → needs a filter on order amount threshold
- "failed payments" → needs a condition to check payment status
- "summarize with AI" → needs an HTTP Request or AI node in between

n8n LOGIC NODES available for intermediate steps:
- IF: branch workflow based on a condition (true/false paths)
- Filter: keep only items matching a condition
- Switch: multiple condition branches
- Set: transform or set/map data fields
- Code: custom JavaScript logic for complex transformations
- Merge: combine data from multiple branches
- HTTP Request: call any external API (AI, custom services)

Return JSON:
{
  "goal": "one sentence describing what the workflow achieves",
  "workflow_name": "short descriptive name",
  "integrations": ["only external services like Gmail, Slack, Sheets"],
  "trigger": {
    "service": "Gmail",
    "event": "new email received"
  },
  "logic_steps": [
    {
      "order": 1,
      "type": "trigger",
      "node_category": "trigger",
      "service": "Gmail",
      "action": "Watch for new emails",
      "description": "Triggers on every new incoming email",
      "requires_logic_node": false
    },
    {
      "order": 2,
      "type": "filter",
      "node_category": "logic",
      "service": "IF",
      "action": "Check if email is from a recruiter",
      "description": "Filter based on sender domain or subject keywords",
      "condition": "sender or subject contains recruitment-related content",
      "true_path": "continue to store",
      "false_path": "stop processing",
      "requires_logic_node": true,
      "suggested_n8n_node": "n8n-nodes-base.if"
    },
    {
      "order": 3,
      "type": "action",
      "node_category": "action",
      "service": "Google Sheets",
      "action": "Append email details to spreadsheet",
      "description": "Store sender, subject, date in Google Sheets",
      "requires_logic_node": false
    }
  ],
  "mode": "create",
  "complexity": "simple|medium|complex"
}

RULES:
- Never skip implied logic steps
- Always include IF/Filter nodes when the user says words like:
  only, filter, check if, when, if it is, specific, certain, matching
- Include Set/Code nodes when data needs transformation before the next step
- Include HTTP Request when an AI or custom API call is needed
- Think about what data flows between each node
"""


def intent_parser_node(state: WorkflowState) -> dict:
    """
    LangGraph node: Parse user prompt into full structured intent with logic steps.
    """
    user_prompt = state["user_prompt"]
    mode = state.get("mode", "create")

    print(f"[IntentParser] Parsing: {user_prompt[:100]}...")

    user_message = f"""
User automation request: "{user_prompt}"
Mode: {mode}

Think through the COMPLETE solution step by step.
What trigger, logic nodes, conditions, transformations, and actions are needed?
Include ALL intermediate steps the user needs even if not explicitly stated.
"""

    try:
        intent = call_llm_json(SYSTEM_PROMPT, user_message)
        if "mode" not in intent:
            intent["mode"] = mode

        logic_steps = intent.get("logic_steps", [])
        logic_nodes = [s for s in logic_steps if s.get("requires_logic_node")]

        print(f"[IntentParser] Workflow: {intent.get('workflow_name')}")
        print(f"[IntentParser] Steps: {len(logic_steps)} total | {len(logic_nodes)} logic nodes")
        for step in logic_steps:
            marker = "⚙" if step.get("requires_logic_node") else "→"
            print(f"  {marker} Step {step.get('order')}: [{step.get('type')}] {step.get('service')} — {step.get('action')}")

        return {
            "intent": intent,
            "mode": intent.get("mode", mode),
            "messages": [f"[IntentParser] {len(logic_steps)} steps planned for: {intent.get('goal', '')}"],
        }

    except Exception as e:
        print(f"[IntentParser] Error: {e}")
        return {
            "error": f"Intent parsing failed: {str(e)}",
            "messages": [f"[IntentParser] ERROR: {e}"],
        }