"""
agents/schema_retriever.py
---------------------------
Retrieves the full node schema for each selected node from Supabase.
"""

from agents.state import WorkflowState
from services.supabase_service import get_node_schema


def schema_retriever_node(state: WorkflowState) -> dict:
    """
    LangGraph node: Fetch full schemas for all selected nodes.
    """
    selected_nodes = state.get("selected_nodes", [])
    print(f"[SchemaRetriever] Fetching schemas for {len(selected_nodes)} nodes...")

    node_schemas = {}
    for node in selected_nodes:
        node_type = node.get("node_type")
        if not node_type:
            continue
        schema = get_node_schema(node_type)
        if schema:
            node_schemas[node_type] = schema
            print(f"  → {node_type}: schema loaded")
        else:
            print(f"  → {node_type}: schema NOT found in registry")

    return {
        "node_schemas": node_schemas,
        "messages": [f"[SchemaRetriever] Loaded {len(node_schemas)} schemas"],
    }
