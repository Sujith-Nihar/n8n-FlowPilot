"""
agents/orchestrator.py
-----------------------
LangGraph multi-agent orchestrator with reflection loops.

Fixes:
1. Only deploys when validation passed OR max attempts exhausted
2. Reflection threshold lowered to 6 (not 7) since user-config gaps are expected
3. Better routing logic throughout
"""

from langgraph.graph import StateGraph, END
from agents.state import WorkflowState
from agents.intent_parser import intent_parser_node
from agents.node_discovery import node_discovery_node
from agents.schema_retriever import schema_retriever_node
from agents.workflow_planner import workflow_planner_node
from agents.parameter_filler import parameter_filler_node
from agents.workflow_builder import workflow_builder_node
from agents.credential_resolver import credential_resolver_node
from agents.validator import validator_node
from agents.repair_agent import repair_agent_node
from agents.reflection_agent import reflection_agent_node
from agents.deployer import deployer_node
from config import settings


# ─── Routing Functions ────────────────────────────────────────────────────────

def route_after_validation(state: WorkflowState) -> str:
    errors = state.get("validation_errors", [])
    repair_attempts = state.get("repair_attempts", 0)

    if state.get("error"):
        return "end_with_error"

    if errors and repair_attempts < settings.MAX_REPAIR_ATTEMPTS:
        print(f"[Router] Validation failed ({len(errors)} errors) → repair (attempt {repair_attempts + 1})")
        return "repair"

    if errors:
        print(f"[Router] Validation max repairs reached → reflection")
    else:
        print(f"[Router] Validation passed → reflection")

    return "reflect"


def route_after_reflection(state: WorkflowState) -> str:
    score = state.get("reflection_score", 7)
    reflection_attempts = state.get("reflection_attempts", 0)
    validation_passed = state.get("validation_passed", False)

    if state.get("error"):
        return "end_with_error"

    # Only re-plan if score is very low AND we have attempts left
    # AND validation passed (no point re-planning if structure is broken)
    if (
        score < 6
        and reflection_attempts < settings.MAX_REFLECTION_ATTEMPTS
        and validation_passed
    ):
        print(f"[Router] Reflection score {score}/10 → re-planning (attempt {reflection_attempts})")
        return "replan"

    print(f"[Router] Reflection score {score}/10 → deploying")
    return "deploy"


def route_after_intent(state: WorkflowState) -> str:
    if state.get("error"):
        return "end_with_error"
    return "continue"


def route_after_discovery(state: WorkflowState) -> str:
    if state.get("error"):
        return "end_with_error"
    if not state.get("selected_nodes"):
        return "end_with_error"
    return "continue"


def error_node(state: WorkflowState) -> dict:
    error = state.get("error", "Unknown error occurred")
    return {
        "final_response": f"❌ Workflow generation failed:\n{error}",
        "messages": [f"[Error] {error}"],
    }


# ─── Build Graph ──────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(WorkflowState)

    # Register nodes
    graph.add_node("intent_parser", intent_parser_node)
    graph.add_node("node_discovery", node_discovery_node)
    graph.add_node("schema_retriever", schema_retriever_node)
    graph.add_node("workflow_planner", workflow_planner_node)
    graph.add_node("parameter_filler", parameter_filler_node)
    graph.add_node("workflow_builder", workflow_builder_node)
    graph.add_node("credential_resolver", credential_resolver_node)
    graph.add_node("validator", validator_node)
    graph.add_node("repair_agent", repair_agent_node)
    graph.add_node("reflection_agent", reflection_agent_node)
    graph.add_node("deployer", deployer_node)
    graph.add_node("error_handler", error_node)

    # Entry point
    graph.set_entry_point("intent_parser")

    # Linear flow
    graph.add_conditional_edges(
        "intent_parser",
        route_after_intent,
        {"continue": "node_discovery", "end_with_error": "error_handler"},
    )
    graph.add_conditional_edges(
        "node_discovery",
        route_after_discovery,
        {"continue": "schema_retriever", "end_with_error": "error_handler"},
    )

    graph.add_edge("schema_retriever", "workflow_planner")
    graph.add_edge("workflow_planner", "parameter_filler")
    graph.add_edge("parameter_filler", "workflow_builder")
    graph.add_edge("workflow_builder", "credential_resolver")
    graph.add_edge("credential_resolver", "validator")

    # Validation / Repair loop
    graph.add_conditional_edges(
        "validator",
        route_after_validation,
        {
            "repair": "repair_agent",
            "reflect": "reflection_agent",
            "end_with_error": "error_handler",
        },
    )
    graph.add_edge("repair_agent", "validator")

    # Reflection loop
    graph.add_conditional_edges(
        "reflection_agent",
        route_after_reflection,
        {
            "replan": "workflow_planner",
            "deploy": "deployer",
            "end_with_error": "error_handler",
        },
    )

    # Terminal nodes
    graph.add_edge("deployer", END)
    graph.add_edge("error_handler", END)

    return graph


# Compile
workflow_graph = build_graph().compile()


# ─── Public Run Function ──────────────────────────────────────────────────────

async def run_workflow_agent(
    user_prompt: str,
    session_id: str,
    mode: str = "create",
    credential_hints: list = None,
    current_workflow_json: dict = None,
) -> WorkflowState:

    initial_state: WorkflowState = {
        "user_prompt": user_prompt,
        "session_id": session_id,
        "mode": mode,
        "credential_hints": credential_hints or [],
        "current_workflow_json": current_workflow_json,
        "intent": None,
        "selected_nodes": None,
        "node_schemas": None,
        "workflow_plan": None,
        "filled_parameters": None,
        "generated_workflow_json": None,
        "required_credentials": None,
        "credential_mapping": None,
        "validation_errors": None,
        "validation_passed": False,
        "reflection_feedback": None,
        "reflection_score": None,
        "reflection_attempts": 0,
        "repair_attempts": 0,
        "deployment_result": None,
        "final_response": None,
        "error": None,
        "messages": [],
    }

    print(f"\n{'='*60}")
    print(f"  n8n Agent Pipeline Starting")
    print(f"  Session: {session_id} | Mode: {mode}")
    print(f"  Prompt: {user_prompt[:80]}...")
    print(f"{'='*60}\n")

    final_state = await workflow_graph.ainvoke(initial_state)

    print(f"\n{'='*60}")
    print(f"  Pipeline Complete")
    print(f"  Reflection score:   {final_state.get('reflection_score', 'N/A')}/10")
    print(f"  Validation:         {'PASSED' if final_state.get('validation_passed') else 'FAILED'}")
    print(f"  Repair attempts:    {final_state.get('repair_attempts', 0)}")
    print(f"  Reflection loops:   {final_state.get('reflection_attempts', 0)}")
    print(f"{'='*60}\n")

    return final_state