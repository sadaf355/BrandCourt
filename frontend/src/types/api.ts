/**
 * BrandCourt API Contract & Domain Types
 */

export type Role = 'creator' | 'reviewer' | 'manager' | 'admin'

export type User = {
  id: string
  workspace_id: string
  email: string
  full_name: string
  role: Role
  created_at?: string
}

export type Channel =
  | 'website'
  | 'instagram'
  | 'facebook'
  | 'linkedin'
  | 'email'
  | 'paid_ad'
  | 'packaging'
  | 'other'

export type ContentStatus =
  | 'draft'
  | 'analyzed'
  | 'submitted'
  | 'in_review'
  | 'approved'
  | 'rejected'

export type FindingVerdict =
  | 'supported'
  | 'contradicted'
  | 'outdated'
  | 'unsupported'
  | 'needs_human_review'

export type FindingSeverity = 'critical' | 'major' | 'advisory'

export type FindingState = 'open' | 'accepted' | 'disputed' | 'overridden' | 'resolved'

export type EvidenceItem = {
  id?: string
  source_type: 'fact' | 'rule' | 'precedent' | 'guideline'
  source_id?: string
  title: string
  statement?: string
  claim_value?: string
  unit?: string
  source_reference?: string
  valid_from?: string
  valid_until?: string
  version?: number
  confidence?: number
}

export type FindingDecision = {
  id: string
  action: 'accept' | 'dispute' | 'override' | 'resolve'
  user_id: string
  user_name?: string
  user_role?: Role
  note?: string
  created_at: string
}

export type ClaimFinding = {
  id: string
  content_id?: string
  revision_id?: string
  claim_text: string
  verdict: FindingVerdict
  rationale: string
  evidence: EvidenceItem[]
  severity: FindingSeverity
  analysis_method: string
  state: FindingState
  confidence?: number
  rule_id?: string
  rule_version?: number
  rule_valid_from?: string
  rule_valid_until?: string
  layer?: 'rules' | 'claims' | 'tone' | 'image' | 'compliance'
  span?: { start: number; end: number }
  image_region?: { x: number; y: number; width: number; height: number }
  suggested_fix?: string
  intent_preserved?: {
    purpose: string
    cta: string
    claims_changed: string[]
    safe: boolean
  }
  decisions?: FindingDecision[]
  created_at: string
}

export type ContentRevision = {
  id: string
  content_id: string
  version: number
  caption: string
  creative_filename?: string
  ocr_status: 'not_run' | 'completed' | 'failed' | 'not_supported'
  ocr_text?: string
  alt_text?: string
  is_ai_media: boolean
  is_paid_gifted?: boolean
  detected_language: string
  image_analysis?: any
  created_by: string
  created_at: string
}

export type ContentItem = {
  id: string
  workspace_id?: string
  title: string
  channel: Channel
  campaign: string
  status: ContentStatus
  current_revision: number
  created_by: string
  created_at: string
  updated_at: string
  revisions?: ContentRevision[]
  findings?: ClaimFinding[]
}

export type JobStatus = 'queued' | 'running' | 'completed' | 'failed'
export type JobStage = 'masking' | 'rules' | 'claims' | 'tone' | 'images' | 'completed'

export type ReviewJob = {
  id: string
  job_type: string
  status: JobStatus
  progress: number
  stage: JobStage
  error?: string
}

export type Rule = {
  id: string
  workspace_id?: string
  name: string
  description: string
  rule_type: string
  severity: FindingSeverity
  channel_scope: string
  pattern?: string
  status: 'draft' | 'active' | 'retired'
  version: number
  created_at: string
}

export type Fact = {
  id: string
  workspace_id?: string
  statement: string
  claim_value?: string
  unit?: string
  source_reference: string
  valid_from?: string
  valid_until?: string
  status?: 'active' | 'expired'
  version: number
  created_at: string
}

export type BrandAsset = {
  id: string
  workspace_id?: string
  name: string
  asset_type: string
  content_json: any
  created_at: string
}

export type AuditEvent = {
  id: string
  user_id: string
  user_name?: string
  action: string
  details: Record<string, any>
  created_at: string
}

// ── B3: Notifications ─────────────────────────────────────────────────────────
export type NotificationType =
  | 'assigned_for_review'
  | 'decision_made'
  | 'fact_expiring'
  | 'precedent_awaiting_approval'

export type AppNotification = {
  id: string
  type: NotificationType
  title: string
  message: string
  link?: string
  created_at: string
  read?: boolean
}

// ── B3: Comments ──────────────────────────────────────────────────────────────
export type Comment = {
  id: string
  content_id: string
  finding_id?: string
  parent_id?: string
  user_id: string
  user_name: string
  user_role: Role
  body: string
  resolved: boolean
  replies?: Comment[]
  created_at: string
}

// ── B3: Review Queue ──────────────────────────────────────────────────────────
export type QueueItem = {
  id: string
  title: string
  channel: Channel
  campaign: string
  status: ContentStatus
  created_by_name: string
  created_at: string
  priority_score: number
  critical_count: number
  major_count: number
  advisory_count: number
  disputed_count: number
}

export type ReviewQueuePage = {
  items: QueueItem[]
  total: number
  limit: number
  offset: number
}

// ── B3: Members ───────────────────────────────────────────────────────────────
export type WorkspaceMember = {
  id: string
  workspace_id: string
  email: string
  full_name: string
  role: Role
  is_active: boolean
  created_at: string
}

// ── B3: Guidelines / Rules with version history ───────────────────────────────
export type RuleVersion = {
  version: number
  name: string
  description: string
  status: 'draft' | 'active' | 'retired'
  changed_by: string
  created_at: string
}

export type RuleWithHistory = Rule & {
  versions?: RuleVersion[]
  good_examples?: string[]
  bad_examples?: string[]
  source_page?: string
  is_india_pack?: boolean
}

// ── B3: Fact with version history ─────────────────────────────────────────────
export type FactVersion = {
  version: number
  statement: string
  valid_from?: string
  valid_until?: string
  changed_by: string
  created_at: string
}

export type FactWithHistory = Fact & {
  versions?: FactVersion[]
  expiry_warning?: boolean
}

// ── B3: Approval ──────────────────────────────────────────────────────────────
export type ApprovalResult = {
  content_id: string
  status: ContentStatus
  locked_revision_id?: string
  snapshot_version?: number
  approved_at?: string
  approved_by?: string
  blockers?: string[]
}

// ── B3: Guideline upload ──────────────────────────────────────────────────────
export type GuidelineUploadResult = {
  guideline_id: string
  source_filename: string
  draft_rules: Array<{
    id: string
    name: string
    description: string
    source_page?: string
    severity: FindingSeverity
  }>
  total_pages: number
}


// ── B4: Insights, Reports & Round 3 Governance ─────────────────────────────

export type InsightsSummary = {
  workspace_id: string
  total_items: number
  approved_items: number
  total_findings: number
  severity_distribution: {
    critical: number
    major: number
    advisory: number
  }
  overrides_total: number
  disputes_total: number
  expiring_facts_count: number
  average_approval_hours: number
  average_review_rounds: number
  model_mode: string
  is_seeded_reference?: boolean
}

export type TopRuleBroken = {
  group_by: 'channel' | 'creator' | 'week'
  data: Array<{
    channel?: string
    creator?: string
    week?: string
    rule_code: string
    count: number
  }>
}

export type OverrideRateItem = {
  rule_code: string
  overrides: number
  disputes: number
  total: number
  override_rate_pct: number
  dispute_rate_pct: number
}

export type ExpiringFactItem = {
  id: string
  code: string
  statement: string
  valid_to: string
  days_remaining: number
  is_expired: boolean
  requires_review: boolean
}

export type ComplianceReport = {
  report_id: string
  generated_at: string
  workspace_id: string
  content: {
    id: string
    title: string
    channel: Channel
    campaign: string
    status: ContentStatus
    created_by: string
    created_at?: string
  }
  approved_revision: {
    id: string
    version: number
    caption: string
    alt_text?: string
    is_ai_media: boolean
    ocr_status: string
    ocr_text?: string
    detected_language: string
    locked_at?: string
    approved_by?: string
    snapshot_version?: number
  }
  governance_notice: string
  masking_status: {
    is_masked: boolean
    protocol: string
    secret_terms_masked: boolean
    personal_data_masked: boolean
  }
  stated_limits: string[]
  intent_preserved: {
    purpose: string
    call_to_action_preserved: boolean
    claims_changed: string[]
    safe_to_publish: boolean
  }
  findings: Array<{
    finding_id: string
    claim_text: string
    verdict: FindingVerdict
    severity: FindingSeverity
    analysis_method: string
    state: FindingState
    rationale: string
    evidence: Array<{
      source_type: string
      code: string
      version: number
      title: string
      valid_until?: string
    }>
    decisions: Array<{
      id: string
      action: string
      reason: string
      decided_by: string
      created_at?: string
    }>
  }>
  models_and_services_used: Array<{
    call_id: string
    provider: string
    model: string
    purpose: string
    characters_sent: number
    entities_masked: number
    duration_ms?: number
    status: string
  }>
}

export type GuidelineHealthIssue = {
  type: string
  severity: string
  rule_id?: string
  other_rule_id?: string
  code: string
  title: string
  explanation: string
  suggestion: string
  accepted?: boolean
  edited_text?: string
  ignored?: boolean
}

export type GuidelineHealthReport = {
  active_rules: number
  issue_count: number
  issues: GuidelineHealthIssue[]
  method: string
  notice: string
}

export type PrecedentItem = {
  id: string
  finding_id: string
  rule_id?: string
  channel: string
  pattern_text: string
  reason: string
  valid_to?: string
  status: 'pending' | 'approved'
  created_by: string
  approved_by?: string
  created_at: string
}

export type ActiveModel = {
  name: string
  provider: string
  purpose: string
  is_local: boolean
  status: string
}

export type DataFlowLogItem = {
  id: string
  revision_id?: string
  provider: string
  model: string
  purpose: string
  input_chars: number
  masked_entities: number
  started_at?: string
  duration_ms?: number
  status: string
  masking_confirmed: boolean
}

export type ModelSettings = {
  local_model_enabled: boolean
  active_models: ActiveModel[]
  data_flow_log: DataFlowLogItem[]
  masking_policy: {
    strict_pre_masking: boolean
    secret_terms_masked: boolean
    personal_identifiable_info_masked: boolean
  }
}
