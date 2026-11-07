import React from 'react'
import { ShieldCheck, ShieldAlert, Lock, CheckCircle2 } from 'lucide-react'
import { ClaimFinding } from '../../../types/api'

interface ApprovalGateProps {
  findings: ClaimFinding[]
  userRole: string
  onApprove?: () => void
  onReject?: () => void
  disabled?: boolean
}

export function ApprovalGate({
  findings,
  userRole,
  onApprove,
  onReject,
  disabled = false,
}: ApprovalGateProps) {
  const isManagerOrAdmin = userRole === 'manager' || userRole === 'admin'

  // Blocker findings: unresolved critical, or contradicted / outdated / unsupported findings
  const blockers = findings.filter(
    (f) =>
      f.state !== 'accepted' &&
      f.state !== 'overridden' &&
      f.state !== 'resolved' &&
      (f.severity === 'critical' ||
        f.verdict === 'contradicted' ||
        f.verdict === 'outdated' ||
        f.verdict === 'unsupported')
  )

  const isBlocked = blockers.length > 0

  return (
    <div
      className="approval-gate-card"
      style={{
        padding: '1.25rem',
        borderRadius: '10px',
        backgroundColor: isBlocked
          ? 'rgba(239, 68, 68, 0.08)'
          : 'rgba(34, 197, 94, 0.08)',
        border: `1px solid ${isBlocked ? 'rgba(239, 68, 68, 0.3)' : 'rgba(34, 197, 94, 0.3)'}`,
        marginTop: '1.5rem',
      }}
      data-testid="approval-gate"
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {isBlocked ? (
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '50%',
                backgroundColor: 'rgba(239, 68, 68, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#ef4444',
              }}
            >
              <ShieldAlert size={22} />
            </div>
          ) : (
            <div
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '50%',
                backgroundColor: 'rgba(34, 197, 94, 0.15)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#22c55e',
              }}
            >
              <ShieldCheck size={22} />
            </div>
          )}

          <div>
            <h4 style={{ fontSize: '1rem', fontWeight: 600, margin: '0 0 0.2rem 0' }}>
              {isBlocked ? 'Publication Approval Gate: Blocked' : 'Approval Gate: Ready for Sign-Off'}
            </h4>
            <p style={{ fontSize: '0.825rem', color: 'var(--color-text-secondary, #cbd5e1)', margin: 0 }}>
              {isBlocked
                ? `${blockers.length} unresolved finding(s) prevent approval. Rules require explicit accept, override, or edit.`
                : 'All claim findings and starter rule checks are cleared or accepted. Manager sign-off permitted.'}
            </p>
          </div>
        </div>

        {/* Approval buttons */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {onReject && isManagerOrAdmin && (
            <button
              onClick={onReject}
              disabled={disabled}
              style={{
                padding: '0.5rem 1rem',
                borderRadius: '6px',
                backgroundColor: 'transparent',
                border: '1px solid rgba(239, 68, 68, 0.4)',
                color: '#ef4444',
                fontSize: '0.85rem',
                fontWeight: 600,
                cursor: disabled ? 'not-allowed' : 'pointer',
              }}
            >
              Reject
            </button>
          )}

          {onApprove && (
            <button
              onClick={onApprove}
              disabled={disabled || isBlocked || !isManagerOrAdmin}
              title={
                !isManagerOrAdmin
                  ? 'Only manager or guideline owner roles can approve content'
                  : isBlocked
                  ? `Blocked by ${blockers.length} finding(s)`
                  : 'Approve content revision'
              }
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.4rem',
                padding: '0.5rem 1.25rem',
                borderRadius: '6px',
                backgroundColor: isBlocked || !isManagerOrAdmin ? '#64748b' : '#22c55e',
                color: '#ffffff',
                fontSize: '0.85rem',
                fontWeight: 600,
                border: 'none',
                cursor: isBlocked || !isManagerOrAdmin || disabled ? 'not-allowed' : 'pointer',
              }}
            >
              {isBlocked || !isManagerOrAdmin ? <Lock size={14} /> : <CheckCircle2 size={14} />}
              Approve for Publication
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

