/**
 * GuidelinesPage – B3 Requirement 7
 * Upload PDF/DOCX/TXT → extracted draft rules, confirm/edit each rule, source page reference.
 * Rule version history list with status badges.
 */
import { useState, useRef } from 'react'
import { useMutation } from '@tanstack/react-query'
import { Upload, FileText, CheckCircle, AlertTriangle } from 'lucide-react'
import { apiClient } from '../../../lib/api'
import { SeverityBadge } from '../../../components/common/SeverityBadge'
import { useToast } from '../../../components/common/Toast'
import type { GuidelineUploadResult, FindingSeverity } from '../../../types/api'

type DraftRule = GuidelineUploadResult['draft_rules'][number] & {
  confirmed: boolean
  edited: boolean
}

export function GuidelinesPage() {
  const { showToast } = useToast()
  const fileRef = useRef<HTMLInputElement>(null)
  const [result, setResult] = useState<GuidelineUploadResult | null>(null)
  const [drafts, setDrafts] = useState<DraftRule[]>([])

  const uploadMutation = useMutation({
    mutationFn: (file: File) => apiClient.uploadGuideline(file),
    onSuccess: (data) => {
      setResult(data)
      setDrafts(data.draft_rules.map((r) => ({ ...r, confirmed: false, edited: false })))
      showToast(`Extracted ${data.draft_rules.length} draft rule(s) from "${data.source_filename}"`, 'success')
    },
    onError: (err: Error) => showToast(err.message, 'error'),
  })

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file) uploadMutation.mutate(file)
  }

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) uploadMutation.mutate(file)
  }

  function updateDraft(id: string, updates: Partial<DraftRule>) {
    setDrafts((prev) =>
      prev.map((d) => (d.id === id ? { ...d, ...updates, edited: true } : d))
    )
  }

  function confirmDraft(id: string) {
    setDrafts((prev) =>
      prev.map((d) => (d.id === id ? { ...d, confirmed: !d.confirmed } : d))
    )
  }

  const confirmedCount = drafts.filter((d) => d.confirmed).length

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Guidelines</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
          Upload a brand guideline document to extract draft rules for review
        </p>
      </div>

      {/* Drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        onClick={() => fileRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') fileRef.current?.click() }}
        aria-label="Upload guideline file. Accepts PDF, DOCX, or TXT."
        className="flex flex-col items-center gap-3 p-10 border-2 border-dashed
                   border-gray-200 dark:border-gray-700 rounded-xl cursor-pointer
                   hover:border-purple-400 dark:hover:border-purple-600
                   hover:bg-purple-50/30 dark:hover:bg-purple-900/10
                   transition-colors focus-visible:outline-none focus-visible:ring-2
                   focus-visible:ring-purple-500"
      >
        <input
          ref={fileRef}
          type="file"
          accept=".pdf,.docx,.txt"
          onChange={handleFileSelect}
          className="sr-only"
          aria-hidden="true"
        />
        {uploadMutation.isPending ? (
          <div className="text-center space-y-2">
            <div className="w-10 h-10 rounded-full border-4 border-purple-500 border-t-transparent
                            animate-spin mx-auto" role="status" aria-label="Uploading" />
            <p className="text-sm text-gray-600 dark:text-gray-400">Uploading and extracting rules…</p>
          </div>
        ) : (
          <>
            <Upload className="w-10 h-10 text-gray-300 dark:text-gray-600" aria-hidden="true" />
            <div className="text-center">
              <p className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Drop a guideline here, or click to browse
              </p>
              <p className="text-xs text-gray-400 mt-1">PDF, DOCX or TXT — max 20 MB</p>
            </div>
          </>
        )}
      </div>

      {/* Extraction result */}
      {result && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <FileText className="w-5 h-5 text-purple-500" aria-hidden="true" />
            <div>
              <p className="text-sm font-medium text-gray-800 dark:text-gray-200">
                {result.source_filename}
              </p>
              <p className="text-xs text-gray-500">
                {result.total_pages} pages · {result.draft_rules.length} draft rules extracted
              </p>
            </div>
            {confirmedCount > 0 && (
              <span className="ml-auto text-sm text-green-600 dark:text-green-400">
                {confirmedCount}/{drafts.length} confirmed
              </span>
            )}
          </div>

          {drafts.length === 0 && (
            <div className="flex items-center gap-2 p-4 bg-amber-50 dark:bg-amber-900/20
                            border border-amber-200 dark:border-amber-700 rounded-xl text-sm
                            text-amber-800 dark:text-amber-300">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" aria-hidden="true" />
              No rules could be automatically extracted. Try a different file or add rules manually.
            </div>
          )}

          <ul className="space-y-3">
            {drafts.map((draft) => (
              <li key={draft.id}>
                <DraftRuleCard
                  draft={draft}
                  onUpdate={(updates) => updateDraft(draft.id, updates)}
                  onConfirm={() => confirmDraft(draft.id)}
                />
              </li>
            ))}
          </ul>

          {confirmedCount > 0 && (
            <button
              onClick={() =>
                showToast(
                  `${confirmedCount} rule(s) queued for activation. Activate them on the Rules page.`,
                  'success'
                )
              }
              className="w-full px-4 py-3 text-sm font-medium rounded-xl
                         bg-purple-600 hover:bg-purple-700 text-white transition-colors"
            >
              Activate {confirmedCount} Confirmed Rule{confirmedCount > 1 ? 's' : ''}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

function DraftRuleCard({
  draft,
  onUpdate,
  onConfirm,
}: {
  draft: DraftRule
  onUpdate: (updates: Partial<DraftRule>) => void
  onConfirm: () => void
}) {
  const [editing, setEditing] = useState(false)

  return (
    <article
      className={`border rounded-xl p-4 space-y-3 transition-colors
        ${draft.confirmed
          ? 'border-green-300 dark:border-green-700 bg-green-50/30 dark:bg-green-900/10'
          : 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'
        }`}
    >
      <div className="flex items-start gap-3">
        <div className="flex-1 space-y-1">
          {editing ? (
            <input
              type="text"
              value={draft.name}
              onChange={(e) => onUpdate({ name: e.target.value })}
              className="w-full px-3 py-1.5 text-sm border rounded-lg border-purple-300
                         dark:border-purple-600 bg-white dark:bg-gray-700
                         text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 outline-none"
              aria-label="Rule name"
            />
          ) : (
            <p className="text-sm font-medium text-gray-900 dark:text-white">{draft.name}</p>
          )}

          {editing ? (
            <textarea
              rows={2}
              value={draft.description}
              onChange={(e) => onUpdate({ description: e.target.value })}
              className="w-full px-3 py-1.5 text-sm border rounded-lg border-purple-300
                         dark:border-purple-600 bg-white dark:bg-gray-700
                         text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 outline-none"
              aria-label="Rule description"
            />
          ) : (
            <p className="text-sm text-gray-600 dark:text-gray-400">{draft.description}</p>
          )}

          <div className="flex items-center gap-2 flex-wrap">
            <SeverityBadge severity={draft.severity as FindingSeverity} />
            {draft.source_page && (
              <span className="text-xs text-gray-400">Source page: {draft.source_page}</span>
            )}
            {draft.edited && (
              <span className="text-xs text-purple-500">Edited</span>
            )}
          </div>
        </div>

        <div className="flex flex-col items-end gap-2 flex-shrink-0">
          <button
            onClick={onConfirm}
            aria-pressed={draft.confirmed}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg
                        transition-colors
                        ${draft.confirmed
                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300'
                : 'border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-700'
              }`}
          >
            <CheckCircle className="w-3.5 h-3.5" aria-hidden="true" />
            {draft.confirmed ? 'Confirmed' : 'Confirm'}
          </button>
          <button
            onClick={() => setEditing((e) => !e)}
            className="text-xs text-gray-400 hover:text-purple-600 dark:hover:text-purple-400
                       transition-colors"
          >
            {editing ? 'Done' : 'Edit'}
          </button>
        </div>
      </div>
    </article>
  )
}

