/**
 * ReviewerQueuePage – B3 Requirement 1
 * Critical/major/disputed items first; advisory only when filtered in.
 * Server-side pagination. Filters by status, channel, creator, severity.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, MessageSquare, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react'
import { apiClient } from '../../../lib/api'
import { StatusBadge } from '../../../components/common/StatusBadge'
import { SeverityBadge } from '../../../components/common/SeverityBadge'
import { EmptyState, ErrorState } from '../../../components/common/FeedbackStates'
import type { ContentStatus, FindingSeverity, QueueItem } from '../../../types/api'

const CHANNELS = ['instagram', 'facebook', 'linkedin', 'email', 'paid_ad', 'website', 'other']
const PAGE_SIZE = 20

export function ReviewerQueuePage() {
  const navigate = useNavigate()
  const [status, setStatus] = useState<ContentStatus | ''>('')
  const [channel, setChannel] = useState('')
  const [severity, setSeverity] = useState<FindingSeverity | ''>('')
  const [creator, setCreator] = useState('')
  const [includeAdvisory, setIncludeAdvisory] = useState(false)
  const [offset, setOffset] = useState(0)
  const [advisoryOpen, setAdvisoryOpen] = useState(false)

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['review-queue', status, channel, severity, creator, includeAdvisory, offset],
    queryFn: () =>
      apiClient.listReviewQueue({
        status: status || undefined,
        channel: channel || undefined,
        severity: (severity || undefined) as FindingSeverity | undefined,
        creator: creator || undefined,
        include_advisory: includeAdvisory,
        limit: PAGE_SIZE,
        offset,
      }),
    refetchInterval: 30000,
  })

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const totalPages = Math.ceil(total / PAGE_SIZE)
  const currentPage = Math.floor(offset / PAGE_SIZE) + 1

  const blocking = items.filter(
    (i) => i.critical_count > 0 || i.disputed_count > 0
  )
  const major = items.filter(
    (i) => i.critical_count === 0 && i.disputed_count === 0 && i.major_count > 0
  )
  const advisory = items.filter(
    (i) => i.critical_count === 0 && i.disputed_count === 0 && i.major_count === 0
  )

  function handleRow(id: string) {
    navigate(`/app/reviews/${id}`)
  }

  if (isLoading) {
    return (
      <div className="p-8 space-y-3" role="status" aria-label="Loading review queue">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="h-14 rounded-lg bg-gray-100 dark:bg-gray-800 animate-pulse" />
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <ErrorState
        title="Could not load review queue"
        message="Check your connection and try again."
        action={{ label: 'Retry', onClick: () => refetch() }}
      />
    )
  }

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6">
      <div className="flex flex-wrap gap-4 items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Reviewer Queue</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            {total} item{total !== 1 ? 's' : ''} pending review
          </p>
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 px-3 py-2 text-sm border rounded-lg
                     border-gray-200 dark:border-gray-700 hover:bg-gray-50
                     dark:hover:bg-gray-800 transition-colors"
          aria-label="Refresh queue"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Filters */}
      <fieldset className="flex flex-wrap gap-3 p-4 bg-gray-50 dark:bg-gray-800/50
                           rounded-xl border border-gray-200 dark:border-gray-700">
        <legend className="sr-only">Queue filters</legend>

        <div className="flex flex-col gap-1">
          <label htmlFor="q-status" className="text-xs font-medium text-gray-600 dark:text-gray-400">
            Status
          </label>
          <select
            id="q-status"
            value={status}
            onChange={(e) => { setStatus(e.target.value as ContentStatus | ''); setOffset(0) }}
            className="text-sm px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-600
                       bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="">All statuses</option>
            <option value="submitted">Submitted</option>
            <option value="in_review">In Review</option>
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="q-channel" className="text-xs font-medium text-gray-600 dark:text-gray-400">
            Channel
          </label>
          <select
            id="q-channel"
            value={channel}
            onChange={(e) => { setChannel(e.target.value); setOffset(0) }}
            className="text-sm px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-600
                       bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="">All channels</option>
            {CHANNELS.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="q-severity" className="text-xs font-medium text-gray-600 dark:text-gray-400">
            Min severity
          </label>
          <select
            id="q-severity"
            value={severity}
            onChange={(e) => { setSeverity(e.target.value as FindingSeverity | ''); setOffset(0) }}
            className="text-sm px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-600
                       bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
          >
            <option value="">All severities</option>
            <option value="critical">Critical</option>
            <option value="major">Major</option>
            <option value="advisory">Advisory</option>
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="q-creator" className="text-xs font-medium text-gray-600 dark:text-gray-400">
            Creator
          </label>
          <input
            id="q-creator"
            type="text"
            placeholder="Name or ID"
            value={creator}
            onChange={(e) => { setCreator(e.target.value); setOffset(0) }}
            className="text-sm px-3 py-1.5 rounded-lg border border-gray-200 dark:border-gray-600
                       bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400"
          />
        </div>

        <div className="flex items-end pb-0.5">
          <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
            <input
              type="checkbox"
              checked={includeAdvisory}
              onChange={(e) => { setIncludeAdvisory(e.target.checked); setOffset(0) }}
              className="rounded border-gray-300 dark:border-gray-600"
            />
            Include advisory-only
          </label>
        </div>
      </fieldset>

      {items.length === 0 ? (
        <EmptyState
          title="No items in queue"
          message="All caught up! No content matches your current filters."
        />
      ) : (
        <div className="space-y-6">
          {/* Blocking section */}
          {blocking.length > 0 && (
            <QueueSection
              title="Blocking"
              subtitle="Critical or disputed findings — requires immediate attention"
              items={blocking}
              accentClass="border-l-red-500"
              onRow={handleRow}
            />
          )}

          {/* Major section */}
          {major.length > 0 && (
            <QueueSection
              title="Major"
              subtitle="Major findings that need a reviewer decision"
              items={major}
              accentClass="border-l-amber-500"
              onRow={handleRow}
            />
          )}

          {/* Advisory section — collapsed by default */}
          {advisory.length > 0 && (
            <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
              <button
                onClick={() => setAdvisoryOpen((o) => !o)}
                className="w-full flex items-center justify-between p-4 text-left
                           hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                aria-expanded={advisoryOpen}
              >
                <div>
                  <span className="font-semibold text-gray-700 dark:text-gray-300">
                    Advisory-only ({advisory.length})
                  </span>
                  <span className="ml-2 text-sm text-gray-500">
                    No critical or major findings
                  </span>
                </div>
                {advisoryOpen ? (
                  <ChevronUp className="w-4 h-4 text-gray-400" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-gray-400" />
                )}
              </button>
              {advisoryOpen && (
                <div className="border-t border-gray-200 dark:border-gray-700">
                  <QueueSection
                    title=""
                    items={advisory}
                    accentClass="border-l-blue-400"
                    onRow={handleRow}
                  />
                </div>
              )}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <nav
              className="flex items-center justify-between pt-4"
              aria-label="Queue pagination"
            >
              <button
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                disabled={offset === 0}
                className="px-4 py-2 text-sm border rounded-lg disabled:opacity-40
                           border-gray-200 dark:border-gray-700 hover:bg-gray-50
                           dark:hover:bg-gray-800 transition-colors"
              >
                Previous
              </button>
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setOffset(offset + PAGE_SIZE)}
                disabled={offset + PAGE_SIZE >= total}
                className="px-4 py-2 text-sm border rounded-lg disabled:opacity-40
                           border-gray-200 dark:border-gray-700 hover:bg-gray-50
                           dark:hover:bg-gray-800 transition-colors"
              >
                Next
              </button>
            </nav>
          )}
        </div>
      )}
    </div>
  )
}

function QueueSection({
  title,
  subtitle,
  items,
  accentClass,
  onRow,
}: {
  title: string
  subtitle?: string
  items: QueueItem[]
  accentClass: string
  onRow: (id: string) => void
}) {
  return (
    <div>
      {title && (
        <div className="mb-3">
          <h2 className="text-base font-semibold text-gray-800 dark:text-gray-200">{title}</h2>
          {subtitle && (
            <p className="text-sm text-gray-500 dark:text-gray-400">{subtitle}</p>
          )}
        </div>
      )}
      <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 dark:bg-gray-800/60 text-left">
              <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-400">Title</th>
              <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-400">Channel</th>
              <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-400">Status</th>
              <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-400">Findings</th>
              <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-400">Creator</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr
                key={item.id}
                onClick={() => onRow(item.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onRow(item.id) }}
                className={`border-l-4 ${accentClass} border-t border-gray-100
                             dark:border-gray-800 cursor-pointer
                             hover:bg-purple-50 dark:hover:bg-purple-900/10
                             focus-visible:outline-none focus-visible:ring-2
                             focus-visible:ring-purple-500 focus-visible:ring-inset
                             transition-colors`}
                aria-label={`Review item: ${item.title}`}
              >
                <td className="px-4 py-3">
                  <div className="font-medium text-gray-900 dark:text-white truncate max-w-xs">
                    {item.title}
                  </div>
                  <div className="text-xs text-gray-400">{item.campaign}</div>
                </td>
                <td className="px-4 py-3 text-gray-600 dark:text-gray-300 capitalize">
                  {item.channel}
                </td>
                <td className="px-4 py-3">
                  <StatusBadge status={item.status} />
                </td>
                <td className="px-4 py-3">
                  <FindingCounts item={item} />
                </td>
                <td className="px-4 py-3 text-gray-600 dark:text-gray-300">
                  {item.created_by_name}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function FindingCounts({ item }: { item: QueueItem }) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      {item.critical_count > 0 && (
        <span className="inline-flex items-center gap-1">
          <SeverityBadge severity="critical" />
          <span className="sr-only">critical:</span>
          <span className="text-xs font-semibold text-red-600 dark:text-red-400">
            {item.critical_count}
          </span>
        </span>
      )}
      {item.major_count > 0 && (
        <span className="inline-flex items-center gap-1">
          <SeverityBadge severity="major" />
          <span className="sr-only">major:</span>
          <span className="text-xs font-semibold text-amber-600 dark:text-amber-400">
            {item.major_count}
          </span>
        </span>
      )}
      {item.disputed_count > 0 && (
        <span
          className="inline-flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400"
          aria-label={`${item.disputed_count} disputed`}
        >
          <MessageSquare className="w-3.5 h-3.5" aria-hidden="true" />
          {item.disputed_count} disputed
        </span>
      )}
      {item.advisory_count > 0 && item.critical_count === 0 && item.major_count === 0 && (
        <span className="inline-flex items-center gap-1">
          <SeverityBadge severity="advisory" />
          <span className="text-xs text-gray-500">{item.advisory_count}</span>
        </span>
      )}
      {item.critical_count === 0 && item.major_count === 0 && item.disputed_count === 0 && item.advisory_count === 0 && (
        <span className="text-xs text-green-600 dark:text-green-400 flex items-center gap-1">
          <AlertTriangle className="w-3.5 h-3.5" aria-hidden="true" />
          None
        </span>
      )}
    </div>
  )
}

