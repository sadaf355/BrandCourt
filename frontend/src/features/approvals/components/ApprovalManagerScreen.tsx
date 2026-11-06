/**
 * ApprovalManagerScreen – B3 Requirement 4 & 5
 * Readiness summary, unresolved blockers, approve/reject with reason,
 * locked revision snapshot ID on success, reopen flow.
 * Never implies content is published to a social platform.
 */
import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { CheckCircle, XCircle, RotateCcw, Lock, AlertTriangle, Info } from 'lucide-react'
import { apiClient } from '../../../lib/api'
import { StatusBadge } from '../../../components/common/StatusBadge'
import { SeverityBadge } from '../../../components/common/SeverityBadge'
import { ConfirmDialog } from '../../../components/common/ConfirmDialog'
import { ErrorState } from '../../../components/common/FeedbackStates'
import { useToast } from '../../../components/common/Toast'

export function ApprovalManagerScreen() {
  const { id } = useParams<{ id: string }>()
  const qc = useQueryClient()
  const { showToast } = useToast()

  const [rejectReason, setRejectReason] = useState('')
  const [showRejectForm, setShowRejectForm] = useState(false)
  const [showReopenConfirm, setShowReopenConfirm] = useState(false)
  const [approvalResult, setApprovalResult] = useState<{
    locked_revision_id?: string
    snapshot_version?: number
    approved_at?: string
  } | null>(null)

  const { data: content, isLoading, isError } = useQuery({
    queryKey: ['content', id],
    queryFn: () => apiClient.getContent(id!),
    enabled: !!id,
  })

  const approveMutation = useMutation({
    mutationFn: () => apiClient.approveContentWithReason(id!),
    onSuccess: (result) => {
      setApprovalResult(result)
      qc.invalidateQueries({ queryKey: ['content', id] })
      showToast('Content approved and revision locked.', 'success')
    },
    onError: (err: Error) => {
      showToast(err.message || 'Approval failed — resolve all blockers first.', 'error')
    },
  })

  const rejectMutation = useMutation({
    mutationFn: (reason: string) => apiClient.rejectContentWithReason(id!, reason),
    onSuccess: () => {
      setShowRejectForm(false)
      setRejectReason('')
      qc.invalidateQueries({ queryKey: ['content', id] })
      showToast('Content rejected with reason recorded.', 'info')
    },
    onError: (err: Error) => {
      showToast(err.message || 'Rejection failed.', 'error')
    },
  })

  const reopenMutation = useMutation({
    mutationFn: () => apiClient.reopenContent(id!),
    onSuccess: () => {
      setShowReopenConfirm(false)
      qc.invalidateQueries({ queryKey: ['content', id] })
      showToast('A new draft revision has been created. The locked version is preserved.', 'info')
    },
    onError: (err: Error) => {
      showToast(err.message, 'error')
    },
  })

  if (isLoading) {
    return (
      <div className="p-8 space-y-4" role="status" aria-label="Loading approval screen">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-16 rounded-xl bg-gray-100 dark:bg-gray-800 animate-pulse" />
        ))}
      </div>
    )
  }

  if (isError || !content) {
    return (
      <ErrorState
        title="Content not found"
        message="This item may have been removed or you do not have access."
      />
    )
  }

  const findings = content.findings ?? []
  const blockers = findings.filter(
    (f) =>
      f.state !== 'overridden' &&
      f.state !== 'resolved' &&
      (f.severity === 'critical' ||
        f.verdict === 'contradicted' ||
        f.verdict === 'outdated' ||
        f.verdict === 'unsupported')
  )
  const hasBlockers = blockers.length > 0
  const isApproved = content.status === 'approved'
  const isRejected = content.status === 'rejected'

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{content.title}</h1>
        <div className="flex items-center gap-3 mt-2">
          <StatusBadge status={content.status} />
          <span className="text-sm text-gray-500 dark:text-gray-400">
            {content.channel} · {content.campaign}
          </span>
        </div>
      </div>

      {/* Governance notice — non-negotiable */}
      <div className="flex gap-3 p-4 bg-blue-50 dark:bg-blue-900/20 border border-blue-200
                      dark:border-blue-700 rounded-xl text-sm text-blue-800 dark:text-blue-300">
        <Info className="w-5 h-5 flex-shrink-0 mt-0.5" aria-hidden="true" />
        <p>
          <strong>Content governance approval only.</strong> BrandCourt does not publish to any
          social platform. Approving here locks the revision for brand compliance purposes and
          does not trigger distribution to any external channel.
        </p>
      </div>

      {/* Approval result banner */}
      {approvalResult && (
        <div className="flex gap-3 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200
                        dark:border-green-700 rounded-xl" role="status">
          <Lock className="w-5 h-5 text-green-600 dark:text-green-400 flex-shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-semibold text-green-800 dark:text-green-300">
              Revision locked successfully
            </p>
            <p className="text-green-700 dark:text-green-400 mt-1">
              Locked revision ID: <code className="font-mono bg-green-100 dark:bg-green-900/40
              px-1.5 py-0.5 rounded">{approvalResult.locked_revision_id}</code>
              {' '}(version {approvalResult.snapshot_version})
            </p>
            <p className="text-green-600 dark:text-green-500 text-xs mt-1">
              Approved at {approvalResult.approved_at
                ? new Date(approvalResult.approved_at).toLocaleString()
                : 'just now'}
            </p>
          </div>
        </div>
      )}

      {/* Readiness summary */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <SummaryCard
          label="Total findings"
          value={findings.length}
          colorClass="text-gray-700 dark:text-gray-300"
        />
        <SummaryCard
          label="Unresolved blockers"
          value={blockers.length}
          colorClass={
            blockers.length > 0
              ? 'text-red-600 dark:text-red-400'
              : 'text-green-600 dark:text-green-400'
          }
        />
        <SummaryCard
          label="Current revision"
          value={`v${content.current_revision}`}
          colorClass="text-gray-700 dark:text-gray-300"
        />
        <SummaryCard
          label="Status"
          value={<StatusBadge status={content.status} />}
          colorClass=""
        />
      </div>

      {/* Blockers list */}
      {hasBlockers && !isApproved && (
        <div className="p-4 bg-red-50 dark:bg-red-900/20 border border-red-200
                        dark:border-red-700 rounded-xl space-y-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" aria-hidden="true" />
            <h2 className="font-semibold text-red-800 dark:text-red-300">
              Unresolved blockers ({blockers.length})
            </h2>
          </div>
          <ul className="space-y-2">
            {blockers.map((f) => (
              <li
                key={f.id}
                className="flex items-start gap-3 text-sm text-red-700 dark:text-red-300"
              >
                <SeverityBadge severity={f.severity} />
                <span>
                  <strong>"{f.claim_text}"</strong> — {f.verdict} · {f.rationale.substring(0, 80)}…
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Actions */}
      {!isApproved && !isRejected && (
        <div className="flex flex-wrap gap-4 pt-2">
          {/* Approve */}
          <button
            onClick={() => approveMutation.mutate()}
            disabled={hasBlockers || approveMutation.isPending}
            aria-disabled={hasBlockers}
            title={
              hasBlockers
                ? `Cannot approve: ${blockers.length} unresolved blocker(s) must be overridden or resolved`
                : 'Approve and lock revision'
            }
            className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-xl
                       bg-green-600 hover:bg-green-700 text-white
                       disabled:opacity-40 disabled:cursor-not-allowed transition-colors
                       focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-green-500"
          >
            <CheckCircle className="w-4 h-4" aria-hidden="true" />
            {approveMutation.isPending ? 'Approving…' : 'Approve & Lock Revision'}
          </button>

          {/* Reject */}
          {!showRejectForm ? (
            <button
              onClick={() => setShowRejectForm(true)}
              className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-xl
                         bg-red-600 hover:bg-red-700 text-white transition-colors
                         focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-500"
            >
              <XCircle className="w-4 h-4" aria-hidden="true" />
              Reject
            </button>
          ) : (
            <div className="w-full space-y-3">
              <label
                htmlFor="reject-reason"
                className="block text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                Rejection reason <span aria-hidden="true" className="text-red-500">*</span>
              </label>
              <textarea
                id="reject-reason"
                rows={3}
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Provide a clear reason that the creator can act on…"
                className="w-full px-4 py-3 text-sm border rounded-xl
                           border-gray-200 dark:border-gray-600
                           bg-white dark:bg-gray-800
                           text-gray-900 dark:text-white
                           placeholder-gray-400 focus:ring-2 focus:ring-red-500 outline-none"
              />
              <div className="flex gap-3">
                <button
                  onClick={() => rejectMutation.mutate(rejectReason)}
                  disabled={!rejectReason.trim() || rejectMutation.isPending}
                  className="px-4 py-2 text-sm font-medium rounded-xl bg-red-600
                             hover:bg-red-700 text-white disabled:opacity-40
                             disabled:cursor-not-allowed transition-colors"
                >
                  {rejectMutation.isPending ? 'Rejecting…' : 'Confirm Reject'}
                </button>
                <button
                  onClick={() => { setShowRejectForm(false); setRejectReason('') }}
                  className="px-4 py-2 text-sm border rounded-xl
                             border-gray-200 dark:border-gray-700
                             hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Reopen flow — creates new revision, never overwrites locked */}
      {(isApproved || isRejected) && (
        <div className="pt-2">
          <button
            onClick={() => setShowReopenConfirm(true)}
            className="flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-xl
                       border border-gray-300 dark:border-gray-600
                       hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors
                       focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500"
          >
            <RotateCcw className="w-4 h-4" aria-hidden="true" />
            Reopen (create new draft revision)
          </button>
          <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
            Reopening creates a new draft revision. The locked revision (if any) is preserved and
            never overwritten.
          </p>
        </div>
      )}

      <ConfirmDialog
        open={showReopenConfirm}
        title="Reopen content?"
        message="A new draft revision will be created. Any previously locked revision snapshot is kept intact and cannot be overwritten."
        confirmLabel="Reopen"
        onConfirm={() => reopenMutation.mutate()}
        onCancel={() => setShowReopenConfirm(false)}
      />
    </div>
  )
}

function SummaryCard({
  label,
  value,
  colorClass,
}: {
  label: string
  value: React.ReactNode
  colorClass: string
}) {
  return (
    <div className="p-4 bg-white dark:bg-gray-800 border border-gray-200
                    dark:border-gray-700 rounded-xl">
      <div className="text-xs text-gray-500 dark:text-gray-400 font-medium uppercase tracking-wide">
        {label}
      </div>
      <div className={`mt-1 text-xl font-bold ${colorClass}`}>{value}</div>
    </div>
  )
}

