/**
 * MemberManagementPage – B3 Requirement 8
 * Table of workspace members, role change (admin only), deactivate with confirm, invite form.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { UserPlus, UserX, Shield } from 'lucide-react'
import { apiClient } from '../../../lib/api'
import { ConfirmDialog } from '../../../components/common/ConfirmDialog'
import { EmptyState, ErrorState } from '../../../components/common/FeedbackStates'
import { useToast } from '../../../components/common/Toast'
import type { Role, WorkspaceMember } from '../../../types/api'

type InviteForm = { email: string; role: Role }

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
  const [deactivateTarget, setDeactivateTarget] = useState<WorkspaceMember | null>(null)
  const [showInvite, setShowInvite] = useState(false)

  const isAdmin = currentUserRole === 'admin'

  const { data: members = [], isLoading, isError, refetch } = useQuery({
    queryKey: ['members'],
    queryFn: () => apiClient.listMembers(),
  })

  const { register, handleSubmit, reset, formState: { errors } } = useForm<InviteForm>({
    defaultValues: { role: 'creator' },
  })

  const inviteMutation = useMutation({
    mutationFn: (data: InviteForm) => apiClient.inviteMember(data.email, data.role),
    onSuccess: (m) => {
      qc.invalidateQueries({ queryKey: ['members'] })
      setShowInvite(false)
      reset()
      showToast(`Invited ${m.email} as ${m.role}.`, 'success')
    },
    onError: (err: Error) => showToast(err.message, 'error'),
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

  const deactivateMutation = useMutation({
    mutationFn: (userId: string) => apiClient.deactivateMember(userId),
    onSuccess: (m) => {
      setDeactivateTarget(null)
      qc.invalidateQueries({ queryKey: ['members'] })
      showToast(`${m.full_name} deactivated.`, 'info')
    },
    onError: (err: Error) => {
      setDeactivateTarget(null)
      showToast(err.message, 'error')
    },
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
    <div className="p-6 max-w-5xl mx-auto space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Members</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            {members.length} workspace member{members.length !== 1 ? 's' : ''}
          </p>
        </div>
        {isAdmin && (
          <button
            onClick={() => setShowInvite((s) => !s)}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-xl
                       bg-purple-600 hover:bg-purple-700 text-white transition-colors
                       focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-500"
          >
            <UserPlus className="w-4 h-4" aria-hidden="true" />
            Invite Member
          </button>
        )}
      </div>

      {/* Invite form */}
      {showInvite && isAdmin && (
        <form
          onSubmit={handleSubmit((data) => inviteMutation.mutate(data))}
          className="p-5 bg-white dark:bg-gray-800 border border-purple-200
                     dark:border-purple-700 rounded-xl space-y-4"
          aria-label="Invite new member"
        >
          <h2 className="font-semibold text-gray-800 dark:text-gray-200">Invite New Member</h2>
          <div className="flex flex-wrap gap-4">
            <div className="flex-1 min-w-48 space-y-1">
              <label htmlFor="invite-email" className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Email <span className="text-red-500" aria-hidden="true">*</span>
              </label>
              <input
                id="invite-email"
                type="email"
                placeholder="colleague@brand.com"
                {...register('email', { required: 'Required', pattern: { value: /\S+@\S+\.\S+/, message: 'Valid email required' } })}
                className="w-full px-3 py-2 text-sm border rounded-lg border-gray-200
                           dark:border-gray-600 bg-white dark:bg-gray-700
                           text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 outline-none"
              />
              {errors.email && (
                <p className="text-xs text-red-500" role="alert">{errors.email.message}</p>
              )}
            </div>
            <div className="space-y-1">
              <label htmlFor="invite-role" className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Role
              </label>
              <select
                id="invite-role"
                {...register('role')}
                className="px-3 py-2 text-sm border rounded-lg border-gray-200
                           dark:border-gray-600 bg-white dark:bg-gray-700
                           text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 outline-none"
              >
                <option value="creator">Creator</option>
                <option value="reviewer">Reviewer</option>
                <option value="manager">Manager</option>
                <option value="admin">Admin</option>
              </select>
            </div>
          </div>
          <div className="flex gap-3">
            <button
              type="submit"
              disabled={inviteMutation.isPending}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-purple-600
                         hover:bg-purple-700 text-white disabled:opacity-40 transition-colors"
            >
              {inviteMutation.isPending ? 'Inviting…' : 'Send Invite'}
            </button>
            <button
              type="button"
              onClick={() => { setShowInvite(false); reset() }}
              className="px-4 py-2 text-sm border rounded-lg border-gray-200
                         dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {members.length === 0 ? (
        <EmptyState title="No members yet" message="Invite your team to get started." />
      ) : (
        <div className="border border-gray-200 dark:border-gray-700 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 dark:bg-gray-800/60 text-left">
                <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-400">Name</th>
                <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-400">Email</th>
                <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-400">Role</th>
                <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-400">Status</th>
                {isAdmin && (
                  <th className="px-4 py-3 font-medium text-gray-600 dark:text-gray-400">
                    Actions
                  </th>
                )}
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
                  {isAdmin && (
                    <td className="px-4 py-3">
                      {m.id !== currentUserId && m.is_active && (
                        <button
                          onClick={() => setDeactivateTarget(m)}
                          className="flex items-center gap-1 text-xs text-red-500
                                     hover:text-red-700 dark:hover:text-red-400 transition-colors"
                          aria-label={`Deactivate ${m.full_name}`}
                        >
                          <UserX className="w-3.5 h-3.5" aria-hidden="true" />
                          Deactivate
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <ConfirmDialog
        open={!!deactivateTarget}
        title={`Deactivate ${deactivateTarget?.full_name}?`}
        message="This member will lose access to the workspace immediately. This action is recorded in the audit log."
        confirmLabel="Deactivate"
        onConfirm={() => deactivateTarget && deactivateMutation.mutate(deactivateTarget.id)}
        onCancel={() => setDeactivateTarget(null)}
      />
    </div>
  )
}

