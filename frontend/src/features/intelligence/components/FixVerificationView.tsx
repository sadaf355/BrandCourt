import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import {
  Sparkles,
  ShieldCheck,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Info,
} from 'lucide-react'
import { apiClient } from '../../../lib/api'
import { useToast } from '../../../components/common/Toast'

export function FixVerificationView() {
  const { showToast } = useToast()
  const [contentId, setContentId] = useState('cnt-glowserum-1')
  const [candidateText, setCandidateText] = useState(
    "Experience radiant skin with our GlowSerum! Formulated with saffron extracts to help visibly improve dark spots. Dermatologist tested. Link in bio."
  )
  const [verificationResult, setVerificationResult] = useState<any>(null)

  const verifyMutation = useMutation({
    mutationFn: () => apiClient.verifyFix(contentId, candidateText),
    onSuccess: (data) => {
      setVerificationResult(data)
      if (data.safe_to_suggest) {
        showToast('Fix verified: Safe and preserves marketing intent.', 'success')
      } else {
        showToast('Verification warning: New regulatory blockers detected.', 'error')
      }
    },
    onError: (err: Error) => showToast(err.message, 'error'),
  })

  return (
    <div className="page-container p-6 space-y-6" data-testid="fix-verification-view">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
          <Sparkles className="text-indigo-400" size={26} />
          Fix Verification & Intent Sandbox
        </h1>
        <p className="text-sm text-slate-400">
          Test candidate copy edits in an isolated sandbox against the Claim Court engine before applying them.
        </p>
      </div>

      {/* Advisory Banner */}
      <div className="p-4 rounded-xl border border-indigo-500/20 bg-indigo-500/5 flex items-start gap-3 text-xs text-indigo-300">
        <Info size={16} className="text-indigo-400 mt-0.5 shrink-0" />
        <div>
          <span className="font-semibold text-white">Full Engine Rollback Evaluation:</span> Testing a fix spins up a temporary
          candidate revision in the Claim Court engine, evaluates all 3 intelligence layers (Rules, Claims, Tone), and
          rolls it back cleanly without mutating production revision history.
        </div>
      </div>

      {/* Input Form */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 space-y-4">
          <h2 className="text-sm font-semibold text-white">Candidate Proposed Copy</h2>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Target Content Item ID</label>
            <input
              type="text"
              value={contentId}
              onChange={(e) => setContentId(e.target.value)}
              className="w-full text-xs bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Proposed Caption Text</label>
            <textarea
              value={candidateText}
              onChange={(e) => setCandidateText(e.target.value)}
              rows={6}
              className="w-full text-xs bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-white focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>

          <button
            onClick={() => verifyMutation.mutate()}
            disabled={!candidateText.trim() || verifyMutation.isPending}
            className="w-full py-2.5 rounded-lg text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
          >
            <Sparkles size={14} />
            {verifyMutation.isPending ? 'Simulating Engine Check...' : 'Verify Candidate Copy'}
          </button>
        </div>

        {/* Results Panel */}
        <div className="p-5 rounded-xl border border-slate-800 bg-slate-900/60 space-y-4">
          <h2 className="text-sm font-semibold text-white">Verification Engine Verdict</h2>

          {!verificationResult ? (
            <div className="h-64 flex flex-col items-center justify-center text-center p-6 text-slate-500 border border-dashed border-slate-800 rounded-lg">
              <HelpCircle size={32} className="mb-2 text-slate-600" />
              <p className="text-xs">Enter candidate copy and click "Verify Candidate Copy" to run full engine analysis.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Intent Preserved Card */}
              <div
                className={`p-4 rounded-xl border flex items-center justify-between gap-3 ${
                  verificationResult.safe_to_suggest
                    ? 'border-emerald-500/30 bg-emerald-500/10'
                    : 'border-red-500/30 bg-red-500/10'
                }`}
              >
                <div className="flex items-center gap-3">
                  {verificationResult.safe_to_suggest ? (
                    <ShieldCheck size={28} className="text-emerald-400" />
                  ) : (
                    <ShieldAlert size={28} className="text-red-400" />
                  )}
                  <div>
                    <h3 className="text-sm font-bold text-white">
                      {verificationResult.safe_to_suggest ? 'Safe to Suggest' : 'Unsafe: Blocker Detected'}
                    </h3>
                    <p className="text-xs text-slate-300">
                      {verificationResult.safe_to_suggest
                        ? 'Candidate resolves previous violations without introducing new errors.'
                        : 'Proposed fix introduces new regulatory or brand rule violations.'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Metrics Grid */}
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-lg border border-slate-800 bg-slate-900">
                  <span className="text-slate-400 block mb-1">Intent Preserved:</span>
                  <span className="font-semibold text-white flex items-center gap-1.5">
                    {verificationResult.intent_preserved ? (
                      <CheckCircle2 size={14} className="text-emerald-400" />
                    ) : (
                      <XCircle size={14} className="text-red-400" />
                    )}
                    {verificationResult.intent_preserved ? 'Preserved' : 'Altered'}
                  </span>
                </div>

                <div className="p-3 rounded-lg border border-slate-800 bg-slate-900">
                  <span className="text-slate-400 block mb-1">Call to Action:</span>
                  <span className="font-semibold text-white flex items-center gap-1.5">
                    {verificationResult.call_to_action_preserved ? (
                      <CheckCircle2 size={14} className="text-emerald-400" />
                    ) : (
                      <XCircle size={14} className="text-amber-400" />
                    )}
                    {verificationResult.call_to_action_preserved ? 'Retained' : 'Missing'}
                  </span>
                </div>
              </div>

              {/* Detected Blockers if any */}
              {verificationResult.new_blocking_findings && verificationResult.new_blocking_findings.length > 0 && (
                <div className="p-3 rounded-lg border border-red-500/30 bg-red-500/5 space-y-2">
                  <span className="text-xs font-semibold text-red-400 block">Identified Blockers:</span>
                  {verificationResult.new_blocking_findings.map((bf: any, i: number) => (
                    <div key={i} className="text-xs text-slate-300">
                      &bull; <strong className="text-red-300">{bf.claim_text}:</strong> {bf.rationale}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

