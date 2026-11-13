import React from 'react'
import { CheckCircle2, Clock, FileCheck2, AlertTriangle, XCircle, ShieldQuestion } from 'lucide-react'
import { ContentStatus, FindingState } from '../../types/api'

type StatusType = ContentStatus | FindingState | 'active' | 'retired' | 'expired'

interface StatusBadgeProps {
  status: StatusType
  className?: string
}

const statusConfig: Record<
  StatusType,
  { label: string; icon: React.ComponentType<{ size: number; className?: string }>; bg: string; color: string; border: string }
> = {
  draft: {
    label: 'Draft',
    icon: Clock,
    bg: 'var(--severity-advisory-bg, #f1f5f9)',
    color: 'var(--severity-advisory-text, #475569)',
    border: 'var(--severity-advisory-border, #cbd5e1)',
  },
  analyzed: {
    label: 'Analyzed',
    icon: FileCheck2,
    bg: 'var(--severity-advisory-bg, #f1f5f9)',
    color: 'var(--severity-advisory-text, #475569)',
    border: 'var(--severity-advisory-border, #cbd5e1)',
  },
  submitted: {
    label: 'Submitted',
    icon: Clock,
    bg: 'var(--severity-major-bg, #fffbeb)',
    color: 'var(--severity-major-text, #b45309)',
    border: 'var(--severity-major-border, #fde68a)',
  },
  in_review: {
    label: 'In Review',
    icon: Clock,
    bg: 'var(--severity-review-bg, #f5f3ff)',
    color: 'var(--severity-review-text, #6d28d9)',
    border: 'var(--severity-review-border, #ddd6fe)',
  },
  approved: {
    label: 'Approved',
    icon: CheckCircle2,
    bg: 'var(--severity-success-bg, #f0fdf4)',
    color: 'var(--severity-success-text, #15803d)',
    border: 'var(--severity-success-border, #bbf7d0)',
  },
  rejected: {
    label: 'Rejected',
    icon: XCircle,
    bg: 'var(--severity-critical-bg, #fff1f2)',
    color: 'var(--severity-critical-text, #be123c)',
    border: 'var(--severity-critical-border, #fecdd3)',
  },
  open: {
    label: 'Open',
    icon: AlertTriangle,
    bg: 'var(--severity-major-bg, #fffbeb)',
    color: 'var(--severity-major-text, #b45309)',
    border: 'var(--severity-major-border, #fde68a)',
  },
  accepted: {
    label: 'Accepted',
    icon: CheckCircle2,
    bg: 'var(--severity-advisory-bg, #f1f5f9)',
    color: 'var(--severity-advisory-text, #475569)',
    border: 'var(--severity-advisory-border, #cbd5e1)',
  },
  disputed: {
    label: 'Disputed',
    icon: ShieldQuestion,
    bg: 'var(--severity-major-bg, #fffbeb)',
    color: 'var(--severity-major-text, #b45309)',
    border: 'var(--severity-major-border, #fde68a)',
  },
  overridden: {
    label: 'Overridden',
    icon: AlertTriangle,
    bg: 'var(--severity-review-bg, #f5f3ff)',
    color: 'var(--severity-review-text, #6d28d9)',
    border: 'var(--severity-review-border, #ddd6fe)',
  },
  resolved: {
    label: 'Resolved',
    icon: CheckCircle2,
    bg: 'var(--severity-success-bg, #f0fdf4)',
    color: 'var(--severity-success-text, #15803d)',
    border: 'var(--severity-success-border, #bbf7d0)',
  },
  active: {
    label: 'Active',
    icon: CheckCircle2,
    bg: 'var(--severity-success-bg, #f0fdf4)',
    color: 'var(--severity-success-text, #15803d)',
    border: 'var(--severity-success-border, #bbf7d0)',
  },
  retired: {
    label: 'Retired',
    icon: XCircle,
    bg: 'var(--severity-advisory-bg, #f1f5f9)',
    color: 'var(--severity-advisory-text, #475569)',
    border: 'var(--severity-advisory-border, #cbd5e1)',
  },
  expired: {
    label: 'Expired',
    icon: Clock,
    bg: 'var(--severity-critical-bg, #fff1f2)',
    color: 'var(--severity-critical-text, #be123c)',
    border: 'var(--severity-critical-border, #fecdd3)',
  },
}

export function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  const cfg = statusConfig[status] || {
    label: String(status),
    icon: Clock,
    bg: 'var(--severity-advisory-bg, #f1f5f9)',
    color: 'var(--severity-advisory-text, #475569)',
    border: 'var(--severity-advisory-border, #cbd5e1)',
  }
  const Icon = cfg.icon

  return (
    <span
      className={`status-badge ${className}`}
      style={{
        backgroundColor: cfg.bg,
        color: cfg.color,
        border: `1px solid ${cfg.border}`,
        display: 'inline-flex',
        alignItems: 'center',
        gap: '6px',
        padding: '4px 10px',
        borderRadius: '999px',
        fontSize: '12px',
        fontWeight: 600,
        lineHeight: 1,
      }}
      data-testid="status-badge"
    >
      <Icon size={12} />
      <span>{cfg.label}</span>
    </span>
  )
}

