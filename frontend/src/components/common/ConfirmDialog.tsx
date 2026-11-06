import React, { useEffect, useRef } from 'react'
import { AlertTriangle, X } from 'lucide-react'

interface ConfirmDialogProps {
  isOpen?: boolean
  open?: boolean
  title: string
  message: string
  confirmText?: string
  confirmLabel?: string
  cancelText?: string
  isDestructive?: boolean
  onConfirm?: () => void
  onCancel: () => void
}

export function ConfirmDialog({
  isOpen,
  open,
  title,
  message,
  confirmText,
  confirmLabel,
  cancelText = 'Cancel',
  isDestructive = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const isShown = isOpen ?? open ?? false
  const resolvedConfirmText = confirmText ?? confirmLabel ?? 'Confirm'
  const dialogRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (!isShown) return
      if (e.key === 'Escape') onCancel()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [isShown, onCancel])

  if (!isShown) return null

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        backgroundColor: 'rgba(0, 0, 0, 0.65)',
        backdropFilter: 'blur(4px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '1rem',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onCancel()
      }}
    >
      <div
        ref={dialogRef}
        style={{
          width: '100%',
          maxWidth: '460px',
          borderRadius: '12px',
          backgroundColor: 'var(--color-bg-panel, #1e293b)',
          border: '1px solid var(--color-border, rgba(148, 163, 184, 0.2))',
          boxShadow: '0 20px 40px rgba(0, 0, 0, 0.4)',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '1.25rem 1.5rem',
            borderBottom: '1px solid var(--color-border, rgba(148, 163, 184, 0.15))',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            {isDestructive && (
              <span style={{ color: '#ef4444' }}>
                <AlertTriangle size={20} />
              </span>
            )}
            <h3 id="dialog-title" style={{ fontSize: '1.1rem', fontWeight: 600, margin: 0 }}>
              {title}
            </h3>
          </div>
          <button
            onClick={onCancel}
            aria-label="Close dialog"
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--color-text-muted, #94a3b8)',
              cursor: 'pointer',
              padding: '4px',
            }}
          >
            <X size={18} />
          </button>
        </div>

        <div style={{ padding: '1.5rem', color: 'var(--color-text-secondary, #cbd5e1)', fontSize: '0.9rem' }}>
          {message}
        </div>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'flex-end',
            gap: '0.75rem',
            padding: '1rem 1.5rem',
            backgroundColor: 'var(--color-bg-subtle, rgba(0, 0, 0, 0.15))',
            borderTop: '1px solid var(--color-border, rgba(148, 163, 184, 0.15))',
          }}
        >
          <button
            type="button"
            onClick={onCancel}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: '6px',
              backgroundColor: 'transparent',
              border: '1px solid var(--color-border, rgba(148, 163, 184, 0.3))',
              color: 'var(--color-text-primary, #ffffff)',
              fontSize: '0.85rem',
              cursor: 'pointer',
            }}
          >
            {cancelText}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            style={{
              padding: '0.5rem 1.25rem',
              borderRadius: '6px',
              backgroundColor: isDestructive ? '#ef4444' : 'var(--accent, #6366f1)',
              border: 'none',
              color: '#ffffff',
              fontWeight: 600,
              fontSize: '0.85rem',
              cursor: 'pointer',
            }}
          >
            {resolvedConfirmText}
          </button>
        </div>
      </div>
    </div>
  )
}

