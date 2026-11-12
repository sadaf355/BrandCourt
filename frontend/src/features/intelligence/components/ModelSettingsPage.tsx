import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Cpu,
  ShieldCheck,
  ToggleLeft,
  ToggleRight,
  Layers,
  Activity,
  CheckCircle2,
} from 'lucide-react'
import { apiClient } from '../../../lib/api'
import { useToast } from '../../../components/common/Toast'
import { Skeleton, ErrorState } from '../../../components/common/FeedbackStates'

export function ModelSettingsPage() {
  const { showToast } = useToast()
  const qc = useQueryClient()

  const { data: currentUser } = useQuery({
    queryKey: ['me'],
    queryFn: () => apiClient.getMe(),
  })

  const { data: settingsData, isLoading, isError, refetch } = useQuery({
    queryKey: ['model-settings'],
    queryFn: () => apiClient.getModelSettings(),
  })

  const updateModeMutation = useMutation({
    mutationFn: (enabled: boolean) => apiClient.updateModelSettings({ local_model_enabled: enabled }),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ['model-settings'] })
      showToast(data.message, 'success')
    },
    onError: (err: Error) => showToast(err.message, 'error'),
  })

  if (isLoading) {
    return (
      <div className="page-container p-6 space-y-4">
        <Skeleton height="36px" width="280px" />
        <Skeleton height="140px" />
        <Skeleton height="240px" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="page-container p-6">
        <ErrorState
          title="Could not load model settings"
          message="Failed to retrieve AI model configurations and data-flow logs."
          onRetry={() => refetch()}
        />
      </div>
    )
  }

  const isAdmin = currentUser?.role === 'admin'
  const isLocalEnabled = settingsData?.local_model_enabled ?? false

  const handleToggle = () => {
    if (!isAdmin) {
      showToast('Only workspace administrators can change model infrastructure settings.', 'error')
      return
    }
    updateModeMutation.mutate(!isLocalEnabled)
  }

  return (
    <div className="page-container p-6 space-y-6" data-testid="model-settings-page">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-gray-900 dark:text-white flex items-center gap-2">
          <Cpu style={{ color: 'var(--accent, #0f766e)' }} size={26} />
          Model Architecture & Privacy Controls
        </h1>
        <p className="text-sm text-slate-400">
          Manage workspace model mode, review configured pipeline stages, and inspect audited data-flow metadata.
        </p>
      </div>

      {/* Admin Local Model Switch Card */}
      <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <h2 className="text-base font-semibold text-gray-900 dark:text-white">Local-Only Model Execution Mode</h2>
            <span
              className={`px-2 py-0.5 rounded-full text-xs font-semibold ${
                isLocalEnabled ? 'bg-emerald-500/10 text-emerald-400' : 'bg-slate-800 text-slate-300'
              }`}
            >
              {isLocalEnabled ? 'Ollama enabled' : 'Deterministic mode'}
            </span>
          </div>
          <p className="text-xs text-slate-400 max-w-xl">
            When enabled, BrandCourt uses the configured Ollama service for masked ambiguity analysis and embeddings.
            Whether requests remain inside your network depends on where that Ollama service is hosted.
          </p>
        </div>

        <button
          onClick={handleToggle}
          disabled={updateModeMutation.isPending}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-semibold transition-colors ${
            !isAdmin ? 'opacity-50 cursor-not-allowed bg-slate-800 text-slate-300' : 'bg-indigo-600 hover:bg-indigo-500 text-white'
          }`}
          title={!isAdmin ? 'Admin role required' : 'Toggle local execution'}
        >
          {isLocalEnabled ? <ToggleRight size={20} /> : <ToggleLeft size={20} />}
          <span>{isLocalEnabled ? 'Disable Local Mode' : 'Enable Local Mode'}</span>
        </button>
      </div>

      {/* Privacy Guarantee & Masking Policy */}
      <div className="p-4 rounded-xl border border-indigo-500/20 bg-indigo-500/5 flex items-start gap-3 text-xs text-indigo-300">
        <ShieldCheck size={18} className="text-indigo-400 shrink-0 mt-0.5" />
        <div className="space-y-1">
          <span className="font-semibold text-gray-900 dark:text-white">Non-Negotiable Data Privacy Rule:</span>
          <p className="leading-relaxed">
            BrandCourt masks configured secret terms and detected personal information before optional model calls.
            Model/service call metadata is recorded in the <code className="text-indigo-300">ai_calls</code> log.
            Review the masking policy and hosting location before enabling a model provider.
          </p>
        </div>
      </div>

      {/* Active Models Table */}
      <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 space-y-4">
        <h2 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <Layers size={16} className="text-indigo-400" />
          Active Model Services Pipeline
        </h2>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400">
                <th className="py-2.5 px-3">Service / Engine</th>
                <th className="py-2.5 px-3">Provider</th>
                <th className="py-2.5 px-3">Pipeline Role & Purpose</th>
                <th className="py-2.5 px-3">Hosting</th>
                <th className="py-2.5 px-3 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {settingsData?.active_models.map((m, idx) => (
                <tr key={idx} className="hover:bg-slate-800/30">
                  <td className="py-3 px-3 font-semibold text-gray-900 dark:text-white">{m.name}</td>
                  <td className="py-3 px-3 font-mono text-slate-400">{m.provider}</td>
                  <td className="py-3 px-3 text-slate-300">{m.purpose}</td>
                  <td className="py-3 px-3">
                    <span className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800 text-slate-300">
                      {m.is_local ? 'Local / Edge' : 'Managed Cloud'}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[11px] font-semibold uppercase ${
                        m.status === 'active'
                          ? 'bg-emerald-500/10 text-emerald-400'
                          : (m.status === 'ready' || m.status === 'configured')
                          ? 'bg-blue-500/10 text-blue-400'
                          : 'bg-slate-800 text-slate-300'
                      }`}
                    >
                      {m.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Per-Item Data-Flow Audit Log */}
      <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Activity size={16} style={{ color: 'var(--accent, #0f766e)' }} />
            Model / Service Data-Flow Log (Last 20 Invocations)
          </h2>
          <span className="text-xs text-slate-400 font-mono">Table: ai_calls</span>
        </div>

        <div className="overflow-x-auto" style={{ overflowX: 'auto', maxWidth: '100%' }}>
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-medium">
                <th className="py-2.5 px-3">Call ID</th>
                <th className="py-2.5 px-3">Model</th>
                <th className="py-2.5 px-3">Purpose</th>
                <th className="py-2.5 px-3">Chars Sent</th>
                <th className="py-2.5 px-3">Entities Masked</th>
                <th className="py-2.5 px-3">Masking Status</th>
                <th className="py-2.5 px-3 text-right">Duration</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {settingsData?.data_flow_log.map((log) => (
                <tr key={log.id} className="hover:bg-slate-800/30">
                  <td className="py-3 px-3 font-mono text-slate-400">{log.id}</td>
                  <td className="py-3 px-3 font-medium text-gray-900 dark:text-white">{log.model}</td>
                  <td className="py-3 px-3 text-slate-300">{log.purpose}</td>
                  <td className="py-3 px-3 font-mono">{log.input_chars}</td>
                  <td className="py-3 px-3 font-mono">{log.masked_entities}</td>
                  <td className="py-3 px-3">
                    <span className="inline-flex items-center gap-1 text-[11px] text-emerald-400">
                      <CheckCircle2 size={12} /> Pre-masked
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right font-mono text-slate-400">
                    {log.duration_ms != null ? `${log.duration_ms} ms` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
