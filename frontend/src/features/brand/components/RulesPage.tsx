/**
 * RulesPage – B3 Requirement 7
 * Active rules table, good/bad examples, activate/retire buttons (admin/manager).
 * India pack toggle. Rule version history.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle, XCircle, Globe, Flag, ChevronDown, ChevronUp } from 'lucide-react'
import { apiClient } from '../../../lib/api'
import { SeverityBadge } from '../../../components/common/SeverityBadge'
import { EmptyState, ErrorState } from '../../../components/common/FeedbackStates'
import { useToast } from '../../../components/common/Toast'
import type { RuleWithHistory, Role } from '../../../types/api'

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  retired: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  draft: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
}

export function RulesPage({ userRole }: { userRole: Role }) {
  const qc = useQueryClient()
  const { showToast } = useToast()
  const [indiaPackOnly, setIndiaPackOnly] = useState(false)
  const [statusFilter, setStatusFilter] = useState<'active' | 'retired' | 'draft' | ''>('active')
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const canEdit = userRole === 'admin' || userRole === 'manager'

  const { data: rules = [], isLoading, isError, refetch } = useQuery({
    queryKey: ['rules', statusFilter, indiaPackOnly],
    queryFn: () =>
      apiClient.listRules({
        status: statusFilter || undefined,
        is_india_pack: indiaPackOnly ? true : undefined,
      }),
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'draft' | 'active' | 'retired' }) =>
      apiClient.updateRule(id, { status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['rules'] })
      showToast('Rule updated.', 'success')
    },
    onError: (err: Error) => showToast(err.message, 'error'),
  })

  if (isLoading) {
    return (
      <div className="p-8 space-y-3" role="status" aria-label="Loading rules">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-14 rounded-lg bg-gray-100 dark:bg-gray-800 animate-pulse" />
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <ErrorState title="Could not load rules" action={{ label: 'Retry', onClick: () => refetch() }} />
    )
  }

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex flex-wrap gap-4 items-end justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Brand Rules</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            {rules.length} rule{rules.length !== 1 ? 's' : ''} shown
          </p>
        </div>

        <div className="flex flex-wrap gap-3 items-center">
          <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
            <input
              type="checkbox"
              checked={indiaPackOnly}
              onChange={(e) => setIndiaPackOnly(e.target.checked)}
              className="rounded border-gray-300 dark:border-gray-600"
            />
            <Flag className="w-4 h-4 text-orange-500" aria-hidden="true" />
            India pack only
          </label>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as typeof statusFilter)}
            aria-label="Filter by status"
            className="text-sm px-3 py-1.5 rounded-lg border border-gray-200
                       dark:border-gray-600 bg-white dark:bg-gray-700
                       text-gray-900 dark:text-white"
          >
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="draft">Draft</option>
            <option value="retired">Retired</option>
          </select>
        </div>
      </div>

      {rules.length === 0 ? (
        <EmptyState title="No rules found" message="Adjust your filters or upload a guideline to generate rules." />
      ) : (
        <div className="space-y-3">
          {rules.map((rule) => (
            <RuleCard
              key={rule.id}
              rule={rule}
              canEdit={canEdit}
              expanded={expandedId === rule.id}
              onToggle={() => setExpandedId(expandedId === rule.id ? null : rule.id)}
              onActivate={() => updateMutation.mutate({ id: rule.id, status: 'active' })}
              onRetire={() => updateMutation.mutate({ id: rule.id, status: 'retired' })}
              isPending={updateMutation.isPending}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function RuleCard({
  rule,
  canEdit,
  expanded,
  onToggle,
  onActivate,
  onRetire,
  isPending,
}: {
  rule: RuleWithHistory
  canEdit: boolean
  expanded: boolean
  onToggle: () => void
  onActivate: () => void
  onRetire: () => void
  isPending: boolean
}) {
  return (
    <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden
                    bg-white dark:bg-gray-800">
      <button
        onClick={onToggle}
        className="w-full flex items-start gap-4 p-4 text-left hover:bg-gray-50
                   dark:hover:bg-gray-800/50 transition-colors"
        aria-expanded={expanded}
        aria-controls={`rule-${rule.id}-detail`}
      >
        <div className="flex-1 min-w-0 space-y-1">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-medium text-gray-900 dark:text-white">{rule.name}</span>
            {rule.is_india_pack && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded-full
                               bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300">
                <Flag className="w-3 h-3" aria-hidden="true" /> India pack
              </span>
            )}
            <span className={`text-xs px-2 py-0.5 rounded-full ${STATUS_COLORS[rule.status]}`}>
              {rule.status}
            </span>
            <SeverityBadge severity={rule.severity} />
            <span className="text-xs text-gray-400">v{rule.version}</span>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
            {rule.description}
          </p>
          <p className="text-xs text-gray-400">{rule.id} · {rule.channel_scope}</p>
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-gray-400 mt-1 flex-shrink-0" aria-hidden="true" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-400 mt-1 flex-shrink-0" aria-hidden="true" />
        )}
      </button>

      {expanded && (
        <div
          id={`rule-${rule.id}-detail`}
          className="border-t border-gray-100 dark:border-gray-700 p-4 space-y-4"
        >
          {/* Examples */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {rule.good_examples && rule.good_examples.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm font-medium text-green-700
                                dark:text-green-400">
                  <CheckCircle className="w-4 h-4" aria-hidden="true" />
                  Good examples
                </div>
                <ul className="space-y-1">
                  {rule.good_examples.map((ex, i) => (
                    <li key={i} className="text-sm text-gray-600 dark:text-gray-400
                                           bg-green-50 dark:bg-green-900/20 rounded-lg px-3 py-2">
                      "{ex}"
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {rule.bad_examples && rule.bad_examples.length > 0 && (
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm font-medium text-red-700
                                dark:text-red-400">
                  <XCircle className="w-4 h-4" aria-hidden="true" />
                  Bad examples
                </div>
                <ul className="space-y-1">
                  {rule.bad_examples.map((ex, i) => (
                    <li key={i} className="text-sm text-gray-600 dark:text-gray-400
                                           bg-red-50 dark:bg-red-900/20 rounded-lg px-3 py-2">
                      "{ex}"
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>

          {/* Source page */}
          {rule.source_page && (
            <p className="text-xs text-gray-400 flex items-center gap-1">
              <Globe className="w-3.5 h-3.5" aria-hidden="true" />
              Source: Guideline page {rule.source_page}
            </p>
          )}

          {/* Admin / Manager actions */}
          {canEdit && (
            <div className="flex gap-3 pt-2">
              {rule.status !== 'active' && (
                <button
                  onClick={onActivate}
                  disabled={isPending}
                  className="px-4 py-2 text-sm font-medium rounded-lg bg-green-600
                             hover:bg-green-700 text-white disabled:opacity-40 transition-colors"
                >
                  Activate
                </button>
              )}
              {rule.status === 'active' && (
                <button
                  onClick={onRetire}
                  disabled={isPending}
                  className="px-4 py-2 text-sm font-medium rounded-lg border
                             border-gray-300 dark:border-gray-600
                             hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700
                             dark:text-gray-300 disabled:opacity-40 transition-colors"
                >
                  Retire
                </button>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

