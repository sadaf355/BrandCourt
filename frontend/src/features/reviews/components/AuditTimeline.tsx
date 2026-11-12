import React from 'react'
import { AuditEvent } from '../../../types/api'

interface AuditTimelineProps {
  events: AuditEvent[]
}

export function AuditTimeline({ events }: AuditTimelineProps) {
  if (events.length === 0) {
    return (
      <div style={{ padding: '1.5rem', textAlign: 'center', color: 'var(--color-text-muted, #94a3b8)', fontSize: '0.85rem' }}>
        No audit events recorded yet.
      </div>
    )
  }

  return (
    <div className="audit-timeline" style={{ position: 'relative', paddingLeft: '1.5rem' }}>
      {/* Vertical line */}
      <div
        style={{
          position: 'absolute',
          left: '7px',
          top: '8px',
          bottom: '8px',
          width: '2px',
          backgroundColor: 'var(--color-border, rgba(148, 163, 184, 0.2))',
        }}
      />

      {events.map((evt) => {
        return (
          <div
            key={evt.id}
            style={{
              position: 'relative',
              marginBottom: '1.25rem',
            }}
          >
            {/* Timeline node */}
            <div
              style={{
                position: 'absolute',
                left: '-1.5rem',
                top: '2px',
                width: '16px',
                height: '16px',
                borderRadius: '50%',
                backgroundColor: 'var(--accent, #0f766e)',
                border: '3px solid var(--color-bg-panel, #ffffff)',
              }}
            />

            <div
              style={{
                display: 'flex',
                alignItems: 'baseline',
                justifyContent: 'space-between',
                flexWrap: 'wrap',
                gap: '0.5rem',
              }}
            >
              <strong style={{ fontSize: '0.85rem', color: 'var(--color-text-primary, #ffffff)' }}>
                {evt.action}
              </strong>
              <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted, #94a3b8)' }}>
                {new Date(evt.created_at).toLocaleString()}
              </span>
            </div>

            <div style={{ fontSize: '0.785rem', color: 'var(--color-text-secondary, #cbd5e1)', marginTop: '0.2rem' }}>
              Actor: <span style={{ fontFamily: 'monospace' }}>{evt.user_id}</span>
            </div>

            {evt.details && Object.keys(evt.details).length > 0 && (
              <pre
                style={{
                  marginTop: '0.4rem',
                  padding: '0.5rem',
                  borderRadius: '4px',
                  backgroundColor: 'var(--color-bg-subtle, rgba(0, 0, 0, 0.25))',
                  fontSize: '0.725rem',
                  overflowX: 'auto',
                  fontFamily: 'monospace',
                  color: 'var(--color-text-muted, #94a3b8)',
                }}
              >
                {JSON.stringify(evt.details, null, 2)}
              </pre>
            )}
          </div>
        )
      })}
    </div>
  )
}

