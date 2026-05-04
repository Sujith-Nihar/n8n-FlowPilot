# Agentic n8n Workflow Builder — Claude Code Instructions

## What This Project Is

An agentic AI system that converts natural language automation requests into
executable n8n workflows. The user describes an automation in plain English
and the system builds, validates, and deploys a complete n8n workflow via
the n8n REST API. Users can then keep chatting to modify the same workflow.

This is NOT a template generator. It is schema-driven — every node type used
must exist in the Supabase registry extracted from locally installed n8n packages.

---

## Project Structure

```
n8n-agent/
├── CLAUDE.md                          ← you are here
├── load_registry.py                   Loads JSON registry files into Supabase
├── .env                               API keys (never commit)
├── venv/                              Python 3.12 virtual environment
│
├── n8n-registry-extractor/            Node.js — extracts n8n node schemas
│   ├── scripts/
│   │   ├── extract-n8n-registry.js    Step 1: extract raw registry (645 nodes)
│   │   ├── normalize_registry.js      Step 2: clean and normalize (555 valid)
│   │   ├── build_operation_index.js   Step 3: build per-operation index (3,602)
│   │   └── inspect_node.js            CLI: verify registry quality for a keyword
│   └── output/
│       ├── n8n_registry_normalized.json
│       └── n8n_operation_index.json
│
├── backend/                           Python FastAPI backend
│   ├── main.py                        FastAPI entry point — port 8000
│   ├── config.py                      Settings via pydantic-settings from .env
│   ├── requirements.txt               Python dependencies
│   ├── .env                           API keys for backend
│   │
│   ├── agents/                        LangGraph agent nodes
│   │   ├── state.py                   WorkflowState TypedDict (shared across all agents)
│   │   ├── orchestrator.py            LangGraph graph — wires all agents with loops
│   │   ├── intent_parser.py           Prompt → full logic steps (trigger/logic/action)
│   │   ├── node_discovery.py          Find n8n nodes for every step in logic plan
│   │   ├── schema_retriever.py        Fetch full schemas from Supabase
│   │   ├── workflow_planner.py        Plan node positions + connections + IF conditions
│   │   ├── parameter_filler.py        Fill parameters from real schema fields
│   │   ├── workflow_builder.py        Build complete n8n JSON with correct typeVersions
│   │   ├── credential_resolver.py     Detect and optionally attach credentials
│   │   ├── validator.py               Validate structure (whitelist built-in nodes)
│   │   ├── repair_agent.py            Fix validation errors — loops up to 3x
│   │   ├── reflection_agent.py        Score quality 1-10 — loops up to 2x
│   │   └── deployer.py                POST/PUT to n8n + save version to Supabase
│   │
│   ├── services/
│   │   ├── supabase_service.py        All Supabase/PostgreSQL queries
│   │   ├── n8n_client.py              n8n REST API client (create/update/get/delete)
│   │   └── gemini_client.py           Gemini 2.5 Flash LLM wrapper with retry
│   │
│   └── api/
│       ├── routes.py                  All FastAPI HTTP endpoints
│       └── models.py                  Pydantic ChatRequest / ChatResponse
│
└── n8n-agent-ui/                      React 18 + Vite frontend
    ├── src/
    │   ├── App.jsx                    Root layout — sidebar + chat window
    │   ├── index.css                  n8n design system CSS variables
    │   ├── api/client.js              fetch() calls to FastAPI /api/v1
    │   └── components/
    │       ├── Sidebar.jsx            Session history + registry stats + status
    │       ├── ChatWindow.jsx         Chat UI — owns workflow_id tracking state
    │       ├── PipelineStatus.jsx     Live animated pipeline progress
    │       ├── Message.jsx            User + agent message bubbles
    │       └── WorkflowResult.jsx     Workflow card with colored node pills
    ├── vite.config.js                 Proxies /api → localhost:8000
    └── package.json
```

---

## How to Run

### Start n8n (Docker)
```bash
docker start n8n
# Runs at http://localhost:5678
# API key: n8n → Settings → API → Create API Key
```

### Start Backend
```bash
cd /Users/sujiththota/Downloads/Python/n8n-agent
source venv/bin/activate
cd backend
uvicorn main:app --reload --port 8000
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

### Start Frontend
```bash
cd /Users/sujiththota/Downloads/Python/n8n-agent/n8n-agent-ui
npm run dev
# UI: http://localhost:3000
```

---

## Environment Variables

### backend/.env
```
SUPABASE_URL=https://rjrfpwgfohfjhecgcnpx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...        # service_role key (NOT anon key)
GEMINI_API_KEY=AIza...             # from aistudio.google.com
GEMINI_MODEL=gemini-2.5-flash-preview-04-17
N8N_BASE_URL=http://localhost:5678
N8N_API_KEY=eyJ...                 # from n8n → Settings → API
MAX_REPAIR_ATTEMPTS=3
MAX_REFLECTION_ATTEMPTS=2
MAX_NODE_CANDIDATES=5
```

---

## Tech Stack

| Layer      | Technology                                        |
|------------|---------------------------------------------------|
| Backend    | FastAPI + Python 3.12 + uvicorn                   |
| Agents     | LangGraph StateGraph with repair + reflection loops |
| LLM        | Gemini 2.5 Flash via langchain-google-genai       |
| Database   | Supabase PostgreSQL + JSONB + pgvector            |
| Workflows  | n8n running in Docker on localhost:5678           |
| Frontend   | React 18 + Vite + DM Sans — n8n design language  |
| Registry   | Extracted from locally installed n8n-nodes-base   |

---

## Agent Pipeline (Full Flow)

```
User message (natural language)
        │
        ▼
FastAPI POST /api/v1/chat
        │
        ▼
LangGraph StateGraph
        │
   intent_parser         → reasons about FULL solution including logic nodes
        │
   node_discovery        → finds nodes for trigger + logic + action steps
        │                   Built-in: IF, Set, Code, Filter, Switch, Merge, HTTP
        │                   Registry: Gmail, Sheets, Notion, Stripe, etc.
        │
   schema_retriever      → loads full schemas from Supabase for each node
        │
   workflow_planner      → plans positions (280px apart), connections, IF conditions
        │
   parameter_filler      → fills params from real schemas (no invented fields)
        │                   Trigger nodes: only filters/options — NO resource/operation
        │                   Logic nodes: fixed templates (IF v2, Set v3, etc.)
        │                   Service nodes: resource + operation + correct format
        │
   workflow_builder      → builds n8n JSON with correct typeVersions
        │                   Strips 'name' from parameters (critical bug fix)
        │
   credential_resolver   → detects needed creds, attaches if user provided hints
        │                   Logic nodes NEVER get credentials
        │                   Missing creds = expected gap, not an error
        │
   validator             → validates structure
        │                   Built-in nodes (IF, Set, Code) → skip registry check
        │                   User-config fields (spreadsheetId, sheetName) → skip
        │
   [if errors + attempts < 3]
        └──→ repair_agent → validator  (repair loop)
        │
   reflection_agent      → scores 1-10, checks goal alignment
        │                   Does NOT penalize for missing user-config values
        │
   [if score < 6 + attempts < 2 + validation passed]
        └──→ workflow_planner  (re-plan loop)
        │
   deployer              → POST (create) or PUT (update) to n8n REST API
                           → saves version to Supabase workflow_versions
                           → always creates as inactive draft
```

---

## Session & Workflow Tracking Architecture

### How tracking works

The **frontend** owns workflow tracking state — NOT the backend.

```
ChatWindow.jsx
  ├── activeWorkflowId    (null until first workflow created)
  ├── activeWorkflowName  (display name of active workflow)
  ├── workflowHistory     (array of all versions in this session)
  └── currentMode         ('create' if no activeWorkflowId, 'update' if set)
```

When the user sends a message:
```
1. If activeWorkflowId is null:
   → sends mode: 'create', no workflowId
   → agent creates NEW workflow
   → response contains workflow_id
   → frontend sets activeWorkflowId = workflow_id

2. If activeWorkflowId is set:
   → sends mode: 'update', workflowId: activeWorkflowId
   → agent FETCHES current workflow from n8n (always fresh)
   → agent modifies it and calls PUT /api/v1/workflows/{id}
   → same workflow is updated, version incremented

3. User clicks "Start new workflow":
   → activeWorkflowId reset to null
   → next message creates a brand new workflow
```

### Backend session tracking (Supabase)
```
workflow_versions table
  session_id       → matches frontend sessionId
  n8n_workflow_id  → the workflow ID in n8n
  version          → auto-incremented per session
  user_prompt      → what the user asked
  workflow_json    → full workflow JSON snapshot
  missing_credentials → list of creds user needs to configure
  status           → 'created' | 'updated' | 'draft'
```

### Update mode — what happens in n8n_client.py
```python
# For updates — ALWAYS fetch fresh from n8n first
current = n8n_client.get_workflow(workflow_id)
# Never rely on chat history or cached state

# Then PUT the modified workflow
n8n_client.update_workflow(workflow_id, new_workflow_json)
```

---

## Complex Workflow Support

### Node types the agent can use

**Trigger nodes** (start the workflow):
- `n8n-nodes-base.gmailTrigger` — new Gmail email
- `n8n-nodes-base.googleSheetsTrigger` — new Google Sheets row
- `n8n-nodes-base.webhook` — HTTP webhook
- `n8n-nodes-base.scheduleTrigger` — cron/schedule
- `n8n-nodes-base.manualTrigger` — manual test trigger

**Logic/control nodes** (built-in, always available):
- `n8n-nodes-base.if` (v2) — true/false branching
- `n8n-nodes-base.switch` (v3) — multi-branch routing
- `n8n-nodes-base.filter` (v2) — keep matching items
- `n8n-nodes-base.set` (v3) — transform/map data fields
- `n8n-nodes-base.code` (v2) — custom JS/Python logic
- `n8n-nodes-base.merge` (v3) — combine branches
- `n8n-nodes-base.httpRequest` (v4) — call any API (AI, custom services)

**Action nodes** (from registry, 524 available):
- Gmail, Google Sheets, Google Drive, Notion, Airtable
- Stripe, Shopify, HubSpot, Asana, Trello, Jira, Linear
- OpenAI, Telegram, Discord, Typeform, and 500+ more

### Complex workflow examples the agent can build

```
# Multi-branch with Switch
"Route support tickets: urgent → Notion + email, normal → Sheets, low → ignore"
→ Webhook → Switch (3 outputs) → Notion + Gmail | Google Sheets | NoOp

# AI in the middle
"Summarize customer feedback emails with AI and store insights in Sheets"
→ Gmail Trigger → HTTP Request (Gemini API) → Set (extract summary) → Google Sheets

# Scheduled with filter
"Every Monday, find overdue tasks in Notion and email a reminder for each"
→ Schedule Trigger → Notion (query) → Filter (overdue) → Gmail (send per item)

# Multi-step data pipeline
"When Typeform gets a new response, enrich with company data, score the lead,
 save to Sheets if qualified, create Notion task if high score"
→ Webhook → HTTP (enrichment API) → Set (calculate score) → IF (qualified?)
  → [true] Google Sheets → IF (high score?) → [true] Notion
  → [false] NoOp
```

### How the agent handles complex logic

The `intent_parser` reasons about the full solution:
```json
{
  "logic_steps": [
    { "order": 1, "type": "trigger",   "requires_logic_node": false },
    { "order": 2, "type": "filter",    "requires_logic_node": true,
      "suggested_n8n_node": "n8n-nodes-base.switch" },
    { "order": 3, "type": "transform", "requires_logic_node": true,
      "suggested_n8n_node": "n8n-nodes-base.set" },
    { "order": 4, "type": "action",    "requires_logic_node": false }
  ]
}
```

---

## Critical Rules — Never Break These

### Node type rules
- **Never invent node types** — only use what is in the Supabase registry OR the built-in whitelist
- **typeVersion must be correct** — see NODE_TYPE_VERSIONS in `workflow_builder.py`
  - IF → 2, Set → 3, Code → 2, Switch → 3, Google Sheets → 4, HTTP Request → 4
- **Never put 'name' in parameters** — it belongs on the node object, not inside parameters
- **Trigger nodes get NO resource/operation** — they have their own parameter structure

### Connection rules
- IF node: output 0 = true branch, output 1 = false branch
- Switch node: output 0,1,2... = each case branch
- Most nodes: output 0 is the only output
- Never connect to a node that doesn't exist in the nodes array

### Credential rules
- Logic nodes (IF, Set, Code, Filter, Switch) NEVER get credentials
- Assign credentials only to the matching service node (Gmail creds → Gmail node only)
- Missing credentials are EXPECTED — never block workflow creation
- Always create workflows as inactive drafts — never activate automatically

### Update mode rules
- Always fetch the latest workflow JSON from n8n before modifying
- Never rely on chat history or in-memory state for the current workflow JSON
- Use PUT /api/v1/workflows/{id} not POST for updates

---

## Database Tables (Supabase)

| Table                    | Rows  | Purpose |
|--------------------------|-------|---------|
| `n8n_node_registry`      | 524   | Full node schemas, properties, credentials |
| `n8n_operation_index`    | 3,602 | Searchable per-operation records for discovery |
| `n8n_credential_registry`| 420   | All credential types for detection |
| `workflow_versions`      | grows | Every workflow version per session |

---

## API Endpoints

| Method | Endpoint                         | Description |
|--------|----------------------------------|-------------|
| POST   | `/api/v1/chat`                   | Main: natural language → workflow |
| GET    | `/api/v1/health`                 | Check n8n + Supabase + registry stats |
| GET    | `/api/v1/workflows`              | List all n8n workflows |
| GET    | `/api/v1/workflows/{id}`         | Get specific workflow |
| DELETE | `/api/v1/workflows/{id}`         | Delete a workflow |
| GET    | `/api/v1/registry/search?q=`     | Search operation index by keyword |
| GET    | `/api/v1/sessions/{id}/history`  | Workflow version history for session |
| GET    | `/api/v1/sessions/{id}/download` | Download latest workflow JSON |

### Chat request body
```json
{
  "message": "Add a filter that only processes emails from VIP customers",
  "session_id": "session-abc123",
  "mode": "update",
  "workflow_id": "n8n-workflow-id-here",
  "credential_hints": ["My Gmail Account"]
}
```

---

## Frontend Design System

Matches n8n's exact design language:
- **Font**: DM Sans (closest to n8n's typography)
- **Brand color**: `#ff6d5a` (n8n's coral orange — used for buttons, badges, accents)
- **Backgrounds**: `#101014` base → `#16161c` surface → `#1c1c24` card
- **Borders**: `#2a2a38` default, `#3d3d56` focus
- **Text**: `#ececf1` primary, `#9595a5` secondary, `#525270` muted
- **Green**: `#22c55e` (success, connected)
- **Blue**: `#6366f1` (update mode badge)
- All tokens are CSS variables in `src/index.css`

---

## Common Tasks for Claude Code

### Fix a node not rendering in n8n
1. Check `NODE_TYPE_VERSIONS` in `workflow_builder.py` — wrong version = silent fail
2. Check `INVALID_PARAM_FIELDS` — 'name' must never be in parameters
3. Check `TRIGGER_NODE_TYPES` in `parameter_filler.py` — no resource/operation for triggers
4. Check `BUILT_IN_NODES` in `validator.py` — IF/Set/Code must be whitelisted

### Add a new agent to the pipeline
1. Create file in `backend/agents/new_agent.py`
2. Import and register in `orchestrator.py`: `graph.add_node("new_agent", new_agent_node)`
3. Add edges: `graph.add_edge("previous", "new_agent")` and `graph.add_edge("new_agent", "next")`
4. Add any new state fields to `agents/state.py`

### Add support for a new n8n node type
1. Add its typeVersion to `NODE_TYPE_VERSIONS` in `workflow_builder.py`
2. If it's a trigger, add to `TRIGGER_NODE_TYPES` in `parameter_filler.py`
3. If it's a logic node, add to `BUILT_IN_NODES` in `validator.py` and `LOGIC_NODE_TYPES` in `credential_resolver.py`
4. Add its credential keyword mapping to `CREDENTIAL_SERVICE_MAP` in `credential_resolver.py`

### Add a new frontend suggestion
Edit `SUGGESTIONS` array in `n8n-agent-ui/src/components/ChatWindow.jsx`

### Reload registry into Supabase
```bash
source venv/bin/activate && python load_registry.py
```

### Rebuild operation index
```bash
cd n8n-registry-extractor && node scripts/build_operation_index.js
```

### Inspect a node's registry quality
```bash
node n8n-registry-extractor/scripts/inspect_node.js gmail
node n8n-registry-extractor/scripts/inspect_node.js sheets --full
node n8n-registry-extractor/scripts/inspect_node.js if
```

---

## Known Fixes Already Applied (Do Not Revert)

| Bug | Fix Location |
|-----|-------------|
| `name` in parameters → empty nodes | `parameter_filler.py` + `workflow_builder.py` + `n8n_client._clean_node()` |
| Wrong `typeVersion` → silent render fail | `NODE_TYPE_VERSIONS` dict in `workflow_builder.py` |
| `resource/operation` in trigger nodes | `TRIGGER_NODE_TYPES` in `parameter_filler.py` |
| IF/Set/Code failing validator | `BUILT_IN_NODES` whitelist in `validator.py` |
| Wrong creds on IF/Set/Gmail nodes | `credential_resolver.py` with type matching |
| Missing creds blocking creation | Credentials treated as expected gaps |
| Re-planning when validation failed | Router in `orchestrator.py` checks `validation_passed` |
| Google Sheets missing `__rl` wrapper | Parameter filler prompt specifies the format |

---

## Next Steps (Planned)

1. Test complex multi-branch workflows (Switch node with 3 outputs)
2. Test update mode — send follow-up messages to modify existing workflows
3. Add vector search — pgvector embeddings for semantic node discovery
4. Add streaming — stream pipeline stage updates via SSE for real-time UI
5. Deploy backend to Railway/Render for production use
6. Add workflow template library — save and reuse common patterns