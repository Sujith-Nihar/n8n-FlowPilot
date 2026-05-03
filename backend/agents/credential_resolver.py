"""
agents/credential_resolver.py
------------------------------
Resolves credentials for the workflow.

DESIGN DECISION:
- Missing credentials are EXPECTED and NORMAL — not errors
- If user provides credential names/hints → attach them to matching nodes
- If user provides nothing → leave credentials empty, report what's needed
- NEVER block workflow creation because of missing credentials
- Logic nodes (IF, Set, Code) NEVER get credentials assigned

Two modes:
  Mode 1: No credentials provided → create workflow draft, list what's missing
  Mode 2: User provides credential names → attach references to matching nodes
"""

from agents.state import WorkflowState
from services.n8n_client import n8n_client
import json

# Logic nodes never need credentials — always skip
LOGIC_NODE_TYPES = {
    "n8n-nodes-base.if",
    "n8n-nodes-base.filter",
    "n8n-nodes-base.set",
    "n8n-nodes-base.code",
    "n8n-nodes-base.switch",
    "n8n-nodes-base.merge",
    "n8n-nodes-base.noOp",
    "n8n-nodes-base.wait",
    "n8n-nodes-base.manualTrigger",
    "n8n-nodes-base.scheduleTrigger",
    "n8n-nodes-base.stickyNote",
    "n8n-nodes-base.start",
    "n8n-nodes-base.respondToWebhook",
    "n8n-nodes-base.splitInBatches",
}

# Credential type → node type keywords for matching
CREDENTIAL_SERVICE_MAP = {
    "gmailOAuth2":              ["gmail"],
    "googleSheetsOAuth2Api":    ["googlesheets", "sheets"],
    "googleDriveOAuth2Api":     ["googledrive", "drive"],
    "googleCalendarOAuth2Api":  ["googlecalendar", "calendar"],
    "googleOAuth2Api":          ["google"],
    "slackApi":                 ["slack"],
    "slackOAuth2Api":           ["slack"],
    "notionApi":                ["notion"],
    "airtableTokenApi":         ["airtable"],
    "githubApi":                ["github"],
    "openAiApi":                ["openai"],
    "stripeApi":                ["stripe"],
    "twilioApi":                ["twilio"],
    "sendGridApi":              ["sendgrid"],
    "shopifyApi":               ["shopify"],
    "hubspotAppToken":          ["hubspot"],
    "asanaApi":                 ["asana"],
    "trelloApi":                ["trello"],
    "jiraApi":                  ["jira"],
    "linearApi":                ["linear"],
    "discordApi":               ["discord"],
    "telegramApi":              ["telegram"],
    "twitterOAuth2Api":         ["twitter"],
}


def credential_matches_node(cred_type: str, node_type: str) -> bool:
    """Check if a credential belongs to a specific node type."""
    node_type_lower = node_type.lower()
    keywords = CREDENTIAL_SERVICE_MAP.get(cred_type, [])
    if keywords:
        return any(kw in node_type_lower for kw in keywords)
    # Fallback: strip common suffixes and match
    cred_base = (
        cred_type.lower()
        .replace("oauth2api", "")
        .replace("oauth2", "")
        .replace("api", "")
        .replace("token", "")
    )
    return bool(cred_base) and cred_base in node_type_lower


def credential_resolver_node(state: WorkflowState) -> dict:
    """
    LangGraph node: Resolve credentials.

    - Always continues — never blocks workflow creation
    - If user provided hints → try to attach matching credentials
    - If no hints or not found → leave empty, just report what's needed
    - Logic nodes always get credentials removed
    """
    selected_nodes = state.get("selected_nodes", [])
    credential_hints = state.get("credential_hints", []) or []
    generated_workflow_json = state.get("generated_workflow_json", {})

    print("[CredentialResolver] Resolving credentials...")

    # ── Collect what credentials are needed ───────────────────────────────────
    required_creds = set()
    for node in selected_nodes:
        node_type = node.get("node_type", "")
        if node_type in LOGIC_NODE_TYPES:
            continue

        creds = node.get("credentials", [])
        if isinstance(creds, str):
            try:
                creds = json.loads(creds)
            except Exception:
                creds = []

        for c in creds:
            if isinstance(c, str) and c:
                required_creds.add(c)
            elif isinstance(c, dict):
                name = c.get("name") or c.get("type", "")
                if name:
                    required_creds.add(name)

    required_creds.discard("")
    required_creds_list = sorted(list(required_creds))
    print(f"[CredentialResolver] Credentials needed: {required_creds_list}")

    # ── Try to resolve only if user provided hints ────────────────────────────
    credential_mapping = {}
    missing_credentials = list(required_creds_list)  # Start as all missing

    if credential_hints:
        print(f"[CredentialResolver] User provided hints: {credential_hints}")

        # Fetch existing credentials from n8n
        try:
            existing_creds = n8n_client.list_credentials()
            existing_by_type = {c.get("type", ""): c for c in existing_creds}
            existing_by_name = {c.get("name", "").lower(): c for c in existing_creds}
        except Exception as e:
            print(f"[CredentialResolver] Could not fetch n8n credentials: {e}")
            existing_by_type = {}
            existing_by_name = {}

        missing_credentials = []
        for cred_type in required_creds_list:
            resolved = False

            # Try matching user hint
            for hint in credential_hints:
                hint_lower = hint.lower()
                n8n_cred = existing_by_name.get(hint_lower)
                if n8n_cred and credential_matches_node(cred_type, n8n_cred.get("type", hint)):
                    credential_mapping[cred_type] = {
                        "id": n8n_cred.get("id"),
                        "name": n8n_cred.get("name"),
                    }
                    print(f"  → {cred_type}: resolved via hint '{hint}'")
                    resolved = True
                    break

            # Try auto-resolving from n8n by type
            if not resolved and cred_type in existing_by_type:
                n8n_cred = existing_by_type[cred_type]
                credential_mapping[cred_type] = {
                    "id": n8n_cred.get("id"),
                    "name": n8n_cred.get("name"),
                }
                print(f"  → {cred_type}: auto-resolved from n8n")
                resolved = True

            if not resolved:
                missing_credentials.append(cred_type)
                print(f"  → {cred_type}: not found — user must configure in n8n")
    else:
        print("[CredentialResolver] No credential hints provided — leaving credentials empty")
        print(f"  → User must configure these in n8n: {required_creds_list}")

    # ── Update workflow JSON nodes ─────────────────────────────────────────────
    if generated_workflow_json:
        nodes = generated_workflow_json.get("nodes", [])
        for node in nodes:
            node_type = node.get("type", "")

            # Always remove credentials from logic nodes
            if node_type in LOGIC_NODE_TYPES:
                node.pop("credentials", None)
                continue

            # Build credentials for this node
            if credential_mapping:
                node_creds = {}
                for cred_type, cred_ref in credential_mapping.items():
                    if credential_matches_node(cred_type, node_type):
                        node_creds[cred_type] = {
                            "id": cred_ref["id"],
                            "name": cred_ref["name"],
                        }
                if node_creds:
                    node["credentials"] = node_creds
                    print(f"  → Attached {list(node_creds.keys())} to '{node.get('name')}'")
                else:
                    # No matching credential found — leave empty, not an error
                    node.pop("credentials", None)
            else:
                # No credentials provided — leave nodes without credentials
                # n8n will prompt user to configure when they open the workflow
                node.pop("credentials", None)

    resolved_count = len(credential_mapping)
    missing_count = len(missing_credentials)

    print(
        f"[CredentialResolver] Done — "
        f"Resolved: {resolved_count} | "
        f"Missing (expected): {missing_count}"
    )

    return {
        "required_credentials": missing_credentials,
        "credential_mapping": credential_mapping,
        "generated_workflow_json": generated_workflow_json,
        "messages": [
            f"[CredentialResolver] "
            f"Resolved: {resolved_count} | "
            f"Missing (needs config in n8n): {missing_count} — {missing_credentials}"
        ],
    }