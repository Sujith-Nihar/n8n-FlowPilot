import { useState } from 'react'

/* ── icons (inline SVG to avoid lucide version issues) ── */
const Icon = ({ d, size = 16, color = 'currentColor', strokeWidth = 1.75 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
)
const ICO = {
  plus:     'M12 5v14M5 12h14',
  chat:     'M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z',
  zap:      'M13 2L3 14h9l-1 10 10-12h-9l1-10z',
  db:       'M12 2C6.5 2 2 4.24 2 7s4.5 5 10 5 10-2.24 10-5-4.5-5-10-5zM2 17c0 2.76 4.5 5 10 5s10-2.24 10-5M2 12c0 2.76 4.5 5 10 5s10-2.24 10-5',
  workflow: 'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z',
  menu:     'M3 12h18M3 6h18M3 18h18',
}

function N8NLogo() {
  return (
    <div style={{ display:'flex', alignItems:'center', gap:10 }}>
      {/* n8n orange node icon */}
      <div style={{
        width:32, height:32, borderRadius:8,
        background:'linear-gradient(135deg, #ff6d5a 0%, #ff3d2f 100%)',
        display:'flex', alignItems:'center', justifyContent:'center',
        flexShrink:0, boxShadow:'0 2px 8px rgba(255,109,90,0.35)',
      }}>
        <Icon d={ICO.zap} size={16} color="#fff" strokeWidth={2.5} />
      </div>
      <div>
        <div style={{ fontSize:14, fontWeight:700, color:'var(--n8n-text-1)', letterSpacing:'-0.2px' }}>
          n8n FlowPilot
        </div>
        <div style={{ fontSize:11, color:'var(--n8n-text-3)', marginTop:1 }}>
          Powered by n8n
        </div>
      </div>
    </div>
  )
}

function StatusDot({ ok }) {
  return (
    <span style={{
      display:'inline-block', width:6, height:6, borderRadius:'50%', flexShrink:0,
      background: ok ? 'var(--n8n-green)' : 'var(--n8n-red)',
      boxShadow: ok ? '0 0 5px rgba(34,197,94,0.6)' : 'none',
      animation: ok ? 'none' : 'pulse-dot 1.5s ease infinite',
    }} />
  )
}

export default function Sidebar({ open, health, sessions, activeId, onNew, onSelect, onToggle }) {
  const n8nOk = health?.n8n_connected
  const dbOk  = health?.supabase_connected
  const stats = health?.registry_stats || {}
  const [hovered, setHovered] = useState(null)

  return (
    <div style={{
      width: open ? 260 : 0,
      minWidth: open ? 260 : 0,
      overflow:'hidden',
      display:'flex', flexDirection:'column',
      background:'var(--n8n-surface)',
      borderRight:'1px solid var(--n8n-border)',
      transition:'width 0.2s cubic-bezier(0.4,0,0.2,1), min-width 0.2s cubic-bezier(0.4,0,0.2,1)',
      position:'relative', flexShrink:0,
    }}>
      <div style={{ width:260, height:'100%', display:'flex', flexDirection:'column' }}>

        {/* Logo header */}
        <div style={{ padding:'18px 16px 14px', borderBottom:'1px solid var(--n8n-border)' }}>
          <N8NLogo />
        </div>

        {/* New chat button */}
        <div style={{ padding:'12px 12px 8px' }}>
          <button
            onClick={onNew}
            style={{
              width:'100%', padding:'9px 14px',
              background:'var(--n8n-orange)', border:'none', borderRadius:8,
              color:'#fff', fontSize:13, fontWeight:600,
              display:'flex', alignItems:'center', gap:8,
              transition:'background 0.15s, transform 0.1s',
              letterSpacing:'-0.1px',
            }}
            onMouseEnter={e => e.currentTarget.style.background='var(--n8n-orange-hover)'}
            onMouseLeave={e => e.currentTarget.style.background='var(--n8n-orange)'}
            onMouseDown={e  => e.currentTarget.style.transform='scale(0.98)'}
            onMouseUp={e    => e.currentTarget.style.transform='scale(1)'}
          >
            <Icon d={ICO.plus} size={15} color="#fff" strokeWidth={2.5} />
            New Workflow
          </button>
        </div>

        {/* Sessions */}
        <div style={{ padding:'0 8px 4px' }}>
          <div style={{ fontSize:10, fontWeight:600, letterSpacing:'0.08em', textTransform:'uppercase', color:'var(--n8n-text-3)', padding:'6px 8px 4px' }}>
            Recent
          </div>
          {sessions.map(s => {
            const isActive = s.id === activeId
            const isHov = hovered === s.id
            return (
              <div
                key={s.id}
                onClick={() => onSelect(s.id)}
                onMouseEnter={() => setHovered(s.id)}
                onMouseLeave={() => setHovered(null)}
                style={{
                  display:'flex', alignItems:'center', gap:10,
                  padding:'8px 10px', borderRadius:7, cursor:'pointer', marginBottom:1,
                  background: isActive ? 'var(--n8n-orange-dim)' : isHov ? 'var(--n8n-card-hover)' : 'transparent',
                  border: isActive ? '1px solid var(--n8n-orange-border)' : '1px solid transparent',
                  transition:'all 0.12s',
                }}
              >
                <Icon d={ICO.chat} size={13}
                  color={isActive ? 'var(--n8n-orange)' : 'var(--n8n-text-3)'}
                  strokeWidth={isActive ? 2 : 1.75} />
                <span style={{
                  fontSize:13, flex:1,
                  color: isActive ? 'var(--n8n-text-1)' : 'var(--n8n-text-2)',
                  fontWeight: isActive ? 500 : 400,
                  whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis',
                }}>
                  {s.label}
                </span>
              </div>
            )
          })}
        </div>

        <div style={{ flex:1 }} />

        {/* Registry stats */}
        {stats.nodes && (
          <div style={{ margin:'0 12px 10px', padding:'12px', background:'var(--n8n-card)', borderRadius:10, border:'1px solid var(--n8n-border)' }}>
            <div style={{ fontSize:10, fontWeight:600, letterSpacing:'0.08em', textTransform:'uppercase', color:'var(--n8n-text-3)', marginBottom:10 }}>
              Registry
            </div>
            <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr 1fr', gap:6 }}>
              {[['Nodes', stats.nodes], ['Ops', stats.operations], ['Creds', stats.credentials]].map(([l, v]) => (
                <div key={l} style={{ textAlign:'center', padding:'6px 4px', background:'var(--n8n-surface)', borderRadius:6 }}>
                  <div style={{ fontSize:14, fontWeight:700, color:'var(--n8n-text-1)' }}>{v?.toLocaleString()}</div>
                  <div style={{ fontSize:10, color:'var(--n8n-text-3)', marginTop:1 }}>{l}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Connection status */}
        <div style={{ padding:'10px 16px 16px', borderTop:'1px solid var(--n8n-border)' }}>
          {[['n8n', n8nOk], ['Supabase', dbOk]].map(([label, ok]) => (
            <div key={label} style={{ display:'flex', alignItems:'center', gap:8, marginBottom:5 }}>
              <StatusDot ok={ok} />
              <span style={{ fontSize:12, color:'var(--n8n-text-3)' }}>
                {label} — <span style={{ color: ok ? 'var(--n8n-green)' : 'var(--n8n-red)' }}>
                  {ok === undefined ? 'checking...' : ok ? 'connected' : 'offline'}
                </span>
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}