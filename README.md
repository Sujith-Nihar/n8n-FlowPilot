# Agentic n8n Workflow Builder

> Convert natural language automation requests into executable n8n workflows using LangGraph, Gemini 2.5 Flash, a dynamic node registry, and the n8n REST API.

---

## Table of Contents

- [What This Project Does](#what-this-project-does)
- [How It Works](#how-it-works)
- [Project Structure](#project-structure)
- [Setup & Running](#setup--running)
- [File Reference](#file-reference)
  - [Registry Extractor](#registry-extractor)
  - [Backend — Agents](#backend--agents)
  - [Backend — Services](#backend--services)
  - [Backend — API](#backend--api)
- [API Endpoints](#api-endpoints)
- [Agent Pipeline Deep Dive](#agent-pipeline-deep-dive)
- [Database Schema](#database-schema)
- [Environment Variables](#environment-variables)
- [Known Issues & Fixes Applied](#known-issues--fixes-applied)
- [Next Steps](#next-steps)

---

## What This Project Does

A user types a natural language request like:

```
"Create a workflow that checks Gmail for recruiter emails and stores them in Google Sheets"
```

The system:

1. **Reasons** about the full solution — not just the services mentioned, but the logic steps needed (trigger → filter → action)
2. **Searches** a dynamic registry of 524 real n8n nodes to find the right nodes
3. **Plans** the workflow — node order, connections, IF conditions, positions
4. **Fills** parameters from real node schemas — no invented fields
5. **Validates** the workflow JSON — checks structure, connections, node types
6. **Self-repairs** validation errors automatically (up to 3 attempts)
7. **Reflects** on quality (scores 1-10) and re-plans if needed
8. **Deploys** directly to your running n8n instance as an inactive draft
9. **Saves** a version history to Supabase

The result appears in your n8n editor:

```
Gmail Trigger → IF (sender contains recruiter) → Google Sheets (append)
```

This is **not** a template generator. It is a schema-driven agentic pipeline that works for any automation request.

---

## How It Works

```
User prompt (natural language)
         │
         ▼
   FastAPI Backend
         │
         ▼
   LangGraph Agent Pipeline
         │
   ┌─────┴──────────────────────────────────────────┐
   │  intent_parser    → understand the full problem  │
   │  node_discovery   → find real n8n nodes          │
   │  schema_retriever → load actual node schemas      │
   │  workflow_planner → plan nodes + connections      │
   │  parameter_filler → fill params from schema       │
   │  workflow_builder → build n8n JSON                │
   │  credential_resolver → detect missing creds       │
   │  validator        → check structure               │
   │  repair_agent     → fix errors (loops 3x)         │
   │  reflection_agent → score quality (loops 2x)      │
   │  deployer         → POST to n8n API               │
   └────────────────────────────────────────────────┘
         │
         ▼
   n8n Workflow Created (inactive draft)
         │
         ▼
   Supabase (version saved)
```

---

## Project Structure

```
n8n-agent/
├── venv/                              Python 3.12 virtual environment
├── load_registry.py                   Loads JSON registry files into Supabase
├── .env                               API keys (do not commit)
│
├── n8n-registry-extractor/            Node.js registry extraction project
│   ├── package.json
│   ├── node_modules/                  n8n + n8n-nodes-base installed here
│   ├── n8n_registry.json              Layer 1: Raw registry (645 nodes, 420 creds)
│   ├── scripts/
│   │   ├── extract-n8n-registry.js    Extracts raw node data from installed packages
│   │   ├── normalize_registry.js      Normalizes raw data (555 valid nodes)
│   │   ├── build_operation_index.js   Builds per-operation index (3,602 records)
│   │   └── inspect_node.js            CLI tool to verify registry quality
│   └── output/
│       ├── n8n_registry_normalized.json
│       └── n8n_operation_index.json
│
└── backend/                           Python FastAPI backend
    ├── main.py                        FastAPI app entry point
    ├── config.py                      Settings loaded from .env
    ├── requirements.txt               Python dependencies
    ├── .env                           API keys
    │
    ├── agents/                        LangGraph agent nodes
    │   ├── state.py                   WorkflowState TypedDict (shared state)
    │   ├── orchestrator.py            LangGraph graph with all edges and loops
    │   ├── intent_parser.py           Parses prompt into structured logic steps
    │   ├── node_discovery.py          Finds the right n8n node for every step
    │   ├── schema_retriever.py        Fetches full node schemas from Supabase
    │   ├── workflow_planner.py        Plans positions, connections, IF conditions
    │   ├── parameter_filler.py        Fills parameters from real schema fields
    │   ├── workflow_builder.py        Builds complete n8n workflow JSON
    │   ├── credential_resolver.py     Detects and attaches credentials
    │   ├── validator.py               Validates workflow structure
    │   ├── repair_agent.py            Fixes validation errors (repair loop)
    │   ├── reflection_agent.py        Scores quality and triggers re-planning
    │   └── deployer.py                Deploys to n8n and saves to Supabase
    │
    ├── services/                      External service clients
    │   ├── supabase_service.py        All Supabase/PostgreSQL queries
    │   ├── n8n_client.py              n8n REST API client
    │   └── gemini_client.py           Gemini 2.5 Flash LLM client
    │
    └── api/                           FastAPI routes and models
        ├── routes.py                  All HTTP endpoints
        └── models.py                  Pydantic request/response models
```

---

## Setup & Running

### Prerequisites

- Python 3.12
- Node.js 18+
- Docker (for n8n)
- Supabase account (free tier)
- Google AI Studio account (for Gemini API key)

### 1. Clone and set up Python environment

```bash
cd /Users/sujiththota/Downloads/Python/n8n-agent
python3.12 -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
```

### 2. Configure environment

```bash
cp backend/.env.template backend/.env
# Fill in all 5 required keys — see Environment Variables section
```

### 3. Start n8n (Docker)

```bash
docker run -d \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  docker.n8n.io/n8nio/n8n

# Open http://localhost:5678 → Settings → API → Create API Key
```

### 4. Start the backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

### 5. Open Swagger UI

```
http://localhost:8000/docs
```

### 6. Test it

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Create a workflow that monitors Gmail for invoices and saves them to Google Sheets",
    "session_id": "my-session-1",
    "mode": "create"
  }'
```

---

## File Reference

### Registry Extractor

#### `scripts/extract-n8n-registry.js`

Scans the locally installed `n8n-nodes-base` package (and any community packages) and extracts every node class definition. For each `.node.js` file it requires the file, instantiates the class, reads `instance.description`, and saves everything to `n8n_registry.json`.

**Output:** `n8n_registry.json` with 645 nodes and 420 credentials.

**Run:** `node scripts/extract-n8n-registry.js`

---

#### `scripts/normalize_registry.js`

Reads the raw registry and cleans it up:
- Removes invalid nodes (empty properties, `.undefined` node types)
- Normalizes version numbers (handles floats like `1.1`, `2.2`)
- Normalizes `inputs` and `outputs` (some are dynamic expression strings)
- Extracts `resources` and `operations` arrays from properties
- Builds `search_text` for keyword search
- Marks each node as `is_valid_for_generation: true/false`

**Output:** `output/n8n_registry_normalized.json` with 555 valid nodes.

**Run:** `node scripts/normalize_registry.js`

---

#### `scripts/build_operation_index.js`

Reads the normalized registry and expands each node into per-operation records. For a node like Gmail with 5 resources × 4 operations each, it creates 20 individual records. Each record has:
- `node_type`, `display_name`, `resource`, `operation`, `action`
- `required_fields` — resolved for that specific resource+operation combination
- `credentials` — credential types needed
- `search_text` — combined searchable string

**Output:** `output/n8n_operation_index.json` with 3,602 operation records.

**Run:** `node scripts/build_operation_index.js [keyword]`

---

#### `scripts/inspect_node.js`

CLI tool to verify registry quality for a specific keyword. Searches both the normalized registry and operation index and prints a formatted quality report.

```bash
node scripts/inspect_node.js gmail
node scripts/inspect_node.js sheets
node scripts/inspect_node.js http
node scripts/inspect_node.js slack --full        # Show all properties
node scripts/inspect_node.js gmail --json        # Raw JSON output
```

**Quality report shows:**
- Node validity status
- Credentials needed
- Resources and operations
- Required fields
- Search text quality
- READY / PARTIAL / NOT FOUND verdict

---

#### `load_registry.py`

Python script that reads all three JSON files and loads them into Supabase. Uses batch inserts of 100 rows with upsert (safe to re-run). Deduplicates by `node_type` and `credential_name` before inserting.

**Run:** `python load_registry.py` (from the `n8n-agent/` root, with venv active)

---

### Backend — Agents

#### `agents/state.py`

Defines `WorkflowState` — the TypedDict that is shared across all LangGraph agent nodes. Every agent reads from this state and returns a partial dict that updates it.

Key fields:
- `user_prompt` — the raw user message
- `session_id` — identifies the chat session
- `mode` — `"create"` or `"update"`
- `intent` — parsed structured intent with logic steps
- `selected_nodes` — list of chosen n8n nodes
- `node_schemas` — full schemas fetched from Supabase
- `workflow_plan` — node order, positions, connections
- `filled_parameters` — parameters per node
- `generated_workflow_json` — the final n8n JSON
- `required_credentials` — what the user needs to configure
- `validation_errors` — errors found by validator
- `validation_passed` — boolean
- `reflection_score` — 1-10 quality score from reflection agent
- `repair_attempts` / `reflection_attempts` — loop counters
- `deployment_result` — workflow ID, URL from n8n
- `final_response` — human-readable message to return to user

---

#### `agents/orchestrator.py`

The LangGraph `StateGraph` that wires all agents together with conditional edges. This is the brain of the pipeline.

**Graph structure:**
```
START → intent_parser → node_discovery → schema_retriever
      → workflow_planner → parameter_filler → workflow_builder
      → credential_resolver → validator
        ├── [errors + attempts < 3] → repair_agent → validator
        └── [passed or max repairs] → reflection_agent
            ├── [score < 6 + attempts < 2 + validation passed] → workflow_planner
            └── [score >= 6 or max reflections] → deployer → END
```

**Routing functions:**
- `route_after_validation` — decides repair vs reflect
- `route_after_reflection` — decides replan vs deploy

**Key rule:** Only re-plans when validation passed AND score < 6. Never re-plans when validation failed (no point replanning a broken structure).

---

#### `agents/intent_parser.py`

Sends the user prompt to Gemini 2.5 Flash with a structured prompt that asks it to think like a solutions architect. The key innovation is extracting `logic_steps` — not just the services mentioned, but every step including implicit filter/condition nodes.

**For `"check Gmail for recruiter emails"` it infers:**
```json
{
  "logic_steps": [
    { "order": 1, "type": "trigger", "service": "Gmail", "requires_logic_node": false },
    { "order": 2, "type": "filter", "service": "IF", "requires_logic_node": true,
      "suggested_n8n_node": "n8n-nodes-base.if" },
    { "order": 3, "type": "action", "service": "Google Sheets", "requires_logic_node": false }
  ]
}
```

This is what makes the system agentic — it reasons about the problem, not just the services.

---

#### `agents/node_discovery.py`

Finds the best n8n node for every step in the logic plan. Uses a two-track approach:

**Track 1 — Service nodes:** Searches the Supabase operation index using keywords derived from integrations. Uses `search_operations_multi()` to search multiple keywords simultaneously.

**Track 2 — Logic nodes:** Built-in n8n nodes (IF, Set, Code, Filter, Switch, Merge, HTTP Request) are defined directly in a `BUILT_IN_LOGIC_NODES` dict — no registry search needed.

**Fallback:** If no native node found for a service, adds an HTTP Request node with a note about which service it's a fallback for.

Finally asks Gemini to select the best node for each step from the candidates, preserving the correct execution order.

---

#### `agents/schema_retriever.py`

Simple agent that fetches the full node schema from `n8n_node_registry` in Supabase for each selected node. The full schema includes:
- `properties` — all parameters, their types, defaults, options
- `credentials` — what auth types are needed
- `required_fields` — pre-resolved required fields
- `defaults` — schema default values

Built-in logic nodes (IF, Set, etc.) will show "schema NOT found" — this is expected and normal.

---

#### `agents/workflow_planner.py`

Asks Gemini to plan the complete workflow structure given the selected nodes. Gemini is responsible for:
- Setting correct node positions (left to right, 280px apart)
- Defining all connections (which output connects to which input)
- Setting IF node conditions using n8n expression syntax (`={{$json.from}}`)
- Setting `params_to_fill` hints for the parameter filler

**Critical rule for IF nodes:** Output 0 = true branch, Output 1 = false branch. The planner must set connections accordingly.

---

#### `agents/parameter_filler.py`

Fills parameters for each node. Uses two strategies:

**Logic nodes** (IF, Set, Code, Filter, Switch): Uses fixed parameter templates defined in `LOGIC_NODE_PARAMS`. These are the exact structures n8n expects — no LLM involved.

**Service nodes** (Gmail, Google Sheets, etc.): Asks Gemini to fill parameters using a prompt that enforces:
- Never put `name` in parameters
- Trigger nodes get NO resource/operation
- Use `__rl` wrapper format for resource locators (Google Sheets documentId, sheetName)
- Omit user-specific values (spreadsheetId, credentials) rather than using placeholders

**Important:** The `name` field is the most common cause of nodes rendering empty in n8n. It belongs on the node object, not inside parameters.

---

#### `agents/workflow_builder.py`

Builds the final n8n workflow JSON from the plan and filled parameters.

**Key fixes implemented:**
- `NODE_TYPE_VERSIONS` whitelist — correct typeVersion per node type (IF=2, GoogleSheets=4, Set=3, etc.)
- `INVALID_PARAM_FIELDS` — strips `name`, `_missing`, `_is_fallback` from parameters
- `clean_parameters()` — removes None values and invalid fields
- `build_connections()` — produces correct n8n connections format
- Prints a full JSON preview to terminal for debugging

**Why typeVersion matters:** n8n will silently fail to render nodes with the wrong typeVersion. IF node v1 has a completely different parameter structure than v2. Google Sheets v1 vs v4 are incompatible.

---

#### `agents/credential_resolver.py`

Detects what credentials are needed and optionally attaches them.

**Two modes:**

Mode 1 (default — no hints provided):
- Identifies what credentials are needed from selected nodes
- Creates workflow with no credentials attached
- Reports the full list of credentials the user must configure in n8n

Mode 2 (credential hints provided):
- Tries to match user-provided credential names to n8n credentials
- Uses keyword matching (`gmailOAuth2` → nodes with `gmail` in type)
- Attaches matched credentials to the correct nodes only

**Critical rule:** Logic nodes (IF, Set, Code, etc.) NEVER get credentials. The `LOGIC_NODE_TYPES` set ensures this. Wrong credential assignment was causing nodes to fail silently.

---

#### `agents/validator.py`

Validates the generated workflow JSON before deployment. Checks:
1. Top-level structure (name, nodes array, connections object)
2. Each node has required fields (id, name, type, typeVersion, position, parameters)
3. Node type exists in registry — but **skips built-in nodes** (IF, Set, Code, etc.) via `BUILT_IN_NODES` whitelist
4. Required fields from schema are present — but **skips user-config fields** (spreadsheetId, sheetId, etc.) via `USER_CONFIG_FIELDS`
5. Connections reference valid node names
6. `active: false` is set

**Returns:** `validation_errors` list and `validation_passed` boolean.

---

#### `agents/repair_agent.py`

When validation fails, sends the workflow JSON and list of errors to Gemini and asks it to fix them. Loops back to the validator. Maximum 3 repair attempts before giving up and moving to reflection.

**What it can fix:**
- Wrong node type names
- Missing connection targets
- `active: true` (sets to false)
- Missing required structural fields

**What it cannot fix:**
- User-specific values (spreadsheetId, credentials) — these are expected gaps

---

#### `agents/reflection_agent.py`

Reviews the completed workflow for quality. Scores it 1-10 based on:
- Does it achieve the user's stated goal?
- Are all requested integrations present?
- Are nodes in correct logical order?
- Are connections correct?
- Is there appropriate logic for any filtering/conditions mentioned?

**Scoring guidance:**
- 8-10: Deploy immediately
- 6-7: Deploy (minor issues, user-config gaps are expected)
- Below 6: Re-plan (structural issues)

**Critical rule:** Does NOT penalize for missing spreadsheetId, credentials, or other user-config gaps. These are expected.

---

#### `agents/deployer.py`

Final agent in the pipeline. Calls `n8n_client.create_workflow()` (or `update_workflow()` for updates), saves a version to Supabase `workflow_versions`, and builds the human-readable response.

**Always creates as inactive draft.** The response includes:
- Workflow name and n8n URL
- Node flow summary (Node A → Node B → Node C)
- List of missing credentials with instructions
- Quality score
- Next steps for the user

---

### Backend — Services

#### `services/gemini_client.py`

Wrapper around `langchain-google-genai` for Gemini 2.5 Flash calls.

**Functions:**
- `call_llm(system, user)` — plain text response
- `call_llm_json(system, user)` — expects JSON response, strips markdown fences, parses safely
- `parse_json_response(raw)` — handles markdown fences, finds JSON blocks, handles arrays

Uses `tenacity` for automatic retry with exponential backoff (3 attempts, 2-10s wait).

---

#### `services/supabase_service.py`

All database queries against Supabase. Uses the `supabase-py` client.

**Key functions:**
- `search_operations(keyword, limit)` — keyword search on operation index using `ilike`
- `search_operations_multi(keywords, limit)` — searches multiple keywords, deduplicates
- `get_node_schema(node_type)` — fetches full schema from node registry
- `search_nodes(keyword, limit)` — searches node registry
- `get_http_request_node()` — fetches HTTP Request node for fallback
- `find_credential(name)` — looks up a credential by name
- `save_workflow_version(...)` — saves workflow version to workflow_versions table
- `get_latest_workflow_version(session_id)` — gets most recent version for a session
- `get_next_version_number(session_id)` — increments version counter

---

#### `services/n8n_client.py`

HTTP client for the n8n REST API v1. Uses `httpx` for synchronous requests.

**Key functions:**
- `create_workflow(json)` — POST to `/api/v1/workflows`, always sets `active: false`
- `update_workflow(id, json)` — PUT to `/api/v1/workflows/{id}`
- `get_workflow(id)` — GET full workflow JSON (always fetch before updating)
- `list_workflows(limit)` — GET all workflows
- `delete_workflow(id)` — DELETE a workflow
- `list_credentials()` — GET all configured credentials
- `health_check()` — verifies n8n is reachable

**Critical cleaning in `create_workflow`:**
- `_clean_node()` removes invalid fields, ensures correct types
- `typeVersion` is cast to int
- `position` is cast to `[int, int]`
- `name` is removed from parameters if present

---

### Backend — API

#### `api/models.py`

Pydantic request and response models.

**`ChatRequest`:**
- `message` (required) — the natural language automation request
- `session_id` (auto-generated UUID if not provided) — identifies the chat session
- `mode` (default: `"create"`) — `"create"` or `"update"`
- `credential_hints` (optional) — list of existing n8n credential names to attach
- `workflow_id` (optional) — n8n workflow ID, required for update mode

**`ChatResponse`:**
- `session_id`, `response`, `workflow_name`, `workflow_id`, `n8n_url`
- `nodes` — list of node names in the workflow
- `missing_credentials` — what the user needs to configure
- `reflection_score`, `validation_passed`, `status`, `error`

---

#### `api/routes.py`

All FastAPI route handlers.

**`POST /api/v1/chat`** — Main endpoint. Accepts natural language, runs the full agent pipeline, returns the result. For update mode, fetches the current workflow from n8n before running the pipeline.

**`GET /api/v1/health`** — Checks both n8n and Supabase connectivity and returns registry statistics.

**`GET /api/v1/workflows`** — Lists all workflows in n8n.

**`GET /api/v1/workflows/{id}`** — Gets a specific workflow.

**`DELETE /api/v1/workflows/{id}`** — Deletes a workflow.

**`GET /api/v1/sessions/{id}/history`** — Returns version history for a session from Supabase.

**`GET /api/v1/sessions/{id}/download`** — Downloads the latest workflow JSON for a session as a file.

**`GET /api/v1/registry/search`** — Searches the operation index by keyword (useful for debugging).

---

#### `main.py`

FastAPI application entry point. Configures:
- CORS middleware (allow all origins for development)
- Router mounted at `/api/v1`
- Logging setup
- Root endpoint returning service info

**Run:** `uvicorn main:app --reload --port 8000`

---

#### `config.py`

All settings loaded from `.env` via `pydantic-settings`. Cached with `@lru_cache` so it only reads the file once.

**Settings:**
- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`
- `GEMINI_API_KEY`, `GEMINI_MODEL`
- `N8N_BASE_URL`, `N8N_API_KEY`
- `MAX_REPAIR_ATTEMPTS` (default: 3)
- `MAX_REFLECTION_ATTEMPTS` (default: 2)
- `MAX_NODE_CANDIDATES` (default: 5)

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/chat` | Create or update workflow from natural language |
| GET | `/api/v1/health` | Check connectivity and registry stats |
| GET | `/api/v1/workflows` | List all n8n workflows |
| GET | `/api/v1/workflows/{id}` | Get specific workflow |
| DELETE | `/api/v1/workflows/{id}` | Delete a workflow |
| GET | `/api/v1/registry/search?q=gmail` | Search operation index |
| GET | `/api/v1/sessions/{id}/history` | Get session workflow versions |
| GET | `/api/v1/sessions/{id}/download` | Download workflow JSON |

---

## Agent Pipeline Deep Dive

### Create Mode

```
User: "Create a workflow that monitors Stripe for failed payments and notifies on Slack"

Step 1 — IntentParser reasons:
  - Trigger: Stripe webhook (payment failed event)
  - Logic: IF (payment status == failed)     ← inferred, not stated
  - Action: Slack message to #alerts channel

Step 2 — NodeDiscovery finds:
  - n8n-nodes-base.webhook (Stripe trigger)
  - n8n-nodes-base.if (built-in logic)
  - n8n-nodes-base.slack (action)

Step 3 — SchemaRetriever loads schemas for webhook + slack

Step 4 — WorkflowPlanner sets:
  - Webhook @ [250, 300]
  - IF @ [530, 300] with condition: {{$json.type}} == "payment_intent.payment_failed"
  - Slack @ [810, 300] connected from IF true branch

Step 5 — ParameterFiller sets:
  - Webhook: { httpMethod: "POST", path: "/stripe-webhook" }
  - IF: { conditions: { ... payment_failed check ... } }
  - Slack: { channel: "#alerts", text: "Payment failed: {{$json.amount}}" }

Step 6 — WorkflowBuilder builds JSON with correct typeVersions

Step 7 — CredentialResolver: slackApi → MISSING (user must configure)

Step 8 — Validator: PASSED (0 errors)

Step 9 — ReflectionAgent: Score 8/10 → PASSED

Step 10 — Deployer: Creates workflow in n8n as inactive draft
```

### Update Mode

```
User: "Add a filter to only alert for amounts over $1000"
Mode: update
workflow_id: "abc123"

→ Fetches current workflow from n8n (always fresh, never from cache)
→ Loads session context
→ Adds/modifies IF node condition: {{$json.amount}} > 100000 (cents)
→ Validates → Deploys → Saves version 2
```

---

## Database Schema

### `n8n_node_registry` (524 rows)
Full node schemas from the normalized registry.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| node_type | TEXT | e.g. `n8n-nodes-base.gmail` |
| display_name | TEXT | e.g. `Gmail` |
| description | TEXT | What the node does |
| default_version | FLOAT | e.g. `2.0` |
| properties | JSONB | Full parameter definitions |
| credentials | JSONB | Required credential types |
| required_fields | JSONB | Pre-resolved required fields |
| search_text | TEXT | Keyword search index |
| is_valid_for_generation | BOOL | Whether agent can use this node |
| embedding | vector(1536) | For semantic search (future) |

### `n8n_operation_index` (3,602 rows)
One record per node+resource+operation combination.

| Column | Type | Description |
|--------|------|-------------|
| node_type | TEXT | e.g. `n8n-nodes-base.gmail` |
| resource | TEXT | e.g. `message` |
| operation | TEXT | e.g. `getAll` |
| action | TEXT | e.g. `Get many messages` |
| required_fields | JSONB | Fields required for this op |
| credentials | JSONB | Credentials needed |
| search_text | TEXT | Full keyword search string |

### `n8n_credential_registry` (420 rows)
All credential types available in n8n.

### `workflow_versions`
Every workflow version created or updated by the agent.

| Column | Type | Description |
|--------|------|-------------|
| session_id | TEXT | Chat session identifier |
| n8n_workflow_id | TEXT | ID in n8n |
| version | INT | Increments per session |
| user_prompt | TEXT | What the user asked |
| workflow_json | JSONB | Full workflow JSON |
| missing_credentials | JSONB | What user needs to configure |
| status | TEXT | `draft`, `created`, `updated` |

---

## Environment Variables

```bash
# Supabase — get from: Supabase → Settings → Data API
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=eyJ...    # service_role key (not anon key)

# Gemini — get from: https://aistudio.google.com → Get API Key
GEMINI_API_KEY=AIza...
GEMINI_MODEL=gemini-2.5-flash-preview-04-17

# n8n — get from: n8n → Settings → API → Create API Key
N8N_BASE_URL=http://localhost:5678
N8N_API_KEY=eyJ...

# Agent tuning (optional)
MAX_REPAIR_ATTEMPTS=3
MAX_REFLECTION_ATTEMPTS=2
MAX_NODE_CANDIDATES=5
```

---

## Known Issues & Fixes Applied

### ✅ Fixed — IF node not in registry causing validator failure
Built-in nodes (IF, Set, Code, Filter, etc.) are now in a `BUILT_IN_NODES` whitelist in `validator.py`. Registry check is skipped for these nodes.

### ✅ Fixed — Wrong credentials assigned to logic nodes
`credential_resolver.py` now has a `LOGIC_NODE_TYPES` set. These nodes always have credentials removed. Credential assignment uses keyword matching against node type.

### ✅ Fixed — Missing credentials blocking workflow creation
Credentials are now treated as expected user-configuration gaps. Workflow is always created. Missing credentials are reported clearly in the response.

### ✅ Fixed — `name` field inside parameters (main empty node bug)
`parameter_filler.py` and `workflow_builder.py` now strip `name` from parameters. `n8n_client.py` does a final cleanup pass in `_clean_node()`.

### ✅ Fixed — Wrong typeVersion per node
`workflow_builder.py` has a `NODE_TYPE_VERSIONS` whitelist with correct versions for all major nodes. IF=2, GoogleSheets=4, Set=3, Code=2, etc.

### ✅ Fixed — Trigger nodes getting resource/operation injected
`parameter_filler.py` has a `TRIGGER_NODE_TYPES` set. These nodes never get resource/operation parameters.

### ✅ Fixed — Google Sheets missing `__rl` wrapper
Google Sheets uses resource locators for documentId and sheetName. The parameter filler now produces the correct `{"__rl": true, "value": "", "mode": "list"}` format.

### ✅ Fixed — Reflection re-planning when validation failed
`orchestrator.py` only triggers re-planning when `validation_passed=True AND score < 6`.

### 🔧 Active — Nodes rendering empty in n8n editor
The root causes above have been fixed. Testing in progress.

---

## Next Steps

1. **Test the node rendering fix** — run a chat request and verify nodes appear correctly in n8n editor
2. **Build Streamlit Chat UI** — replace Swagger with a proper chat interface that handles session/workflow IDs automatically
3. **Test update mode end-to-end** — send a follow-up message to modify an existing workflow
4. **Add vector search** — generate embeddings for node descriptions and enable semantic search (pgvector extension is already enabled in Supabase)
5. **Test complex workflows** — multi-branch (Switch node), HTTP Request fallbacks, 5+ node workflows
6. **Add more node type versions** — expand `NODE_TYPE_VERSIONS` as more nodes are tested
7. **Deploy to cloud** — Railway/Render for FastAPI, cloud n8n instance for production

---

## Quick Commands

```bash
# Start everything
docker start n8n
source venv/bin/activate && cd backend && uvicorn main:app --reload --port 8000

# Test chat
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Create a Gmail to Sheets workflow", "session_id": "s1", "mode": "create"}'

# Health check
curl http://localhost:8000/api/v1/health

# List n8n workflows
curl http://localhost:5678/api/v1/workflows -H "X-N8N-API-KEY: your_key"

# Delete a test workflow
curl -X DELETE http://localhost:5678/api/v1/workflows/WORKFLOW_ID -H "X-N8N-API-KEY: your_key"

# Inspect registry
node n8n-registry-extractor/scripts/inspect_node.js gmail
node n8n-registry-extractor/scripts/inspect_node.js sheets
node n8n-registry-extractor/scripts/inspect_node.js http

# Reload registry into Supabase
python load_registry.py
```
