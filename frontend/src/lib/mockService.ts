import {
  User,
  ContentItem,
  ContentRevision,
  ClaimFinding,
  ReviewJob,
  Rule,
  Fact,
  BrandAsset,
  AuditEvent,
  FindingDecision,
  Role,
  ContentStatus,
  FindingSeverity,
  Comment,
  AppNotification,
  WorkspaceMember,
  RuleWithHistory,
  FactWithHistory,
  ApprovalResult,
  GuidelineUploadResult,
  ReviewQueuePage,
  InsightsSummary,
  TopRuleBroken,
  OverrideRateItem,
  ExpiringFactItem,
  ComplianceReport,
  GuidelineHealthReport,
  PrecedentItem,
  ModelSettings,
} from '../types/api'

// Deterministic in-memory storage for mock mode before A1 API merge
let mockUser: User = {
  id: 'usr-101',
  workspace_id: 'ws-aurora-7',
  email: 'creator@aurorabrand.com',
  full_name: 'Priya Sharma',
  role: 'creator',
}

let mockContentItems: ContentItem[] = [
  {
    id: 'cnt-glowserum-1',
    workspace_id: 'ws-aurora-7',
    title: 'GlowSerum Launch Instagram Reel',
    channel: 'instagram',
    campaign: 'Festive Radiance 2026',
    status: 'analyzed',
    current_revision: 1,
    created_by: 'usr-101',
    created_at: new Date(Date.now() - 3600000).toISOString(),
    updated_at: new Date(Date.now() - 1800000).toISOString(),
  },
]

let mockRevisions: Record<string, ContentRevision[]> = {
  'cnt-glowserum-1': [
    {
      id: 'rev-1',
      content_id: 'cnt-glowserum-1',
      version: 1,
      caption:
        "Experience India's #1 radiant skin formula! Our clinically proven GlowSerum cures acne and lightens dark spots in just 28 days with 100% natural organic saffron extracts. Dermatologist tested and guaranteed results.",
      creative_filename: 'glowserum-hero.png',
      ocr_status: 'completed',
      ocr_text: "AURORA GLOWSERUM - CURES ACNE IN 28 DAYS - INDIA'S #1 DERMA FORMULA",
      alt_text: 'Bottle of Aurora GlowSerum with saffron dropper and botanical elements',
      is_ai_media: false,
      is_paid_gifted: true,
      detected_language: 'en',
      created_by: 'usr-101',
      created_at: new Date(Date.now() - 3600000).toISOString(),
    },
  ],
}

let mockFindings: Record<string, ClaimFinding[]> = {
  'cnt-glowserum-1': [
    {
      id: 'fnd-1',
      content_id: 'cnt-glowserum-1',
      revision_id: 'rev-1',
      claim_text: "India's #1 radiant skin formula",
      verdict: 'unsupported',
      severity: 'critical',
      layer: 'rules',
      analysis_method: 'deterministic_rule_in_2',
      rationale:
        'Starter rule IN-2: Absolute leadership claim ("India\'s #1") requires an audited third-party market share report or syndicated survey source dated within 12 months.',
      span: { start: 11, end: 41 },
      confidence: 0.98,
      rule_id: 'RULE-IN-002',
      rule_version: 1,
      rule_valid_from: '2025-01-01',
      rule_valid_until: '2027-12-31',
      suggested_fix: 'Our premier radiant skin formula',
      intent_preserved: {
        purpose: 'Highlight product excellence and high market stature',
        cta: 'Experience formula',
        claims_changed: ['Removed unverified rank #1 superlative'],
        safe: true,
      },
      evidence: [
        {
          source_type: 'rule',
          source_id: 'RULE-IN-002',
          title: 'India ASCI Rule 2: Comparative Superlative Substantiation',
          statement:
            'Claims claiming #1 rank must cite syndicated market research or independent retail audit data.',
          source_reference: 'ASCI Guidelines Chapter 1.4',
          version: 1,
        },
      ],
      state: 'open',
      decisions: [],
      created_at: new Date(Date.now() - 3500000).toISOString(),
    },
    {
      id: 'fnd-2',
      content_id: 'cnt-glowserum-1',
      revision_id: 'rev-1',
      claim_text: 'cures acne',
      verdict: 'contradicted',
      severity: 'critical',
      layer: 'rules',
      analysis_method: 'starter_rule_in_5_prohibited_drug_claims',
      rationale:
        'Rule IN-5: Cosmetic products cannot make therapeutic "cure" claims for medical skin disorders (Acne vulgaris) under the Drugs and Cosmetics Act.',
      span: { start: 79, end: 89 },
      confidence: 1.0,
      rule_id: 'RULE-IN-005',
      rule_version: 2,
      rule_valid_from: '2024-06-01',
      rule_valid_until: '2027-01-01',
      suggested_fix: 'reduces the appearance of acne blemishes',
      intent_preserved: {
        purpose: 'Convey efficacy in tackling acne spots without medicinal cure claims',
        cta: 'None',
        claims_changed: ['Changed disease cure to cosmetic blemish appearance reduction'],
        safe: true,
      },
      evidence: [
        {
          source_type: 'rule',
          source_id: 'RULE-IN-005',
          title: 'Drugs & Magic Remedies / Cosmetics Act Rule 5',
          statement:
            'Cosmetics may claim to cleanse, soothe or improve appearance, but must not claim treatment or cure for clinical conditions.',
          source_reference: 'Schedule J & ASCI Code 2.2',
          version: 2,
        },
        {
          source_type: 'fact',
          source_id: 'FACT-012',
          title: 'Clinical Trial CT-2025-08',
          statement: 'Aurora GlowSerum reduced visible blemish surface area by 42% in 28 days.',
          claim_value: '42%',
          unit: 'reduction',
          source_reference: 'Dermatological Evaluation Study Report 2025-08',
          valid_from: '2025-01-01',
          valid_until: '2027-01-01',
        },
      ],
      state: 'open',
      decisions: [],
      created_at: new Date(Date.now() - 3500000).toISOString(),
    },
    {
      id: 'fnd-3',
      content_id: 'cnt-glowserum-1',
      revision_id: 'rev-1',
      claim_text: 'just 28 days',
      verdict: 'supported',
      severity: 'advisory',
      layer: 'claims',
      analysis_method: 'normalized_duration_match',
      rationale:
        'Matched approved Fact FACT-012: 28 days equals 4 weeks trial duration verified in internal study CT-2025-08.',
      span: { start: 120, end: 132 },
      confidence: 0.95,
      suggested_fix: '28 days',
      evidence: [
        {
          source_type: 'fact',
          source_id: 'FACT-012',
          title: 'Clinical Trial CT-2025-08',
          statement: 'Evaluated across 120 participants over a 28-day regimen.',
          source_reference: 'Study CT-2025-08',
          version: 1,
        },
      ],
      state: 'open',
      decisions: [],
      created_at: new Date(Date.now() - 3500000).toISOString(),
    },
  ],
}

let mockJobs: Record<string, ReviewJob> = {}

// ── B3 seed data ─────────────────────────────────────────────────────────────

const mockMembers: WorkspaceMember[] = [
  {
    id: 'usr-101',
    workspace_id: 'ws-aurora-7',
    email: 'creator@aurorabrand.com',
    full_name: 'Priya Sharma',
    role: 'creator',
    is_active: true,
    created_at: '2025-01-10T09:00:00Z',
  },
  {
    id: 'usr-102',
    workspace_id: 'ws-aurora-7',
    email: 'reviewer@aurorabrand.com',
    full_name: 'Rohit Verma',
    role: 'reviewer',
    is_active: true,
    created_at: '2025-01-11T09:00:00Z',
  },
  {
    id: 'usr-103',
    workspace_id: 'ws-aurora-7',
    email: 'manager@aurorabrand.com',
    full_name: 'Deepa Nair',
    role: 'manager',
    is_active: true,
    created_at: '2025-01-12T09:00:00Z',
  },
  {
    id: 'usr-104',
    workspace_id: 'ws-aurora-7',
    email: 'admin@aurorabrand.com',
    full_name: 'Arjun Patel',
    role: 'admin',
    is_active: true,
    created_at: '2025-01-13T09:00:00Z',
  },
]

const mockRules: RuleWithHistory[] = [
  {
    id: 'RULE-IN-001',
    workspace_id: 'ws-aurora-7',
    name: 'Mandatory Paid Partnership Disclosure',
    description: 'All paid or gifted content must include #Ad or Paid Partnership disclosure.',
    rule_type: 'disclosure',
    severity: 'critical',
    channel_scope: 'instagram,facebook',
    status: 'active',
    version: 1,
    is_india_pack: true,
    good_examples: ['#Ad #GlowSerum — gifted by Aurora Brand'],
    bad_examples: ['Try GlowSerum! (no disclosure for gifted product)'],
    created_at: '2025-01-01T00:00:00Z',
  },
  {
    id: 'RULE-IN-002',
    workspace_id: 'ws-aurora-7',
    name: 'Superlative Substantiation',
    description:
      'Claims of #1 rank require an audited third-party market share or syndicated survey source dated within 12 months.',
    rule_type: 'claim_verification',
    severity: 'critical',
    channel_scope: 'all',
    status: 'active',
    version: 2,
    is_india_pack: true,
    good_examples: ['Ranked #1 in Nielsen Skincare Survey 2026 (Q1)'],
    bad_examples: ["India's #1 skincare brand (no source)"],
    created_at: '2025-01-01T00:00:00Z',
  },
  {
    id: 'RULE-IN-005',
    workspace_id: 'ws-aurora-7',
    name: 'No Therapeutic/Cure Claims for Cosmetics',
    description:
      'Cosmetics cannot claim to treat or cure medical conditions under the Drugs and Cosmetics Act, 1940.',
    rule_type: 'prohibited_claim',
    severity: 'critical',
    channel_scope: 'all',
    status: 'active',
    version: 2,
    is_india_pack: true,
    good_examples: ['Reduces the appearance of acne blemishes'],
    bad_examples: ['Cures acne in 28 days'],
    created_at: '2024-06-01T00:00:00Z',
  },
  {
    id: 'RULE-GLOBAL-01',
    workspace_id: 'ws-aurora-7',
    name: 'AI-Generated Media Disclosure',
    description: 'AI-generated images must be labelled "AI-generated imagery" in caption or overlay.',
    rule_type: 'disclosure',
    severity: 'major',
    channel_scope: 'all',
    status: 'active',
    version: 1,
    is_india_pack: false,
    good_examples: ['AI-generated imagery | GlowSerum'],
    bad_examples: ['[AI image with no disclosure]'],
    created_at: '2025-03-01T00:00:00Z',
  },
]

const mockFacts: FactWithHistory[] = [
  {
    id: 'FACT-012',
    workspace_id: 'ws-aurora-7',
    statement: 'Aurora GlowSerum reduced visible blemish surface area by 42% in 28 days.',
    claim_value: '42%',
    unit: 'reduction',
    source_reference: 'Dermatological Evaluation Study Report 2025-08',
    valid_from: '2025-01-01',
    valid_until: '2027-01-01',
    status: 'active',
    version: 1,
    expiry_warning: false,
    created_at: '2025-01-15T00:00:00Z',
  },
  {
    id: 'FACT-015',
    workspace_id: 'ws-aurora-7',
    statement: '95% of users reported brighter skin tone after 4 weeks.',
    claim_value: '95%',
    unit: 'users',
    source_reference: 'Consumer Perception Study Q1-2026',
    valid_from: '2026-01-01',
    valid_until: '2026-12-15',
    status: 'active',
    version: 1,
    expiry_warning: true,
    created_at: '2026-01-20T00:00:00Z',
  },
]

const mockAssets: BrandAsset[] = [
  {
    id: 'asset-01',
    workspace_id: 'ws-aurora-7',
    name: 'Primary Palette',
    asset_type: 'palette',
    content_json: {
      primary: '#7C3AED',
      secondary: '#F59E0B',
      neutral: '#F3F4F6',
    },
    created_at: '2025-01-01T00:00:00Z',
  },
  {
    id: 'asset-02',
    workspace_id: 'ws-aurora-7',
    name: 'Secret Term List',
    asset_type: 'secret_terms',
    content_json: { terms: ['GlowX-Pro', 'Project Radiance', 'AuraClin'] },
    created_at: '2025-01-01T00:00:00Z',
  },
]

const mockComments: Record<string, Comment[]> = {}

const mockAuditEvents: AuditEvent[] = [
  {
    id: 'evt-001',
    user_id: 'usr-101',
    user_name: 'Priya Sharma',
    action: 'content.submitted',
    details: { content_id: 'cnt-glowserum-1', title: 'GlowSerum Launch Instagram Reel' },
    created_at: new Date(Date.now() - 7200000).toISOString(),
  },
  {
    id: 'evt-002',
    user_id: 'usr-102',
    user_name: 'Rohit Verma',
    action: 'review.started',
    details: { content_id: 'cnt-glowserum-1' },
    created_at: new Date(Date.now() - 3600000).toISOString(),
  },
  {
    id: 'evt-003',
    user_id: 'usr-102',
    user_name: 'Rohit Verma',
    action: 'finding.overridden',
    details: { finding_id: 'fnd-1', reason: 'Verified via submitted market share report.' },
    created_at: new Date(Date.now() - 1800000).toISOString(),
  },
  {
    id: 'evt-004',
    user_id: 'usr-003',
    user_name: 'Deepa Nair',
    action: 'content.approved',
    details: { content_id: 'cnt-glowserum-1', locked_revision_id: 'rev-1' },
    created_at: new Date(Date.now() - 900000).toISOString(),
  },
]

const mockPrecedents: PrecedentItem[] = [
  {
    id: 'prec-001',
    finding_id: 'fnd-1',
    rule_id: 'IN-ASCI-01',
    channel: 'instagram',
    pattern_text: "India's #1 radiant skin formula",
    reason: 'Permitted when market share audit report from Nielsen/Kantar (Q4-2025) is cited in caption link.',
    status: 'approved',
    valid_to: '2026-12-31T23:59:59Z',
    created_by: 'usr-102',
    approved_by: 'usr-003',
    created_at: '2026-02-01T10:00:00Z',
  },
  {
    id: 'prec-002',
    finding_id: 'fnd-2',
    rule_id: 'RUL-CLINICAL-02',
    channel: 'all',
    pattern_text: 'clinically proven GlowSerum cures acne',
    reason: 'Acne prevention phrasing approved only when referencing clinical trial CT-9941; curative language prohibited.',
    status: 'pending',
    valid_to: '2026-09-30T23:59:59Z',
    created_by: 'usr-102',
    created_at: '2026-02-05T14:30:00Z',
  },
]

let mockGuidelineHealthIssues: any[] = [
  {
    type: 'possible_conflict',
    severity: 'major',
    rule_id: 'RUL-CLINICAL-02',
    other_rule_id: 'RUL-VOICE-01',
    code: 'RUL-CLINICAL-02 / RUL-VOICE-01',
    title: 'Clinical Efficacy Rigor ↔ Friendly Brand Voice',
    explanation:
      'RUL-CLINICAL-02 mandates exact clinical metrics (p-values, trial duration), whereas RUL-VOICE-01 encourages colloquial, jargon-free conversational storytelling. Creators are forced into frequent disputes.',
    suggestion: 'Allow simplified percentage improvements in primary captions with clinical citations in footnotes or link-in-bio.',
    accepted: false,
    ignored: false,
  },
  {
    type: 'vague_rule',
    severity: 'major',
    rule_id: 'RUL-TONE-03',
    code: 'RUL-TONE-03',
    title: 'Maintain Appropriate Product Premiumness',
    explanation:
      'Contains subjective terms: "appropriate", "good quality". Rules without objective thresholds lead to high reviewer inconsistency.',
    suggestion: 'Replace with: "Do not use discount emojis (💥🔥), all-caps promotional verbs (BUY NOW), or unverified urgency claims."',
    accepted: false,
    ignored: false,
  },
  {
    type: 'high_override_rate',
    severity: 'major',
    rule_id: 'IN-ASCI-01',
    code: 'IN-ASCI-01',
    title: 'Superlative & Ranking Substantiation',
    explanation:
      'This rule accounts for 45% of all reviewer overrides in Q1. Most creators submit valid Kantar reports that reviewers manually approve.',
    suggestion: 'Automate validation by registering Kantar and Nielsen market share certificates directly in the Brand Facts table.',
    accepted: false,
    ignored: false,
  },
]

let mockLocalModelEnabled = false

export const mockService = {
  getUser: () => mockUser,
  setUserRole: (role: User['role']) => {
    mockUser = { ...mockUser, role }
    return mockUser
  },
  listContent: async (): Promise<ContentItem[]> => {
    return [...mockContentItems]
  },
  getContent: async (id: string): Promise<ContentItem | null> => {
    const item = mockContentItems.find((x) => x.id === id)
    if (!item) return null
    return {
      ...item,
      revisions: mockRevisions[id] || [],
      findings: mockFindings[id] || [],
    }
  },
  createContent: async (data: {
    title: string
    channel: ContentItem['channel']
    campaign?: string
    caption?: string
    alt_text?: string
    is_ai_media?: boolean
    is_paid_gifted?: boolean
  }): Promise<ContentItem> => {
    const newId = `cnt-${Date.now()}`
    const revId = `rev-${Date.now()}`
    const newItem: ContentItem = {
      id: newId,
      workspace_id: mockUser.workspace_id,
      title: data.title,
      channel: data.channel,
      campaign: data.campaign || '',
      status: 'draft',
      current_revision: 1,
      created_by: mockUser.id,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    }
    const newRev: ContentRevision = {
      id: revId,
      content_id: newId,
      version: 1,
      caption: data.caption || '',
      alt_text: data.alt_text || '',
      is_ai_media: data.is_ai_media || false,
      is_paid_gifted: data.is_paid_gifted || false,
      ocr_status: 'not_run',
      detected_language: 'en',
      created_by: mockUser.id,
      created_at: new Date().toISOString(),
    }
    mockContentItems.unshift(newItem)
    mockRevisions[newId] = [newRev]
    mockFindings[newId] = []
    return { ...newItem, revisions: [newRev], findings: [] }
  },
  createRevision: async (
    contentId: string,
    data: {
      caption: string
      alt_text?: string
      is_ai_media?: boolean
      is_paid_gifted?: boolean
      title?: string
      channel?: ContentItem['channel']
      campaign?: string
    }
  ): Promise<ContentRevision> => {
    const item = mockContentItems.find((x) => x.id === contentId)
    if (!item) throw new Error('Content not found')
    const revs = mockRevisions[contentId] || []
    const nextVer = (revs[0]?.version || 0) + 1
    const newRev: ContentRevision = {
      id: `rev-${Date.now()}`,
      content_id: contentId,
      version: nextVer,
      caption: data.caption,
      alt_text: data.alt_text ?? revs[0]?.alt_text,
      is_ai_media: data.is_ai_media ?? revs[0]?.is_ai_media ?? false,
      is_paid_gifted: data.is_paid_gifted ?? revs[0]?.is_paid_gifted ?? false,
      creative_filename: revs[0]?.creative_filename,
      ocr_status: revs[0]?.ocr_status || 'not_run',
      ocr_text: revs[0]?.ocr_text,
      detected_language: 'en',
      created_by: mockUser.id,
      created_at: new Date().toISOString(),
    }
    revs.unshift(newRev)
    item.current_revision = nextVer
    item.updated_at = new Date().toISOString()
    if (data.title) item.title = data.title
    if (data.channel) item.channel = data.channel
    if (data.campaign) item.campaign = data.campaign
    return newRev
  },
  startAnalysisJob: async (contentId: string): Promise<string> => {
    const jobId = `job-${Date.now()}`
    mockJobs[jobId] = {
      id: jobId,
      job_type: 'claim_court_review',
      status: 'queued',
      progress: 0,
      stage: 'masking',
    }
    // Simulate real asynchronous progress stages
    setTimeout(() => {
      if (mockJobs[jobId]) mockJobs[jobId] = { ...mockJobs[jobId], status: 'running', progress: 20, stage: 'masking' }
    }, 400)
    setTimeout(() => {
      if (mockJobs[jobId]) mockJobs[jobId] = { ...mockJobs[jobId], progress: 40, stage: 'rules' }
    }, 900)
    setTimeout(() => {
      if (mockJobs[jobId]) mockJobs[jobId] = { ...mockJobs[jobId], progress: 65, stage: 'claims' }
    }, 1500)
    setTimeout(() => {
      if (mockJobs[jobId]) mockJobs[jobId] = { ...mockJobs[jobId], progress: 85, stage: 'tone' }
    }, 2100)
    setTimeout(() => {
      if (mockJobs[jobId]) {
        mockJobs[jobId] = { ...mockJobs[jobId], status: 'completed', progress: 100, stage: 'completed' }
        const item = mockContentItems.find((x) => x.id === contentId)
        if (item) item.status = 'analyzed'
      }
    }, 2800)
    return jobId
  },
  getJob: async (jobId: string): Promise<ReviewJob> => {
    return (
      mockJobs[jobId] || {
        id: jobId,
        job_type: 'claim_court_review',
        status: 'completed',
        progress: 100,
        stage: 'completed',
      }
    )
  },
  submitFindingDecision: async (
    contentId: string,
    findingId: string,
    action: 'accept' | 'dispute' | 'override' | 'resolve',
    note?: string
  ): Promise<ClaimFinding> => {
    const findings = mockFindings[contentId] || []
    const finding = findings.find((f) => f.id === findingId)
    if (!finding) throw new Error('Finding not found')

    const decision: FindingDecision = {
      id: `dec-${Date.now()}`,
      action,
      user_id: mockUser.id,
      user_name: mockUser.full_name,
      user_role: mockUser.role,
      note,
      created_at: new Date().toISOString(),
    }
    finding.decisions = [...(finding.decisions || []), decision]
    finding.state =
      action === 'accept'
        ? 'accepted'
        : action === 'dispute'
          ? 'disputed'
          : action === 'override'
            ? 'overridden'
            : 'resolved'
    return finding
  },
  submitForReview: async (contentId: string): Promise<ContentItem> => {
    const item = mockContentItems.find((x) => x.id === contentId)
    if (!item) throw new Error('Content not found')
    item.status = 'submitted'
    item.updated_at = new Date().toISOString()
    return item
  },
  startReview: async (contentId: string): Promise<ContentItem> => {
    const item = mockContentItems.find((x) => x.id === contentId)
    if (!item) throw new Error('Content not found')
    item.status = 'in_review'
    item.updated_at = new Date().toISOString()
    return item
  },
  approveContent: async (contentId: string): Promise<ContentItem> => {
    const item = mockContentItems.find((x) => x.id === contentId)
    if (!item) throw new Error('Content not found')
    const findings = mockFindings[contentId] || []
    const blockers = findings.filter(
      (f) =>
        f.state !== 'accepted' &&
        f.state !== 'overridden' &&
        f.state !== 'resolved' &&
        (f.severity === 'critical' || f.verdict === 'contradicted' || f.verdict === 'outdated' || f.verdict === 'unsupported')
    )
    if (blockers.length > 0) {
      throw new Error(`Cannot approve: ${blockers.length} unresolved blocking findings exist.`)
    }
    item.status = 'approved'
    item.updated_at = new Date().toISOString()
    return item
  },
  rejectContent: async (contentId: string): Promise<ContentItem> => {
    const item = mockContentItems.find((x) => x.id === contentId)
    if (!item) throw new Error('Content not found')
    item.status = 'rejected'
    item.updated_at = new Date().toISOString()
    return item
  },
  reopenContent: async (contentId: string): Promise<ContentItem> => {
    const item = mockContentItems.find((x) => x.id === contentId)
    if (!item) throw new Error('Content not found')
    item.status = 'draft'
    item.updated_at = new Date().toISOString()
    return item
  },

  // ── B3 methods ─────────────────────────────────────────────────────────────

  listReviewQueue: async (params?: {
    status?: ContentStatus
    channel?: string
    severity?: FindingSeverity
    creator?: string
    include_advisory?: boolean
    limit?: number
    offset?: number
  }): Promise<ReviewQueuePage> => {
    let items = mockContentItems
      .filter((c) => c.status === 'submitted' || c.status === 'in_review')
      .map((c) => {
        const findings = mockFindings[c.id] || []
        const critical_count = findings.filter((f) => f.severity === 'critical').length
        const major_count = findings.filter((f) => f.severity === 'major').length
        const advisory_count = findings.filter((f) => f.severity === 'advisory').length
        const disputed_count = findings.filter((f) => f.state === 'disputed').length
        const priority_score = critical_count * 100 + disputed_count * 50 + major_count * 30
        return {
          id: c.id,
          title: c.title,
          channel: c.channel,
          campaign: c.campaign,
          status: c.status,
          created_by_name: mockMembers.find((m) => m.id === c.created_by)?.full_name ?? 'Unknown',
          created_at: c.created_at,
          priority_score,
          critical_count,
          major_count,
          advisory_count,
          disputed_count,
        }
      })
    if (params?.status) items = items.filter((i) => i.status === params.status)
    if (params?.channel) items = items.filter((i) => i.channel === params.channel)
    if (!params?.include_advisory) {
      items = items.filter((i) => i.critical_count + i.major_count + i.disputed_count > 0)
    }
    items.sort((a, b) => b.priority_score - a.priority_score)
    const limit = params?.limit ?? 20
    const offset = params?.offset ?? 0
    return { items: items.slice(offset, offset + limit), total: items.length, limit, offset }
  },

  approveContentWithReason: async (contentId: string): Promise<ApprovalResult> => {
    const item = mockContentItems.find((x) => x.id === contentId)
    if (!item) throw new Error('Content not found')
    const findings = mockFindings[contentId] || []
    const blockers = findings
      .filter(
        (f) =>
          f.state !== 'overridden' &&
          f.state !== 'resolved' &&
          (f.severity === 'critical' ||
            f.verdict === 'contradicted' ||
            f.verdict === 'outdated' ||
            f.verdict === 'unsupported')
      )
      .map((f) => f.claim_text)
    if (blockers.length > 0) {
      throw Object.assign(new Error('Unresolved blockers prevent approval'), { blockers })
    }
    const lockedRevisionId = mockRevisions[contentId]?.[0]?.id ?? 'rev-unknown'
    item.status = 'approved'
    item.updated_at = new Date().toISOString()
    return {
      content_id: contentId,
      status: 'approved',
      locked_revision_id: lockedRevisionId,
      snapshot_version: item.current_revision,
      approved_at: new Date().toISOString(),
      approved_by: mockUser.id,
    }
  },

  rejectContentWithReason: async (contentId: string, _reason: string): Promise<ContentItem> => {
    const item = mockContentItems.find((x) => x.id === contentId)
    if (!item) throw new Error('Content not found')
    item.status = 'rejected'
    item.updated_at = new Date().toISOString()
    return item
  },

  overrideFinding: async (
    contentId: string,
    findingId: string,
    reason: string
  ): Promise<ClaimFinding> => {
    return mockService.submitFindingDecision(contentId, findingId, 'override', reason)
  },

  listComments: async (contentId: string, findingId?: string): Promise<Comment[]> => {
    const all = mockComments[contentId] || []
    if (findingId) return all.filter((c) => c.finding_id === findingId && !c.parent_id)
    return all.filter((c) => !c.finding_id && !c.parent_id).map((c) => ({
      ...c,
      replies: all.filter((r) => r.parent_id === c.id),
    }))
  },

  addComment: async (
    contentId: string,
    body: string,
    findingId?: string,
    parentId?: string
  ): Promise<Comment> => {
    if (!mockComments[contentId]) mockComments[contentId] = []
    const comment: Comment = {
      id: `cmt-${Date.now()}`,
      content_id: contentId,
      finding_id: findingId,
      parent_id: parentId,
      user_id: mockUser.id,
      user_name: mockUser.full_name,
      user_role: mockUser.role,
      body,
      resolved: false,
      created_at: new Date().toISOString(),
    }
    mockComments[contentId].push(comment)
    return comment
  },

  resolveComment: async (contentId: string, commentId: string): Promise<Comment> => {
    const list = mockComments[contentId] || []
    const c = list.find((x) => x.id === commentId)
    if (!c) throw new Error('Comment not found')
    c.resolved = true
    return c
  },

  listNotifications: async (): Promise<AppNotification[]> => {
    const expiring = mockFacts
      .filter((f) => f.expiry_warning)
      .map<AppNotification>((f) => ({
        id: `notif-exp-${f.id}`,
        type: 'fact_expiring',
        title: 'Fact Expiring Soon',
        message: `"${f.statement.substring(0, 60)}…" expires on ${f.valid_until}`,
        link: '/app/brand/facts',
        created_at: new Date().toISOString(),
        read: false,
      }))
    return expiring
  },

  listMembers: async (): Promise<WorkspaceMember[]> => [...mockMembers],

  inviteMember: async (email: string, role: Role): Promise<WorkspaceMember> => {
    const existing = mockMembers.find((m) => m.email === email)
    if (existing) throw new Error('Member already exists')
    const newMember: WorkspaceMember = {
      id: `usr-${Date.now()}`,
      workspace_id: mockUser.workspace_id,
      email,
      full_name: email.split('@')[0],
      role,
      is_active: true,
      created_at: new Date().toISOString(),
    }
    mockMembers.push(newMember)
    return newMember
  },

  changeMemberRole: async (userId: string, role: Role): Promise<WorkspaceMember> => {
    const m = mockMembers.find((x) => x.id === userId)
    if (!m) throw new Error('Member not found')
    m.role = role
    return m
  },

  deactivateMember: async (userId: string): Promise<WorkspaceMember> => {
    const m = mockMembers.find((x) => x.id === userId)
    if (!m) throw new Error('Member not found')
    if (m.id === mockUser.id) throw new Error('Cannot deactivate yourself')
    m.is_active = false
    return m
  },

  deleteWorkspaceData: async (_reason: string): Promise<{ audit_event_id: string }> => {
    return { audit_event_id: `evt-del-${Date.now()}` }
  },

  listRules: async (params?: {
    status?: 'draft' | 'active' | 'retired'
    is_india_pack?: boolean
  }): Promise<RuleWithHistory[]> => {
    let rules = [...mockRules]
    if (params?.status) rules = rules.filter((r) => r.status === params.status)
    if (params?.is_india_pack != null)
      rules = rules.filter((r) => r.is_india_pack === params.is_india_pack)
    return rules
  },

  updateRule: async (ruleId: string, data: Partial<RuleWithHistory>): Promise<RuleWithHistory> => {
    const rule = mockRules.find((r) => r.id === ruleId)
    if (!rule) throw new Error('Rule not found')
    Object.assign(rule, data)
    rule.version += 1
    return rule
  },

  listFacts: async (): Promise<FactWithHistory[]> => {
    const now = new Date()
    return mockFacts.map((f) => ({
      ...f,
      expiry_warning: f.valid_until
        ? (new Date(f.valid_until).getTime() - now.getTime()) / 86400000 <= 30
        : false,
    }))
  },

  createFact: async (data: {
    statement: string
    claim_value?: string
    unit?: string
    source_reference: string
    valid_from?: string
    valid_until?: string
  }): Promise<FactWithHistory> => {
    const newFact: FactWithHistory = {
      id: `FACT-${Date.now()}`,
      workspace_id: mockUser.workspace_id,
      statement: data.statement,
      claim_value: data.claim_value,
      unit: data.unit,
      source_reference: data.source_reference,
      valid_from: data.valid_from,
      valid_until: data.valid_until,
      status: 'active',
      version: 1,
      expiry_warning: false,
      created_at: new Date().toISOString(),
    }
    mockFacts.push(newFact)
    return newFact
  },

  listAssets: async (): Promise<BrandAsset[]> => [...mockAssets],

  upsertAsset: async (
    name: string,
    assetType: string,
    contentJson: unknown
  ): Promise<BrandAsset> => {
    const existing = mockAssets.find((a) => a.name === name && a.asset_type === assetType)
    if (existing) {
      existing.content_json = contentJson
      return existing
    }
    const newAsset: BrandAsset = {
      id: `asset-${Date.now()}`,
      workspace_id: mockUser.workspace_id,
      name,
      asset_type: assetType,
      content_json: contentJson,
      created_at: new Date().toISOString(),
    }
    mockAssets.push(newAsset)
    return newAsset
  },

  uploadGuideline: async (_file: File): Promise<GuidelineUploadResult> => {
    return {
      guideline_id: `guide-${Date.now()}`,
      source_filename: _file.name,
      draft_rules: [
        {
          id: `draft-${Date.now()}-1`,
          name: 'No unsubstantiated efficacy claims',
          description: 'Efficacy claims must reference a clinical study or approved fact.',
          source_page: '14',
          severity: 'major',
        },
      ],
      total_pages: 32,
    }
  },

  listAuditEvents: async (params?: {
    scope?: 'own' | 'assigned' | 'workspace' | 'rules'
    limit?: number
    offset?: number
  }): Promise<{ events: AuditEvent[]; total: number }> => {
    let events = [...mockAuditEvents]
    if (params?.scope === 'own') {
      events = events.filter((e) => e.user_id === mockUser.id)
    } else if (params?.scope === 'rules') {
      events = events.filter(
        (e) => e.action.startsWith('rule.') || e.action.startsWith('fact.')
      )
    }
    const limit = params?.limit ?? 20
    const offset = params?.offset ?? 0
    return { events: events.slice(offset, offset + limit), total: events.length }
  },

  // ── B4: Insights & Analytics ──────────────────────────────────────────────
  getInsightsSummary: async (): Promise<InsightsSummary> => {
    return {
      workspace_id: 'ws-aurora-7',
      total_items: 12,
      approved_items: 8,
      total_findings: 34,
      severity_distribution: {
        critical: 4,
        major: 12,
        advisory: 18,
      },
      overrides_total: 9,
      disputes_total: 5,
      expiring_facts_count: 1,
      average_approval_hours: 3.8,
      average_review_rounds: 1.5,
      model_mode: mockLocalModelEnabled ? 'local' : 'deterministic',
      is_seeded_reference: false,
    }
  },

  getTopRulesBroken: async (
    groupBy: 'channel' | 'creator' | 'week' = 'channel'
  ): Promise<TopRuleBroken> => {
    if (groupBy === 'creator') {
      return {
        group_by: 'creator',
        data: [
          { creator: 'Priya Sharma', rule_code: 'IN-ASCI-01', count: 6 },
          { creator: 'Priya Sharma', rule_code: 'RUL-CLINICAL-02', count: 4 },
          { creator: 'Ananya Roy', rule_code: 'TONE-HYPER-01', count: 5 },
          { creator: 'Ananya Roy', rule_code: 'CLM-PERC-04', count: 3 },
          { creator: 'Vikram Joshi', rule_code: 'IN-ASCI-01', count: 4 },
        ],
      }
    }
    if (groupBy === 'week') {
      return {
        group_by: 'week',
        data: [
          { week: 'Week 5', rule_code: 'IN-ASCI-01', count: 5 },
          { week: 'Week 5', rule_code: 'RUL-CLINICAL-02', count: 3 },
          { week: 'Week 6', rule_code: 'IN-ASCI-01', count: 7 },
          { week: 'Week 6', rule_code: 'CLM-PERC-04', count: 4 },
          { week: 'Week 7', rule_code: 'TONE-HYPER-01', count: 6 },
        ],
      }
    }
    return {
      group_by: 'channel',
      data: [
        { channel: 'instagram', rule_code: 'IN-ASCI-01', count: 12 },
        { channel: 'instagram', rule_code: 'CLM-PERC-04', count: 8 },
        { channel: 'website', rule_code: 'RUL-CLINICAL-02', count: 6 },
        { channel: 'linkedin', rule_code: 'TONE-HYPER-01', count: 4 },
        { channel: 'paid_ad', rule_code: 'IN-ASCI-01', count: 9 },
      ],
    }
  },

  getOverrideRates: async (): Promise<{ rules: OverrideRateItem[] }> => {
    return {
      rules: [
        {
          rule_code: 'IN-ASCI-01',
          overrides: 8,
          disputes: 3,
          total: 21,
          override_rate_pct: 38.1,
          dispute_rate_pct: 14.3,
        },
        {
          rule_code: 'TONE-HYPER-01',
          overrides: 6,
          disputes: 2,
          total: 15,
          override_rate_pct: 40.0,
          dispute_rate_pct: 13.3,
        },
        {
          rule_code: 'RUL-CLINICAL-02',
          overrides: 2,
          disputes: 1,
          total: 14,
          override_rate_pct: 14.3,
          dispute_rate_pct: 7.1,
        },
        {
          rule_code: 'CLM-PERC-04',
          overrides: 1,
          disputes: 0,
          total: 10,
          override_rate_pct: 10.0,
          dispute_rate_pct: 0.0,
        },
      ],
    }
  },

  getExpiringFacts: async (): Promise<{ facts: ExpiringFactItem[] }> => {
    return {
      facts: [
        {
          id: 'FACT-015',
          code: 'FACT-015',
          statement: '95% of users reported brighter skin tone after 4 weeks.',
          valid_to: '2026-12-15T00:00:00Z',
          days_remaining: 24,
          is_expired: false,
          requires_review: true,
        },
        {
          id: 'FACT-008',
          code: 'FACT-008',
          statement: 'Dermatologist tested by DermScan Asia on 120 Indian female subjects.',
          valid_to: '2027-01-30T00:00:00Z',
          days_remaining: 72,
          is_expired: false,
          requires_review: false,
        },
      ],
    }
  },

  downloadReportJson: async (contentId: string): Promise<ComplianceReport> => {
    const item = mockContentItems.find((x) => x.id === contentId)
    const rev = (mockRevisions[contentId] || [])[0]
    return {
      report_id: `RPT-${(contentId || 'DEMO').slice(0, 8).toUpperCase()}-V1`,
      generated_at: new Date().toISOString(),
      workspace_id: 'ws-aurora-7',
      content: {
        id: item?.id || contentId,
        title: item?.title || 'GlowSerum Launch Instagram Reel',
        channel: item?.channel || 'instagram',
        campaign: item?.campaign || 'Festive Radiance 2026',
        status: item?.status || 'approved',
        created_by: 'Priya Sharma (creator)',
        created_at: item?.created_at,
      },
      approved_revision: {
        id: rev?.id || 'rev-1',
        version: rev?.version || 1,
        caption: rev?.caption || '',
        alt_text: rev?.alt_text,
        is_ai_media: rev?.is_ai_media ?? false,
        ocr_status: rev?.ocr_status || 'completed',
        ocr_text: rev?.ocr_text,
        detected_language: rev?.detected_language || 'en-IN',
        locked_at: new Date().toISOString(),
        approved_by: 'Deepa Nair (manager)',
        snapshot_version: 1,
      },
      governance_notice:
        'BrandCourt is an evidence-first governance platform. Approval confirms internal compliance only. Content is not published to social platforms.',
      masking_status: {
        is_masked: true,
        protocol: 'Deterministic regex and secret dictionary tokenization',
        secret_terms_masked: true,
        personal_data_masked: true,
      },
      stated_limits: [
        'Deterministic code first, AI second. No source reference means no error-level finding.',
        'The starter India rules pack provides guidance, not legal advice.',
      ],
      intent_preserved: {
        purpose: 'Festive season product launch highlighting natural saffron benefits',
        call_to_action_preserved: true,
        claims_changed: ['Substantiated dark spot reduction claim with FACT-015.'],
        safe_to_publish: true,
      },
      findings: [
        {
          finding_id: 'fnd-1',
          claim_text: "India's #1 radiant skin formula",
          verdict: 'unsupported',
          severity: 'critical',
          analysis_method: 'rules_engine_v1',
          state: 'overridden',
          rationale: 'Superlative claim requires certified market share survey reference.',
          evidence: [
            {
              source_type: 'rule',
              code: 'IN-ASCI-01',
              version: 2,
              title: 'Superlative and #1 claims substantiation',
            },
          ],
          decisions: [
            {
              id: 'dec-1',
              action: 'override',
              reason: 'Overridden with manager sign-off: Kantar Q4-2025 derma audit certificate attached.',
              decided_by: 'Deepa Nair (manager)',
              created_at: new Date().toISOString(),
            },
          ],
        },
      ],
      models_and_services_used: [
        {
          call_id: 'call-001',
          provider: 'deterministic',
          model: 'deterministic_rules_v1',
          purpose: 'ASC/ASCI compliance & brand rules check',
          characters_sent: 245,
          entities_masked: 0,
          duration_ms: 14,
          status: 'completed',
        },
        {
          call_id: 'call-002',
          provider: 'deterministic',
          model: 'claim_policy_engine',
          purpose: 'Clinical fact verification & unit normalization',
          characters_sent: 180,
          entities_masked: 0,
          duration_ms: 22,
          status: 'completed',
        },
      ],
    }
  },

  downloadReportPdf: async (contentId: string): Promise<Blob> => {
    // Return a minimal valid PDF blob for mock browser download
    const pdfHeader = `%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>\nendobj\n4 0 obj\n<< /Length 75 >>\nstream\nBT /F1 16 Tf 50 720 Td (BrandCourt Governance Compliance Report: ${contentId}) Tj ET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000262 00000 n \ntrailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n386\n%%EOF`
    return new Blob([pdfHeader], { type: 'application/pdf' })
  },

  // ── B4: Guideline Health & Precedents ─────────────────────────────────────
  getGuidelineHealth: async (): Promise<GuidelineHealthReport> => {
    return {
      active_rules: 4,
      issue_count: mockGuidelineHealthIssues.length,
      issues: mockGuidelineHealthIssues,
      method: 'heuristic_screening_v1',
      notice:
        'Heuristic screening only. Lexical overlap or high override frequency flags candidates for human review, not proven contradictions.',
    }
  },

  listPrecedents: async (): Promise<PrecedentItem[]> => {
    return mockPrecedents
  },

  createPrecedent: async (data: {
    finding_id: string
    rule_id?: string
    channel?: string
    pattern_text: string
    reason: string
    valid_to?: string
  }): Promise<PrecedentItem> => {
    const item: PrecedentItem = {
      id: `prec-${Date.now()}`,
      finding_id: data.finding_id,
      rule_id: data.rule_id,
      channel: data.channel || 'all',
      pattern_text: data.pattern_text,
      reason: data.reason,
      valid_to: data.valid_to,
      status: 'pending',
      created_by: mockUser.id,
      created_at: new Date().toISOString(),
    }
    mockPrecedents.unshift(item)
    return item
  },

  approvePrecedent: async (id: string): Promise<{ id: string; status: string }> => {
    const p = mockPrecedents.find((x) => x.id === id)
    if (p) {
      p.status = 'approved'
      p.approved_by = mockUser.id
    }
    return { id, status: 'approved' }
  },

  promotePrecedent: async (
    id: string
  ): Promise<{ precedent_id: string; rule_id: string; code: string; message: string }> => {
    const p = mockPrecedents.find((x) => x.id === id)
    const code = `PREC-${(id || '0000').slice(0, 8).toUpperCase()}`
    return {
      precedent_id: id,
      rule_id: `rule-${Date.now()}`,
      code,
      message: `Precedent promoted to draft rule ${code}. Guideline owner confirmation required before activation.`,
    }
  },

  verifyFix: async (contentId: string, proposedText: string): Promise<any> => {
    const hasCure = proposedText.toLowerCase().includes('cure')
    const hasNumberOne = proposedText.toLowerCase().includes('#1')
    const hasCTA = /(buy|shop|order|book|sign up|learn more|link in bio)/i.test(proposedText)

    return {
      content_id: contentId,
      candidate_text: proposedText,
      similarity: 0.88,
      call_to_action_preserved: hasCTA,
      intent_preserved: hasCTA && !hasCure,
      safe_to_suggest: !hasCure && !hasNumberOne,
      new_blocking_findings: hasCure
        ? [
            {
              claim_text: 'cures acne',
              verdict: 'needs_human_review',
              severity: 'critical',
              rationale: 'Curative claims for OTC cosmetic products violate regulatory guidelines.',
            },
          ]
        : [],
      method: 'deterministic_candidate_evaluation',
      limitations: [
        'Candidate evaluation matches claims and checks rule violations.',
        'Intent preservation checks CTA retention and semantic claim coverage.',
      ],
    }
  },

  getModelSettings: async (): Promise<ModelSettings> => {
    return {
      local_model_enabled: mockLocalModelEnabled,
      active_models: [
        {
          name: 'Deterministic Baseline Engine v1',
          provider: 'deterministic',
          purpose: 'Rules check, exact claims matching, unit conversions',
          is_local: true,
          status: 'active',
        },
        {
          name: 'Sentence-Transformers All-MiniLM-L6-v2',
          provider: 'local_embeddings',
          purpose: 'Semantic guideline & precedent similarity retrieval',
          is_local: true,
          status: 'active',
        },
        {
          name: 'Ollama / Llama-3-8B-Instruct',
          provider: 'ollama_local',
          purpose: 'Complex ambiguity analysis (masked payload only)',
          is_local: true,
          status: mockLocalModelEnabled ? 'ready' : 'disabled',
        },
      ],
      data_flow_log: [
        {
          id: 'flow-01',
          revision_id: 'rev-1',
          provider: 'deterministic',
          model: 'deterministic_rules_v1',
          purpose: 'Rule evaluation',
          input_chars: 245,
          masked_entities: 0,
          started_at: new Date(Date.now() - 3600000).toISOString(),
          duration_ms: 12,
          status: 'completed',
          masking_confirmed: true,
        },
        {
          id: 'flow-02',
          revision_id: 'rev-1',
          provider: 'deterministic',
          model: 'claim_policy_engine',
          purpose: 'Claim & unit normalization',
          input_chars: 180,
          masked_entities: 0,
          started_at: new Date(Date.now() - 3590000).toISOString(),
          duration_ms: 18,
          status: 'completed',
          masking_confirmed: true,
        },
      ],
      masking_policy: {
        strict_pre_masking: true,
        secret_terms_masked: true,
        personal_identifiable_info_masked: true,
      },
    }
  },

  updateModelSettings: async (data: {
    local_model_enabled: boolean
    default_model?: string
  }): Promise<{ local_model_enabled: boolean; message: string }> => {
    mockLocalModelEnabled = data.local_model_enabled
    return {
      local_model_enabled: mockLocalModelEnabled,
      message: `Model configuration updated. Local mode is now ${mockLocalModelEnabled ? 'enabled' : 'disabled'}.`,
    }
  },
}
