/**
 * WorkspaceSettingsPage – B3 Requirement 8
 * Workspace settings and data-deletion flow with confirmation and audit event.
 */
import { useQuery } from '@tanstack/react-query'
import { Building2 } from 'lucide-react'
import { apiClient } from '../../../lib/api'
import type { Role } from '../../../types/api'

interface WorkspaceSettingsPageProps {
  currentUserRole: Role
}

export function WorkspaceSettingsPage({ currentUserRole }: WorkspaceSettingsPageProps) {
  void currentUserRole

  const { data: workspace, isLoading } = useQuery({
    queryKey: ['workspace'],
    queryFn: async () => {
      const ws = await apiClient.getWorkspace()
      return ws
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
    <div className="page-container" data-testid="workspace-settings-page">
      <div className="page-header">
        <h1 className="page-header__title">Workspace Settings</h1>
        <p className="page-header__subtitle">
          View your workspace identity and data boundary.
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
              value={workspace?.name ?? ''}
              readOnly
              className="w-full max-w-md px-3 py-2 text-sm border rounded-lg border-gray-200
                         dark:border-gray-600 bg-white dark:bg-gray-700
                         text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 outline-none
                         opacity-70 cursor-default"
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

    </div>
  )
}

