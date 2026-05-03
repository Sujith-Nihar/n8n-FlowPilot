"""
api/routes.py
-------------
FastAPI route handlers for the n8n agent.
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from api.models import ChatRequest, ChatResponse, HealthResponse
from agents.orchestrator import run_workflow_agent
from services.n8n_client import n8n_client
from services.supabase_service import (
    get_client,
    get_latest_workflow_version,
    get_next_version_number,
)

router = APIRouter()


# ─── Chat Endpoint ────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint.
    Accepts natural language automation requests and returns workflow results.
    """
    current_workflow_json = None

    # For update mode — fetch latest workflow from n8n
    if request.mode == "update" and request.workflow_id:
        try:
            current_workflow_json = n8n_client.get_workflow(request.workflow_id)
        except Exception as e:
            raise HTTPException(
                status_code=404,
                detail=f"Could not fetch workflow {request.workflow_id} from n8n: {e}",
            )
    elif request.mode == "update" and not request.workflow_id:
        # Try to get from session history
        latest = get_latest_workflow_version(request.session_id)
        if latest and latest.get("n8n_workflow_id"):
            try:
                current_workflow_json = n8n_client.get_workflow(latest["n8n_workflow_id"])
            except Exception:
                current_workflow_json = latest.get("workflow_json")

    # ── Run agent pipeline ────────────────────────────────────────────────────
    try:
        final_state = await run_workflow_agent(
            user_prompt=request.message,
            session_id=request.session_id,
            mode=request.mode,
            credential_hints=request.credential_hints,
            current_workflow_json=current_workflow_json,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent pipeline error: {str(e)}")

    # ── Extract response data ─────────────────────────────────────────────────
    deployment = final_state.get("deployment_result") or {}
    workflow_json = final_state.get("generated_workflow_json") or {}
    nodes = workflow_json.get("nodes", [])
    error = final_state.get("error")

    return ChatResponse(
        session_id=request.session_id,
        response=final_state.get("final_response", "Workflow processing complete."),
        workflow_name=workflow_json.get("name"),
        workflow_id=deployment.get("workflow_id"),
        n8n_url=deployment.get("n8n_url"),
        nodes=[n.get("name") for n in nodes],
        missing_credentials=final_state.get("required_credentials", []),
        reflection_score=final_state.get("reflection_score"),
        validation_passed=final_state.get("validation_passed"),
        status="error" if error else "success",
        error=error,
    )


# ─── Health Check ─────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse)
async def health():
    """Health check — verifies n8n and Supabase connections."""
    n8n_ok = n8n_client.health_check()

    supabase_ok = False
    registry_stats = {}
    try:
        client = get_client()
        node_count = client.table("n8n_node_registry").select("id", count="exact").execute()
        op_count = client.table("n8n_operation_index").select("id", count="exact").execute()
        cred_count = client.table("n8n_credential_registry").select("id", count="exact").execute()
        registry_stats = {
            "nodes": node_count.count,
            "operations": op_count.count,
            "credentials": cred_count.count,
        }
        supabase_ok = True
    except Exception as e:
        registry_stats = {"error": str(e)}

    return HealthResponse(
        status="ok" if (n8n_ok and supabase_ok) else "degraded",
        n8n_connected=n8n_ok,
        supabase_connected=supabase_ok,
        registry_stats=registry_stats,
    )


# ─── Workflow Management ──────────────────────────────────────────────────────

@router.get("/workflows")
async def list_workflows():
    """List all workflows in n8n."""
    try:
        workflows = n8n_client.list_workflows()
        return {"workflows": workflows, "count": len(workflows)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get a specific workflow from n8n."""
    try:
        return n8n_client.get_workflow(workflow_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """Delete a workflow from n8n."""
    try:
        return n8n_client.delete_workflow(workflow_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Session History ──────────────────────────────────────────────────────────

@router.get("/sessions/{session_id}/history")
async def get_session_history(session_id: str):
    """Get workflow version history for a session."""
    try:
        client = get_client()
        result = (
            client.table("workflow_versions")
            .select("id, session_id, n8n_workflow_id, version, user_prompt, status, created_at, missing_credentials")
            .eq("session_id", session_id)
            .order("version", desc=True)
            .execute()
        )
        return {"session_id": session_id, "versions": result.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Registry Search ──────────────────────────────────────────────────────────

@router.get("/registry/search")
async def search_registry(q: str, limit: int = 10):
    """Search the operation index for a keyword."""
    from services.supabase_service import search_operations
    results = search_operations(q, limit=limit)
    return {"query": q, "count": len(results), "results": results}
