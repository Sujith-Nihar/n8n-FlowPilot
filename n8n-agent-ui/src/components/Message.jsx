import WorkflowResult from './WorkflowResult'

const Icon = ({ d, size = 14, color = 'currentColor', sw = 1.75 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
    stroke={color} strokeWidth={sw} strokeLinecap="round" strokeLinejoin="round">
    <path d={d} />
  </svg>
)

function UserAvatar() {
  return (
    <div style={{
      width: 32, height: 32, borderRadius: 8, flexShrink: 0,
      background: 'var(--n8n-border-focus)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: 12, fontWeight: 700, color: 'var(--n8n-text-1)',
    }}>
      U
    </div>
  )
}

function AgentAvatar() {
  return (
    <div style={{
      width: 32, height: 32, borderRadius: 8, flexShrink: 0,
      background: 'linear-gradient(135deg, #ff6d5a, #ff3d2f)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      boxShadow: '0 2px 8px rgba(255,109,90,0.3)',
    }}>
      <Icon d="M13 2L3 14h9l-1 10 10-12h-9l1-10z" size={16} color="#fff" sw={2.5} />
    </div>
  )
}

export default function Message({ message }) {
  const isUser = message.role === 'user'

  return (
    <div className="fade-up" style={{
      display: 'flex',
      gap: 12,
      flexDirection: isUser ? 'row-reverse' : 'row',
      marginBottom: 20,
      alignItems: 'flex-start',
    }}>
      {isUser ? <UserAvatar /> : <AgentAvatar />}

      <div style={{ maxWidth: '78%', minWidth: 0 }}>
        {/* Sender label */}
        <div style={{
          fontSize: 11,
          color: 'var(--n8n-text-3)',
          marginBottom: 5,
          textAlign: isUser ? 'right' : 'left',
        }}>
          {isUser ? 'You' : 'n8n Agent'}
        </div>

        {/* User bubble */}
        {isUser ? (
          <div style={{
            background: 'var(--n8n-card)',
            border: '1px solid var(--n8n-border)',
            borderRadius: '12px 4px 12px 12px',
            padding: '11px 15px',
            fontSize: 14,
            color: 'var(--n8n-text-1)',
            lineHeight: 1.65,
          }}>
            {message.content}
          </div>
        ) : (
          /* Agent bubble */
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            <div style={{
              background: message.error ? 'var(--n8n-red-dim)' : 'var(--n8n-surface)',
              border: `1px solid ${message.error ? 'rgba(239,68,68,0.25)' : 'var(--n8n-border)'}`,
              borderRadius: '4px 12px 12px 12px',
              padding: '11px 15px',
              fontSize: 14,
              color: message.error ? 'var(--n8n-red)' : 'var(--n8n-text-1)',
              lineHeight: 1.65,
            }}>
              {renderText(message.content)}
            </div>

            {/* Workflow result card */}
            {message.result?.workflow_id && (
              <WorkflowResult result={message.result} />
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function renderText(text) {
  if (!text) return null
  return text.split('\n').map((line, i) => {
    if (!line.trim()) return <div key={i} style={{ height: 6 }} />
    return <div key={i}>{line}</div>
  })
}