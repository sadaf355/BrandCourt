import {
  User,
  ContentItem,
  ContentRevision,
  ClaimFinding,
  ReviewJob,
  Comment,
  ReviewQueuePage,
  WorkspaceMember,
  RuleWithHistory,
  FactWithHistory,
  BrandAsset,
  AuditEvent,
  AppNotification,
  ApprovalResult,
  GuidelineUploadResult,
  FindingSeverity,
  ContentStatus,
  Role,
  InsightsSummary,
  TopRuleBroken,
  OverrideRateItem,
  ExpiringFactItem,
  ComplianceReport,
  GuidelineHealthReport,
  PrecedentItem,
  ModelSettings,
} from '../types/api'
import { mockService } from './mockService'

const API_BASE = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api').replace(/\/$/, '')
export const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true' || false

export function getToken(): string | null {
  try {
    return localStorage.getItem('brandcourt-token')
  } catch {
    return null
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) {
      localStorage.setItem('brandcourt-token', token)
    } else {
      localStorage.removeItem('brandcourt-token')
    }
  } catch {
    // Storage might be disabled
  }
}

export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers)
  const token = getToken()
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (options.body && !(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_BASE}${path.startsWith('/') ? path : `/${path}`}`, {
    ...options,
    headers,
  })

  if (response.status === 401) {
    setToken(null)
    window.dispatchEvent(new CustomEvent('brandcourt-unauthorized'))
  }

  if (response.status === 204) return undefined as T
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(typeof data.detail === 'string' ? data.detail : `Request failed (${response.status})`)
  }
  return data as T
}

export const apiBase = API_BASE

export type HealthPayload = {
  status: 'ok' | 'degraded'
  service: string
  version: string
  timestamp: string
  database: 'connected' | 'not_configured' | 'unavailable'
}

export function getHealth(signal?: AbortSignal) {
  return api<HealthPayload>('/health', { signal })
}

// Unified client switching seamlessly between real API and mockService
export const apiClient = {
  async getMe(): Promise<User> {
    if (USE_MOCK) return mockService.getUser()
    return api<User>('/me')
  },
  async getWorkspace(): Promise<{ id: string; name: string }> {
    if (USE_MOCK) return { id: mockService.getUser().workspace_id, name: 'Aurora Brand Lab' }
    return api<{ id: string; name: string }>('/workspace')
  },
  async listContent(): Promise<ContentItem[]> {
    if (USE_MOCK) return mockService.listContent()
    return api<ContentItem[]>('/content')
  },
  async getContent(id: string): Promise<ContentItem> {
    if (USE_MOCK) {
      const res = await mockService.getContent(id)
      if (!res) throw new Error('Content not found')
      return res
    }
    return api<ContentItem>(`/content/${id}`)
  },
  async createContent(data: {
    title: string
    channel: ContentItem['channel']
    campaign?: string
    caption?: string
    alt_text?: string
    is_ai_media?: boolean
    paid_gifted?: boolean
  }): Promise<ContentItem> {
    if (USE_MOCK) return mockService.createContent(data)
    return api<ContentItem>('/content', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },
  async createRevision(
    contentId: string,
    data: {
      caption: string
      alt_text?: string
      is_ai_media?: boolean
      paid_gifted?: boolean
      title?: string
      channel?: ContentItem['channel']
      campaign?: string
    }
  ): Promise<ContentRevision> {
    if (USE_MOCK) return mockService.createRevision(contentId, data)
    return api<ContentRevision>(`/content/${contentId}/revisions`, {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },
  async startAnalysisJob(contentId: string): Promise<{ job_id: string; status: string; progress: number; stage: string; content_id: string; revision_id: string; poll_url: string }> {
    if (USE_MOCK) {
      const jobId = await mockService.startAnalysisJob(contentId)
      return { job_id: jobId, status: 'queued', progress: 0, stage: 'queued', content_id: contentId, revision_id: '', poll_url: `/jobs/${jobId}` }
    }
    return api<{ job_id: string; status: string; progress: number; stage: string; content_id: string; revision_id: string; poll_url: string }>(`/content/${contentId}/analyze`, {
      method: 'POST',
    })
  },
  async getJob(jobId: string): Promise<ReviewJob> {
    if (USE_MOCK) return mockService.getJob(jobId)
    return api<any>(`/jobs/${jobId}`).then(job => ({ ...job, id: job.job_id ?? job.id, job_type: job.job_type ?? 'content_analysis' }))
  },
  async submitFindingDecision(
    contentId: string,
    findingId: string,
    action: 'accept' | 'edit' | 'dispute' | 'override' | 'resolve',
    note?: string,
    editedText?: string
  ): Promise<ClaimFinding> {
    if (USE_MOCK) return mockService.submitFindingDecision(contentId, findingId, action === 'edit' ? 'resolve' : action, note)
    return api<ClaimFinding>(`/findings/${findingId}/decision`, {
      method: 'POST',
      body: JSON.stringify({ action, reason: note, edited_text: editedText }),
    })
  },
  async submitForReview(contentId: string): Promise<ContentItem> {
    if (USE_MOCK) return mockService.submitForReview(contentId)
    await api(`/content/${contentId}/workflow`, {
      method: 'POST',
      body: JSON.stringify({ action: 'submit' }),
    })
    return api<ContentItem>(`/content/${contentId}`)
  },
  async startReview(contentId: string): Promise<ContentItem> {
    if (USE_MOCK) return mockService.startReview(contentId)
    await api(`/content/${contentId}/workflow`, {
      method: 'POST',
      body: JSON.stringify({ action: 'start_review' }),
    })
    return api<ContentItem>(`/content/${contentId}`)
  },
  async approveContent(contentId: string): Promise<ContentItem> {
    if (USE_MOCK) return mockService.approveContent(contentId)
    await api(`/content/${contentId}/workflow`, {
      method: 'POST',
      body: JSON.stringify({ action: 'approve' }),
    })
    return api<ContentItem>(`/content/${contentId}`)
  },
  async rejectContent(contentId: string): Promise<ContentItem> {
    if (USE_MOCK) return mockService.rejectContent(contentId)
    await api(`/content/${contentId}/workflow`, {
      method: 'POST',
      body: JSON.stringify({ action: 'reject' }),
    })
    return api<ContentItem>(`/content/${contentId}`)
  },
  async reopenContent(contentId: string): Promise<ContentItem> {
    if (USE_MOCK) return mockService.reopenContent(contentId)
    await api(`/content/${contentId}/workflow`, {
      method: 'POST',
      body: JSON.stringify({ action: 'reopen' }),
    })
    return api<ContentItem>(`/content/${contentId}`)
  },

  // ── B3: Review queue ───────────────────────────────────────────────────────
  async listReviewQueue(params?: {
    status?: ContentStatus
    channel?: string
    severity?: FindingSeverity
    creator?: string
    include_advisory?: boolean
    limit?: number
    offset?: number
  }): Promise<ReviewQueuePage> {
    if (USE_MOCK) return mockService.listReviewQueue(params)
    const q = new URLSearchParams()
    if (params?.status) q.set('status', params.status)
    if (params?.channel) q.set('channel', params.channel)
    if (params?.severity) q.set('severity', params.severity)
    if (params?.creator) q.set('creator', params.creator)
    if (params?.include_advisory) q.set('include_advisory', 'true')
    if (params?.limit != null) q.set('limit', String(params.limit))
    if (params?.offset != null) q.set('offset', String(params.offset))
    return api<ReviewQueuePage>(`/review-queue?${q}`)
  },

  // ── B3: Approve / reject with reason ──────────────────────────────────────
  async approveContentWithReason(contentId: string): Promise<ApprovalResult> {
    if (USE_MOCK) return mockService.approveContentWithReason(contentId)
    return api<ApprovalResult>(`/content/${contentId}/workflow`, { method: 'POST', body: JSON.stringify({ action: 'approve' }) })
  },
  async rejectContentWithReason(contentId: string, reason: string): Promise<ContentItem> {
    if (USE_MOCK) return mockService.rejectContentWithReason(contentId, reason)
    await api(`/content/${contentId}/workflow`, { method: 'POST', body: JSON.stringify({ action: 'reject', reason }) })
    return api<ContentItem>(`/content/${contentId}`)
  },
  async overrideFinding(
    contentId: string,
    findingId: string,
    reason: string
  ): Promise<ClaimFinding> {
    if (USE_MOCK) return mockService.overrideFinding(contentId, findingId, reason)
    return api<ClaimFinding>(`/findings/${findingId}/decision`, { method: 'POST', body: JSON.stringify({ action: 'override', reason }) })
  },

  // ── B3: Comments ──────────────────────────────────────────────────────────
  async listComments(contentId: string, findingId?: string): Promise<Comment[]> {
    if (USE_MOCK) return mockService.listComments(contentId, findingId)
    const q = findingId ? `?finding_id=${encodeURIComponent(findingId)}` : ''
    return api<Comment[]>(`/content/${contentId}/comments${q}`)
  },
  async addComment(
    contentId: string,
    body: string,
    findingId?: string,
    parentId?: string
  ): Promise<Comment> {
    if (USE_MOCK) return mockService.addComment(contentId, body, findingId, parentId)
    return api<Comment>(`/content/${contentId}/comments`, {
      method: 'POST',
      body: JSON.stringify({ body, finding_id: findingId }),
    })
  },
  async resolveComment(contentId: string, commentId: string): Promise<Comment> {
    if (USE_MOCK) return mockService.resolveComment(contentId, commentId)
    throw new Error('Comment resolution is not exposed by the published API contract.')
  },

  // ── B3: Notifications ─────────────────────────────────────────────────────
  async listNotifications(): Promise<AppNotification[]> {
    if (USE_MOCK) return mockService.listNotifications()
    return api<AppNotification[]>('/notifications')
  },

  // ── B3: Members ───────────────────────────────────────────────────────────
  async listMembers(): Promise<WorkspaceMember[]> {
    if (USE_MOCK) return mockService.listMembers()
    return api<WorkspaceMember[]>('/users')
  },
  async inviteMember(email: string, role: Role): Promise<WorkspaceMember> {
    if (USE_MOCK) return mockService.inviteMember(email, role)
    throw new Error('The API contract has user creation, not email invitations. Create a user with full_name, email, password and role.')
  },
  async changeMemberRole(userId: string, role: Role): Promise<WorkspaceMember> {
    if (USE_MOCK) return mockService.changeMemberRole(userId, role)
    return api<WorkspaceMember>(`/users/${userId}/role?role=${encodeURIComponent(role)}`, { method: 'PATCH' })
  },
  async deactivateMember(userId: string): Promise<WorkspaceMember> {
    if (USE_MOCK) return mockService.deactivateMember(userId)
    throw new Error('Member deactivation is not exposed by the published API contract.')
  },
  async deleteWorkspaceData(reason: string): Promise<{ audit_event_id: string }> {
    if (USE_MOCK) return mockService.deleteWorkspaceData(reason)
    throw new Error('Workspace deletion is not exposed by the published API contract.')
  },

  // ── B3: Rules ─────────────────────────────────────────────────────────────
  async listRules(params?: {
    status?: 'draft' | 'active' | 'retired'
    is_india_pack?: boolean
  }): Promise<RuleWithHistory[]> {
    if (USE_MOCK) return mockService.listRules(params)
    const query = params?.status ? `?status=${encodeURIComponent(params.status)}` : ''
    return api<RuleWithHistory[]>(`/rules${query}`)
  },
  async updateRule(
    ruleId: string,
    data: Partial<{ name: string; description: string; status: 'draft' | 'active' | 'retired' }>
  ): Promise<RuleWithHistory> {
    if (USE_MOCK) return mockService.updateRule(ruleId, data)
    return api<RuleWithHistory>(`/rules/${ruleId}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  },

  // ── B3: Facts ─────────────────────────────────────────────────────────────
  async listFacts(): Promise<FactWithHistory[]> {
    if (USE_MOCK) return mockService.listFacts()
    return api<FactWithHistory[]>('/facts')
  },
  async createFact(data: {
    statement: string
    claim_value?: string
    unit?: string
    source_reference: string
    valid_from?: string
    valid_until?: string
  }): Promise<FactWithHistory> {
    if (USE_MOCK) return mockService.createFact(data)
    return api<FactWithHistory>('/facts', {
      method: 'POST',
      body: JSON.stringify({ statement: data.statement, value: data.claim_value ?? '', unit: data.unit, source_ref: data.source_reference, valid_from: data.valid_from, valid_to: data.valid_until }),
    })
  },

  // ── B3: Assets ────────────────────────────────────────────────────────────
  async listAssets(): Promise<BrandAsset[]> {
    if (USE_MOCK) return mockService.listAssets()
    return api<BrandAsset[]>('/assets')
  },
  async upsertAsset(name: string, assetType: string, contentJson: unknown): Promise<BrandAsset> {
    if (USE_MOCK) return mockService.upsertAsset(name, assetType, contentJson)
    return api<BrandAsset>('/assets', {
      method: 'POST',
      body: JSON.stringify({ name, kind: assetType, data: contentJson }),
    })
  },

  // ── B3: Guidelines ────────────────────────────────────────────────────────
  async uploadGuideline(file: File): Promise<GuidelineUploadResult> {
    if (USE_MOCK) return mockService.uploadGuideline(file)
    const form = new FormData()
    form.append('file', file)
    return api<GuidelineUploadResult>('/guidelines', {
      method: 'POST',
      body: form,
    })
  },

  // ── B3: Audit trail ───────────────────────────────────────────────────────
  async listAuditEvents(params?: {
    scope?: 'own' | 'assigned' | 'workspace' | 'rules'
    limit?: number
    offset?: number
  }): Promise<{ events: AuditEvent[]; total: number }> {
    if (USE_MOCK) return mockService.listAuditEvents(params)
    const q = new URLSearchParams()
    if (params?.scope) q.set('scope', params.scope)
    if (params?.limit != null) q.set('limit', String(params.limit))
    if (params?.offset != null) q.set('offset', String(params.offset))
    return api<AuditEvent[]>(`/audit-events${params?.limit ? `?limit=${params.limit}` : ''}`).then(events => ({ events, total: events.length }))
  },

  // ── B4: Insights & Analytics ──────────────────────────────────────────────
  async getInsightsSummary(): Promise<InsightsSummary> {
    if (USE_MOCK) return mockService.getInsightsSummary()
    return api<InsightsSummary>('/insights/summary')
  },
  async getTopRulesBroken(groupBy: 'channel' | 'creator' | 'week' = 'channel'): Promise<TopRuleBroken> {
    if (USE_MOCK) return mockService.getTopRulesBroken(groupBy)
    return api<TopRuleBroken>(`/insights/top-rules?group_by=${groupBy}`)
  },
  async getOverrideRates(): Promise<{ rules: OverrideRateItem[] }> {
    if (USE_MOCK) return mockService.getOverrideRates()
    return api<{ rules: OverrideRateItem[] }>('/insights/override-rates')
  },
  async getExpiringFacts(): Promise<{ facts: ExpiringFactItem[] }> {
    if (USE_MOCK) return mockService.getExpiringFacts()
    return api<{ facts: ExpiringFactItem[] }>('/insights/expiring-facts')
  },

  // ── B4: Reports ───────────────────────────────────────────────────────────
  async downloadReportJson(contentId: string): Promise<ComplianceReport> {
    if (USE_MOCK) return mockService.downloadReportJson(contentId)
    return api<ComplianceReport>(`/content/${contentId}/report?format=json`)
  },
  async downloadReportPdf(contentId: string): Promise<Blob> {
    if (USE_MOCK) return mockService.downloadReportPdf(contentId)
    const res = await fetch(`${API_BASE}/content/${contentId}/report?format=pdf`, {
      headers: { Authorization: `Bearer ${getToken() || ''}` },
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Failed to download PDF' }))
      throw new Error(err.detail || 'Download failed')
    }
    return res.blob()
  },

  // ── B4: Intelligence screens (Health, Precedents, Fix Verification, Models)
  async getGuidelineHealth(): Promise<GuidelineHealthReport> {
    if (USE_MOCK) return mockService.getGuidelineHealth()
    return api<GuidelineHealthReport>('/guideline-health')
  },
  async listPrecedents(): Promise<PrecedentItem[]> {
    if (USE_MOCK) return mockService.listPrecedents()
    return api<PrecedentItem[]>('/precedents')
  },
  async createPrecedent(data: {
    finding_id: string
    rule_id?: string
    channel?: string
    pattern_text: string
    reason: string
    valid_to?: string
  }): Promise<PrecedentItem> {
    if (USE_MOCK) return mockService.createPrecedent(data)
    return api<PrecedentItem>('/precedents', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  },
  async approvePrecedent(id: string): Promise<{ id: string; status: string }> {
    if (USE_MOCK) return mockService.approvePrecedent(id)
    return api<{ id: string; status: string }>(`/precedents/${id}/approve`, {
      method: 'POST',
    })
  },
  async promotePrecedent(id: string): Promise<{ precedent_id: string; rule_id: string; code: string; message: string }> {
    if (USE_MOCK) return mockService.promotePrecedent(id)
    return api<{ precedent_id: string; rule_id: string; code: string; message: string }>(`/precedents/${id}/promote`, {
      method: 'POST',
    })
  },
  async verifyFix(contentId: string, proposedText: string): Promise<any> {
    if (USE_MOCK) return mockService.verifyFix(contentId, proposedText)
    return api<any>(`/content/${contentId}/verify-fix`, {
      method: 'POST',
      body: JSON.stringify({ proposed_text: proposedText }),
    })
  },
  async getModelSettings(): Promise<ModelSettings> {
    if (USE_MOCK) return mockService.getModelSettings()
    return api<ModelSettings>('/settings/models')
  },
  async updateModelSettings(data: { local_model_enabled: boolean; default_model?: string }): Promise<{ local_model_enabled: boolean; message: string }> {
    if (USE_MOCK) return mockService.updateModelSettings(data)
    return api<{ local_model_enabled: boolean; default_model: string; message: string }>('/settings/models', { method: 'PATCH', body: JSON.stringify(data) })
  },
}
