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
    bg: 'var(--color-bg-subtle, rgba(148, 163, 184, 0.1))',
    color: 'var(--color-text-muted, #64748b)',
    border: 'rgba(148, 163, 184, 0.25)',
  },
  analyzed: {
    label: 'Analyzed',
    icon: FileCheck2,
    bg: 'rgba(59, 130, 246, 0.1)',
    color: '#3b82f6',
    border: 'rgba(59, 130, 246, 0.25)',
  },
  submitted: {
    label: 'Submitted',
    icon: Clock,
    bg: 'rgba(234, 179, 8, 0.1)',
    color: '#eab308',
    border: 'rgba(234, 179, 8, 0.25)',
  },
  in_review: {
    label: 'In Review',
    icon: Clock,
    bg: 'rgba(168, 85, 247, 0.1)',
    color: '#a855f7',
    border: 'rgba(168, 85, 247, 0.25)',
  },
  approved: {
    label: 'Approved',
    icon: CheckCircle2,
    bg: 'rgba(34, 197, 94, 0.1)',
    color: '#22c55e',
    border: 'rgba(34, 197, 94, 0.25)',
  },
  rejected: {
    label: 'Rejected',
    icon: XCircle,
    bg: 'rgba(239, 68, 68, 0.1)',
    color: '#ef4444',
    border: 'rgba(239, 68, 68, 0.25)',
  },
  open: {
    label: 'Open',
    icon: AlertTriangle,
    bg: 'rgba(234, 179, 8, 0.1)',
    color: '#eab308',
    border: 'rgba(234, 179, 8, 0.25)',
  },
  accepted: {
    label: 'Accepted',
    icon: CheckCircle2,
    bg: 'rgba(59, 130, 246, 0.1)',
    color: '#3b82f6',
    border: 'rgba(59, 130, 246, 0.25)',
  },
  disputed: {
    label: 'Disputed',
    icon: ShieldQuestion,
    bg: 'rgba(249, 115, 22, 0.1)',
    color: '#f97316',
    border: 'rgba(249, 115, 22, 0.25)',
  },
  overridden: {
    label: 'Overridden',
    icon: AlertTriangle,
    bg: 'rgba(168, 85, 247, 0.1)',
    color: '#a855f7',
    border: 'rgba(168, 85, 247, 0.25)',
  },
  resolved: {
    label: 'Resolved',
    icon: CheckCircle2,
    bg: 'rgba(34, 197, 94, 0.1)',
    color: '#22c55e',
    border: 'rgba(34, 197, 94, 0.25)',
  },
  active: {
    label: 'Active',
    icon: CheckCircle2,
    bg: 'rgba(34, 197, 94, 0.1)',
    color: '#22c55e',
    border: 'rgba(34, 197, 94, 0.25)',
  },
  retired: {
    label: 'Retired',
    icon: XCircle,
    bg: 'rgba(148, 163, 184, 0.1)',
    color: '#64748b',
    border: 'rgba(148, 163, 184, 0.25)',
  },
  expired: {
    label: 'Expired',
    icon: Clock,
    bg: 'rgba(239, 68, 68, 0.1)',
    color: '#ef4444',
    border: 'rgba(239, 68, 68, 0.25)',
  },
}

export function StatusBadge({ status, className = '' }: StatusBadgeProps) {
  const cfg = statusConfig[status] || {
    label: String(status),
    icon: Clock,
    bg: 'rgba(148, 163, 184, 0.1)',
    color: '#64748b',
    border: 'rgba(148, 163, 184, 0.25)',
  }
  const Icon = cfg.icon

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold ${className}`}
      style={{
        backgroundColor: cfg.bg,
        color: cfg.color,
        border: `1px solid ${cfg.border}`,
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.375rem',
        padding: '0.125rem 0.625rem',
        borderRadius: '9999px',
        fontSize: '0.75rem',
        fontWeight: 600,
      }}
      data-testid="status-badge"
    >
      <Icon size={12} />
      <span>{cfg.label}</span>
    </span>
  )
}

