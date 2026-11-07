/**
 * NotificationBell – B3 Requirement 6
 * Bell icon in AppShell topbar. Fetches /notifications every 60 s.
 * Unread count badge. Click marks as read (client-side state).
 * Navigates to the linked route on click.
 */
import { useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Bell, BellOff, ExternalLink } from 'lucide-react'
import { apiClient } from '../../lib/api'
import type { AppNotification } from '../../types/api'

const ICON_MAP: Record<AppNotification['type'], string> = {
  assigned_for_review: '📋',
  decision_made: '✅',
  fact_expiring: '⏰',
  precedent_awaiting_approval: '🔔',
}

export function NotificationBell() {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [readIds, setReadIds] = useState<Set<string>>(new Set())
  const panelRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)

  const { data: notifications = [] } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => apiClient.listNotifications(),
    refetchInterval: 60000,
  })

  const unread = notifications.filter((n) => !readIds.has(n.id))

  // Close on outside click
  useEffect(() => {
    if (!open) return
    function handler(e: MouseEvent) {
      if (
        panelRef.current &&
        !panelRef.current.contains(e.target as Node) &&
        buttonRef.current &&
        !buttonRef.current.contains(e.target as Node)
      ) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [open])

  // Close on Escape
  useEffect(() => {
    if (!open) return
    function handler(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setOpen(false)
        buttonRef.current?.focus()
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open])

  function markAllRead() {
    setReadIds(new Set(notifications.map((n) => n.id)))
  }

  function handleNotificationClick(notification: AppNotification) {
    setReadIds((prev) => new Set([...prev, notification.id]))
    if (notification.link) {
      navigate(notification.link)
    }
    setOpen(false)
  }

  return (
    <div className="relative">
      <button
        ref={buttonRef}
        onClick={() => setOpen((o) => !o)}
        aria-label={
          unread.length > 0
            ? `Notifications: ${unread.length} unread`
            : 'Notifications'
        }
        aria-expanded={open}
        aria-haspopup="true"
        className="relative p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800
                   transition-colors focus-visible:outline-none focus-visible:ring-2
                   focus-visible:ring-purple-500"
      >
        <Bell className="w-5 h-5 text-gray-600 dark:text-gray-400" aria-hidden="true" />
        {unread.length > 0 && (
          <span
            aria-hidden="true"
            className="absolute top-1 right-1 w-4 h-4 text-xs font-bold
                       bg-red-500 text-white rounded-full flex items-center justify-center
                       leading-none"
          >
            {unread.length > 9 ? '9+' : unread.length}
          </span>
        )}
      </button>

      {open && (
        <div
          ref={panelRef}
          role="menu"
          aria-label="Notifications panel"
          className="absolute right-0 mt-2 w-80 max-h-96 overflow-y-auto
                     bg-white dark:bg-gray-900
                     border border-gray-200 dark:border-gray-700
                     rounded-xl shadow-xl z-50"
        >
          <div className="flex items-center justify-between p-3 border-b
                          border-gray-100 dark:border-gray-800">
            <span className="text-sm font-semibold text-gray-800 dark:text-gray-200">
              Notifications
            </span>
            {unread.length > 0 && (
              <button
                onClick={markAllRead}
                className="text-xs text-purple-600 dark:text-purple-400 hover:underline"
              >
                Mark all read
              </button>
            )}
          </div>

          {notifications.length === 0 && (
            <div className="flex flex-col items-center gap-2 py-8 text-gray-400">
              <BellOff className="w-8 h-8" aria-hidden="true" />
              <p className="text-sm">No notifications</p>
            </div>
          )}

          <ul>
            {notifications.map((n) => {
              const isRead = readIds.has(n.id)
              return (
                <li key={n.id} role="menuitem">
                  <button
                    onClick={() => handleNotificationClick(n)}
                    className={`w-full text-left flex items-start gap-3 p-3
                                border-b border-gray-50 dark:border-gray-800
                                hover:bg-gray-50 dark:hover:bg-gray-800/50
                                transition-colors
                                ${isRead ? 'opacity-60' : ''}`}
                  >
                    <span
                      className="text-lg flex-shrink-0"
                      aria-hidden="true"
                    >
                      {ICON_MAP[n.type] ?? '🔔'}
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-start justify-between gap-2">
                        <p className={`text-sm font-medium text-gray-800 dark:text-gray-200
                                      ${!isRead ? 'font-semibold' : ''}`}>
                          {n.title}
                        </p>
                        {n.link && (
                          <ExternalLink
                            className="w-3.5 h-3.5 text-gray-400 flex-shrink-0 mt-0.5"
                            aria-hidden="true"
                          />
                        )}
                      </div>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2">
                        {n.message}
                      </p>
                      <time
                        dateTime={n.created_at}
                        className="text-xs text-gray-400 mt-1 block"
                      >
                        {new Date(n.created_at).toLocaleString()}
                      </time>
                    </div>
                    {!isRead && (
                      <div
                        className="w-2 h-2 rounded-full bg-purple-500 flex-shrink-0 mt-1.5"
                        aria-hidden="true"
                      />
                    )}
                  </button>
                </li>
              )
            })}
          </ul>
        </div>
      )}
    </div>
  )
}

