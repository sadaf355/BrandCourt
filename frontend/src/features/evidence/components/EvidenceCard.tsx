import React from 'react'
import { FileText, BookOpen, ShieldCheck, ExternalLink, Calendar, Layers } from 'lucide-react'
import { EvidenceItem } from '../../../types/api'

interface EvidenceCardProps {
  evidence: EvidenceItem
  isActive?: boolean
  onClick?: () => void
}

export function EvidenceCard({ evidence, isActive = false, onClick }: EvidenceCardProps) {
  const isRule = evidence.source_type === 'rule'
  const isFact = evidence.source_type === 'fact'

  const Icon = isRule ? BookOpen : isFact ? ShieldCheck : FileText
  const badgeColor = isRule ? '#f97316' : isFact ? '#22c55e' : '#3b82f6'

  return (
    <div
      onClick={onClick}
      className={`evidence-card ${isActive ? 'evidence-card--active' : ''}`}
      style={{
        padding: '1rem',
        borderRadius: '10px',
        border: isActive
          ? '2px solid var(--accent, #6366f1)'
          : '1px solid var(--color-border, rgba(148, 163, 184, 0.2))',
        backgroundColor: isActive
          ? 'var(--color-bg-subtle, rgba(99, 102, 241, 0.08))'
          : 'var(--color-bg-panel, rgba(30, 41, 59, 0.5))',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all 0.15s ease',
        marginBottom: '0.75rem',
      }}
      data-testid="evidence-card"
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <span
            style={{
              padding: '0.15rem 0.45rem',
              borderRadius: '4px',
              fontSize: '0.7rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              color: badgeColor,
              backgroundColor: `${badgeColor}22`,
              border: `1px solid ${badgeColor}44`,
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.25rem',
            }}
          >
            <Icon size={11} />
            {evidence.source_type}
          </span>
          {evidence.source_id && (
            <span style={{ fontSize: '0.75rem', fontFamily: 'monospace', color: 'var(--color-text-muted, #94a3b8)' }}>
              {evidence.source_id}
            </span>
          )}
        </div>
        {evidence.version !== undefined && (
          <span style={{ fontSize: '0.7rem', color: 'var(--color-text-muted, #94a3b8)' }}>v{evidence.version}</span>
        )}
      </div>

      <h4 style={{ fontSize: '0.9rem', fontWeight: 600, margin: '0 0 0.35rem 0' }}>{evidence.title}</h4>

      {evidence.statement && (
        <p style={{ fontSize: '0.825rem', color: 'var(--color-text-secondary, #cbd5e1)', margin: '0 0 0.5rem 0', lineHeight: 1.45 }}>
          "{evidence.statement}"
        </p>
      )}

      {/* Sourced Metrics or Claim values */}
      {evidence.claim_value && (
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.35rem',
            padding: '0.2rem 0.5rem',
            borderRadius: '4px',
            backgroundColor: 'rgba(34, 197, 94, 0.1)',
            border: '1px solid rgba(34, 197, 94, 0.25)',
            fontSize: '0.75rem',
            color: '#22c55e',
            fontWeight: 600,
            marginBottom: '0.5rem',
          }}
        >
          <span>Approved value:</span>
          <span>
            {evidence.claim_value} {evidence.unit || ''}
          </span>
        </div>
      )}

      {/* Validity & Source citation */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '0.5rem',
          fontSize: '0.75rem',
          color: 'var(--color-text-muted, #94a3b8)',
          borderTop: '1px solid var(--color-border, rgba(148, 163, 184, 0.15))',
          paddingTop: '0.5rem',
          marginTop: '0.5rem',
        }}
      >
        {evidence.source_reference && (
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
            <ExternalLink size={12} />
            <span style={{ fontStyle: 'italic' }}>{evidence.source_reference}</span>
          </div>
        )}
        {(evidence.valid_from || evidence.valid_until) && (
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
            <Calendar size={12} />
            <span>
              {evidence.valid_from || '—'} to {evidence.valid_until || 'Indefinite'}
            </span>
          </div>
        )}
      </div>
    </div>
  )
}
