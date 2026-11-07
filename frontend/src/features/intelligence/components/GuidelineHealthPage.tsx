import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  HeartPulse,
  CheckCircle2,
  Edit3,
  EyeOff,
  Sparkles,
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
  const [ignoredList, setIgnoredList] = useState<number[]>([])
  const [acceptedList, setAcceptedList] = useState<number[]>([])

  const { data: healthReport, isLoading, isError, refetch } = useQuery({
    queryKey: ['guideline-health'],
    queryFn: () => apiClient.getGuidelineHealth(),
  })

  const updateRuleMutation = useMutation({
    mutationFn: ({ ruleId, newDescription }: { ruleId: string; newDescription: string }) =>
      apiClient.updateRule(ruleId, { description: newDescription }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['rules'] })
      qc.invalidateQueries({ queryKey: ['guideline-health'] })
      showToast('Rule definition updated with improved wording.', 'success')
      setEditingIndex(null)
    },
    onError: (err: Error) => showToast(err.message, 'error'),
  })

  if (isLoading) {
    return (
      <div className="page-container p-6 space-y-4">
        <Skeleton height="36px" width="300px" />
        <Skeleton height="120px" />
        <Skeleton height="200px" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="page-container p-6">
        <ErrorState
          title="Could not evaluate guideline health"
          message="Failed to execute heuristic guideline conflict and ambiguity screening."
          onRetry={() => refetch()}
        />
      </div>
    )
  }

  const issues = (healthReport?.issues || []).filter((_, idx) => !ignoredList.includes(idx))

  const handleAcceptSuggestion = (issue: GuidelineHealthIssue, idx: number) => {
    if (issue.rule_id) {
      updateRuleMutation.mutate({
        ruleId: issue.rule_id,
        newDescription: issue.suggestion,
      })
    }
    setAcceptedList((prev) => [...prev, idx])
    showToast('Accepted suggested wording.', 'success')
  }

  const handleStartEdit = (issue: GuidelineHealthIssue, idx: number) => {
    setEditingIndex(idx)
    setEditText(issue.suggestion)
  }

  const handleSaveEdit = (issue: GuidelineHealthIssue, idx: number) => {
    if (issue.rule_id) {
      updateRuleMutation.mutate({
        ruleId: issue.rule_id,
        newDescription: editText,
      })
    }
    setAcceptedList((prev) => [...prev, idx])
    setEditingIndex(null)
  }

  const handleIgnore = (idx: number) => {
    setIgnoredList((prev) => [...prev, idx])
    showToast('Suggestion dismissed from active list.', 'info')
  }

  return (
    <div className="page-container p-6 space-y-6" data-testid="guideline-health-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
            <HeartPulse className="text-pink-500" size={26} />
            Guideline Health & Conflict Radar
          </h1>
          <p className="text-sm text-slate-400">
            Heuristic detection of ambiguous phrasing, contradictory rule pairs, and high-override friction points.
          </p>
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-400 bg-slate-900 border border-slate-800 px-3 py-1.5 rounded-lg">
          <Info size={14} className="text-indigo-400" />
          <span>Screening {healthReport?.active_rules ?? 0} active rules</span>
        </div>
      </div>

      {/* Advisory Notice */}
      <div className="p-4 rounded-xl border border-indigo-500/20 bg-indigo-500/5 flex items-start gap-3 text-xs text-indigo-300">
        <Sparkles size={16} className="text-indigo-400 mt-0.5 shrink-0" />
        <div>
          <span className="font-semibold text-white">Heuristic screening notice:</span> Lexical similarity and override
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
            const isAccepted = acceptedList.includes(idx)
            const isEditing = editingIndex === idx

            return (
              <div
                key={idx}
                className={`p-5 rounded-xl border transition-all ${
                  isAccepted
                    ? 'border-emerald-500/30 bg-emerald-500/5'
                    : 'border-slate-800 bg-slate-900/60 hover:border-slate-700'
                }`}
              >
                {/* Title and Badges */}
                <div className="flex flex-wrap items-center justify-between gap-2 mb-2.5">
                  <div className="flex items-center gap-2">
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider ${
                        issue.type === 'possible_conflict'
                          ? 'bg-red-500/10 text-red-400 border border-red-500/20'
                          : issue.type === 'high_override_rate'
                          ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                          : 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
                      }`}
                    >
                      {issue.type.replace(/_/g, ' ')}
                    </span>
                    <span className="text-xs font-mono text-slate-400">{issue.code}</span>
                  </div>

                  {isAccepted && (
                    <span className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-400">
                      <CheckCircle2 size={14} /> Accepted & Updated
                    </span>
                  )}
                </div>

                <h3 className="text-base font-semibold text-white mb-1.5">{issue.title}</h3>
                <p className="text-xs text-slate-300 leading-relaxed mb-4">{issue.explanation}</p>

                {/* Suggested Wording Box */}
                <div className="p-3.5 rounded-lg border border-slate-700/80 bg-slate-800/60 mb-4">
                  <div className="text-[11px] font-semibold text-indigo-400 uppercase tracking-wider mb-1 flex items-center gap-1.5">
                    <Sparkles size={12} />
                    Suggested Objective Revision
                  </div>

                  {isEditing ? (
                    <div className="space-y-2 mt-2">
                      <textarea
                        value={editText}
                        onChange={(e) => setEditText(e.target.value)}
                        rows={3}
                        className="w-full text-xs bg-slate-900 border border-indigo-500/50 rounded-lg p-2.5 text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
                      />
                      <div className="flex justify-end gap-2">
                        <button
                          onClick={() => setEditingIndex(null)}
                          className="px-3 py-1 rounded text-xs text-slate-400 hover:text-white"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => handleSaveEdit(issue, idx)}
                          disabled={updateRuleMutation.isPending}
                          className="px-3.5 py-1 rounded text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white"
                        >
                          Save & Apply
                        </button>
                      </div>
                    </div>
                  ) : (
                    <p className="text-xs text-slate-200 italic">"{issue.suggestion}"</p>
                  )}
                </div>

                {/* Actions */}
                {!isAccepted && !isEditing && (
                  <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-slate-800/80">
                    <button
                      onClick={() => handleIgnore(idx)}
                      className="px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors flex items-center gap-1"
                    >
                      <EyeOff size={13} />
                      Ignore
                    </button>

                    <button
                      onClick={() => handleStartEdit(issue, idx)}
                      className="px-3 py-1.5 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 border border-slate-700 transition-colors flex items-center gap-1"
                    >
                      <Edit3 size={13} />
                      Edit Wording
                    </button>

                    <button
                      onClick={() => handleAcceptSuggestion(issue, idx)}
                      disabled={updateRuleMutation.isPending}
                      className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white transition-colors flex items-center gap-1 shadow-sm"
                    >
                      <CheckCircle2 size={13} />
                      Accept Suggestion
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

