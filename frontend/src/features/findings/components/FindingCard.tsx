import { useState } from 'react'
import {
  Check,
  Edit2,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  Sparkles,
  History,
  Lock,
} from 'lucide-react'
import { ClaimFinding } from '../../../types/api'
import { SeverityBadge } from '../../../components/common/SeverityBadge'
import { StatusBadge } from '../../../components/common/StatusBadge'

interface FindingCardProps {
  finding: ClaimFinding
  isSelected?: boolean
  onSelect?: () => void
  onAccept?: () => void
  onEdit?: (suggestedText: string) => void
  onDispute?: (note: string) => void
  canDecide?: boolean
}

export function FindingCard({
  finding,
  isSelected = false,
  onSelect,
  onAccept,
  onEdit,
  onDispute,
  canDecide = true,
}: FindingCardProps) {
  const [showHistory, setShowHistory] = useState(false)
  const [disputeOpen, setDisputeOpen] = useState(false)
  const [disputeNote, setDisputeNote] = useState('')

  const isSafeFix = finding.intent_preserved ? finding.intent_preserved.safe : true

  return (
    <div
      onClick={onSelect}
      className={`finding-card ${isSelected ? 'finding-card--selected' : ''}`}
      style={{
        borderRadius: '12px',
        border: isSelected
          ? '2px solid var(--accent, #6366f1)'
          : '1px solid var(--color-border, rgba(148, 163, 184, 0.2))',
        backgroundColor: 'var(--color-bg-panel, rgba(30, 41, 59, 0.6))',
        padding: '1.25rem',
        marginBottom: '1rem',
        cursor: 'pointer',
        transition: 'all 0.15s ease',
        boxShadow: isSelected ? '0 8px 24px -4px rgba(99, 102, 241, 0.25)' : 'none',
      }}
      data-testid="finding-card"
    >
      {/* Top Header: Verdict, Severity, State */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '0.5rem',
          marginBottom: '0.75rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <SeverityBadge severity={finding.severity} />
          <StatusBadge status={finding.state} />
        </div>
        {finding.confidence !== undefined && (
          <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted, #94a3b8)' }}>
            Confidence: <strong>{Math.round(finding.confidence * 100)}%</strong>
          </span>
        )}
      </div>

      {/* Claim Span / Text */}
      <div style={{ marginBottom: '0.75rem' }}>
        <span
          style={{
            fontSize: '0.75rem',
            textTransform: 'uppercase',
            fontWeight: 700,
            color: 'var(--color-text-muted, #94a3b8)',
            letterSpacing: '0.05em',
          }}
        >
          Flagged span
        </span>
        <div
          style={{
            marginTop: '0.25rem',
            padding: '0.5rem 0.75rem',
            borderRadius: '6px',
            backgroundColor: 'var(--color-bg-subtle, rgba(0, 0, 0, 0.2))',
            borderLeft: `3px solid ${finding.severity === 'critical' ? '#ef4444' : finding.severity === 'major' ? '#f97316' : '#3b82f6'
              }`,
            fontFamily: 'monospace',
            fontSize: '0.875rem',
            color: 'var(--color-text-primary, #ffffff)',
          }}
        >
          "{finding.claim_text}"
        </div>
      </div>

      {/* Rationale */}
      <p style={{ fontSize: '0.85rem', color: 'var(--color-text-secondary, #cbd5e1)', margin: '0 0 0.75rem 0', lineHeight: 1.5 }}>
        {finding.rationale}
      </p>

      {/* Method & Rule citations */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          flexWrap: 'wrap',
          fontSize: '0.75rem',
          color: 'var(--color-text-muted, #94a3b8)',
          marginBottom: '1rem',
        }}
      >
        <span>
          Method: <strong style={{ fontFamily: 'monospace' }}>{finding.analysis_method}</strong>
        </span>
        {finding.rule_id && (
          <span>
            Rule: <strong>{finding.rule_id}</strong> (v{finding.rule_version || 1})
          </span>
        )}
        {finding.layer && (
          <span
            style={{
              textTransform: 'capitalize',
              backgroundColor: 'rgba(148, 163, 184, 0.1)',
              padding: '0.1rem 0.4rem',
              borderRadius: '4px',
            }}
          >
            Layer: {finding.layer}
          </span>
        )}
      </div>

      {/* Suggested Fix and Intent Preserved */}
      {finding.suggested_fix && (
        <div
          style={{
            padding: '0.875rem',
            borderRadius: '8px',
            backgroundColor: isSafeFix ? 'rgba(34, 197, 94, 0.05)' : 'rgba(239, 68, 68, 0.05)',
            border: `1px solid ${isSafeFix ? 'rgba(34, 197, 94, 0.25)' : 'rgba(239, 68, 68, 0.25)'}`,
            marginBottom: '1rem',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '0.35rem',
            }}
          >
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.75rem', fontWeight: 600, color: isSafeFix ? '#22c55e' : '#ef4444' }}>
              <Sparkles size={13} />
              <span>Suggested Fix {isSafeFix ? '(Safe)' : '(Unsafe / Blocks auto-accept)'}</span>
            </div>
            {onEdit && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  onEdit(finding.suggested_fix!)
                }}
                disabled={!isSafeFix}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.3rem',
                  fontSize: '0.75rem',
                  padding: '0.2rem 0.5rem',
                  borderRadius: '4px',
                  backgroundColor: isSafeFix ? 'var(--accent, #6366f1)' : '#64748b',
                  color: '#ffffff',
                  border: 'none',
                  cursor: isSafeFix ? 'pointer' : 'not-allowed',
                }}
                title={isSafeFix ? 'Apply this fix to a new revision' : 'Unsafe fix cannot be auto-applied'}
              >
                {!isSafeFix ? <Lock size={11} /> : <Edit2 size={11} />} Apply fix
              </button>
            )}
          </div>
          <div
            style={{
              fontFamily: 'monospace',
              fontSize: '0.825rem',
              color: 'var(--color-text-primary, #ffffff)',
              marginBottom: '0.5rem',
            }}
          >
            "{finding.suggested_fix}"
          </div>

          {finding.intent_preserved && (
            <div
              style={{
                fontSize: '0.75rem',
                color: 'var(--color-text-muted, #94a3b8)',
                borderTop: '1px solid rgba(148, 163, 184, 0.15)',
                paddingTop: '0.4rem',
              }}
            >
              <div>
                <strong>Intent:</strong> {finding.intent_preserved.purpose}
              </div>
              <div>
                <strong>CTA preserved:</strong> {finding.intent_preserved.cta}
              </div>
              {finding.intent_preserved.claims_changed.length > 0 && (
                <div>
                  <strong>Changes:</strong> {finding.intent_preserved.claims_changed.join(', ')}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Action Buttons: Accept, Edit, Dispute */}
      {canDecide && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            flexWrap: 'wrap',
            paddingTop: '0.75rem',
            borderTop: '1px solid var(--color-border, rgba(148, 163, 184, 0.15))',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {onAccept && (
            <button
              type="button"
              onClick={onAccept}
              disabled={finding.state === 'accepted'}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.4rem 0.75rem',
                borderRadius: '6px',
                fontSize: '0.8rem',
                fontWeight: 600,
                backgroundColor:
                  finding.state === 'accepted' ? 'rgba(34, 197, 94, 0.2)' : 'var(--color-bg-subtle, rgba(255, 255, 255, 0.08))',
                border: '1px solid var(--color-border, rgba(148, 163, 184, 0.25))',
                color: finding.state === 'accepted' ? '#22c55e' : 'var(--color-text-primary, #ffffff)',
                cursor: finding.state === 'accepted' ? 'default' : 'pointer',
              }}
            >
              <Check size={14} /> Accept finding
            </button>
          )}

          {onDispute && (
            <button
              type="button"
              onClick={() => setDisputeOpen((prev) => !prev)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.4rem 0.75rem',
                borderRadius: '6px',
                fontSize: '0.8rem',
                fontWeight: 600,
                backgroundColor: 'transparent',
                border: '1px solid var(--color-border, rgba(148, 163, 184, 0.25))',
                color: 'var(--color-text-secondary, #cbd5e1)',
                cursor: 'pointer',
              }}
            >
              <HelpCircle size={14} /> Dispute
            </button>
          )}

          {finding.decisions && finding.decisions.length > 0 && (
            <button
              type="button"
              onClick={() => setShowHistory((prev) => !prev)}
              style={{
                marginLeft: 'auto',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.25rem',
                fontSize: '0.75rem',
                color: 'var(--color-text-muted, #94a3b8)',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
              }}
            >
              <History size={13} />
              <span>{finding.decisions.length} decision(s)</span>
              {showHistory ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
          )}
        </div>
      )}

      {/* Dispute Note Form */}
      {disputeOpen && (
        <div
          style={{
            marginTop: '0.75rem',
            padding: '0.75rem',
            borderRadius: '6px',
            backgroundColor: 'var(--color-bg-subtle, rgba(0, 0, 0, 0.25))',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, marginBottom: '0.25rem' }}>
            Rationale for dispute (required):
          </label>
          <textarea
            value={disputeNote}
            onChange={(e) => setDisputeNote(e.target.value)}
            rows={2}
            placeholder="Explain why this claim or finding is substantiated or misclassified..."
            style={{
              width: '100%',
              borderRadius: '4px',
              padding: '0.5rem',
              fontSize: '0.8rem',
              backgroundColor: 'var(--color-bg-panel, #0f172a)',
              color: '#ffffff',
              border: '1px solid var(--color-border, rgba(148, 163, 184, 0.3))',
              marginBottom: '0.5rem',
            }}
          />
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
            <button
              type="button"
              onClick={() => setDisputeOpen(false)}
              style={{
                padding: '0.25rem 0.6rem',
                fontSize: '0.75rem',
                backgroundColor: 'transparent',
                border: '1px solid var(--color-border, rgba(148, 163, 184, 0.3))',
                color: '#cbd5e1',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={!disputeNote.trim()}
              onClick={() => {
                if (onDispute && disputeNote.trim()) {
                  onDispute(disputeNote.trim())
                  setDisputeOpen(false)
                  setDisputeNote('')
                }
              }}
              style={{
                padding: '0.25rem 0.75rem',
                fontSize: '0.75rem',
                fontWeight: 600,
                backgroundColor: disputeNote.trim() ? '#f97316' : '#64748b',
                color: '#ffffff',
                border: 'none',
                borderRadius: '4px',
                cursor: disputeNote.trim() ? 'pointer' : 'not-allowed',
              }}
            >
              Submit dispute
            </button>
          </div>
        </div>
      )}

      {/* Decision history list */}
      {showHistory && finding.decisions && (
        <div
          style={{
            marginTop: '0.75rem',
            padding: '0.75rem',
            borderRadius: '6px',
            backgroundColor: 'var(--color-bg-subtle, rgba(0, 0, 0, 0.15))',
            fontSize: '0.75rem',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <div style={{ fontWeight: 600, marginBottom: '0.4rem' }}>Decision Timeline:</div>
          {finding.decisions.map((dec) => (
            <div
              key={dec.id}
              style={{
                borderBottom: '1px solid rgba(148, 163, 184, 0.1)',
                paddingBottom: '0.35rem',
                marginBottom: '0.35rem',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <strong>
                  {dec.user_name || 'User'} ({dec.user_role || 'member'})
                </strong>
                <span style={{ color: 'var(--color-text-muted, #94a3b8)' }}>
                  {new Date(dec.created_at).toLocaleTimeString()}
                </span>
              </div>
              <div style={{ textTransform: 'capitalize', color: 'var(--accent, #818cf8)' }}>
                Action: {dec.action}
              </div>
              {dec.note && <div style={{ fontStyle: 'italic', marginTop: '0.15rem' }}>"{dec.note}"</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

