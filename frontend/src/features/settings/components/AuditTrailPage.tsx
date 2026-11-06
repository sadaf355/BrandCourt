/**
 * AuditTrailPage – B3 Requirement 9
 * Audit trail page filtered by permission:
 * - own items (creator)
 * - assigned items (reviewer)
 * - workspace (manager/admin)
 * - rule history (guideline owners / admin)
 * Uses AuditTimeline and server-side filtering.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { History, Shield, Filter, Search } from 'lucide-react'
import { apiClient } from '../../../lib/api'
import { AuditTimeline } from '../../reviews/components/AuditTimeline'
import { EmptyState, ErrorState } from '../../../components/common/FeedbackStates'
import type { Role, AuditEvent } from '../../../types/api'

interface AuditTrailPageProps {
  currentUserRole: Role
}

type Scope = 'own' | 'assigned' | 'workspace' | 'rules'

export function AuditTrailPage({ currentUserRole }: AuditTrailPageProps) {
  // Creators are constrained to 'own' by default. Manager/admin have workspace-wide visibility.
  const defaultScope: Scope = currentUserRole === 'creator' ? 'own' : 'workspace'
  const [scope, setScope] = useState<Scope>(defaultScope)
  const [search, setSearch] = useState('')
  const [offset, setOffset] = useState(0)
  const limit = 20

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['audit-events', scope, offset, limit],
    queryFn: () => apiClient.listAuditEvents({ scope, offset, limit }),
  })

  const rawEvents = data?.events ?? []
  const total = data?.total ?? 0

  const events = rawEvents.filter((e: AuditEvent) => {
    if (!search.trim()) return true
    const term = search.toLowerCase()
    return (
      e.action.toLowerCase().includes(term) ||
      (e.user_name && e.user_name.toLowerCase().includes(term)) ||
      e.id.toLowerCase().includes(term) ||
      JSON.stringify(e.details).toLowerCase().includes(term)
    )
  })

  const totalPages = Math.ceil(total / limit)
  const currentPage = Math.floor(offset / limit) + 1

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <History className="w-6 h-6 text-purple-600 dark:text-purple-400" />
            Audit Trail
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            Immutable, append-only ledger of all decisions, overrides, and revisions.
          </p>
        </div>
      </div>

      {/* Scope Filter Tabs */}
      <div className="flex flex-wrap gap-2 border-b border-gray-200 dark:border-gray-700 pb-3">
        <button
          onClick={() => { setScope('own'); setOffset(0) }}
          className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
            scope === 'own'
              ? 'bg-purple-600 text-white'
              : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
          }`}
        >
          My Actions
        </button>

        {currentUserRole !== 'creator' && (
          <button
            onClick={() => { setScope('assigned'); setOffset(0) }}
            className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
              scope === 'assigned'
                ? 'bg-purple-600 text-white'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
            }`}
          >
            Assigned Reviews
          </button>
        )}

        {(currentUserRole === 'manager' || currentUserRole === 'admin') && (
          <button
            onClick={() => { setScope('workspace'); setOffset(0) }}
            className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
              scope === 'workspace'
                ? 'bg-purple-600 text-white'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
            }`}
          >
            Workspace-Wide
          </button>
        )}

        {(currentUserRole === 'manager' || currentUserRole === 'admin') && (
          <button
            onClick={() => { setScope('rules'); setOffset(0) }}
            className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
              scope === 'rules'
                ? 'bg-purple-600 text-white'
                : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
            }`}
          >
            Rule & Fact History
          </button>
        )}
      </div>

      {/* Search Bar */}
      <div className="flex items-center gap-3 bg-white dark:bg-gray-800 p-3 rounded-xl border border-gray-200 dark:border-gray-700">
        <Search className="w-4 h-4 text-gray-400" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Filter audit records by user, action or keyword..."
          className="flex-1 bg-transparent text-sm text-gray-900 dark:text-white placeholder-gray-400 outline-none"
        />
        {search && (
          <button
            onClick={() => setSearch('')}
            className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
          >
            Clear
          </button>
        )}
      </div>

      {isLoading ? (
        <div className="p-8 space-y-3" role="status" aria-label="Loading audit trail">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-14 rounded-lg bg-gray-100 dark:bg-gray-800 animate-pulse" />
          ))}
        </div>
      ) : isError ? (
        <ErrorState
          title="Could not load audit events"
          message="Please check permissions or network connectivity."
          action={{ label: 'Retry', onClick: () => refetch() }}
        />
      ) : events.length === 0 ? (
        <EmptyState
          title="No audit events found"
          message="No recorded actions match the selected scope and filter criteria."
        />
      ) : (
        <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6 shadow-sm">
          <AuditTimeline events={events} />

          {totalPages > 1 && (
            <div className="flex items-center justify-between border-t border-gray-100 dark:border-gray-700 pt-4 mt-6">
              <button
                disabled={offset === 0}
                onClick={() => setOffset(Math.max(0, offset - limit))}
                className="px-3 py-1.5 text-xs font-medium border rounded-lg border-gray-200 dark:border-gray-700 disabled:opacity-40"
              >
                Previous
              </button>
              <span className="text-xs text-gray-500">
                Page {currentPage} of {totalPages}
              </span>
              <button
                disabled={offset + limit >= total}
                onClick={() => setOffset(offset + limit)}
                className="px-3 py-1.5 text-xs font-medium border rounded-lg border-gray-200 dark:border-gray-700 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

