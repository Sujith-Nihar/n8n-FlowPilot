const BASE = '/api/v1'

export async function sendChat({ message, sessionId, mode, workflowId, credentialHints }) {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      mode: mode || 'create',
      workflow_id: workflowId || undefined,
      credential_hints: credentialHints || undefined,
    }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export async function getHealth() {
  const res = await fetch(`${BASE}/health`)
  return res.json()
}

export async function listWorkflows() {
  const res = await fetch(`${BASE}/workflows`)
  return res.json()
}

export async function deleteWorkflow(id) {
  const res = await fetch(`${BASE}/workflows/${id}`, { method: 'DELETE' })
  return res.json()
}

export async function searchRegistry(q) {
  const res = await fetch(`${BASE}/registry/search?q=${encodeURIComponent(q)}&limit=8`)
  return res.json()
}
