const Icon = ({ d, size=13, color='currentColor', sw=1.75 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke={color} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
)

const ICO = {
  check:   'M20 6L9 17l-5-5',
  link:    'M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3',
  key:     'M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4',
  arrow:   'M5 12h14M12 5l7 7-7 7',
  star:    'M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z',
  warning: 'M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4M12 17h.01',
  node:    'M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z',
}

// Map node display names to colors (matches n8n's node color palette)
function nodeColor(name) {
  const n = name.toLowerCase()
  if (n.includes('gmail') || n.includes('email'))  return { bg:'#EA4335', light:'rgba(234,67,53,0.12)' }
  if (n.includes('sheet') || n.includes('google')) return { bg:'#34A853', light:'rgba(52,168,83,0.12)' }
  if (n.includes('if') || n.includes('filter'))    return { bg:'#FF6D5A', light:'rgba(255,109,90,0.12)' }
  if (n.includes('set') || n.includes('code'))     return { bg:'#6366F1', light:'rgba(99,102,241,0.12)' }
  if (n.includes('webhook'))                        return { bg:'#F59E0B', light:'rgba(245,158,11,0.12)' }
  if (n.includes('notion'))                         return { bg:'#ffffff', light:'rgba(255,255,255,0.08)' }
  if (n.includes('http'))                           return { bg:'#8B5CF6', light:'rgba(139,92,246,0.12)' }
  return { bg:'#6B7280', light:'rgba(107,114,128,0.12)' }
}

function NodePill({ name }) {
  const { bg, light } = nodeColor(name)
  return (
    <div style={{
      display:'flex', alignItems:'center', gap:7,
      padding:'5px 12px 5px 8px',
      background: light,
      border:`1px solid ${bg}30`,
      borderRadius:8, flexShrink:0,
    }}>
      <div style={{ width:18, height:18, borderRadius:5, background:bg, display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
        <Icon d={ICO.node} size={10} color="#fff" sw={2} />
      </div>
      <span style={{ fontSize:12, fontWeight:500, color:'var(--n8n-text-1)', whiteSpace:'nowrap' }}>{name}</span>
    </div>
  )
}

function ArrowConnector() {
  return (
    <div style={{ display:'flex', alignItems:'center', padding:'0 4px', flexShrink:0 }}>
      <Icon d={ICO.arrow} size={13} color="var(--n8n-text-4)" sw={1.75} />
    </div>
  )
}

export default function WorkflowResult({ result }) {
  const {
    workflow_name, workflow_id, n8n_url,
    nodes = [], missing_credentials = [],
    reflection_score, validation_passed,
  } = result

  const score = reflection_score || 0
  const scoreColor = score >= 8 ? 'var(--n8n-green)' : score >= 6 ? 'var(--n8n-yellow)' : 'var(--n8n-red)'
  const scoreBg = score >= 8 ? 'var(--n8n-green-dim)' : score >= 6 ? 'var(--n8n-yellow-dim)' : 'var(--n8n-red-dim)'

  return (
    <div style={{
      background:'var(--n8n-card)',
      border:'1px solid var(--n8n-border)',
      borderRadius:12, overflow:'hidden',
    }}>
      {/* Header bar */}
      <div style={{
        padding:'12px 16px',
        background:'var(--n8n-surface)',
        borderBottom:'1px solid var(--n8n-border)',
        display:'flex', alignItems:'center', gap:10,
      }}>
        {/* Green check */}
        <div style={{
          width:22, height:22, borderRadius:6, background:'var(--n8n-green)',
          display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0,
        }}>
          <Icon d={ICO.check} size={12} color="#fff" sw={2.5} />
        </div>

        <div style={{ flex:1 }}>
          <div style={{ fontSize:13, fontWeight:600, color:'var(--n8n-text-1)', letterSpacing:'-0.1px' }}>
            {workflow_name}
          </div>
          <div style={{ fontSize:11, color:'var(--n8n-text-3)', marginTop:1 }}>
            Created as inactive draft — configure credentials to activate
          </div>
        </div>

        {/* Quality score badge */}
        {score > 0 && (
          <div style={{
            display:'flex', alignItems:'center', gap:4,
            fontSize:12, fontWeight:600, color:scoreColor,
            background:scoreBg, padding:'3px 10px', borderRadius:20,
            border:`1px solid ${scoreColor}30`,
          }}>
            <Icon d={ICO.star} size={10} color={scoreColor} sw={0} />
            <span style={{ fill:scoreColor }}>{score}/10</span>
          </div>
        )}
      </div>

      {/* Node flow */}
      {nodes.length > 0 && (
        <div style={{ padding:'14px 16px', borderBottom:'1px solid var(--n8n-border)' }}>
          <div style={{ fontSize:10, fontWeight:600, textTransform:'uppercase', letterSpacing:'0.08em', color:'var(--n8n-text-3)', marginBottom:10 }}>
            Workflow
          </div>
          <div style={{ display:'flex', alignItems:'center', flexWrap:'wrap', gap:4 }}>
            {nodes.map((name, i) => (
              <div key={i} style={{ display:'flex', alignItems:'center', gap:4 }}>
                <NodePill name={name} />
                {i < nodes.length - 1 && <ArrowConnector />}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Missing credentials */}
      {missing_credentials.length > 0 && (
        <div style={{ padding:'12px 16px', borderBottom:'1px solid var(--n8n-border)' }}>
          <div style={{
            display:'flex', alignItems:'center', gap:6, marginBottom:8,
            fontSize:10, fontWeight:600, textTransform:'uppercase', letterSpacing:'0.08em',
            color:'var(--n8n-yellow)',
          }}>
            <Icon d={ICO.warning} size={12} color="var(--n8n-yellow)" sw={2} />
            Configure in n8n before activating
          </div>
          <div style={{ display:'flex', flexDirection:'column', gap:5 }}>
            {missing_credentials.map((c, i) => (
              <div key={i} style={{
                display:'flex', alignItems:'center', gap:10, padding:'6px 10px',
                background:'var(--n8n-yellow-dim)', borderRadius:7,
                border:'1px solid rgba(245,158,11,0.15)',
              }}>
                <Icon d={ICO.key} size={11} color="var(--n8n-yellow)" sw={2} />
                <code style={{ fontSize:12, color:'var(--n8n-text-2)', fontFamily:'var(--font-mono)' }}>{c}</code>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Footer actions */}
      <div style={{
        padding:'10px 16px', display:'flex', alignItems:'center', gap:10,
      }}>
        {n8n_url ? (
          <a href={n8n_url} target="_blank" rel="noreferrer"
            style={{
              display:'flex', alignItems:'center', gap:7, fontSize:12, fontWeight:600,
              color:'var(--n8n-orange)', background:'var(--n8n-orange-dim)',
              border:'1px solid var(--n8n-orange-border)',
              padding:'6px 14px', borderRadius:7, transition:'all 0.15s',
            }}
            onMouseEnter={e => e.currentTarget.style.background='rgba(255,109,90,0.2)'}
            onMouseLeave={e => e.currentTarget.style.background='var(--n8n-orange-dim)'}
          >
            <Icon d={ICO.link} size={12} color="var(--n8n-orange)" sw={2} />
            Open in n8n
          </a>
        ) : null}

        <div style={{ marginLeft:'auto', display:'flex', alignItems:'center', gap:6 }}>
          <span style={{
            fontSize:11, padding:'3px 10px', borderRadius:20,
            background: validation_passed ? 'var(--n8n-green-dim)' : 'var(--n8n-red-dim)',
            color: validation_passed ? 'var(--n8n-green)' : 'var(--n8n-red)',
            border: `1px solid ${validation_passed ? 'var(--n8n-green-border)' : 'rgba(239,68,68,0.2)'}`,
            fontWeight:500,
          }}>
            {validation_passed ? '✓ Validated' : '⚠ Check errors'}
          </span>
          {workflow_id && (
            <span style={{ fontSize:11, color:'var(--n8n-text-4)', fontFamily:'var(--font-mono)' }}>
              #{workflow_id.slice(0,8)}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}