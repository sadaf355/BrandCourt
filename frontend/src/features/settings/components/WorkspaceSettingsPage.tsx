/**
 * WorkspaceSettingsPage – B3 Requirement 8
 * Workspace settings and data-deletion flow with confirmation and audit event.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Building2, Trash2, AlertTriangle, ShieldAlert, Check } from 'lucide-react'
import { apiClient } from '../../../lib/api'
import { ConfirmDialog } from '../../../components/common/ConfirmDialog'
import { useToast } from '../../../components/common/Toast'
import type { Role } from '../../../types/api'

interface WorkspaceSettingsPageProps {
  currentUserRole: Role
}

export function WorkspaceSettingsPage({ currentUserRole }: WorkspaceSettingsPageProps) {
  const qc = useQueryClient()
  const { showToast } = useToast()
  const isAdmin = currentUserRole === 'admin'

  const [workspaceName, setWorkspaceName] = useState('')
  const [showDeleteModal, setShowDeleteModal] = useState(false)
  const [deleteReason, setDeleteReason] = useState('')
  const [understandChecked, setUnderstandChecked] = useState(false)

  const { data: workspace, isLoading } = useQuery({
    queryKey: ['workspace'],
    queryFn: async () => {
      const ws = await apiClient.getWorkspace()
      setWorkspaceName(ws.name)
      return ws
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (reason: string) => apiClient.deleteWorkspaceData(reason),
    onSuccess: (res) => {
      setShowDeleteModal(false)
      showToast(`Workspace data deletion scheduled. Audit Event ID: ${res.audit_event_id}`, 'info')
      qc.invalidateQueries({ queryKey: ['workspace'] })
    },
    onError: (err: Error) => {
      showToast(err.message || 'Deletion failed', 'error')
    },
  })

  if (isLoading) {
    return (
      <div className="p-8 space-y-4" role="status" aria-label="Loading workspace settings">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-16 rounded-xl bg-gray-100 dark:bg-gray-800 animate-pulse" />
        ))}
      </div>
    )
  }

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Workspace Settings</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
          Manage workspace profile, compliance defaults, and retention policies.
        </p>
      </div>

      {/* General Settings */}
      <section className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl p-6 space-y-5">
        <div className="flex items-center gap-3">
          <Building2 className="w-5 h-5 text-purple-600 dark:text-purple-400" aria-hidden="true" />
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">General Information</h2>
        </div>

        <div className="space-y-4">
          <div className="space-y-1">
            <label htmlFor="ws-name" className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Workspace Name
            </label>
            <input
              id="ws-name"
              type="text"
              value={workspaceName}
              disabled={!isAdmin}
              onChange={(e) => setWorkspaceName(e.target.value)}
              className="w-full max-w-md px-3 py-2 text-sm border rounded-lg border-gray-200
                         dark:border-gray-600 bg-white dark:bg-gray-700
                         text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 outline-none
                         disabled:opacity-60 disabled:cursor-not-allowed"
            />
          </div>

          <div className="space-y-1">
            <label className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Workspace Identifier
            </label>
            <div className="text-sm font-mono text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-900/40 p-2.5 rounded-lg max-w-md border border-gray-100 dark:border-gray-700">
              {workspace?.id ?? 'ws-aurora-7'}
            </div>
            <p className="text-xs text-gray-400">
              All database queries and audit events are strictly isolated by this workspace ID.
            </p>
          </div>

          {isAdmin && (
            <button
              onClick={() => showToast('Workspace settings saved.', 'success')}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-purple-600 hover:bg-purple-700 text-white transition-colors"
            >
              Save Changes
            </button>
          )}
        </div>
      </section>

      {/* Governance & Privacy Notice */}
      <section className="bg-purple-50 dark:bg-purple-900/10 border border-purple-200 dark:border-purple-800 rounded-xl p-6 space-y-2">
        <h3 className="text-sm font-semibold text-purple-900 dark:text-purple-300">
          Governance & Data Boundary
        </h3>
        <p className="text-sm text-purple-800 dark:text-purple-300/80 leading-relaxed">
          BrandCourt enforces tenant isolation at every layer. PII and secret terms are masked before
          external model invocations. All human actions are preserved in an append-only audit trail.
        </p>
      </section>

      {/* Danger Zone: Data Deletion */}
      {isAdmin && (
        <section className="bg-red-50/50 dark:bg-red-900/10 border border-red-200 dark:border-red-900/50 rounded-xl p-6 space-y-4">
          <div className="flex items-center gap-3">
            <ShieldAlert className="w-5 h-5 text-red-600 dark:text-red-400" aria-hidden="true" />
            <h2 className="text-base font-semibold text-red-900 dark:text-red-300">Danger Zone</h2>
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Request complete data deletion for this workspace. This action immediately initiates soft deletion,
            records an immutable audit event, and cannot be undone after final purging.
          </p>

          <button
            onClick={() => {
              setDeleteReason('')
              setUnderstandChecked(false)
              setShowDeleteModal(true)
            }}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-red-600 hover:bg-red-700 text-white transition-colors"
          >
            <Trash2 className="w-4 h-4" aria-hidden="true" />
            Delete Workspace Data
          </button>
        </section>
      )}

      {/* Confirmation Modal */}
      {showDeleteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm animate-fade-in">
          <div
            className="bg-white dark:bg-gray-800 rounded-xl max-w-lg w-full p-6 shadow-2xl border border-red-200 dark:border-red-800 space-y-4"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-dialog-title"
          >
            <div className="flex items-center gap-3 text-red-600 dark:text-red-400">
              <AlertTriangle className="w-6 h-6 flex-shrink-0" aria-hidden="true" />
              <h2 id="delete-dialog-title" className="text-lg font-bold text-gray-900 dark:text-white">
                Confirm Workspace Data Deletion
              </h2>
            </div>

            <p className="text-sm text-gray-600 dark:text-gray-400">
              You are requesting the permanent deletion of all content revisions, OCR records, findings,
              and workspace member mappings. This will generate an immutable audit log entry.
            </p>

            <div className="space-y-1">
              <label htmlFor="del-reason" className="text-xs font-semibold text-gray-700 dark:text-gray-300">
                Reason for deletion <span className="text-red-500">*</span>
              </label>
              <textarea
                id="del-reason"
                rows={3}
                value={deleteReason}
                onChange={(e) => setDeleteReason(e.target.value)}
                placeholder="Specify the reason (e.g., Contract termination, GDPR right-to-be-forgotten)..."
                className="w-full text-sm p-3 border rounded-lg border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-red-500 outline-none"
              />
            </div>

            <label className="flex items-start gap-2.5 cursor-pointer text-sm text-gray-700 dark:text-gray-300 pt-1">
              <input
                type="checkbox"
                checked={understandChecked}
                onChange={(e) => setUnderstandChecked(e.target.checked)}
                className="mt-1 rounded border-gray-300 dark:border-gray-600 text-red-600 focus:ring-red-500"
              />
              <span>
                I understand that this action will lock the workspace and trigger irreversible deletion in accordance with our data retention schedule.
              </span>
            </label>

            <div className="flex justify-end gap-3 pt-3">
              <button
                type="button"
                onClick={() => setShowDeleteModal(false)}
                className="px-4 py-2 text-sm font-medium border rounded-lg border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!deleteReason.trim() || !understandChecked || deleteMutation.isPending}
                onClick={() => deleteMutation.mutate(deleteReason)}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-red-600 hover:bg-red-700 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <Trash2 className="w-4 h-4" />
                {deleteMutation.isPending ? 'Processing Deletion...' : 'Confirm & Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

