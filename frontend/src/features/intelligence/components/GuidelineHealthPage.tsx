import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  HeartPulse,
  CheckCircle2,
  Edit3,
  EyeOff,
  Sparkles,
  AlertTriangle,
  Info,
} from 'lucide-react'
import { apiClient } from '../../../lib/api'
import { useToast } from '../../../components/common/Toast'
import { Skeleton, ErrorState, EmptyState } from '../../../components/common/FeedbackStates'
import { GuidelineHealthIssue } from '../../../types/api'

export function GuidelineHealthPage() {
  const { showToast } = useToast()
  const qc = useQueryClient()
  const [editingIndex, setEditingIndex] = useState<number | null>(null)
  const [editText, setEditText] = useState('')
  const [ignoredKeys, setIgnoredKeys] = useState<string[]>([])
  const [acceptedKeys, setAcceptedKeys] = useState<string[]>([])

  const { data: healthReport, isLoading, isError, refetch } = useQuery({
    queryKey: ['guideline-health'],
    queryFn: () => apiClient.getGuidelineHealth(),
  })

  const decisionMutation = useMutation({
    mutationFn: (data: { issue_key: string; rule_id?: string; issue_type?: string; action: 'accept' | 'edit' | 'ignore'; edited_wording?: string }) => apiClient.decideGuidelineIssue(data),
    onSuccess: (_result, variables) => {
      if (variables.action === 'ignore') {
        setIgnoredKeys((prev) => (prev.includes(variables.issue_key) ? prev : [...prev, variables.issue_key]))
      } else {
        setAcceptedKeys((prev) => (prev.includes(variables.issue_key) ? prev : [...prev, variables.issue_key]))
      }
      qc.invalidateQueries({ queryKey: ['guideline-health'] })
      showToast('Guideline decision saved.', 'success')
      setEditingIndex(null)
    },
    onError: (err: Error) => showToast(err.message, 'error'),
  })

  if (isLoading) {
    return (
      <div className="page-container space-y-4">
        <Skeleton height="36px" width="300px" />
        <Skeleton height="120px" />
        <Skeleton height="200px" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="page-container">
        <ErrorState
          title="Could not evaluate guideline health"
          message="Failed to execute heuristic guideline conflict and ambiguity screening."
          onRetry={() => refetch()}
        />
      </div>
    )
  }

  const issues = (healthReport?.issues || []).filter(
    (issue) => !issue.issue_key || !ignoredKeys.includes(issue.issue_key)
  )
  const conflictCount = issues.filter((i) => i.type === 'possible_conflict').length
  const vagueCount = issues.filter((i) => i.type === 'vague_rule').length
  const overrideCount = issues.filter((i) => i.type === 'override_rate').length

  const handleAcceptSuggestion = (issue: GuidelineHealthIssue) => {
    if (issue.issue_key) decisionMutation.mutate({ issue_key: issue.issue_key, rule_id: issue.rule_id, issue_type: issue.type, action: 'accept', edited_wording: issue.suggestion })
    else showToast('This issue cannot be saved because its identifier is missing.', 'error')
  }

  const handleStartEdit = (issue: GuidelineHealthIssue, idx: number) => {
    setEditingIndex(idx)
    setEditText(issue.suggestion)
  }

  const handleSaveEdit = (issue: GuidelineHealthIssue) => {
    if (issue.issue_key) decisionMutation.mutate({ issue_key: issue.issue_key, rule_id: issue.rule_id, issue_type: issue.type, action: 'edit', edited_wording: editText })
    else showToast('This issue cannot be saved because its identifier is missing.', 'error')
  }

  const handleIgnore = (idx: number) => {
    const issue = issues[idx]
    if (issue?.issue_key) decisionMutation.mutate({ issue_key: issue.issue_key, rule_id: issue.rule_id, issue_type: issue.type, action: 'ignore' })
    else showToast('This issue cannot be saved because its identifier is missing.', 'error')
  }

  return (
    <div className="page-container" data-testid="guideline-health-page">
      {/* Standard Page Header */}
      <div className="page-header--row">
        <div>
          <h1 className="page-header__title">
            <HeartPulse className="text-teal-600 dark:text-teal-400" size={26} />
            Guideline Health
          </h1>
          <p className="page-header__subtitle">
            Heuristic screening of unclear and conflicting rules
          </p>
        </div>

        {/* Compact Stat Row with Model Mode Badge */}
        <div className="health-summary-stat">
          <Info size={14} className="text-teal-600 dark:text-teal-400" />
          <span>
            {healthReport?.active_rules ?? 0} active rules · {issues.length} issue{issues.length === 1 ? '' : 's'} ({conflictCount} conflict{conflictCount === 1 ? '' : 's'}, {vagueCount} vague{overrideCount ? `, ${overrideCount} override rate` : ''})
          </span>
          {healthReport?.model_mode && (
            <span className="badge badge-pill badge-advisory font-mono text-[11px] px-2 py-0.5">
              {healthReport.model_mode}
            </span>
          )}
        </div>
      </div>

      {/* Advisory Notice */}
      <div className="p-4 rounded-xl border border-indigo-500/20 bg-indigo-500/5 flex items-start gap-3 text-xs text-indigo-300 mb-6">
        <Sparkles size={16} className="text-indigo-400 mt-0.5 shrink-0" />
        <div>
          <span className="font-semibold text-gray-900 dark:text-white">Heuristic screening notice:</span> Lexical similarity and override
          frequency flag candidates for human decision, not confirmed contradictions. A guideline owner must review and
          accept, refine, or dismiss changes.
        </div>
      </div>

      {/* Issues List */}
      {issues.length === 0 ? (
        <EmptyState
          title="All guidelines are healthy"
          description="No rule conflicts, vague qualifiers, or high-override bottlenecks were identified."
        />
      ) : (
        <div className="space-y-4">
          {issues.map((issue, idx) => {
            const isAccepted = Boolean(issue.issue_key && acceptedKeys.includes(issue.issue_key))
            const isEditing = editingIndex === idx
            const isConflict = issue.type === 'possible_conflict'

            // Parse conflicting rules if available
            const codes = issue.code.includes(' / ') ? issue.code.split(' / ') : [issue.code]
            const titles = issue.title.includes(' ↔ ') ? issue.title.split(' ↔ ') : [issue.title]

            return (
              <div
                key={idx}
                className={`health-issue-card ${
                  isAccepted ? 'border-emerald-500/30 bg-emerald-500/5' : ''
                }`}
              >
                {/* Header row: Single Status Badge + Rule Codes */}
                <div className="health-card-header">
                  <div className="flex items-center gap-2 flex-wrap">
                    {isConflict ? (
                      <span className="badge badge-pill badge-major">
                        <AlertTriangle size={12} /> Possible conflict - needs human review
                      </span>
                    ) : issue.type === 'vague_rule' ? (
                      <span className="badge badge-pill badge-review">
                        <Sparkles size={12} /> Vague rule - needs human review
                      </span>
                    ) : (
                      <span className="badge badge-pill badge-advisory">
                        <Info size={12} /> {issue.type.replace(/_/g, ' ')} - needs human review
                      </span>
                    )}
                    <span className="text-xs font-mono font-semibold text-slate-500 dark:text-slate-400">
                      {issue.code}
                    </span>
                  </div>

                  {isAccepted && (
                    <span className="badge badge-pill badge-success">
                      <CheckCircle2 size={12} /> Accepted & Updated
                    </span>
                  )}
                </div>

                {/* Conflicting Rules as Two Equal Quote Blocks with "vs" Divider */}
                {isConflict && titles.length >= 2 ? (
                  <>
                    <div className="conflict-grid">
                      <div className="conflict-block">
                        <div className="conflict-block__header">
                          <span className="conflict-block__code">{codes[0] || 'Rule A'}</span>
                        </div>
                        <p className="conflict-block__text">"{titles[0]}"</p>
                      </div>
                      <div className="conflict-vs">
                        <span className="conflict-vs__pill">vs</span>
                      </div>
                      <div className="conflict-block">
                        <div className="conflict-block__header">
                          <span className="conflict-block__code">{codes[1] || 'Rule B'}</span>
                        </div>
                        <p className="conflict-block__text">"{titles[1]}"</p>
                      </div>
                    </div>
                    <p className="text-xs text-slate-400 leading-relaxed mb-4">{issue.explanation}</p>
                  </>
                ) : (
                  <div>
                    <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-1.5">{issue.title}</h3>
                    <p className="text-xs text-slate-400 leading-relaxed mb-4">{issue.explanation}</p>
                  </div>
                )}

                {/* Suggested Revision Block with 12px padding and 8px gap under heading */}
                <div className="suggested-revision-block">
                  <div className="suggested-revision-header">
                    <Sparkles size={13} />
                    <span>Suggested revision</span>
                  </div>

                  {isEditing ? (
                    <div className="space-y-2 mt-2">
                      <textarea
                        value={editText}
                        onChange={(e) => setEditText(e.target.value)}
                        rows={3}
                        className="w-full text-xs"
                      />
                      <div className="flex justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => setEditingIndex(null)}
                          className="btn btn--sm btn--ghost"
                        >
                          Cancel
                        </button>
                        <button
                          type="button"
                          onClick={() => handleSaveEdit(issue)}
                          disabled={decisionMutation.isPending}
                          className="btn btn--sm btn--primary"
                        >
                          Save & Apply
                        </button>
                      </div>
                    </div>
                  ) : (
                    <p className="suggested-revision-text">"{issue.suggestion}"</p>
                  )}
                </div>

                {/* Right-aligned action row: Ignore ghost, Edit wording secondary, Accept primary with 12px gaps */}
                {!isAccepted && !isEditing && (
                  <div className="health-card-actions">
                    <button
                      type="button"
                      onClick={() => handleIgnore(idx)}
                      className="btn btn--sm btn--ghost"
                      aria-label="Ignore"
                    >
                      <EyeOff size={13} />
                      <span>Ignore</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => handleStartEdit(issue, idx)}
                      className="btn btn--sm btn--secondary"
                      aria-label="Edit wording"
                    >
                      <Edit3 size={13} />
                      <span>Edit wording</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => handleAcceptSuggestion(issue)}
                      disabled={decisionMutation.isPending}
                      className="btn btn--sm btn--primary"
                      aria-label="Accept"
                    >
                      <CheckCircle2 size={13} />
                      <span>Accept</span>
                    </button>
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}


