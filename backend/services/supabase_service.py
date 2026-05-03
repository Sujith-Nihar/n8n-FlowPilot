"""
services/supabase_service.py
-----------------------------
All Supabase queries used by the agent pipeline.
Provides keyword search over the operation index and node registry.
"""

from supabase import create_client, Client
from config import settings
from typing import Optional
import json

# ─── Client ──────────────────────────────────────────────────────────────────

_client: Optional[Client] = None

def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    return _client

# ─── Operation Index Search ───────────────────────────────────────────────────

def search_operations(keyword: str, limit: int = 10) -> list[dict]:
    """
    Search the operation index for a keyword.
    Searches display_name, node_type, resource, operation, action, search_text.
    Returns list of operation records.
    """
    client = get_client()
    try:
        result = (
            client.table("n8n_operation_index")
            .select(
                "node_type, node_name, display_name, default_version, "
                "resource, resource_name, operation, operation_name, "
                "action, description, credentials, required_fields, search_text"
            )
            .ilike("search_text", f"%{keyword}%")
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception as e:
        print(f"[SupabaseService] search_operations error: {e}")
        return []


def search_operations_multi(keywords: list[str], limit: int = 5) -> list[dict]:
    """
    Search operations for multiple keywords (one query per keyword).
    Deduplicates results by (node_type, resource, operation).
    """
    seen = set()
    results = []
    for kw in keywords:
        rows = search_operations(kw, limit=limit)
        for row in rows:
            key = (row.get("node_type"), row.get("resource"), row.get("operation"))
            if key not in seen:
                seen.add(key)
                results.append(row)
    return results


def get_operations_for_node(node_type: str) -> list[dict]:
    """
    Get all operations for a specific node_type from the operation index.
    """
    client = get_client()
    try:
        result = (
            client.table("n8n_operation_index")
            .select("*")
            .eq("node_type", node_type)
            .execute()
        )
        return result.data or []
    except Exception as e:
        print(f"[SupabaseService] get_operations_for_node error: {e}")
        return []

# ─── Node Registry Search ─────────────────────────────────────────────────────

def get_node_schema(node_type: str) -> Optional[dict]:
    """
    Get the full node schema from n8n_node_registry by node_type.
    Returns the full record including properties, credentials, defaults.
    """
    client = get_client()
    try:
        result = (
            client.table("n8n_node_registry")
            .select("*")
            .eq("node_type", node_type)
            .limit(1)
            .execute()
        )
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        print(f"[SupabaseService] get_node_schema error: {e}")
        return None


def search_nodes(keyword: str, limit: int = 5) -> list[dict]:
    """
    Search the node registry by keyword.
    Only returns nodes valid for generation.
    """
    client = get_client()
    try:
        result = (
            client.table("n8n_node_registry")
            .select(
                "node_type, node_name, display_name, description, "
                "default_version, credentials, required_fields, "
                "resources, operations, is_valid_for_generation, search_text"
            )
            .eq("is_valid_for_generation", True)
            .ilike("search_text", f"%{keyword}%")
            .limit(limit)
            .execute()
        )
        return result.data or []
    except Exception as e:
        print(f"[SupabaseService] search_nodes error: {e}")
        return []


def get_http_request_node() -> Optional[dict]:
    """
    Get the HTTP Request node — used as fallback when no native node is found.
    """
    return get_node_schema("n8n-nodes-base.httpRequest")

# ─── Credential Registry ──────────────────────────────────────────────────────

def find_credential(credential_name: str) -> Optional[dict]:
    """
    Look up a credential by name from the credential registry.
    """
    client = get_client()
    try:
        result = (
            client.table("n8n_credential_registry")
            .select("credential_name, display_name, documentation_url")
            .ilike("credential_name", f"%{credential_name}%")
            .limit(3)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"[SupabaseService] find_credential error: {e}")
        return None


def get_credentials_for_nodes(credential_names: list[str]) -> list[dict]:
    """
    Get credential registry records for a list of credential names.
    """
    results = []
    for name in credential_names:
        cred = find_credential(name)
        if cred:
            results.append(cred)
    return results

# ─── Workflow Versions ────────────────────────────────────────────────────────

def save_workflow_version(
    session_id: str,
    user_prompt: str,
    workflow_json: dict,
    missing_credentials: list,
    n8n_workflow_id: Optional[str] = None,
    version: int = 1,
    status: str = "draft",
) -> Optional[dict]:
    """
    Save a workflow version to the workflow_versions table.
    """
    client = get_client()
    try:
        result = (
            client.table("workflow_versions")
            .insert({
                "session_id": session_id,
                "n8n_workflow_id": n8n_workflow_id,
                "version": version,
                "user_prompt": user_prompt,
                "workflow_json": workflow_json,
                "missing_credentials": missing_credentials,
                "status": status,
            })
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"[SupabaseService] save_workflow_version error: {e}")
        return None


def get_latest_workflow_version(session_id: str) -> Optional[dict]:
    """
    Get the latest workflow version for a session.
    """
    client = get_client()
    try:
        result = (
            client.table("workflow_versions")
            .select("*")
            .eq("session_id", session_id)
            .order("version", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"[SupabaseService] get_latest_workflow_version error: {e}")
        return None


def get_next_version_number(session_id: str) -> int:
    """
    Get the next version number for a session.
    """
    latest = get_latest_workflow_version(session_id)
    if latest:
        return (latest.get("version") or 0) + 1
    return 1
