import React from 'react'
import { AlertCircle, ArrowLeft, RefreshCw, ShieldAlert, FolderOpen } from 'lucide-react'

export function EmptyState({
  title,
  description,
  message,
  actionLabel,
  onAction,
  icon: Icon = FolderOpen,
}: {
  title: string
  description?: string
  message?: string
  actionLabel?: string
  onAction?: () => void
  icon?: React.ComponentType<{ size: number; className?: string }>
}) {
  const text = description || message || ''
  return (
    <div
      className="empty-state-card"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        padding: '3rem 1.5rem',
        borderRadius: '12px',
        border: '1px dashed var(--color-border, rgba(148, 163, 184, 0.3))',
        backgroundColor: 'var(--color-bg-panel, rgba(255, 255, 255, 0.02))',
        margin: '1.5rem 0',
      }}
      data-testid="empty-state"
    >
      <div
        style={{
          width: '48px',
          height: '48px',
          borderRadius: '50%',
          backgroundColor: 'var(--color-bg-subtle, rgba(148, 163, 184, 0.1))',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'var(--accent, #0f766e)',
          marginBottom: '1rem',
        }}
      >
        <Icon size={24} />
      </div>
      <h3 style={{ fontSize: '1.1rem', fontWeight: 600, margin: '0 0 0.5rem 0' }}>{title}</h3>
      <p style={{ maxWidth: '420px', color: 'var(--color-text-muted, #94a3b8)', fontSize: '0.9rem', margin: '0 0 1.25rem 0' }}>
        {text}
      </p>
      {actionLabel && onAction && (
        <button
          onClick={onAction}
          className="landing-btn landing-btn--primary"
          style={{ fontSize: '0.85rem', padding: '0.5rem 1.25rem' }}
        >
          {actionLabel}
        </button>
      )}
    </div>
  )
}

export function ErrorState({
  title = 'Something went wrong',
  message = 'An unexpected error occurred.',
  onRetry,
  action,
}: {
  title?: string
  message?: string
  onRetry?: () => void
  action?: { label: string; onClick: () => void }
}) {
  const retryHandler = onRetry || action?.onClick
  const retryLabel = action?.label || 'Retry'

  return (
    <div
      role="alert"
      className="error-state-card"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        padding: '2.5rem 1.5rem',
        borderRadius: '12px',
        border: '1px solid rgba(239, 68, 68, 0.3)',
        backgroundColor: 'rgba(239, 68, 68, 0.05)',
        margin: '1.5rem 0',
      }}
      data-testid="error-state"
    >
      <div
        style={{
          width: '44px',
          height: '44px',
          borderRadius: '50%',
          backgroundColor: 'rgba(239, 68, 68, 0.15)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#ef4444',
          marginBottom: '0.75rem',
        }}
      >
        <AlertCircle size={22} />
      </div>
      <h3 style={{ fontSize: '1.1rem', fontWeight: 600, color: '#ef4444', margin: '0 0 0.5rem 0' }}>{title}</h3>
      <p style={{ maxWidth: '460px', color: 'var(--color-text-muted, #94a3b8)', fontSize: '0.875rem', margin: '0 0 1.25rem 0' }}>
        {message}
      </p>
      {retryHandler && (
        <button
          onClick={retryHandler}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.5rem 1rem',
            borderRadius: '6px',
            backgroundColor: '#ef4444',
            color: '#ffffff',
            fontWeight: 500,
            fontSize: '0.85rem',
            border: 'none',
            cursor: 'pointer',
          }}
        >
          <RefreshCw size={14} /> {retryLabel}
        </button>
      )}
    </div>
  )
}

export function PermissionDeniedState({
  requiredRole = 'manager or admin',
  onBack,
}: {
  requiredRole?: string
  onBack?: () => void
}) {
  return (
    <div
      role="alert"
      className="permission-denied-card"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        padding: '3rem 1.5rem',
        borderRadius: '12px',
        border: '1px solid rgba(249, 115, 22, 0.3)',
        backgroundColor: 'rgba(249, 115, 22, 0.05)',
        margin: '1.5rem 0',
      }}
      data-testid="permission-denied-state"
    >
      <div
        style={{
          width: '48px',
          height: '48px',
          borderRadius: '50%',
          backgroundColor: 'rgba(249, 115, 22, 0.15)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: '#f97316',
          marginBottom: '1rem',
        }}
      >
        <ShieldAlert size={26} />
      </div>
      <h3 style={{ fontSize: '1.15rem', fontWeight: 600, margin: '0 0 0.5rem 0' }}>Access Restricted</h3>
      <p style={{ maxWidth: '440px', color: 'var(--color-text-muted, #94a3b8)', fontSize: '0.9rem', margin: '0 0 1.25rem 0' }}>
        Your workspace role does not have permission to view or modify this resource. This action requires{' '}
        <strong>{requiredRole}</strong> rights.
      </p>
      {onBack && (
        <button
          onClick={onBack}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.5rem 1rem',
            borderRadius: '6px',
            backgroundColor: 'var(--color-bg-subtle, rgba(255, 255, 255, 0.1))',
            color: 'var(--color-text-primary, #ffffff)',
            border: '1px solid var(--color-border, rgba(255, 255, 255, 0.2))',
            cursor: 'pointer',
            fontSize: '0.85rem',
          }}
        >
          <ArrowLeft size={14} /> Return to previous view
        </button>
      )}
    </div>
  )
}

export function Skeleton({
  height = '20px',
  width = '100%',
  borderRadius = '4px',
  className = '',
}: {
  height?: string
  width?: string
  borderRadius?: string
  className?: string
}) {
  return (
    <div
      className={`skeleton-pulse ${className}`}
      style={{
        height,
        width,
        borderRadius,
        backgroundColor: 'var(--color-bg-subtle, rgba(148, 163, 184, 0.15))',
        animation: 'pulse 1.8s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      }}
      data-testid="skeleton-loader"
    />
  )
}

