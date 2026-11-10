/**
 * AssetsPage – B3 Requirement 7
 * Logo upload, palette JSON, fonts, term lists, secret term list (masked before model calls).
 */
import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Eye, EyeOff, Save, Upload } from 'lucide-react'
import { apiClient } from '../../../lib/api'
import { ErrorState } from '../../../components/common/FeedbackStates'
import { useToast } from '../../../components/common/Toast'

export function AssetsPage() {
  const qc = useQueryClient()
  const { showToast } = useToast()

  const { data: assets = [], isLoading, isError, refetch } = useQuery({
    queryKey: ['assets'],
    queryFn: () => apiClient.listAssets(),
  })

  const upsertMutation = useMutation({
    mutationFn: (args: { name: string; type: string; json: unknown }) =>
      apiClient.upsertAsset(args.name, args.type, args.json),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assets'] })
      showToast('Asset saved.', 'success')
    },
    onError: (err: Error) => showToast(err.message, 'error'),
  })

  const logoMutation = useMutation({
    mutationFn: (file: File) => {
      const baseName = file.name.replace(/\.[^.]+$/, '').trim()
      const assetName = baseName.length >= 2 ? baseName.slice(0, 120) : 'Brand Logo'
      return apiClient.uploadLogoAsset(assetName, file)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['assets'] })
      showToast('Logo uploaded.', 'success')
    },
    onError: (err: Error) => showToast(err.message, 'error'),
  })

  function handleLogoSelect(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) logoMutation.mutate(file)
    e.target.value = ''
  }

  if (isLoading) {
    return (
      <div className="p-8 space-y-3" role="status" aria-label="Loading assets">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="h-20 rounded-xl bg-gray-100 dark:bg-gray-800 animate-pulse" />
        ))}
      </div>
    )
  }

  if (isError) {
    return <ErrorState title="Could not load assets" action={{ label: 'Retry', onClick: () => refetch() }} />
  }

  const palette = assets.find((a) => a.asset_type === 'palette')
  const secretTerms = assets.find((a) => a.asset_type === 'secret_terms')
  const logos = assets.filter((a) => a.asset_type === 'logo')

  return (
    <div className="p-6 max-w-4xl mx-auto space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Brand Assets</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
          Manage logos, palette, fonts and term lists
        </p>
      </div>

      {/* Colour Palette */}
      <section aria-label="Colour palette" className="space-y-4">
        <h2 className="text-base font-semibold text-gray-800 dark:text-gray-200">Colour Palette</h2>
        <PaletteEditor
          initial={palette?.content_json ?? {}}
          onSave={(json) => upsertMutation.mutate({ name: 'Primary Palette', type: 'palette', json })}
          isPending={upsertMutation.isPending}
        />
      </section>

      {/* Secret Term List */}
      <section aria-label="Secret term list" className="space-y-4">
        <div>
          <h2 className="text-base font-semibold text-gray-800 dark:text-gray-200">
            Secret Term List
          </h2>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
            Terms masked before any AI model call. Never sent to external services in plain text.
          </p>
        </div>
        <SecretTermEditor
          initial={secretTerms?.content_json?.terms ?? []}
          onSave={(terms) =>
            upsertMutation.mutate({ name: 'Secret Term List', type: 'secret_terms', json: { terms } })
          }
          isPending={upsertMutation.isPending}
        />
      </section>

      {/* Logo upload */}
      <section aria-label="Logo" className="space-y-4">
        <h2 className="text-base font-semibold text-gray-800 dark:text-gray-200">Logo</h2>
        <div
          onDrop={(e) => {
            e.preventDefault()
            const file = e.dataTransfer.files[0]
            if (file) logoMutation.mutate(file)
          }}
          onDragOver={(e) => e.preventDefault()}
          className="flex items-center gap-4 p-4 border-2 border-dashed
                     border-gray-200 dark:border-gray-700 rounded-xl"
        >
          <Upload className="w-8 h-8 text-gray-300 dark:text-gray-600" aria-hidden="true" />
          <div>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Drag and drop a logo PNG/JPG/WEBP, or{' '}
              <label className="text-purple-600 dark:text-purple-400 cursor-pointer underline">
                browse
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/gif"
                  onChange={handleLogoSelect}
                  disabled={logoMutation.isPending}
                  className="sr-only"
                  aria-label="Upload logo"
                />
              </label>
            </p>
            <p className="text-xs text-gray-400 mt-1">
              {logoMutation.isPending ? 'Uploading logo…' : 'PNG, JPG, WEBP or GIF, max 10 MB'}
            </p>
          </div>
        </div>
        {logos.length > 0 && (
          <ul className="space-y-2">
            {logos.map((logo) => (
              <li
                key={logo.id}
                className="flex items-center justify-between text-sm px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800"
              >
                <span className="font-medium text-gray-800 dark:text-gray-200">{logo.name}</span>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {logo.content_json?.width && logo.content_json?.height
                    ? `${logo.content_json.width}×${logo.content_json.height}`
                    : 'Logo registered'}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}

function PaletteEditor({
  initial,
  onSave,
  isPending,
}: {
  initial: Record<string, string>
  onSave: (json: Record<string, string>) => void
  isPending: boolean
}) {
  const [json, setJson] = useState(JSON.stringify(initial, null, 2))
  const [parseError, setParseError] = useState('')

  function handleSave() {
    try {
      const parsed = JSON.parse(json)
      setParseError('')
      onSave(parsed)
    } catch {
      setParseError('Invalid JSON — please fix before saving.')
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex gap-3 flex-wrap">
        {Object.entries(initial).map(([key, value]) => (
          <div key={key} className="flex items-center gap-2">
            <span
              className="w-6 h-6 rounded-full border border-gray-200 dark:border-gray-600"
              style={{ background: value }}
              aria-hidden="true"
            />
            <span className="text-xs text-gray-600 dark:text-gray-400">
              {key}: {value}
            </span>
          </div>
        ))}
      </div>
      <label htmlFor="palette-json" className="sr-only">Palette JSON</label>
      <textarea
        id="palette-json"
        rows={5}
        value={json}
        onChange={(e) => setJson(e.target.value)}
        spellCheck={false}
        className="w-full font-mono text-sm px-3 py-2 border rounded-lg
                   border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800
                   text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 outline-none"
        aria-describedby={parseError ? 'palette-error' : undefined}
      />
      {parseError && (
        <p id="palette-error" className="text-xs text-red-500" role="alert">{parseError}</p>
      )}
      <button
        onClick={handleSave}
        disabled={isPending}
        className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg
                   bg-purple-600 hover:bg-purple-700 text-white disabled:opacity-40 transition-colors"
      >
        <Save className="w-4 h-4" aria-hidden="true" />
        {isPending ? 'Saving…' : 'Save Palette'}
      </button>
    </div>
  )
}

function SecretTermEditor({
  initial,
  onSave,
  isPending,
}: {
  initial: string[]
  onSave: (terms: string[]) => void
  isPending: boolean
}) {
  const [terms, setTerms] = useState<string[]>(initial)
  const [revealed, setRevealed] = useState(false)
  const [newTerm, setNewTerm] = useState('')

  function addTerm() {
    const t = newTerm.trim()
    if (!t || terms.includes(t)) return
    setTerms([...terms, t])
    setNewTerm('')
  }

  function removeTerm(term: string) {
    setTerms(terms.filter((t) => t !== term))
  }

  return (
    <div className="space-y-3 p-4 border border-amber-200 dark:border-amber-700 rounded-xl
                    bg-amber-50/40 dark:bg-amber-900/10">
      <div className="flex items-center justify-between">
        <p className="text-xs text-amber-700 dark:text-amber-400">
          🔒 These terms are masked with tokens before any model call. Shown here only for
          authorised guideline owners.
        </p>
        <button
          onClick={() => setRevealed((r) => !r)}
          aria-label={revealed ? 'Hide secret terms' : 'Reveal secret terms'}
          className="text-xs flex items-center gap-1 text-gray-700 dark:text-gray-300 transition-colors"
        >
          {revealed ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
          {revealed ? 'Hide' : 'Reveal'}
        </button>
      </div>

      <ul className="flex flex-wrap gap-2">
        {terms.map((t) => (
          <li key={t}>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-full
                             bg-white dark:bg-gray-800 border border-amber-300 dark:border-amber-700
                             text-gray-800 dark:text-gray-200">
              {revealed ? t : '•'.repeat(Math.min(t.length, 8))}
              <button
                onClick={() => removeTerm(t)}
                aria-label={`Remove term ${revealed ? t : '(hidden)'}`}
                className="text-gray-400 hover:text-red-500 transition-colors"
              >
                ×
              </button>
            </span>
          </li>
        ))}
      </ul>

      <div className="flex gap-2">
        <input
          type="text"
          value={newTerm}
          onChange={(e) => setNewTerm(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addTerm() } }}
          placeholder="Add a secret term…"
          aria-label="New secret term"
          className="flex-1 px-3 py-1.5 text-sm border rounded-lg border-gray-200
                     dark:border-gray-600 bg-white dark:bg-gray-700
                     text-gray-900 dark:text-white focus:ring-2 focus:ring-purple-500 outline-none"
        />
        <button
          onClick={addTerm}
          className="px-3 py-1.5 text-sm border rounded-lg border-gray-200
                     dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
        >
          Add
        </button>
      </div>

      <button
        onClick={() => onSave(terms)}
        disabled={isPending}
        className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg
                   bg-purple-600 hover:bg-purple-700 text-white disabled:opacity-40 transition-colors"
      >
        <Save className="w-4 h-4" aria-hidden="true" />
        {isPending ? 'Saving…' : 'Save Secret Terms'}
      </button>
    </div>
  )
}

