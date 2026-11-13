/**
 * FactsPage – B3 Requirement 7
 * Facts with validity window, expiry warnings (highlighted within 30 days),
 * version history per fact, add fact form with validity dates.
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { AlertTriangle, Plus, CheckCircle, Clock } from 'lucide-react'
import { apiClient } from '../../../lib/api'
import { EmptyState, ErrorState } from '../../../components/common/FeedbackStates'
import { useToast } from '../../../components/common/Toast'
import type { FactWithHistory } from '../../../types/api'

type FactFormValues = {
  statement: string
  claim_value?: string
  unit?: string
  source_reference: string
  valid_from?: string
  valid_until?: string
}

export function FactsPage() {
  const qc = useQueryClient()
  const { showToast } = useToast()
  const [showForm, setShowForm] = useState(false)

  const { data: facts = [], isLoading, isError, refetch } = useQuery({
    queryKey: ['facts'],
    queryFn: () => apiClient.listFacts(),
  })

  const { register, handleSubmit, reset, formState: { errors } } = useForm<FactFormValues>()

  const createMutation = useMutation({
    mutationFn: (data: FactFormValues) => apiClient.createFact(data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['facts'] })
      setShowForm(false)
      reset()
      showToast('Fact added.', 'success')
    },
    onError: (err: Error) => showToast(err.message, 'error'),
  })

  if (isLoading) {
    return (
      <div className="p-8 space-y-3" role="status" aria-label="Loading facts">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-16 rounded-lg bg-gray-100 dark:bg-gray-800 animate-pulse" />
        ))}
      </div>
    )
  }

  if (isError) {
    return <ErrorState title="Could not load facts" action={{ label: 'Retry', onClick: () => refetch() }} />
  }

  const expiring = facts.filter((f) => f.expiry_warning)

  return (
    <div className="page-container" data-testid="facts-page">
      <div className="page-header--row">
        <div>
          <h1 className="page-header__title">Approved Facts</h1>
          <p className="page-header__subtitle">
            {facts.length} fact{facts.length !== 1 ? 's' : ''} in workspace
          </p>
        </div>
        <button
          onClick={() => setShowForm((s) => !s)}
          className="btn btn--primary"
        >
          <Plus size={16} aria-hidden="true" />
          Add Fact
        </button>
      </div>

      {/* Expiry warnings */}
      {expiring.length > 0 && (
        <div className="p-4 bg-amber-50 dark:bg-amber-900/20 border border-amber-200
                        dark:border-amber-700 rounded-xl space-y-2">
          <div className="flex items-center gap-2 text-amber-800 dark:text-amber-300">
            <AlertTriangle className="w-5 h-5" aria-hidden="true" />
            <strong className="text-sm">
              {expiring.length} fact{expiring.length > 1 ? 's' : ''} expiring within 30 days
            </strong>
          </div>
          <ul className="space-y-1">
            {expiring.map((f) => (
              <li key={f.id} className="text-sm text-amber-700 dark:text-amber-400">
                "{f.statement.substring(0, 60)}…" — expires {f.valid_until}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Add fact form */}
      {showForm && (
        <form
          onSubmit={handleSubmit((data) => createMutation.mutate(data))}
          className="p-5 bg-white dark:bg-gray-800 border border-purple-200
                     dark:border-purple-700 rounded-xl space-y-4"
          aria-label="Add new fact"
        >
          <h2 className="font-semibold text-gray-800 dark:text-gray-200">New Fact</h2>

          <div className="space-y-1">
            <label htmlFor="fact-statement" className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Statement <span className="text-red-500" aria-hidden="true">*</span>
            </label>
            <textarea
              id="fact-statement"
              rows={2}
              {...register('statement', { required: 'Required' })}
              className="w-full px-3 py-2 text-sm border rounded-lg border-gray-200
                         dark:border-gray-600 bg-white dark:bg-gray-700
                         text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 outline-none"
            />
            {errors.statement && (
              <p className="text-xs text-red-500" role="alert">{errors.statement.message}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label htmlFor="fact-claim-value" className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Claim value
              </label>
              <input
                id="fact-claim-value"
                type="text"
                placeholder="e.g. 42%"
                {...register('claim_value')}
                className="w-full px-3 py-2 text-sm border rounded-lg border-gray-200
                           dark:border-gray-600 bg-white dark:bg-gray-700
                           text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 outline-none"
              />
            </div>
            <div className="space-y-1">
              <label htmlFor="fact-unit" className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Unit
              </label>
              <input
                id="fact-unit"
                type="text"
                placeholder="e.g. reduction"
                {...register('unit')}
                className="w-full px-3 py-2 text-sm border rounded-lg border-gray-200
                           dark:border-gray-600 bg-white dark:bg-gray-700
                           text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 outline-none"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label htmlFor="fact-source" className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Source reference <span className="text-red-500" aria-hidden="true">*</span>
            </label>
            <input
              id="fact-source"
              type="text"
              placeholder="e.g. Clinical Study Report 2025-08"
              {...register('source_reference', { required: 'Required' })}
              className="w-full px-3 py-2 text-sm border rounded-lg border-gray-200
                         dark:border-gray-600 bg-white dark:bg-gray-700
                         text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 outline-none"
            />
            {errors.source_reference && (
              <p className="text-xs text-red-500" role="alert">{errors.source_reference.message}</p>
            )}
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-1">
              <label htmlFor="fact-valid-from" className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Valid from
              </label>
              <input
                id="fact-valid-from"
                type="date"
                {...register('valid_from')}
                className="w-full px-3 py-2 text-sm border rounded-lg border-gray-200
                           dark:border-gray-600 bg-white dark:bg-gray-700
                           text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 outline-none"
              />
            </div>
            <div className="space-y-1">
              <label htmlFor="fact-valid-until" className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Valid until
              </label>
              <input
                id="fact-valid-until"
                type="date"
                {...register('valid_until')}
                className="w-full px-3 py-2 text-sm border rounded-lg border-gray-200
                           dark:border-gray-600 bg-white dark:bg-gray-700
                           text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 outline-none"
              />
            </div>
          </div>

          <div className="flex gap-3">
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-purple-600
                         hover:bg-purple-700 text-white disabled:opacity-40 transition-colors"
            >
              {createMutation.isPending ? 'Saving…' : 'Save Fact'}
            </button>
            <button
              type="button"
              onClick={() => { setShowForm(false); reset() }}
              className="px-4 py-2 text-sm border rounded-lg border-gray-200
                         dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-700
                         transition-colors"
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {facts.length === 0 ? (
        <EmptyState
          title="No approved facts yet"
          message="Add facts with source references to enable claim verification."
        />
      ) : (
        <div className="space-y-3">
          {facts.map((fact) => <FactCard key={fact.id} fact={fact} />)}
        </div>
      )}
    </div>
  )
}

function FactCard({ fact }: { fact: FactWithHistory }) {
  const isExpired = fact.valid_until ? new Date(fact.valid_until) < new Date() : false
  const isExpiring = fact.expiry_warning && !isExpired

  return (
    <article
      className={`p-4 border rounded-xl bg-white dark:bg-gray-800 space-y-2
        ${isExpiring
          ? 'border-amber-300 dark:border-amber-700'
          : isExpired
          ? 'border-red-200 dark:border-red-700 opacity-70'
          : 'border-gray-200 dark:border-gray-700'
        }`}
    >
      <div className="flex items-start gap-3">
        <div className="flex-1">
          <p className="text-sm font-medium text-gray-900 dark:text-white">{fact.statement}</p>
          {fact.claim_value && (
            <p className="text-xs text-purple-600 dark:text-purple-400 mt-0.5">
              {fact.claim_value}{fact.unit ? ` ${fact.unit}` : ''}
            </p>
          )}
          <p className="text-xs text-gray-400 mt-1">{fact.source_reference}</p>
        </div>
        <div className="flex flex-col items-end gap-1">
          {isExpiring && (
            <span className="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
              <AlertTriangle className="w-3.5 h-3.5" aria-hidden="true" />
              Expiring soon
            </span>
          )}
          {isExpired && (
            <span className="flex items-center gap-1 text-xs text-red-500 dark:text-red-400">
              <Clock className="w-3.5 h-3.5" aria-hidden="true" />
              Expired
            </span>
          )}
          {!isExpired && !isExpiring && (
            <span className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
              <CheckCircle className="w-3.5 h-3.5" aria-hidden="true" />
              Active
            </span>
          )}
          <span className="text-xs text-gray-400">v{fact.version}</span>
        </div>
      </div>

      {(fact.valid_from || fact.valid_until) && (
        <div className="flex gap-4 text-xs text-gray-400">
          {fact.valid_from && <span>From: {fact.valid_from}</span>}
          {fact.valid_until && <span>Until: {fact.valid_until}</span>}
          <span className="text-gray-300 dark:text-gray-600">ID: {fact.id}</span>
        </div>
      )}
    </article>
  )
}

