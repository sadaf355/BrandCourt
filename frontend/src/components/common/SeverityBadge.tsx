import React from 'react'
import { ShieldAlert, AlertTriangle, Info } from 'lucide-react'
import { FindingSeverity } from '../../types/api'

interface SeverityBadgeProps {
  severity: FindingSeverity
  className?: string
}

const severityConfig: Record<
  FindingSeverity,
  {
    label: string
    sublabel: string
    icon: React.ComponentType<{ size: number; className?: string }>
    bg: string
    color: string
    border: string
  }
> = {
  critical: {
    label: 'Critical',
    sublabel: 'Blocks approval',
    icon: ShieldAlert,
    bg: 'var(--severity-critical-bg, #fff1f2)',
    color: 'var(--severity-critical-text, #be123c)',
    border: 'var(--severity-critical-border, #fecdd3)',
  },
  major: {
    label: 'Major',
    sublabel: 'Needs reviewer',
    icon: AlertTriangle,
    bg: 'var(--severity-major-bg, #fffbeb)',
    color: 'var(--severity-major-text, #b45309)',
    border: 'var(--severity-major-border, #fde68a)',
  },
  advisory: {
    label: 'Advisory',
    sublabel: 'Never blocks',
    icon: Info,
    bg: 'var(--severity-advisory-bg, #f1f5f9)',
    color: 'var(--severity-advisory-text, #475569)',
    border: 'var(--severity-advisory-border, #cbd5e1)',
  },
}

export function SeverityBadge({ severity, className = '' }: SeverityBadgeProps) {
  const cfg = severityConfig[severity] || severityConfig.advisory
  const Icon = cfg.icon

  return (
    <span
      className={`severity-badge ${className}`}
      title={`${cfg.label}: ${cfg.sublabel}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: '4px 10px',
        borderRadius: '999px',
        fontSize: '12px',
        fontWeight: 600,
        lineHeight: 1,
        backgroundColor: cfg.bg,
        color: cfg.color,
        border: `1px solid ${cfg.border}`,
      }}
      data-testid="severity-badge"
    >
      <Icon size={13} aria-hidden="true" />
      <span>{cfg.label}</span>
      <span
        style={{
          fontSize: '11px',
          opacity: 0.85,
          fontWeight: 400,
          borderLeft: `1px solid ${cfg.border}`,
          paddingLeft: '6px',
          marginLeft: '4px',
        }}
      >
        {cfg.sublabel}
      </span>
    </span>
  )
}

