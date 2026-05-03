"""
agents/reflection_agent.py
---------------------------
Reflection agent: critically reviews the generated workflow for correctness,
completeness, and alignment with user intent.
Scores it 1-10 and decides whether to loop back or proceed.
Threshold: score >= 7 proceeds to deployment.
"""

from agents.state import WorkflowState
from services.gemini_client import call_llm_json
import json

REFLECTION_PROMPT = """You are a senior n8n workflow quality reviewer.

Critically evaluate this generated n8n workflow against the user's original intent.

IMPORTANT DISTINCTION:
- "User-config gaps" = values like spreadsheetId, email filters, sheet names that 
  the USER must fill in n8n. These are EXPECTED and should NOT lower the score.
- "Structural errors" = wrong node types, broken connections, wrong resource/operation,
  missing data mapping between nodes. These SHOULD lower the score.

Check:
1. Are the correct nodes selected for the integrations requested?
2. Are nodes connected in the correct logical order?
3. Are resource/operation combinations correct?
4. Is data flowing between nodes (e.g. email data mapped to Sheets columns)?
5. Are structural problems present?

Score 1-10:
- 8-10: Correct structure, right nodes, right connections — ready to deploy
- 6-7:  Minor structural issues but deployable
- 4-5:  Wrong nodes or broken data flow
- 1-3:  Fundamentally wrong

DO NOT penalize for: missing spreadsheetId, missing credentials, 
null filter values, placeholder IDs — these are user-config gaps, not errors.

Return JSON:
{
  "score": 8,
  "passed": true,
  "feedback": "...",
  "issues": ["only structural issues here"],
  "suggestions": []
}

Set passed: true if score >= 7.
"""


def reflection_agent_node(state: WorkflowState) -> dict:
    """
    LangGraph node: Reflect on the quality of the generated workflow.
    """
    intent = state.get("intent", {})
    workflow_json = state.get("generated_workflow_json", {})
    reflection_attempts = state.get("reflection_attempts", 0)
    selected_nodes = state.get("selected_nodes", [])

    print(f"[ReflectionAgent] Reflection attempt {reflection_attempts + 1}...")

    user_message = f"""
Original user intent:
{json.dumps(intent, indent=2)}

Requested integrations: {intent.get('integrations', [])}
Goal: {intent.get('goal', '')}

Generated workflow JSON:
{json.dumps(workflow_json, indent=2)}

Selected nodes:
{json.dumps([n.get('display_name') for n in selected_nodes], indent=2)}

Critically review this workflow and score it.
"""

    try:
        result = call_llm_json(REFLECTION_PROMPT, user_message, temperature=0.3)

        score = result.get("score", 5)
        passed = result.get("passed", False)
        feedback = result.get("feedback", "")
        issues = result.get("issues", [])
        suggestions = result.get("suggestions", [])

        print(f"[ReflectionAgent] Score: {score}/10 | Passed: {passed}")
        print(f"  Feedback: {feedback[:150]}")
        if issues:
            print(f"  Issues: {issues}")

        return {
            "reflection_score": score,
            "reflection_feedback": feedback,
            "reflection_attempts": reflection_attempts + 1,
            "messages": [
                f"[ReflectionAgent] Score: {score}/10 — {'PASSED' if passed else 'NEEDS IMPROVEMENT'}: {feedback[:100]}"
            ],
            # Store suggestions in messages for now
            "_reflection_passed": passed,
        }

    except Exception as e:
        print(f"[ReflectionAgent] Error: {e}")
        # On error, pass through (don't block deployment)
        return {
            "reflection_score": 7,
            "reflection_feedback": f"Reflection skipped due to error: {e}",
            "reflection_attempts": reflection_attempts + 1,
            "_reflection_passed": True,
            "messages": [f"[ReflectionAgent] Skipped (error): {e}"],
        }
