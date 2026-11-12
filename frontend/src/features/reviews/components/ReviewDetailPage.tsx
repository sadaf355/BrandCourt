import { useState, useEffect, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  Sparkles,
  Send,
  History,
  Image as ImageIcon,
  AlertTriangle,
  BookOpen,
} from 'lucide-react'
import { ContentItem, ReviewJob, User } from '../../../types/api'
import { apiClient } from '../../../lib/api'
import { useToast } from '../../../components/common/Toast'
import { StatusBadge } from '../../../components/common/StatusBadge'
import { FindingCard } from '../../findings/components/FindingCard'
import { EvidenceCard } from '../../evidence/components/EvidenceCard'
import { ReviewProgress } from './ReviewProgress'
import { ApprovalGate } from './ApprovalGate'
import { RevisionDiff } from './RevisionDiff'
import { CommentsPanel } from './CommentsPanel'
import { Skeleton, ErrorState, EmptyState } from '../../../components/common/FeedbackStates'

export function ReviewDetailPage({ user }: { user: User }) {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { showToast } = useToast()

  const [content, setContent] = useState<ContentItem | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [activeJob, setActiveJob] = useState<ReviewJob | null>(null)
  const [startingAnalysis, setStartingAnalysis] = useState(false)
  const [submittingWorkflow, setSubmittingWorkflow] = useState(false)
  const [decidingFindingId, setDecidingFindingId] = useState<string | null>(null)
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'content' | 'findings' | 'evidence'>('findings')

  // Revision edit modal / inline edit state
  const [isEditing, setIsEditing] = useState(false)
  const [editedCaption, setEditedCaption] = useState('')
  const [showRevisionHistory, setShowRevisionHistory] = useState(false)

  const loadContent = useCallback(async () => {
    if (!id) return
    setLoading(true)
    setError(null)
    try {
      const data = await apiClient.getContent(id)
      setContent(data)
      const currentRev = data.revisions?.[0]
      if (currentRev) {
        setEditedCaption(currentRev.caption)
      }
      if (data.findings && data.findings.length > 0) {
        setSelectedFindingId(data.findings[0].id)
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load content review.')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    loadContent()
  }, [loadContent])

  // Recover an in-flight review job across page refreshes
  useEffect(() => {
    if (!id) return
    try {
      const savedJobId = sessionStorage.getItem(`brandcourt:active-job:${id}`)
      if (!savedJobId) return
      apiClient
        .getJob(savedJobId)
        .then((job) => {
          if (job.status === 'completed' || job.status === 'failed') {
            sessionStorage.removeItem(`brandcourt:active-job:${id}`)
            loadContent()
          } else {
            setActiveJob(job)
          }
        })
        .catch(() => {
          sessionStorage.removeItem(`brandcourt:active-job:${id}`)
        })
    } catch {
      // sessionStorage may be unavailable
    }
  }, [id, loadContent])

  // Polling for review job progress if active
  useEffect(() => {
    if (!activeJob || activeJob.status === 'completed' || activeJob.status === 'failed') return
    const interval = setInterval(async () => {
      try {
        const job = await apiClient.getJob(activeJob.id)
        setActiveJob(job)
        if (job.status === 'completed') {
          try { if (id) sessionStorage.removeItem(`brandcourt:active-job:${id}`) } catch { /* ignore */ }
          showToast('Claim Court check complete!', 'success')
          loadContent()
        } else if (job.status === 'failed') {
          try { if (id) sessionStorage.removeItem(`brandcourt:active-job:${id}`) } catch { /* ignore */ }
          showToast('Check stage flagged for human review.', 'warning')
          loadContent()
        }
      } catch {
        // Continue polling
      }
    }, 600)
    return () => clearInterval(interval)
  }, [activeJob, id, loadContent, showToast])

  const handleStartAnalysis = async () => {
    if (!id || startingAnalysis || activeJob?.status === 'queued' || activeJob?.status === 'running') return
    setStartingAnalysis(true)
    try {
      const res = await apiClient.startAnalysisJob(id)
      try { sessionStorage.setItem(`brandcourt:active-job:${id}`, res.job_id) } catch { /* ignore */ }
      setActiveJob({
        id: res.job_id,
        job_type: 'claim_court_review',
        status: 'queued',
        progress: 0,
        stage: 'masking',
      })
      showToast('Analysis job queued. Running deterministic checks & Claim Court...', 'info')
    } catch (err: any) {
      showToast(err.message || 'Failed to start analysis job', 'error')
    } finally {
      setStartingAnalysis(false)
    }
  }

  const handleDecision = async (
    findingId: string,
    action: 'accept' | 'dispute' | 'override' | 'resolve',
    note?: string
  ) => {
    if (!id || decidingFindingId) return
    setDecidingFindingId(findingId)
    try {
      await apiClient.submitFindingDecision(id, findingId, action, note)
      showToast(`Finding marked as ${action}ed`, 'success')
      loadContent()
    } catch (err: any) {
      showToast(err.message || 'Failed to submit decision', 'error')
    } finally {
      setDecidingFindingId(null)
    }
  }

  const handleSaveRevision = async () => {
    if (!id || !editedCaption.trim() || submittingWorkflow) return
    setSubmittingWorkflow(true)
    try {
      await apiClient.createRevision(id, { caption: editedCaption.trim() })
      setIsEditing(false)
      showToast('New revision created! Automatically triggering Claim Court re-check...', 'success')
      await loadContent()
      handleStartAnalysis()
    } catch (err: any) {
      showToast(err.message || 'Failed to create revision', 'error')
    } finally {
      setSubmittingWorkflow(false)
    }
  }

  const handleSubmitForReview = async () => {
    if (!id || submittingWorkflow) return
    setSubmittingWorkflow(true)
    try {
      await apiClient.submitForReview(id)
      showToast('Content successfully submitted for reviewer queue sign-off!', 'success')
      loadContent()
    } catch (err: any) {
      showToast(err.message || 'Failed to submit for review', 'error')
    } finally {
      setSubmittingWorkflow(false)
    }
  }

  const handleStartReview = async () => {
    if (!id || submittingWorkflow) return
    setSubmittingWorkflow(true)
    try {
      await apiClient.startReview(id)
      showToast('Content moved to In Review. Ready for reviewer or manager decision.', 'success')
      loadContent()
    } catch (err: any) {
      showToast(err.message || 'Could not start review', 'error')
    } finally {
      setSubmittingWorkflow(false)
    }
  }

  const handleApprove = async () => {
    if (!id || submittingWorkflow) return
    setSubmittingWorkflow(true)
    try {
      await apiClient.approveContent(id)
      showToast('Content approved for publication! Immutable snapshot saved.', 'success')
      loadContent()
    } catch (err: any) {
      showToast(err.message || 'Cannot approve content', 'error')
    } finally {
      setSubmittingWorkflow(false)
    }
  }

  const handleReject = async () => {
    if (!id || submittingWorkflow) return
    setSubmittingWorkflow(true)
    try {
      await apiClient.rejectContent(id)
      showToast('Content rejected. Returned with feedback.', 'warning')
      loadContent()
    } catch (err: any) {
      showToast(err.message || 'Failed to reject content', 'error')
    } finally {
      setSubmittingWorkflow(false)
    }
  }

  if (loading) {
    return (
      <div style={{ padding: '2rem', maxWidth: '1200px', margin: '0 auto' }}>
        <Skeleton height="40px" width="300px" />
        <div style={{ marginTop: '1.5rem', display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem' }}>
          <Skeleton height="350px" />
          <Skeleton height="350px" />
          <Skeleton height="350px" />
        </div>
      </div>
    )
  }

  if (error || !content) {
    return (
      <div style={{ padding: '2rem', maxWidth: '600px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <ErrorState
          title="Could not open content review"
          message={error || 'This review was not found or belongs to another workspace.'}
          onRetry={loadContent}
        />
        <div style={{ textAlign: 'center' }}>
          <button type="button" className="secondary-button" onClick={() => navigate('/app/reviews')}>
            Back to Content Reviews
          </button>
        </div>
      </div>
    )
  }

  const latestRevision = content.revisions?.[0]
  const findings = content.findings || []
  const selectedFinding = findings.find((f) => f.id === selectedFindingId) || findings[0]

  // Blocker findings count
  const blockerFindings = findings.filter(
    (f) =>
      f.state !== 'accepted' &&
      f.state !== 'overridden' &&
      f.state !== 'resolved' &&
      (f.severity === 'critical' || f.verdict === 'contradicted' || f.verdict === 'outdated' || f.verdict === 'unsupported')
  )

  return (
    <div className="review-detail-view" style={{ padding: '1rem 1.5rem', maxWidth: '1600px', margin: '0 auto' }}>
      {/* Top Bar Navigation & Info */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: '1rem',
          marginBottom: '1.25rem',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            type="button"
            onClick={() => navigate('/app/reviews')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.3rem',
              fontSize: '0.85rem',
              color: 'var(--color-text-muted, #94a3b8)',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
            }}
          >
            <ArrowLeft size={16} /> Reviews
          </button>
          <span style={{ color: 'var(--color-border, rgba(148, 163, 184, 0.3))' }}>/</span>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, margin: 0 }}>{content.title}</h2>
          <StatusBadge status={content.status} />
          <span
            style={{
              padding: '0.2rem 0.5rem',
              borderRadius: '4px',
              backgroundColor: 'var(--color-bg-subtle, rgba(255, 255, 255, 0.08))',
              fontSize: '0.75rem',
              color: 'var(--color-text-muted, #94a3b8)',
            }}
          >
            Revision {content.current_revision}
          </span>
        </div>

        {/* Action Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <button
            type="button"
            onClick={() => setShowRevisionHistory((prev) => !prev)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.35rem',
              padding: '0.45rem 0.85rem',
              borderRadius: '6px',
              backgroundColor: 'transparent',
              border: '1px solid var(--color-border, rgba(148, 163, 184, 0.3))',
              color: 'var(--color-text-secondary, #cbd5e1)',
              fontSize: '0.8rem',
              cursor: 'pointer',
            }}
          >
            <History size={14} /> Revisions ({content.revisions?.length || 1})
          </button>

          <button
            type="button"
            onClick={handleStartAnalysis}
            disabled={startingAnalysis || activeJob?.status === 'queued' || activeJob?.status === 'running' || content.status === 'approved'}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '0.35rem',
              padding: '0.45rem 0.95rem',
              borderRadius: '6px',
              backgroundColor: 'var(--btn-primary-bg, #0f766e)',
              color: '#ffffff',
              fontSize: '0.8rem',
              fontWeight: 600,
              border: 'none',
              cursor: startingAnalysis || activeJob?.status === 'queued' || activeJob?.status === 'running' || content.status === 'approved' ? 'not-allowed' : 'pointer',
              opacity: startingAnalysis || activeJob?.status === 'queued' || activeJob?.status === 'running' || content.status === 'approved' ? 0.55 : 1,
            }}
          >
            <Sparkles size={14} /> {startingAnalysis || activeJob?.status === 'running' || activeJob?.status === 'queued' ? 'Checking…' : 'Run Claim Court Check'}
          </button>

          {/* Submit for review button (creator/manager/admin role) */}
          {(user.role === 'creator' || user.role === 'manager' || user.role === 'admin') && (content.status === 'draft' || content.status === 'analyzed' || content.status === 'rejected') && (
            <button
              type="button"
              onClick={handleSubmitForReview}
              disabled={submittingWorkflow || blockerFindings.length > 0}
              title={
                blockerFindings.length > 0
                  ? `Cannot submit: ${blockerFindings.length} blocking finding(s) require action.`
                  : 'Submit for reviewer review'
              }
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.45rem 1rem',
                borderRadius: '6px',
                backgroundColor: blockerFindings.length > 0 ? '#475569' : '#2563eb',
                color: '#ffffff',
                fontSize: '0.8rem',
                fontWeight: 600,
                border: 'none',
                cursor: submittingWorkflow || blockerFindings.length > 0 ? 'not-allowed' : 'pointer',
                opacity: submittingWorkflow ? 0.6 : 1,
              }}
            >
              <Send size={14} /> Submit for Review
            </button>
          )}

          {/* Start review button (reviewer/manager/admin when submitted) */}
          {(user.role === 'reviewer' || user.role === 'manager' || user.role === 'admin') && content.status === 'submitted' && (
            <button
              type="button"
              onClick={handleStartReview}
              disabled={submittingWorkflow}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.45rem 1rem',
                borderRadius: '6px',
                backgroundColor: '#2563eb',
                color: '#ffffff',
                fontSize: '0.8rem',
                fontWeight: 600,
                border: 'none',
                cursor: submittingWorkflow ? 'not-allowed' : 'pointer',
                opacity: submittingWorkflow ? 0.6 : 1,
              }}
            >
              Start Reviewer Sign-Off
            </button>
          )}

          {content.status === 'approved' && (
            <button
              type="button"
              onClick={() => navigate('/app/insights')}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.35rem',
                padding: '0.45rem 1rem',
                borderRadius: '6px',
                backgroundColor: '#047857',
                color: '#ffffff',
                fontSize: '0.8rem',
                fontWeight: 600,
                border: 'none',
                cursor: 'pointer',
              }}
            >
              Open Compliance Report
            </button>
          )}
        </div>
      </div>

      {/* Real Stage Review Progress Bar */}
      {activeJob && <ReviewProgress job={activeJob} onRetry={handleStartAnalysis} />}

      {/* Revision Diff View if 2 revisions exist */}
      {showRevisionHistory && content.revisions && content.revisions.length > 1 && (
        <div style={{ marginBottom: '1.5rem' }}>
          <h4 style={{ fontSize: '0.9rem', fontWeight: 600, marginBottom: '0.5rem' }}>Word-Level Revision Diff</h4>
          <RevisionDiff
            previousText={content.revisions[1]?.caption || ''}
            currentText={content.revisions[0]?.caption || ''}
          />
        </div>
      )}

      {/* Responsive Tabs for Small Screens */}
      <div className="mobile-tabs" style={{ display: 'none', gap: '0.5rem', marginBottom: '1rem' }}>
        <button
          onClick={() => setActiveTab('content')}
          style={{
            flex: 1,
            padding: '0.5rem',
            borderRadius: '6px',
            backgroundColor: activeTab === 'content' ? 'var(--btn-primary-bg, #0f766e)' : 'transparent',
            border: '1px solid var(--color-border, rgba(148, 163, 184, 0.3))',
            color: activeTab === 'content' ? '#ffffff' : 'var(--text)',
            fontSize: '0.8rem',
          }}
        >
          Creative & Copy
        </button>
        <button
          onClick={() => setActiveTab('findings')}
          style={{
            flex: 1,
            padding: '0.5rem',
            borderRadius: '6px',
            backgroundColor: activeTab === 'findings' ? 'var(--btn-primary-bg, #0f766e)' : 'transparent',
            border: '1px solid var(--color-border, rgba(148, 163, 184, 0.3))',
            color: activeTab === 'findings' ? '#ffffff' : 'var(--text)',
            fontSize: '0.8rem',
          }}
        >
          Findings ({findings.length})
        </button>
        <button
          onClick={() => setActiveTab('evidence')}
          style={{
            flex: 1,
            padding: '0.5rem',
            borderRadius: '6px',
            backgroundColor: activeTab === 'evidence' ? 'var(--btn-primary-bg, #0f766e)' : 'transparent',
            border: '1px solid var(--color-border, rgba(148, 163, 184, 0.3))',
            color: activeTab === 'evidence' ? '#ffffff' : 'var(--text)',
            fontSize: '0.8rem',
          }}
        >
          Evidence Drawer
        </button>
      </div>

      {/* Three Panel Workbench (Desktop: 3 columns; Mobile: tabs) */}
      <div
        className="workbench-grid"
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(300px, 1.1fr) minmax(320px, 1.2fr) minmax(280px, 1fr)',
          gap: '1.25rem',
          alignItems: 'start',
        }}
      >
        {/* PANEL 1: Content, Creative Preview, Spans */}
        <div
          className="workbench-panel"
          style={{
            backgroundColor: 'var(--color-bg-panel, rgba(30, 41, 59, 0.6))',
            borderRadius: '12px',
            border: '1px solid var(--color-border, rgba(148, 163, 184, 0.2))',
            padding: '1.25rem',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '0.75rem',
              borderBottom: '1px solid var(--color-border, rgba(148, 163, 184, 0.15))',
              paddingBottom: '0.5rem',
            }}
          >
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, margin: 0 }}>Content & Media</h3>
            <button
              onClick={() => setIsEditing((p) => !p)}
              style={{
                fontSize: '0.75rem',
                color: 'var(--accent, #818cf8)',
                background: 'none',
                border: 'none',
                cursor: 'pointer',
              }}
            >
              {isEditing ? 'Cancel Edit' : 'Edit Caption'}
            </button>
          </div>

          {/* Creative Media Preview */}
          {latestRevision?.creative_filename && (
            <div style={{ marginBottom: '1rem', textAlign: 'center' }}>
              <div
                style={{
                  position: 'relative',
                  display: 'inline-block',
                  maxWidth: '100%',
                  borderRadius: '8px',
                  overflow: 'hidden',
                  border: '1px solid var(--color-border, rgba(148, 163, 184, 0.2))',
                  backgroundColor: 'rgba(0,0,0,0.3)',
                }}
              >
                <div
                  style={{
                    padding: '2rem 1rem',
                    color: 'var(--color-text-muted, #94a3b8)',
                    fontSize: '0.85rem',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '0.5rem',
                  }}
                >
                  <ImageIcon size={32} />
                  <span>Creative: {latestRevision.creative_filename}</span>
                  {latestRevision.ocr_text && (
                    <div
                      style={{
                        marginTop: '0.5rem',
                        fontSize: '0.75rem',
                        fontFamily: 'monospace',
                        padding: '0.4rem 0.6rem',
                        borderRadius: '4px',
                        backgroundColor: 'rgba(0,0,0,0.5)',
                        border: '1px solid rgba(148, 163, 184, 0.2)',
                      }}
                    >
                      OCR: {latestRevision.ocr_text}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Caption with highlighted spans */}
          {isEditing ? (
            <div>
              <textarea
                value={editedCaption}
                onChange={(e) => setEditedCaption(e.target.value)}
                rows={6}
                style={{
                  width: '100%',
                  padding: '0.75rem',
                  borderRadius: '6px',
                  backgroundColor: 'var(--color-bg-subtle, rgba(0, 0, 0, 0.25))',
                  border: '1px solid var(--accent, #6366f1)',
                  color: 'var(--color-text-primary, #ffffff)',
                  fontSize: '0.875rem',
                  lineHeight: 1.5,
                  marginBottom: '0.5rem',
                }}
              />
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                <button
                  onClick={() => setIsEditing(false)}
                  style={{
                    padding: '0.35rem 0.75rem',
                    fontSize: '0.75rem',
                    backgroundColor: 'transparent',
                    border: '1px solid rgba(148, 163, 184, 0.3)',
                    color: '#cbd5e1',
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}
                >
                  Cancel
                </button>
                <button
                  onClick={handleSaveRevision}
                  style={{
                    padding: '0.35rem 0.85rem',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    backgroundColor: 'var(--accent, #6366f1)',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '4px',
                    cursor: 'pointer',
                  }}
                >
                  Save & Trigger Re-check
                </button>
              </div>
            </div>
          ) : (
            <div
              style={{
                padding: '0.875rem',
                borderRadius: '8px',
                backgroundColor: 'var(--color-bg-subtle, rgba(0, 0, 0, 0.2))',
                border: '1px solid var(--color-border, rgba(148, 163, 184, 0.15))',
                fontSize: '0.9rem',
                lineHeight: 1.6,
                color: 'var(--color-text-primary, #ffffff)',
              }}
            >
              {latestRevision?.caption}
            </div>
          )}

          <div
            style={{
              marginTop: '1rem',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.35rem',
              fontSize: '0.75rem',
              color: 'var(--color-text-muted, #94a3b8)',
            }}
          >
            <div>
              <strong>Channel:</strong> {content.channel}
            </div>
            {content.campaign && (
              <div>
                <strong>Campaign:</strong> {content.campaign}
              </div>
            )}
            {latestRevision?.alt_text && (
              <div>
                <strong>Alt Text:</strong> {latestRevision.alt_text}
              </div>
            )}
            <div>
              <strong>Language:</strong> {latestRevision?.detected_language || 'English'}
            </div>
          </div>
        </div>

        {/* PANEL 2: Findings Grouped by Severity */}
        <div
          className="workbench-panel"
          style={{
            backgroundColor: 'var(--color-bg-panel, rgba(30, 41, 59, 0.6))',
            borderRadius: '12px',
            border: '1px solid var(--color-border, rgba(148, 163, 184, 0.2))',
            padding: '1.25rem',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '0.75rem',
              borderBottom: '1px solid var(--color-border, rgba(148, 163, 184, 0.15))',
              paddingBottom: '0.5rem',
            }}
          >
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, margin: 0 }}>
              Claim Findings ({findings.length})
            </h3>
            {blockerFindings.length > 0 && (
              <span
                style={{
                  fontSize: '0.75rem',
                  color: '#ef4444',
                  fontWeight: 600,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                }}
              >
                <AlertTriangle size={13} /> {blockerFindings.length} blocker(s)
              </span>
            )}
          </div>

          {findings.length === 0 ? (
            <EmptyState
              title="No findings detected"
              description="Click 'Run Claim Court Check' above to inspect caption and claims against approved facts and rules."
            />
          ) : (
            <div>
              {findings.map((f) => (
                <FindingCard
                  key={f.id}
                  finding={f}
                  isSelected={f.id === selectedFindingId}
                  onSelect={() => setSelectedFindingId(f.id)}
                  onAccept={() => handleDecision(f.id, 'accept')}
                  onDispute={(note) => handleDecision(f.id, 'dispute', note)}
                  onEdit={(fix) => {
                    const original = latestRevision?.caption || ''
                    const updated =
                      fix.length >= original.length * 0.6 || !original.includes(f.claim_text)
                        ? fix
                        : original.replace(f.claim_text, fix)
                    setEditedCaption(updated)
                    setIsEditing(true)
                  }}
                  canDecide={content.status !== 'approved'}
                  actionBusy={decidingFindingId === f.id}
                />
              ))}
            </div>
          )}
        </div>

        {/* PANEL 3: Evidence Drawer & Connector */}
        <div
          className="workbench-panel"
          style={{
            backgroundColor: 'var(--color-bg-panel, rgba(30, 41, 59, 0.6))',
            borderRadius: '12px',
            border: '1px solid var(--color-border, rgba(148, 163, 184, 0.2))',
            padding: '1.25rem',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '0.75rem',
              borderBottom: '1px solid var(--color-border, rgba(148, 163, 184, 0.15))',
              paddingBottom: '0.5rem',
            }}
          >
            <h3 style={{ fontSize: '0.95rem', fontWeight: 600, margin: 0, display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
              <BookOpen size={16} /> Traceable Evidence
            </h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted, #94a3b8)' }}>
              {selectedFinding?.evidence?.length || 0} item(s)
            </span>
          </div>

          {selectedFinding ? (
            <div>
              <div
                style={{
                  fontSize: '0.75rem',
                  color: 'var(--color-text-muted, #94a3b8)',
                  marginBottom: '0.75rem',
                }}
              >
                Linked to finding: <strong>"{selectedFinding.claim_text}"</strong>
              </div>

              {selectedFinding.evidence && selectedFinding.evidence.length > 0 ? (
                selectedFinding.evidence.map((ev, i) => <EvidenceCard key={ev.id || i} evidence={ev} isActive />)
              ) : (
                <div
                  style={{
                    padding: '1.5rem',
                    textAlign: 'center',
                    color: 'var(--color-text-muted, #94a3b8)',
                    fontSize: '0.85rem',
                  }}
                >
                  No explicit fact reference linked to this finding.
                </div>
              )}
            </div>
          ) : (
            <div style={{ textAlign: 'center', padding: '2rem 1rem', color: 'var(--color-text-muted, #94a3b8)', fontSize: '0.85rem' }}>
              Select a finding to inspect its ground-truth source evidence.
            </div>
          )}

          {/* Threaded Comments & Short Polling */}
          <div style={{ marginTop: '1.5rem', borderTop: '1px solid var(--color-border, rgba(148, 163, 184, 0.2))', paddingTop: '1rem' }}>
            <CommentsPanel
              contentId={content.id}
              findingId={selectedFindingId || undefined}
              currentUserId={user.id}
              currentUserName={user.full_name}
            />
          </div>
        </div>
      </div>

      {/* Approval Gate for Managers/Admins */}
      <ApprovalGate
        findings={findings}
        userRole={user.role}
        onApprove={handleApprove}
        onReject={handleReject}
        disabled={submittingWorkflow || content.status === 'approved' || content.status === 'rejected'}
      />
    </div>
  )
}

