const Icon = ({ d, size=14, color='currentColor', sw=1.75 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke={color} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
)

const ICO = {
  check: 'M20 6L9 17l-5-5',
  spin:  'M21 12a9 9 0 1 1-6.22-8.56',
  circle:'M12 12m-9 0a9 9 0 1 0 18 0a9 9 0 1 0-18 0',
}

export default function PipelineStatus({ stageIdx, stages }) {
  return (
    <div className="fade-up" style={{
      marginBottom:24, background:'var(--n8n-card)',
      border:'1px solid var(--n8n-border)', borderRadius:12, overflow:'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding:'11px 16px', borderBottom:'1px solid var(--n8n-border)',
        display:'flex', alignItems:'center', gap:10,
        background:'var(--n8n-surface)',
      }}>
        <div style={{
          width:7, height:7, borderRadius:'50%', background:'var(--n8n-orange)',
          boxShadow:'0 0 8px rgba(255,109,90,0.7)',
          animation:'pulse-dot 1s ease infinite',
        }} />
        <span style={{ fontSize:12, fontWeight:600, color:'var(--n8n-text-1)', letterSpacing:'-0.1px' }}>
          Agent Pipeline
        </span>
        <span style={{ fontSize:11, color:'var(--n8n-text-3)', marginLeft:'auto' }}>
          {stageIdx + 1} / {stages.length}
        </span>
      </div>

      {/* Progress bar */}
      <div style={{ height:2, background:'var(--n8n-border)' }}>
        <div style={{
          height:'100%', background:'var(--n8n-orange)',
          width:`${((stageIdx + 1) / stages.length) * 100}%`,
          transition:'width 0.4s cubic-bezier(0.4,0,0.2,1)',
          borderRadius:'0 2px 2px 0',
        }} />
      </div>

      {/* Stage list */}
      <div style={{ padding:'6px 0' }}>
        {stages.map((stage, i) => {
          const done   = i < stageIdx
          const active = i === stageIdx
          const future = i > stageIdx
          return (
            <div key={stage.id} style={{
              display:'flex', alignItems:'center', gap:12,
              padding:'7px 16px',
              background: active ? 'rgba(255,109,90,0.06)' : 'transparent',
              borderLeft:`2px solid ${active ? 'var(--n8n-orange)' : 'transparent'}`,
              transition:'all 0.2s',
            }}>
              {/* Step icon */}
              <div style={{ width:20, height:20, flexShrink:0, display:'flex', alignItems:'center', justifyContent:'center' }}>
                {done ? (
                  <div style={{ width:18, height:18, borderRadius:'50%', background:'var(--n8n-green)', display:'flex', alignItems:'center', justifyContent:'center' }}>
                    <Icon d={ICO.check} size={11} color="#fff" sw={2.5} />
                  </div>
                ) : active ? (
                  <div style={{ width:18, height:18, borderRadius:'50%', border:'2px solid var(--n8n-orange)', display:'flex', alignItems:'center', justifyContent:'center' }}>
                    <div style={{ width:7, height:7, borderRadius:'50%', background:'var(--n8n-orange)', animation:'pulse-dot 1s ease infinite' }} />
                  </div>
                ) : (
                  <div style={{ width:18, height:18, borderRadius:'50%', border:'2px solid var(--n8n-border)' }} />
                )}
              </div>

              {/* Label */}
              <div style={{ flex:1 }}>
                <div style={{
                  fontSize:12, fontWeight: active ? 600 : 400,
                  color: done ? 'var(--n8n-green)' : active ? 'var(--n8n-text-1)' : 'var(--n8n-text-3)',
                }}>
                  {stage.label}
                </div>
                {active && (
                  <div style={{ fontSize:11, color:'var(--n8n-text-3)', marginTop:1 }}>
                    {stage.desc}
                  </div>
                )}
              </div>

              {/* Status */}
              {done && <span style={{ fontSize:11, color:'var(--n8n-green)' }}>Done</span>}
              {active && (
                <svg className="spin" width={13} height={13} viewBox="0 0 24 24" fill="none"
                  stroke="var(--n8n-orange)" strokeWidth={2.5} strokeLinecap="round">
                  <path d={ICO.spin} />
                </svg>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}