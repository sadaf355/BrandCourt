import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Scale,
  CheckCircle2,
  ArrowUpRight,
  Plus,
  Clock,
} from 'lucide-react'
import { apiClient } from '../../../lib/api'
import { useToast } from '../../../components/common/Toast'
import { Skeleton, ErrorState, EmptyState } from '../../../components/common/FeedbackStates'

export function PrecedentLedgerPage() {
  const { showToast } = useToast()
  const qc = useQueryClient()
  const [filter, setFilter] = useState<'all' | 'pending' | 'approved'>('all')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newPattern, setNewPattern] = useState('')
  const [newReason, setNewReason] = useState('')
  const [newChannel, setNewChannel] = useState('all')

  const { data: precedents = [], isLoading, isError, refetch } = useQuery({
    queryKey: ['precedents'],
    queryFn: () => apiClient.listPrecedents(),
  })

  const approveMutation = useMutation({
    mutationFn: (id: string) => apiClient.approvePrecedent(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['precedents'] })
      showToast('Precedent approved by manager.', 'success')
    },
    onError: (err: Error) => showToast(err.message, 'error'),
  })

  const promoteMutation = useMutation({
    mutationFn: (id: string) => apiClient.promotePrecedent(id),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['precedents'] })
      qc.invalidateQueries({ queryKey: ['rules'] })
      showToast(data.message, 'success')
    },
    onError: (err: Error) => showToast(err.message, 'error'),
  })

  const createMutation = useMutation({
    mutationFn: () =>
      apiClient.createPrecedent({
        finding_id: 'fnd-1',
        channel: newChannel,
        pattern_text: newPattern,
        reason: newReason,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['precedents'] })
      setShowCreateModal(false)
      setNewPattern('')
      setNewReason('')
      showToast('New precedent submitted for manager review.', 'success')
    },
    onError: (err: Error) => showToast(err.message, 'error'),
  })

  if (isLoading) {
    return (
      <div className="page-container p-6 space-y-4">
        <Skeleton height="36px" width="280px" />
        <Skeleton height="100px" />
        <Skeleton height="180px" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="page-container p-6">
        <ErrorState
          title="Could not load precedents"
          message="Failed to retrieve precedent records from the database."
          onRetry={() => refetch()}
        />
      </div>
    )
  }

  const filtered = precedents.filter((p) => {
    if (filter === 'pending') return p.status === 'pending'
    if (filter === 'approved') return p.status === 'approved'
    return true
  })

  return (
    <div className="page-container p-6 space-y-6" data-testid="precedent-ledger-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-2">
            <Scale className="text-indigo-400" size={26} />
            Precedent Ledger
          </h1>
          <p className="text-sm text-slate-400">
            Case law repository for approved phrasing exceptions, marketing context carve-outs, and promoted draft rules.
          </p>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="px-4 py-2 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white flex items-center gap-1.5 transition-colors shadow-sm"
        >
          <Plus size={15} /> Record Precedent
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-800 pb-2">
        {(['all', 'pending', 'approved'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setFilter(tab)}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
              filter === tab
                ? 'bg-indigo-600 text-white border border-indigo-500/30'
                : 'text-gray-600 dark:text-slate-300 hover:text-gray-900 dark:hover:text-white'
            }`}
          >
            {tab.charAt(0).toUpperCase() + tab.slice(1)} ({precedents.filter((p) => (tab === 'all' ? true : p.status === tab)).length})
          </button>
        ))}
      </div>

      {/* Precedent Cards */}
      {filtered.length === 0 ? (
        <EmptyState
          title="No precedents found"
          description="Precedents are recorded when reviewers override a finding with a reusable justification."
        />
      ) : (
        <div className="space-y-4">
          {filtered.map((item) => (
            <div
              key={item.id}
              className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 hover:border-slate-700 transition-all"
            >
              <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
                <div className="flex items-center gap-2.5">
                  <span
                    className={`px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider ${
                      item.status === 'approved'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
                    }`}
                  >
                    {item.status}
                  </span>
                  <span className="text-xs text-slate-400 font-mono">Scope: {item.channel.toUpperCase()}</span>
                  {item.rule_id && (
                    <span className="text-xs text-indigo-400 font-mono">Rule: {item.rule_id}</span>
                  )}
                </div>

                <div className="text-xs text-slate-400 flex items-center gap-1.5">
                  <Clock size={13} />
                  <span>Valid until: {item.valid_to ? item.valid_to.slice(0, 10) : 'Ongoing'}</span>
                </div>
              </div>

              {/* Matched Pattern */}
              <div className="mb-2">
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Matched Content Pattern
                </div>
                <div className="p-2.5 rounded-lg bg-slate-950/80 border border-slate-800 text-xs font-mono text-slate-200">
                  "{item.pattern_text}"
                </div>
              </div>

              {/* Rationale */}
              <div className="mb-4">
                <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Established Precedent Justification
                </div>
                <p className="text-xs text-slate-300 leading-relaxed bg-slate-800/40 p-3 rounded-lg border border-slate-700/60">
                  {item.reason}
                </p>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                {item.status === 'pending' && (
                  <button
                    onClick={() => approveMutation.mutate(item.id)}
                    disabled={approveMutation.isPending}
                    className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white flex items-center gap-1.5 transition-colors disabled:opacity-50"
                  >
                    <CheckCircle2 size={14} /> Approve Precedent
                  </button>
                )}

                {item.status === 'approved' && (
                  <button
                    onClick={() => promoteMutation.mutate(item.id)}
                    disabled={promoteMutation.isPending}
                    className="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white flex items-center gap-1.5 transition-colors disabled:opacity-50"
                  >
                    <ArrowUpRight size={14} /> Promote to Draft Rule
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Record Precedent Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="w-full max-w-lg rounded-xl border border-slate-700 bg-slate-900 p-6 space-y-4">
            <h2 className="text-lg font-bold text-white flex items-center gap-2">
              <Scale size={20} className="text-indigo-400" />
              Record New Precedent
            </h2>

            <div className="space-y-3 text-xs">
              <div>
                <label className="block font-medium text-slate-300 mb-1">Channel Scope</label>
                <select
                  value={newChannel}
                  onChange={(e) => setNewChannel(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-white"
                >
                  <option value="all">All Channels</option>
                  <option value="instagram">Instagram</option>
                  <option value="website">Website</option>
                  <option value="facebook">Facebook</option>
                  <option value="linkedin">LinkedIn</option>
                </select>
              </div>

              <div>
                <label className="block font-medium text-slate-300 mb-1">Matched Text Pattern</label>
                <input
                  type="text"
                  value={newPattern}
                  onChange={(e) => setNewPattern(e.target.value)}
                  placeholder="e.g. 100% natural organic extracts"
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-white"
                />
              </div>

              <div>
                <label className="block font-medium text-slate-300 mb-1">Precedent Rationale / Exception Grounds</label>
                <textarea
                  value={newReason}
                  onChange={(e) => setNewReason(e.target.value)}
                  rows={3}
                  placeholder="Explain why this phrase is permitted and what proof/citation must accompany it."
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2 text-white"
                />
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-3 border-t border-slate-800">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-3.5 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                onClick={() => createMutation.mutate()}
                disabled={!newPattern.trim() || !newReason.trim() || createMutation.isPending}
                className="px-4 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white disabled:opacity-50"
              >
                Submit Precedent
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

