import React, { createContext, useContext, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle2, AlertTriangle, AlertCircle, Info, X } from 'lucide-react'

type ToastType = 'success' | 'error' | 'warning' | 'info'

interface ToastMessage {
  id: string
  title?: string
  message: string
  type: ToastType
  duration?: number
}

interface ToastContextValue {
  showToast: (message: string, type?: ToastType, title?: string, duration?: number) => void
  removeToast: (id: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const showToast = useCallback(
    (message: string, type: ToastType = 'info', title?: string, duration = 4000) => {
      const id = `toast-${Date.now()}-${Math.random().toString(36).substr(2, 4)}`
      setToasts((prev) => [...prev, { id, message, type, title, duration }])
      if (duration > 0) {
        setTimeout(() => removeToast(id), duration)
      }
    },
    [removeToast]
  )

  return (
    <ToastContext.Provider value={{ showToast, removeToast }}>
      {children}
      <aside
        aria-label="Notifications"
        style={{
          position: 'fixed',
          bottom: '1.5rem',
          right: '1.5rem',
          zIndex: 9999,
          display: 'flex',
          flexDirection: 'column',
          gap: '0.75rem',
          maxWidth: '380px',
          width: 'calc(100vw - 3rem)',
          pointerEvents: 'none',
        }}
      >
        <AnimatePresence>
          {toasts.map((toast) => {
            const Icon =
              toast.type === 'success'
                ? CheckCircle2
                : toast.type === 'error'
                ? AlertCircle
                : toast.type === 'warning'
                ? AlertTriangle
                : Info

            const border =
              toast.type === 'success'
                ? 'rgba(34, 197, 94, 0.4)'
                : toast.type === 'error'
                ? 'rgba(239, 68, 68, 0.4)'
                : toast.type === 'warning'
                ? 'rgba(249, 115, 22, 0.4)'
                : 'rgba(59, 130, 246, 0.4)'

            const iconColor =
              toast.type === 'success'
                ? '#22c55e'
                : toast.type === 'error'
                ? '#ef4444'
                : toast.type === 'warning'
                ? '#f97316'
                : '#3b82f6'

            return (
              <motion.div
                key={toast.id}
                role="status"
                initial={{ opacity: 0, y: 20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 15, scale: 0.95 }}
                transition={{ duration: 0.2 }}
                style={{
                  pointerEvents: 'auto',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '0.75rem',
                  padding: '0.875rem 1rem',
                  borderRadius: '10px',
                  backgroundColor: 'var(--color-bg-panel, #1e293b)',
                  border: `1px solid ${border}`,
                  boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.35)',
                  color: 'var(--color-text-primary, #ffffff)',
                }}
              >
                <div style={{ color: iconColor, marginTop: '2px', flexShrink: 0 }}>
                  <Icon size={18} />
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  {toast.title && (
                    <div style={{ fontWeight: 600, fontSize: '0.875rem', marginBottom: '0.2rem' }}>
                      {toast.title}
                    </div>
                  )}
                  <div style={{ fontSize: '0.825rem', color: 'var(--color-text-muted, #cbd5e1)' }}>
                    {toast.message}
                  </div>
                </div>
                <button
                  onClick={() => removeToast(toast.id)}
                  aria-label="Close notification"
                  style={{
                    background: 'none',
                    border: 'none',
                    color: 'var(--color-text-muted, #94a3b8)',
                    cursor: 'pointer',
                    padding: '2px',
                    lineHeight: 1,
                  }}
                >
                  <X size={15} />
                </button>
              </motion.div>
            )
          })}
        </AnimatePresence>
      </aside>
    </ToastContext.Provider>
  )
}

export function useToast() {
  const ctx = useContext(ToastContext)
  if (!ctx) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return ctx
}

