import React from 'react'
import { CheckCircle2, Clock, AlertCircle, RefreshCw, UserCheck } from 'lucide-react'
import { ReviewJob, JobStage } from '../../../types/api'

interface ReviewProgressProps {
  job?: ReviewJob | null
  onRetry?: () => void
  onManualReview?: () => void
}

const STAGES: { key: JobStage; label: string }[] = [
  { key: 'masking', label: '1. PII & Secret Masking' },
  { key: 'rules', label: '2. Deterministic Rules' },
  { key: 'claims', label: '3. Claim Court & Facts' },
  { key: 'tone', label: '4. Tone & Consistency' },
  { key: 'images', label: '5. Creative & OCR' },
]

export function ReviewProgress({ job, onRetry, onManualReview }: ReviewProgressProps) {
  if (!job) return null

  const isFailed = job.status === 'failed'
  const isCompleted = job.status === 'completed'

  const currentStageIndex = STAGES.findIndex((s) => s.key === job.stage)
  const effectiveIndex = isCompleted ? STAGES.length : currentStageIndex === -1 ? 0 : currentStageIndex

  return (
    <div
      className="review-progress-panel"
      style={{
        padding: '1.25rem',
        borderRadius: '10px',
        backgroundColor: 'var(--color-bg-panel, rgba(30, 41, 59, 0.7))',
        border: '1px solid var(--color-border, rgba(148, 163, 184, 0.2))',
        marginBottom: '1.5rem',
      }}
      data-testid="review-progress"
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          marginBottom: '1rem',
          flexWrap: 'wrap',
          gap: '0.5rem',
        }}
      >
        <div>
          <h4 style={{ fontSize: '0.95rem', fontWeight: 600, margin: '0 0 0.2rem 0' }}>
            Claim Court Review Job
          </h4>
          <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted, #94a3b8)' }}>
            Job ID: <strong style={{ fontFamily: 'monospace', wordBreak: 'break-all' }}>{job.id}</strong> · Status:{' '}
            <strong style={{ textTransform: 'capitalize', color: isFailed ? '#ef4444' : 'var(--accent, #0f766e)' }}>
              {job.status}
            </strong>
          </span>
        </div>

        {/* Action if failed: retry or human review */}
        {isFailed && (
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {onRetry && (
              <button
                onClick={onRetry}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                  padding: '0.35rem 0.75rem',
                  borderRadius: '6px',
                  backgroundColor: '#ef4444',
                  color: '#ffffff',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  border: 'none',
                  cursor: 'pointer',
                }}
              >
                <RefreshCw size={12} /> Retry stage
              </button>
            )}
            {onManualReview && (
              <button
                onClick={onManualReview}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.35rem',
                  padding: '0.35rem 0.75rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--color-bg-subtle, rgba(255, 255, 255, 0.1))',
                  border: '1px solid var(--color-border, rgba(148, 163, 184, 0.3))',
                  color: '#ffffff',
                  fontSize: '0.75rem',
                  fontWeight: 600,
                  cursor: 'pointer',
                }}
              >
                <UserCheck size={12} /> Flag needs_human_review
              </button>
            )}
          </div>
        )}
      </div>

      {/* Stage indicators - strictly showing actual stages, never fake progress */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
          gap: '0.5rem',
        }}
      >
        {STAGES.map((s, idx) => {
          const isDone = isCompleted || idx < effectiveIndex
          const isCurrent = !isCompleted && !isFailed && idx === effectiveIndex
          const isStageFailed = isFailed && idx === effectiveIndex

          return (
            <div
              key={s.key}
              style={{
                padding: '0.6rem 0.75rem',
                borderRadius: '6px',
                backgroundColor: isDone
                  ? 'rgba(34, 197, 94, 0.1)'
                  : isStageFailed
                  ? 'rgba(239, 68, 68, 0.1)'
                  : isCurrent
                  ? 'rgba(99, 102, 241, 0.15)'
                  : 'var(--color-bg-subtle, rgba(0, 0, 0, 0.2))',
                border: `1px solid ${
                  isDone
                    ? 'rgba(34, 197, 94, 0.3)'
                    : isStageFailed
                    ? 'rgba(239, 68, 68, 0.3)'
                    : isCurrent
                    ? 'rgba(99, 102, 241, 0.4)'
                    : 'var(--color-border, rgba(148, 163, 184, 0.1))'
                }`,
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}
            >
              {isDone ? (
                <CheckCircle2 size={16} color="#22c55e" />
              ) : isStageFailed ? (
                <AlertCircle size={16} color="#ef4444" />
              ) : isCurrent ? (
                <Clock size={16} color="var(--accent, #0f766e)" className="animate-spin" />
              ) : (
                <span
                  style={{
                    width: '16px',
                    height: '16px',
                    borderRadius: '50%',
                    border: '1px solid #64748b',
                    display: 'inline-block',
                  }}
                />
              )}
              <span
                style={{
                  fontSize: '0.75rem',
                  fontWeight: isCurrent || isDone ? 600 : 400,
                  color: isDone
                    ? '#22c55e'
                    : isStageFailed
                    ? '#ef4444'
                    : isCurrent
                    ? 'var(--accent, #0f766e)'
                    : 'var(--color-text-muted, #475569)',
                }}
              >
                {s.label}
              </span>
            </div>
          )
        })}
      </div>

      {isFailed && job.error && (
        <div
          style={{
            marginTop: '0.75rem',
            padding: '0.5rem 0.75rem',
            borderRadius: '6px',
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.3)',
            color: '#ef4444',
            fontSize: '0.8rem',
          }}
        >
          <strong>Stage Error:</strong> {job.error} (Rule 1: Failed steps become needs_human_review findings)
        </div>
      )}
    </div>
  )
}

