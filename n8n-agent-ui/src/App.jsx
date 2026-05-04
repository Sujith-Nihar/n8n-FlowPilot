import { useState, useEffect, useCallback } from 'react'
import { getHealth } from './api/client'
import Sidebar from './components/Sidebar'
import ChatWindow from './components/ChatWindow'

let _counter = 0
const uid = () => `sess-${Date.now()}-${++_counter}`

export default function App() {
  const [health,       setHealth]       = useState(null)
  const [sessions,     setSessions]     = useState([{ id: uid(), label: 'New conversation', ts: Date.now() }])
  const [activeId,     setActiveId]     = useState(sessions[0].id)
  const [workflowId,   setWorkflowId]   = useState(null)
  const [workflowName, setWorkflowName] = useState(null)
  const [sidebarOpen,  setSidebarOpen]  = useState(true)

  useEffect(() => {
    getHealth().then(setHealth).catch(() => setHealth({ status: 'error' }))
  }, [])

  const newSession = useCallback(() => {
    const s = { id: uid(), label: 'New conversation', ts: Date.now() }
    setSessions(p => [s, ...p])
    setActiveId(s.id)
    setWorkflowId(null)
    setWorkflowName(null)
  }, [])

  const selectSession = useCallback((id) => {
    setActiveId(id)
    setWorkflowId(null)
    setWorkflowName(null)
  }, [])

  const onWorkflowCreated = useCallback((id, name) => {
    setWorkflowId(id)
    setWorkflowName(name)
    setSessions(p => p.map(s => s.id === activeId ? { ...s, label: name || s.label } : s))
  }, [activeId])

  return (
    <div style={{ display: 'flex', height: '100vh', background: 'var(--n8n-bg)' }}>
      <Sidebar
        open={sidebarOpen}
        health={health}
        sessions={sessions}
        activeId={activeId}
        onNew={newSession}
        onSelect={selectSession}
        onToggle={() => setSidebarOpen(o => !o)}
      />
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
        <ChatWindow
          key={activeId}
          sessionId={activeId}
          workflowId={workflowId}
          workflowName={workflowName}
          onWorkflowCreated={onWorkflowCreated}
          onToggleSidebar={() => setSidebarOpen(o => !o)}
        />
      </div>
    </div>
  )
}