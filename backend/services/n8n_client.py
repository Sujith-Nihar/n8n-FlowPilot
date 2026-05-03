"""
services/n8n_client.py
-----------------------
n8n REST API client.
Sends clean, validated workflow payloads to n8n API v1.
"""

import httpx
import json
from config import settings
from typing import Optional


class N8NClient:
    def __init__(self):
        self.base_url = settings.N8N_BASE_URL.rstrip("/")
        self.api_key = settings.N8N_API_KEY
        self.headers = {
            "X-N8N-API-KEY": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _url(self, path: str) -> str:
        return f"{self.base_url}/api/v1{path}"

    def _clean_node(self, node: dict) -> dict:
        """
        Final cleanup of a node before sending to n8n.
        Ensures all required fields are present and correct.
        """
        # Required fields
        clean = {
            "id":          node.get("id") or str(__import__("uuid").uuid4()),
            "name":        node.get("name", "Unnamed Node"),
            "type":        node.get("type", "n8n-nodes-base.noOp"),
            "typeVersion": node.get("typeVersion", 1),
            "position":    node.get("position", [250, 300]),
            "parameters":  {},
        }

        # Ensure typeVersion is int not float
        try:
            clean["typeVersion"] = int(clean["typeVersion"])
        except (ValueError, TypeError):
            clean["typeVersion"] = 1

        # Ensure position is [x, y] list of ints not floats
        pos = clean["position"]
        if isinstance(pos, (list, tuple)) and len(pos) >= 2:
            clean["position"] = [int(pos[0]), int(pos[1])]
        else:
            clean["position"] = [250, 300]

        # Clean parameters — remove None values and invalid fields
        raw_params = node.get("parameters", {})
        if isinstance(raw_params, dict):
            clean_params = {}
            for k, v in raw_params.items():
                if k == "name":
                    continue  # Never put 'name' in parameters
                if v is None:
                    continue
                clean_params[k] = v
            clean["parameters"] = clean_params

        # Add credentials only if present and non-empty
        creds = node.get("credentials")
        if creds and isinstance(creds, dict) and len(creds) > 0:
            clean["credentials"] = creds

        return clean

    def create_workflow(self, workflow_json: dict) -> dict:
        """
        Create a new workflow in n8n as an inactive draft.
        Sends a clean, validated payload.
        """
        # Clean all nodes
        raw_nodes = workflow_json.get("nodes", [])
        clean_nodes = [self._clean_node(n) for n in raw_nodes]

        payload = {
            "name":        workflow_json.get("name", "Generated Workflow"),
            "nodes":       clean_nodes,
            "connections": workflow_json.get("connections", {}),
            "settings":    workflow_json.get("settings", {"executionOrder": "v1"}),
            "staticData":  None,
        }

        # ── Full debug print ──────────────────────────────────────────────────
        print(f"\n[N8NClient] ══════════ PAYLOAD TO n8n ══════════")
        print(f"  Name: {payload['name']}")
        print(f"  Nodes ({len(clean_nodes)}):")
        for n in clean_nodes:
            print(f"    [{n['name']}]")
            print(f"      type:        {n['type']}")
            print(f"      typeVersion: {n['typeVersion']}")
            print(f"      position:    {n['position']}")
            params_str = json.dumps(n['parameters'])
            print(f"      parameters:  {params_str[:300]}")
            if n.get("credentials"):
                print(f"      credentials: {list(n['credentials'].keys())}")
        print(f"  Connections:")
        print(f"    {json.dumps(payload['connections'])[:400]}")
        print(f"[N8NClient] ════════════════════════════════════\n")

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                self._url("/workflows"),
                json=payload,
                headers=self.headers,
            )

            print(f"[N8NClient] Response: {resp.status_code}")

            if resp.status_code not in (200, 201):
                print(f"[N8NClient] ERROR: {resp.text[:500]}")

            resp.raise_for_status()
            result = resp.json()

            print(f"[N8NClient] ✔ Created ID: {result.get('id')}")
            print(f"[N8NClient] ✔ Nodes in response: {len(result.get('nodes', []))}")

            return result

    def update_workflow(self, workflow_id: str, workflow_json: dict) -> dict:
        """Update an existing workflow in n8n."""
        raw_nodes = workflow_json.get("nodes", [])
        clean_nodes = [self._clean_node(n) for n in raw_nodes]

        payload = {
            "name":        workflow_json.get("name"),
            "nodes":       clean_nodes,
            "connections": workflow_json.get("connections", {}),
            "settings":    workflow_json.get("settings", {"executionOrder": "v1"}),
            "staticData":  None,
            "active":      False,
        }

        with httpx.Client(timeout=30.0) as client:
            resp = client.put(
                self._url(f"/workflows/{workflow_id}"),
                json=payload,
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    def get_workflow(self, workflow_id: str) -> dict:
        """Fetch the latest workflow JSON from n8n."""
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                self._url(f"/workflows/{workflow_id}"),
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    def list_workflows(self, limit: int = 20) -> list[dict]:
        """List all workflows in n8n."""
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                self._url("/workflows"),
                params={"limit": limit},
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json().get("data", [])

    def delete_workflow(self, workflow_id: str) -> dict:
        """Delete a workflow from n8n."""
        with httpx.Client(timeout=30.0) as client:
            resp = client.delete(
                self._url(f"/workflows/{workflow_id}"),
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    def activate_workflow(self, workflow_id: str) -> dict:
        """Activate a workflow."""
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                self._url(f"/workflows/{workflow_id}/activate"),
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    def deactivate_workflow(self, workflow_id: str) -> dict:
        """Deactivate a workflow."""
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                self._url(f"/workflows/{workflow_id}/deactivate"),
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json()

    def list_credentials(self) -> list[dict]:
        """List all credentials in n8n."""
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                self._url("/credentials"),
                headers=self.headers,
            )
            resp.raise_for_status()
            return resp.json().get("data", [])

    def health_check(self) -> bool:
        """Check if n8n is reachable."""
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(self._url("/workflows"), headers=self.headers)
                return resp.status_code == 200
        except Exception:
            return False


# Singleton
n8n_client = N8NClient()