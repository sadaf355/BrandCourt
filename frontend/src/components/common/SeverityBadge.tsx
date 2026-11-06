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
    bg: 'rgba(239, 68, 68, 0.15)',
    color: '#ef4444',
    border: 'rgba(239, 68, 68, 0.3)',
  },
  major: {
    label: 'Major',
    sublabel: 'Needs reviewer',
    icon: AlertTriangle,
    bg: 'rgba(249, 115, 22, 0.15)',
    color: '#f97316',
    border: 'rgba(249, 115, 22, 0.3)',
  },
  advisory: {
    label: 'Advisory',
    sublabel: 'Never blocks',
    icon: Info,
    bg: 'rgba(59, 130, 246, 0.15)',
    color: '#3b82f6',
    border: 'rgba(59, 130, 246, 0.3)',
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
        gap: '0.35rem',
        padding: '0.2rem 0.55rem',
        borderRadius: '6px',
        fontSize: '0.75rem',
        fontWeight: 600,
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
          fontSize: '0.65rem',
          opacity: 0.8,
          fontWeight: 400,
          borderLeft: `1px solid ${cfg.border}`,
          paddingLeft: '0.35rem',
          marginLeft: '0.2rem',
        }}
      >
        {cfg.sublabel}
      </span>
    </span>
  )
}

