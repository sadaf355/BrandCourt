/**
 * MemberManagementPage – B3 Requirement 8
 * Workspace member directory with supported role management.
 */
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Shield } from 'lucide-react'
import { apiClient } from '../../../lib/api'
import { EmptyState, ErrorState } from '../../../components/common/FeedbackStates'
import { useToast } from '../../../components/common/Toast'
import type { Role } from '../../../types/api'

const ROLE_COLORS: Record<Role, string> = {
  admin: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
  manager: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
  reviewer: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  creator: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
}

export function MemberManagementPage({ currentUserId, currentUserRole }: {
  currentUserId: string
  currentUserRole: Role
}) {
  const qc = useQueryClient()
  const { showToast } = useToast()

  const isAdmin = currentUserRole === 'admin'

  const { data: members = [], isLoading, isError, refetch } = useQuery({
    queryKey: ['members'],
    queryFn: () => apiClient.listMembers(),
  })

  const roleMutation = useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: Role }) =>
      apiClient.changeMemberRole(userId, role),
    onSuccess: (m) => {
      qc.invalidateQueries({ queryKey: ['members'] })
      showToast(`${m.full_name} is now ${m.role}.`, 'success')
    },
    onError: (err: Error) => showToast(err.message, 'error'),
  })

  if (isLoading) {
    return (
      <div className="p-8 space-y-3" role="status" aria-label="Loading members">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="h-14 rounded-lg bg-gray-100 dark:bg-gray-800 animate-pulse" />
        ))}
      </div>
    )
  }

  if (isError) {
    return <ErrorState title="Could not load members" action={{ label: 'Retry', onClick: () => refetch() }} />
  }

  return (
    <div className="page-container" data-testid="member-management-page">
      <div className="page-header">
        <h1 className="page-header__title">Members</h1>
        <p className="page-header__subtitle">
          {members.length} workspace member{members.length !== 1 ? 's' : ''}
        </p>
      </div>

      {members.length === 0 ? (
        <EmptyState title="No members yet" message="No workspace members have been added yet." />
      ) : (
        <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 dark:bg-gray-800/60 text-left">
                <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-400">Name</th>
                <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-400">Email</th>
                <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-400">Role</th>
                <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-400">Status</th>
              </tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <tr
                  key={m.id}
                  className="border-t border-gray-100 dark:border-gray-800
                             hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                >
                  <td className="px-4 py-3">
                    <div className="font-medium text-gray-900 dark:text-white">{m.full_name}</div>
                    {m.id === currentUserId && (
                      <span className="text-xs text-purple-500">(you)</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-600 dark:text-gray-400">{m.email}</td>
                  <td className="px-4 py-3">
                    {isAdmin && m.id !== currentUserId ? (
                      <select
                        value={m.role}
                        onChange={(e) =>
                          roleMutation.mutate({ userId: m.id, role: e.target.value as Role })
                        }
                        disabled={roleMutation.isPending}
                        aria-label={`Change role for ${m.full_name}`}
                        className="text-xs px-2 py-1 rounded-lg border border-gray-200
                                   dark:border-gray-600 bg-white dark:bg-gray-700
                                   text-gray-900 dark:text-white focus:ring-2
                                   focus:ring-purple-500 outline-none"
                      >
                        <option value="creator">Creator</option>
                        <option value="reviewer">Reviewer</option>
                        <option value="manager">Manager</option>
                        <option value="admin">Admin</option>
                      </select>
                    ) : (
                      <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 text-xs
                                       rounded-full font-medium ${ROLE_COLORS[m.role]}`}>
                        <Shield className="w-3 h-3" aria-hidden="true" />
                        {m.role}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    {m.is_active ? (
                      <span className="text-xs text-green-600 dark:text-green-400">Active</span>
                    ) : (
                      <span className="text-xs text-gray-400">Deactivated</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

    </div>
  )
}

