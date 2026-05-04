import { useState, useRef, useEffect, useCallback } from 'react'
import { sendChat } from '../api/client'
import Message from './Message'
import PipelineStatus from './PipelineStatus'

const ICO = {
  menu:   'M3 12h18M3 6h18M3 18h18',
  send:   'M22 2L11 13M22 2l-7 20-4-9-9-4 20-7z',
  spin:   'M21 12a9 9 0 1 1-6.22-8.56',
  link:   'M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3',
  zap:    'M13 2L3 14h9l-1 10 10-12h-9l1-10z',
  arrow:  'M5 12h14M12 5l7 7-7 7',
}

const Icon = ({ d, size = 16, color = 'currentColor', sw = 1.75, fill = 'none' }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={fill}
    stroke={color} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
)

const PIPELINE_STAGES = [
  { id:'intent_parser',       label:'Intent Parser',        desc:'Reasoning about your full automation request' },
  { id:'node_discovery',      label:'Node Discovery',       desc:'Searching 3,602 operations in registry' },
  { id:'schema_retriever',    label:'Schema Retriever',     desc:'Loading full node schemas from Supabase' },
  { id:'workflow_planner',    label:'Workflow Planner',     desc:'Planning node positions and connections' },
  { id:'parameter_filler',    label:'Parameter Filler',     desc:'Filling parameters from real schemas' },
  { id:'workflow_builder',    label:'Workflow Builder',     desc:'Assembling n8n workflow JSON' },
  { id:'credential_resolver', label:'Credential Resolver',  desc:'Detecting required credentials' },
  { id:'validator',           label:'Validator',            desc:'Checking structure and connections' },
  { id:'reflection_agent',    label:'Reflection Agent',     desc:'Scoring workflow quality 1–10' },
  { id:'deployer',            label:'Deployer',             desc:'Creating workflow in n8n via API' },
]

const SUGGESTIONS = [
  { label: 'Schedule + Sheets', text: 'Every morning at 8am, check a Google Sheet for tasks due today and send me a summary email via Gmail' },
  { label: 'Webhook → Notion',  text: 'When a webhook receives a new support ticket, check if it is high priority, and if so create a Notion task' },
  { label: 'Form → Email',      text: 'When a Typeform response comes in, extract the name and email and send them a welcome email via Gmail' },
  { label: 'Sheets → Gmail',    text: 'Every Monday, scan Google Sheets for rows where status is Pending and send a follow-up email to each contact' },
  { label: 'AI Summarizer',     text: 'Monitor Gmail for emails with the word invoice, extract the details and save a structured summary to Google Sheets' },
]

export default function ChatWindow({ sessionId, workflowId, workflowName, onWorkflowCreated, onToggleSidebar }) {
  const [messages,  setMessages]  = useState([])
  const [input,     setInput]     = useState('')
  const [loading,   setLoading]   = useState(false)
  const [stageIdx,  setStageIdx]  = useState(-1)
  const bottomRef = useRef(null)
  const inputRef  = useRef(null)
  const timerRef  = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, stageIdx])

  const addMsg = (m) => setMessages(p => [...p, { _id: Math.random(), ...m }])

  const submit = useCallback(async (text) => {
    const msg = (text || input).trim()
    if (!msg || loading) return
    setInput('')
    setLoading(true)
    setStageIdx(0)
    addMsg({ role:'user', content:msg })

    // Animate pipeline stages
    let i = 0
    timerRef.current = setInterval(() => {
      i = Math.min(i + 1, PIPELINE_STAGES.length - 1)
      setStageIdx(i)
    }, 1600)

    try {
      const res = await sendChat({
        message:    msg,
        sessionId,
        mode:       workflowId ? 'update' : 'create',
        workflowId: workflowId || undefined,
      })
      clearInterval(timerRef.current)
      setStageIdx(-1)
      setLoading(false)
      addMsg({ role:'assistant', content:res.response, result:res })
      if (res.workflow_id) onWorkflowCreated(res.workflow_id, res.workflow_name)
    } catch (err) {
      clearInterval(timerRef.current)
      setStageIdx(-1)
      setLoading(false)
      addMsg({ role:'assistant', content:`Error: ${err.message}`, error:true })
    }
    setTimeout(() => inputRef.current?.focus(), 80)
  }, [input, loading, sessionId, workflowId, onWorkflowCreated])

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); submit() }
  }

  const isEmpty = messages.length === 0 && stageIdx < 0

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100%', background:'var(--n8n-bg)' }}>

      {/* ── Topbar ── */}
      <div style={{
        height:52, flexShrink:0,
        display:'flex', alignItems:'center', gap:12, padding:'0 20px',
        borderBottom:'1px solid var(--n8n-border)',
        background:'var(--n8n-surface)',
      }}>
        <button onClick={onToggleSidebar} style={{
          background:'none', border:'none', color:'var(--n8n-text-3)',
          padding:6, borderRadius:6, display:'flex', cursor:'pointer',
          transition:'color 0.15s, background 0.15s',
        }}
          onMouseEnter={e => { e.currentTarget.style.color='var(--n8n-text-1)'; e.currentTarget.style.background='var(--n8n-card)'; }}
          onMouseLeave={e => { e.currentTarget.style.color='var(--n8n-text-3)'; e.currentTarget.style.background='none'; }}
        >
          <Icon d={ICO.menu} size={16} />
        </button>

        <div style={{ flex:1, display:'flex', alignItems:'center', gap:10 }}>
          {workflowName ? (
            <>
              <span style={{ fontSize:12, color:'var(--n8n-text-3)' }}>Active:</span>
              <span style={{
                fontSize:12, fontWeight:600, color:'var(--n8n-green)',
                background:'var(--n8n-green-dim)', border:'1px solid var(--n8n-green-border)',
                padding:'2px 10px', borderRadius:20,
              }}>{workflowName}</span>
              <span style={{ fontSize:12, color:'var(--n8n-text-3)' }}>· Continue chatting to modify</span>
            </>
          ) : (
            <span style={{ fontSize:14, fontWeight:600, color:'var(--n8n-text-1)', letterSpacing:'-0.2px' }}>
              Build an automation
            </span>
          )}
        </div>

        {workflowId && (
          <a href={`http://localhost:5678/workflow/${workflowId}`} target="_blank" rel="noreferrer"
            style={{
              display:'flex', alignItems:'center', gap:6, fontSize:12, fontWeight:500,
              color:'var(--n8n-orange)', border:'1px solid var(--n8n-orange-border)',
              background:'var(--n8n-orange-dim)', padding:'5px 12px', borderRadius:7,
              transition:'all 0.15s',
            }}
            onMouseEnter={e => e.currentTarget.style.background='rgba(255,109,90,0.2)'}
            onMouseLeave={e => e.currentTarget.style.background='var(--n8n-orange-dim)'}
          >
            Open in n8n <Icon d={ICO.link} size={12} />
          </a>
        )}
      </div>

      {/* ── Messages ── */}
      <div style={{ flex:1, overflowY:'auto', padding:'0' }}>
        {isEmpty ? (
          <EmptyState onSuggest={submit} />
        ) : (
          <div style={{ maxWidth:800, margin:'0 auto', padding:'28px 24px' }}>
            {messages.map(m => <Message key={m._id} message={m} />)}
            {stageIdx >= 0 && <PipelineStatus stageIdx={stageIdx} stages={PIPELINE_STAGES} />}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* ── Input ── */}
      <div style={{
        flexShrink:0, padding:'14px 24px 18px',
        borderTop:'1px solid var(--n8n-border)',
        background:'var(--n8n-surface)',
      }}>
        <div style={{ maxWidth:800, margin:'0 auto' }}>
          <div style={{
            display:'flex', alignItems:'flex-end', gap:10,
            background:'var(--n8n-input)',
            border:'1px solid var(--n8n-border)',
            borderRadius:10, padding:'10px 12px',
            transition:'border-color 0.15s',
          }}
            onFocusCapture={e => e.currentTarget.style.borderColor='var(--n8n-border-focus)'}
            onBlurCapture={e  => e.currentTarget.style.borderColor='var(--n8n-border)'}
          >
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={onKey}
              disabled={loading}
              placeholder={workflowId
                ? 'Describe what you want to change…'
                : 'Describe the automation you want to build…'}
              rows={1}
              style={{
                flex:1, background:'none', border:'none', outline:'none',
                color:'var(--n8n-text-1)', fontFamily:'var(--font)',
                fontSize:14, resize:'none', lineHeight:1.6,
                maxHeight:120, overflow:'auto',
                '::placeholder': { color: 'var(--n8n-text-3)' },
              }}
              onInput={e => {
                e.target.style.height = 'auto'
                e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
              }}
            />
            <button
              onClick={() => submit()}
              disabled={loading || !input.trim()}
              style={{
                flexShrink:0, padding:'7px 14px', borderRadius:7, border:'none',
                background: (!loading && input.trim()) ? 'var(--n8n-orange)' : 'var(--n8n-border)',
                color: (!loading && input.trim()) ? '#fff' : 'var(--n8n-text-3)',
                display:'flex', alignItems:'center', gap:6,
                fontSize:13, fontWeight:600, cursor: (!loading && input.trim()) ? 'pointer' : 'not-allowed',
                transition:'all 0.15s',
              }}
              onMouseEnter={e => { if (!loading && input.trim()) e.currentTarget.style.background='var(--n8n-orange-hover)' }}
              onMouseLeave={e => { if (!loading && input.trim()) e.currentTarget.style.background='var(--n8n-orange)' }}
            >
              {loading
                ? <Icon d={ICO.spin} size={14} color="var(--n8n-text-3)" style={{ animation:'spin 0.8s linear infinite' }} />
                : <Icon d={ICO.send} size={14} color={input.trim() ? '#fff' : 'var(--n8n-text-3)'} sw={2} />
              }
              {loading ? 'Building…' : 'Send'}
            </button>
          </div>
          <div style={{ marginTop:7, textAlign:'center', fontSize:11, color:'var(--n8n-text-4)' }}>
            {loading ? 'Agent pipeline running — this takes 15–30 seconds' : 'Enter to send · Shift+Enter for new line'}
          </div>
        </div>
      </div>
    </div>
  )
}

function EmptyState({ onSuggest }) {
  const [hov, setHov] = useState(null)
  return (
    <div style={{
      display:'flex', flexDirection:'column', alignItems:'center',
      justifyContent:'center', minHeight:'100%', padding:'60px 24px',
    }}>
      {/* Hero */}
      <div style={{ textAlign:'center', marginBottom:48 }}>
        <div style={{
          width:64, height:64, borderRadius:16, margin:'0 auto 20px',
          background:'linear-gradient(135deg,#ff6d5a,#ff3d2f)',
          display:'flex', alignItems:'center', justifyContent:'center',
          boxShadow:'0 8px 24px rgba(255,109,90,0.3)',
        }}>
          <Icon d={ICO.zap} size={28} color="#fff" sw={2.5} />
        </div>
        <h1 style={{ fontSize:26, fontWeight:700, color:'var(--n8n-text-1)', letterSpacing:'-0.5px', marginBottom:10 }}>
          What should we automate?
        </h1>
        <p style={{ fontSize:14, color:'var(--n8n-text-2)', maxWidth:440, lineHeight:1.7, margin:'0 auto' }}>
          Describe your automation in plain English. The agent reasons through the full
          solution, selects real n8n nodes from the registry, and deploys a working workflow.
        </p>
      </div>

      {/* Suggestions grid */}
      <div style={{ width:'100%', maxWidth:660 }}>
        <div style={{ fontSize:11, fontWeight:600, textTransform:'uppercase', letterSpacing:'0.08em', color:'var(--n8n-text-3)', marginBottom:12, textAlign:'center' }}>
          Try one of these
        </div>
        <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
          {SUGGESTIONS.map((s, i) => (
            <button key={i} onClick={() => onSuggest(s.text)}
              onMouseEnter={() => setHov(i)} onMouseLeave={() => setHov(null)}
              style={{
                width:'100%', padding:'13px 16px', textAlign:'left',
                background: hov===i ? 'var(--n8n-card-hover)' : 'var(--n8n-card)',
                border:'1px solid ' + (hov===i ? 'var(--n8n-border-focus)' : 'var(--n8n-border)'),
                borderRadius:10, cursor:'pointer',
                display:'flex', alignItems:'flex-start', gap:12,
                transition:'all 0.15s',
              }}
            >
              <span style={{
                fontSize:10, fontWeight:700, color:'var(--n8n-orange)', textTransform:'uppercase',
                letterSpacing:'0.06em', background:'var(--n8n-orange-dim)',
                border:'1px solid var(--n8n-orange-border)',
                padding:'2px 8px', borderRadius:20, flexShrink:0, marginTop:1,
              }}>{s.label}</span>
              <span style={{ fontSize:13, color: hov===i ? 'var(--n8n-text-1)' : 'var(--n8n-text-2)', lineHeight:1.5 }}>
                {s.text}
              </span>
              <Icon d={ICO.arrow} size={14} color={hov===i ? 'var(--n8n-orange)' : 'var(--n8n-text-4)'} style={{ flexShrink:0, marginLeft:'auto', marginTop:2 }} />
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}