import { useState } from 'react'
import { apiClient } from '../../../lib/api'
import {
  Check,
  Edit2,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  Sparkles,
  History,
  Lock,
} from 'lucide-react'
import { ClaimFinding } from '../../../types/api'
import { SeverityBadge } from '../../../components/common/SeverityBadge'
import { StatusBadge } from '../../../components/common/StatusBadge'

interface FindingCardProps {
  finding: ClaimFinding
  isSelected?: boolean
  onSelect?: () => void
  onAccept?: () => void
  onEdit?: (suggestedText: string) => void
  onDispute?: (note: string) => void
  canDecide?: boolean
  actionBusy?: boolean
}

export function FindingCard({
  finding,
  isSelected = false,
  onSelect,
  onAccept,
  onEdit,
  onDispute,
  canDecide = true,
  actionBusy = false,
}: FindingCardProps) {
  const [showHistory, setShowHistory] = useState(false)
  const [disputeOpen, setDisputeOpen] = useState(false)
  const [disputeNote, setDisputeNote] = useState('')
  const [fixBusy, setFixBusy] = useState(false)
  const [fixResult, setFixResult] = useState<any>(null)
  const [precedents, setPrecedents] = useState<any[]>([])
  const [precedentBusy, setPrecedentBusy] = useState(false)
  const [precedentError, setPrecedentError] = useState('')

  const loadPrecedents = async () => {
    setPrecedentBusy(true); setPrecedentError('')
    try { const result = await apiClient.getPrecedentSuggestions(finding.id); setPrecedents(result.suggestions || []) }
    catch (error) { setPrecedentError(error instanceof Error ? error.message : 'Could not load precedents') }
    finally { setPrecedentBusy(false) }
  }
  const runSuggestFix = async () => {
    setFixBusy(true); setFixResult(null)
    try { setFixResult(await apiClient.suggestFindingFix(finding.id)) }
    catch (error) { setFixResult({ accepted: false, rejection_reason: error instanceof Error ? error.message : 'Verification failed' }) }
    finally { setFixBusy(false) }
  }

  const isSafeFix = finding.intent_preserved ? finding.intent_preserved.safe : true

  return (
    <div
      onClick={onSelect}
      className={`finding-card ${isSelected ? 'finding-card--selected' : ''}`}
      style={{
        borderRadius: '12px',
        border: isSelected
          ? '2px solid var(--accent, #0f766e)'
          : '1px solid var(--color-border, #e2e8f0)',
        backgroundColor: 'var(--color-bg-panel, #ffffff)',
        padding: '20px',
        marginBottom: '16px',
        cursor: 'pointer',
        transition: 'all 0.15s ease',
        boxShadow: isSelected ? '0 8px 24px -4px rgba(99, 102, 241, 0.25)' : 'none',
      }}
      data-testid="finding-card"
    >
      {/* Top Header: Verdict, Severity, State */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '8px',
          marginBottom: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <SeverityBadge severity={finding.severity} />
          <StatusBadge status={finding.state} />
        </div>
        {finding.confidence !== undefined && (
          <span style={{ fontSize: '12px', color: 'var(--color-text-muted, #94a3b8)' }}>
            Confidence: <strong>{Math.round(finding.confidence * 100)}%</strong>
          </span>
        )}
      </div>

      {/* Claim Span / Text */}
      <div style={{ marginBottom: '12px' }}>
        <span
          style={{
            fontSize: '12px',
            textTransform: 'uppercase',
            fontWeight: 700,
            color: 'var(--color-text-muted, #94a3b8)',
            letterSpacing: '0.05em',
          }}
        >
          Flagged span
        </span>
        <div
          style={{
            marginTop: '8px',
            padding: '12px',
            borderRadius: '8px',
            backgroundColor: 'var(--color-bg-subtle, rgba(0, 0, 0, 0.2))',
            borderLeft: `3px solid ${finding.severity === 'critical' ? 'var(--severity-critical-text, #be123c)' : finding.severity === 'major' ? 'var(--severity-major-text, #b45309)' : 'var(--accent, #0f766e)'
              }`,
            fontFamily: 'monospace',
            fontSize: '14px',
            color: 'var(--color-text-primary, #ffffff)',
          }}
        >
          "{finding.claim_text}"
        </div>
      </div>

      {/* Rationale */}
      <p style={{ fontSize: '14px', color: 'var(--color-text-secondary, #cbd5e1)', margin: '0 0 12px 0', lineHeight: 1.5 }}>
        {finding.rationale}
      </p>

      {/* Method & Rule citations */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
          flexWrap: 'wrap',
          fontSize: '12px',
          color: 'var(--color-text-muted, #94a3b8)',
          marginBottom: '16px',
        }}
      >
        <span>
          Method: <strong style={{ fontFamily: 'monospace' }}>{finding.analysis_method}</strong>
        </span>
        {finding.rule_id && (
          <span>
            Rule: <strong>{finding.rule_id}</strong> (v{finding.rule_version || 1})
          </span>
        )}
        {finding.layer && (
          <span
            style={{
              textTransform: 'capitalize',
              backgroundColor: 'var(--surface-muted, rgba(148, 163, 184, 0.1))',
              padding: '2px 8px',
              borderRadius: '999px',
            }}
          >
            Layer: {finding.layer}
          </span>
        )}
      </div>

      <div className="flex flex-wrap gap-2 mb-3" onClick={(e) => e.stopPropagation()}>
        <button type="button" onClick={runSuggestFix} disabled={fixBusy} className="btn btn--sm btn--primary">{fixBusy ? 'Verifying…' : 'Suggest fix'}</button>
        <button type="button" onClick={loadPrecedents} disabled={precedentBusy} className="btn btn--sm btn--secondary">{precedentBusy ? 'Finding precedents…' : 'Show precedent suggestions'}</button>
      </div>
      {fixResult && <div className="mb-3 p-3 rounded-lg border border-slate-700 bg-slate-800/70 text-xs" onClick={(e) => e.stopPropagation()}>
        <strong className={fixResult.accepted ? 'text-emerald-400' : 'text-amber-400'}>{fixResult.accepted ? 'Fix verified — safe to suggest' : 'Fix not approved'}</strong>
        {fixResult.suggested_fix && <p className="mt-2 text-slate-200">{fixResult.suggested_fix}</p>}
        {fixResult.accepted && fixResult.suggested_fix && onEdit && (
          <button
            type="button"
            disabled={actionBusy}
            onClick={() => onEdit(fixResult.suggested_fix)}
            className="mt-2 btn btn--sm btn--primary"
          >
            Apply suggested fix to draft
          </button>
        )}
        {fixResult.rejection_reason && <p className="mt-1 text-slate-400">{fixResult.rejection_reason}</p>}
        {fixResult.verification && <div className="mt-2 space-y-1 text-slate-400">
          <p>Intent preserved: <b>{fixResult.verification.intent_preserved ? 'Yes' : 'No'}</b> · Similarity: <b>{fixResult.verification.embedding_similarity ?? fixResult.verification.similarity ?? 'Not available'}</b></p>
          <p>Claims changed: <b>{(fixResult.verification.changed_claims || []).length}</b>{(fixResult.verification.changed_claims || []).length > 0 ? ` — ${(fixResult.verification.changed_claims || []).join('; ')}` : ' — none detected'}</p>
          <p>Call to action kept: <b>{fixResult.verification.call_to_action_preserved ? 'Yes' : 'No / not preserved'}</b></p>
          {(fixResult.verification.new_blocking_findings || []).length > 0 && <div role="alert" className="mt-2 rounded border border-rose-500/40 bg-rose-950/40 p-2 text-rose-200"><b>Rejected: a new Critical finding was raised.</b><ul className="mt-1 list-disc pl-5">{fixResult.verification.new_blocking_findings.map((item: any, index: number) => <li key={item.finding_id || index}>{item.claim_text}: {item.rationale}</li>)}</ul></div>}
        </div>}
      </div>}
      {precedentError && <p className="text-xs text-rose-400 mb-2">{precedentError}</p>}
      {precedents.length > 0 && <div className="mb-3 space-y-2" onClick={(e) => e.stopPropagation()}>{precedents.map((item) => <div key={item.precedent_id} className="p-3 rounded-lg border border-slate-700 bg-slate-800/60 text-xs">
        <p className="text-slate-100 font-medium">{item.pattern_text}</p><p className="text-slate-400 mt-1">{item.reason} · Similarity {Math.round(item.similarity * 100)}%</p>
        <p className="text-amber-300 mt-1">Reviewer confirmation required. Critical findings cannot be downgraded.</p>
        <button type="button" disabled={finding.severity === 'critical' || finding.state !== 'open'} onClick={async () => { try { await apiClient.confirmPrecedentSuggestion(finding.id, item.precedent_id); await loadPrecedents() } catch (error) { setPrecedentError(error instanceof Error ? error.message : 'Confirmation failed') } }} className="mt-2 btn btn--sm btn--primary">Reviewer confirm</button>
      </div>)}</div>}

      {/* Suggested Fix and Intent Preserved */}
      {finding.suggested_fix && (
        <div
          style={{
            padding: '12px',
            borderRadius: '8px',
            backgroundColor: isSafeFix ? 'var(--severity-success-bg, rgba(34, 197, 94, 0.05))' : 'var(--severity-critical-bg, rgba(239, 68, 68, 0.05))',
            border: `1px solid ${isSafeFix ? 'var(--severity-success-border, rgba(34, 197, 94, 0.25))' : 'var(--severity-critical-border, rgba(239, 68, 68, 0.25))'}`,
            marginBottom: '16px',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '8px',
            }}
          >
            <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 600, color: isSafeFix ? 'var(--severity-success-text, #15803d)' : 'var(--severity-critical-text, #be123c)' }}>
              <Sparkles size={13} />
              <span>Suggested Fix {isSafeFix ? '(Safe)' : '(Unsafe / Blocks auto-accept)'}</span>
            </div>
            {onEdit && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation()
                  onEdit(finding.suggested_fix!)
                }}
                disabled={!isSafeFix}
                className="btn btn--sm btn--primary"
                title={isSafeFix ? 'Apply this fix to a new revision' : 'Unsafe fix cannot be auto-applied'}
              >
                {!isSafeFix ? <Lock size={12} /> : <Edit2 size={12} />} Apply fix
              </button>
            )}
          </div>
          <div
            style={{
              fontFamily: 'monospace',
              fontSize: '13px',
              color: 'var(--color-text-primary, #ffffff)',
              marginBottom: '8px',
            }}
          >
            "{finding.suggested_fix}"
          </div>

          {finding.intent_preserved && (
            <div
              style={{
                fontSize: '12px',
                color: 'var(--color-text-muted, #94a3b8)',
                borderTop: '1px solid var(--border, rgba(148, 163, 184, 0.15))',
                paddingTop: '8px',
              }}
            >
              <div>
                <strong>Intent:</strong> {finding.intent_preserved.purpose}
              </div>
              <div>
                <strong>CTA preserved:</strong> {finding.intent_preserved.cta}
              </div>
              {finding.intent_preserved.embedding_similarity !== undefined && <div><strong>Similarity:</strong> {Math.round(finding.intent_preserved.embedding_similarity * 100)}%</div>}
              {finding.intent_preserved.claims_changed.length > 0 && (
                <div>
                  <strong>Changes:</strong> {finding.intent_preserved.claims_changed.join(', ')}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Action Buttons: Accept, Edit, Dispute */}
      {canDecide && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            flexWrap: 'wrap',
            paddingTop: '12px',
            borderTop: '1px solid var(--color-border, rgba(148, 163, 184, 0.15))',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {onAccept && (
            <button
              type="button"
              onClick={onAccept}
              disabled={actionBusy || finding.state === 'accepted'}
              className="btn btn--sm btn--primary"
            >
              <Check size={14} /> {finding.state === 'accepted' ? 'Accepted ✓' : 'Accept finding'}
            </button>
          )}

          {onDispute && (
            <button
              type="button"
              disabled={actionBusy}
              onClick={() => setDisputeOpen((prev) => !prev)}
              className="btn btn--sm btn--ghost"
            >
              <HelpCircle size={14} /> Dispute
            </button>
          )}

          {finding.decisions && finding.decisions.length > 0 && (
            <button
              type="button"
              onClick={() => setShowHistory((prev) => !prev)}
              style={{
                marginLeft: 'auto',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.25rem',
                fontSize: '0.75rem',
                color: 'var(--color-text-muted, #94a3b8)',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
              }}
            >
              <History size={13} />
              <span>{finding.decisions.length} decision(s)</span>
              {showHistory ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
          )}
        </div>
      )}

      {/* Dispute Note Form */}
      {disputeOpen && (
        <div
          style={{
            marginTop: '0.75rem',
            padding: '0.75rem',
            borderRadius: '6px',
            backgroundColor: 'var(--color-bg-subtle, rgba(0, 0, 0, 0.25))',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <label style={{ display: 'block', fontSize: '0.75rem', fontWeight: 600, marginBottom: '0.25rem' }}>
            Rationale for dispute (required):
          </label>
          <textarea
            value={disputeNote}
            onChange={(e) => setDisputeNote(e.target.value)}
            rows={2}
            placeholder="Explain why this claim or finding is substantiated or misclassified..."
            style={{
              width: '100%',
              borderRadius: '4px',
              padding: '0.5rem',
              fontSize: '0.8rem',
              backgroundColor: 'var(--color-bg-panel, #0f172a)',
              color: '#ffffff',
              border: '1px solid var(--color-border, rgba(148, 163, 184, 0.3))',
              marginBottom: '0.5rem',
            }}
          />
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
            <button
              type="button"
              onClick={() => setDisputeOpen(false)}
              style={{
                padding: '0.25rem 0.6rem',
                fontSize: '0.75rem',
                backgroundColor: 'transparent',
                border: '1px solid var(--color-border, rgba(148, 163, 184, 0.3))',
                color: '#cbd5e1',
                borderRadius: '4px',
                cursor: 'pointer',
              }}
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={!disputeNote.trim()}
              onClick={() => {
                if (onDispute && disputeNote.trim()) {
                  onDispute(disputeNote.trim())
                  setDisputeOpen(false)
                  setDisputeNote('')
                }
              }}
              style={{
                padding: '0.25rem 0.75rem',
                fontSize: '0.75rem',
                fontWeight: 600,
                backgroundColor: disputeNote.trim() ? '#f97316' : '#64748b',
                color: '#ffffff',
                border: 'none',
                borderRadius: '4px',
                cursor: disputeNote.trim() ? 'pointer' : 'not-allowed',
              }}
            >
              Submit dispute
            </button>
          </div>
        </div>
      )}

      {/* Decision history list */}
      {showHistory && finding.decisions && (
        <div
          style={{
            marginTop: '0.75rem',
            padding: '0.75rem',
            borderRadius: '6px',
            backgroundColor: 'var(--color-bg-subtle, rgba(0, 0, 0, 0.15))',
            fontSize: '0.75rem',
          }}
          onClick={(e) => e.stopPropagation()}
        >
          <div style={{ fontWeight: 600, marginBottom: '0.4rem' }}>Decision Timeline:</div>
          {finding.decisions.map((dec) => (
            <div
              key={dec.id}
              style={{
                borderBottom: '1px solid rgba(148, 163, 184, 0.1)',
                paddingBottom: '0.35rem',
                marginBottom: '0.35rem',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <strong>
                  {dec.user_name || 'User'} ({dec.user_role || 'member'})
                </strong>
                <span style={{ color: 'var(--color-text-muted, #94a3b8)' }}>
                  {new Date(dec.created_at).toLocaleTimeString()}
                </span>
              </div>
              <div style={{ textTransform: 'capitalize', color: 'var(--accent, #0f766e)' }}>
                Action: {dec.action}
              </div>
              {dec.note && <div style={{ fontStyle: 'italic', marginTop: '0.15rem' }}>"{dec.note}"</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

