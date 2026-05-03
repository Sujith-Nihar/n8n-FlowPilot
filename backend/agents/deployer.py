"""
agents/deployer.py
------------------
Deploys the validated workflow to n8n via REST API.
Saves a version to Supabase.
Builds the final human-readable response.
"""

from agents.state import WorkflowState
from services.n8n_client import n8n_client
from services.supabase_service import save_workflow_version, get_next_version_number
import json


def deployer_node(state: WorkflowState) -> dict:
    """
    LangGraph node: Deploy workflow to n8n and save version.
    """
    workflow_json = state.get("generated_workflow_json", {})
    session_id = state.get("session_id", "unknown")
    user_prompt = state.get("user_prompt", "")
    mode = state.get("mode", "create")
    required_credentials = state.get("required_credentials", [])
    reflection_score = state.get("reflection_score", 0)
    intent = state.get("intent", {})

    workflow_name = workflow_json.get("name", "Generated Workflow")
    nodes = workflow_json.get("nodes", [])

    print(f"[Deployer] Deploying '{workflow_name}' to n8n (mode={mode})...")

    deployment_result = {}

    try:
        if mode == "update" and state.get("current_workflow_json"):
            # Update existing workflow
            existing_id = state["current_workflow_json"].get("id")
            if existing_id:
                result = n8n_client.update_workflow(existing_id, workflow_json)
                deployment_result = {
                    "workflow_id": result.get("id"),
                    "workflow_name": result.get("name"),
                    "status": "updated",
                    "active": result.get("active", False),
                    "n8n_url": f"{n8n_client.base_url}/workflow/{result.get('id')}",
                }
                print(f"[Deployer] ✔ Updated workflow: {result.get('id')}")
        else:
            # Create new workflow
            result = n8n_client.create_workflow(workflow_json)
            deployment_result = {
                "workflow_id": result.get("id"),
                "workflow_name": result.get("name"),
                "status": "created",
                "active": result.get("active", False),
                "n8n_url": f"{n8n_client.base_url}/workflow/{result.get('id')}",
            }
            print(f"[Deployer] ✔ Created workflow: {result.get('id')}")

    except Exception as e:
        print(f"[Deployer] n8n API error: {e}")
        # Don't fail — save locally and inform user
        deployment_result = {
            "workflow_id": None,
            "workflow_name": workflow_name,
            "status": "local_only",
            "error": str(e),
            "note": "n8n API unavailable — workflow saved locally",
        }

    # ── Save version to Supabase ───────────────────────────────────────────────
    version_num = get_next_version_number(session_id)
    try:
        save_workflow_version(
            session_id=session_id,
            user_prompt=user_prompt,
            workflow_json=workflow_json,
            missing_credentials=required_credentials,
            n8n_workflow_id=deployment_result.get("workflow_id"),
            version=version_num,
            status=deployment_result.get("status", "draft"),
        )
        print(f"[Deployer] ✔ Saved version {version_num} to Supabase")
    except Exception as e:
        print(f"[Deployer] Supabase save error: {e}")

    # ── Build human-readable response ─────────────────────────────────────────
    node_names = [n.get("name", "") for n in nodes]
    node_flow = " → ".join(node_names)

    cred_section = ""
    if required_credentials:
        cred_list = "\n".join(f"  - {c}" for c in required_credentials)
        cred_section = f"\n\n⚠️ Missing credentials — configure these in n8n before activating:\n{cred_list}"

    n8n_url = deployment_result.get("n8n_url", "")
    url_section = f"\n\n🔗 Open in n8n: {n8n_url}" if n8n_url else ""

    quality_section = f"\n\n🎯 Quality score: {reflection_score}/10" if reflection_score else ""

    status = deployment_result.get("status", "unknown")
    status_emoji = "✅" if status in ("created", "updated") else "⚠️"

    final_response = f"""{status_emoji} Workflow {'created' if mode == 'create' else 'updated'} successfully as inactive draft.

📋 Name: {workflow_name}
📦 Nodes: {node_flow}
📊 Status: Inactive draft (safe to review before activating){cred_section}{url_section}{quality_section}

Next step: Configure missing credentials in n8n, review node parameters, then activate."""

    print(f"[Deployer] ✔ Done — {status}")

    return {
        "deployment_result": deployment_result,
        "final_response": final_response,
        "messages": [f"[Deployer] {status}: {workflow_name} (v{version_num})"],
    }
