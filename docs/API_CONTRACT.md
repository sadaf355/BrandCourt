# BrandCourt API Contract

This document specifies the REST API endpoints and data schemas supported by the BrandCourt backend.

## 1. Authentication & Workspace

### `POST /api/register`
- Request: `{ email: string, password: str, full_name: string, workspace_name: string }`
- Response (201): `{ access_token: string, token_type: 'bearer', user: User }`

### `POST /api/token`
- Request: Form data `username` (email) & `password`
- Response (200): `{ access_token: string, token_type: 'bearer', user: User }`

### `GET /api/me`
- Response: `User` (`id, workspace_id, email, full_name, role: 'creator' | 'reviewer' | 'manager' | 'admin'`)

### `GET /api/workspace`
- Response: `{ id: string, name: string }`

### `GET /api/users`
- Response: `Array<User>`

### `PATCH /api/users/{user_id}/role`
- Request: `{ role: 'creator' | 'reviewer' | 'manager' | 'admin' }`
- Response: `User`

---

## 2. Brand Knowledge & Governance

### `GET /api/guidelines`
- Response: `Array<GuidelineDocument>`

### `POST /api/guidelines/upload`
- Multipart file upload (`file: UploadFile`)
- Response: `{ guideline_id: string, filename: string, extracted_rules: RuleDraft[] }`

### `GET /api/rules`
- Response: `Array<Rule>`

### `POST /api/rules`
- Request: `{ name: string, description: string, rule_type: string, severity: 'critical' | 'major' | 'advisory', channel_scope: string, pattern?: string }`
- Response (201): `Rule`

### `PATCH /api/rules/{id}/activate`
- Response: `Rule`

### `PATCH /api/rules/{id}/retire`
- Response: `Rule`

### `GET /api/facts`
- Response: `Array<Fact>`

### `POST /api/facts`
- Request: `{ statement: string, claim_value?: string, unit?: string, source_reference: string, valid_from?: string, valid_until?: string }`
- Response (201): `Fact`

### `GET /api/assets`
- Response: `Array<BrandAsset>`

### `POST /api/assets`
- Request: `{ name: string, asset_type: string, content_json: any }`
- Response (201): `BrandAsset`

### `GET /api/audit`
- Query params: `limit?: number, offset?: number`
- Response: `Array<AuditEvent>`

---

## 3. Content Reviews & Claim Court

### `GET /api/content`
- Response: `Array<ContentItem>`

### `POST /api/content`
- Request: `{ title: string, channel: Channel, campaign?: string, caption?: string, alt_text?: string, is_ai_media?: boolean }`
- Response (201): `ContentItem & { revision: ContentRevision }`

### `GET /api/content/{id}`
- Response: `ContentItem & { revisions: ContentRevision[], findings: ClaimFinding[] }`

### `POST /api/content/{id}/revisions`
- Request: `{ title?: string, channel?: Channel, campaign?: string, caption?: string, alt_text?: string, is_ai_media?: boolean }`
- Response (201): `ContentRevision`

### `POST /api/content/{id}/creative`
- Multipart file upload (`creative: UploadFile`)
- Response: `{ message: string, filename: string, revision_id: string }`

### `POST /api/content/{id}/ocr`
- Triggers OCR text extraction on attached raster creative.
- Response: `{ ocr_status: 'completed' | 'failed' | 'not_supported', ocr_text: string }`

### `POST /api/content/{id}/analyze`
- Enqueues review job.
- Response: `{ message: string, job_id: string, status: 'queued' }`

### `GET /api/jobs/{job_id}`
- Response: `{ id: string, job_type: string, status: 'queued' | 'running' | 'completed' | 'failed', progress: number, stage: string, error?: string }`

---

## 4. Review Workflow & Decisions

### `POST /api/findings/{finding_id}/decisions`
- Request: `{ action: 'accept' | 'dispute' | 'override' | 'resolve', note?: string }`
- Response: `{ message: string, state: string, finding_id: string }`

### `POST /api/content/{id}/submit`
- Transition status from `draft` / `analyzed` to `submitted`.
- Response: `ContentItem`

### `POST /api/content/{id}/start-review`
- Transition status from `submitted` to `in_review`.
- Response: `ContentItem`

### `POST /api/content/{id}/approve`
- Manager / Admin action. Blocks if unresolved critical or contradicted findings exist. Creates immutable snapshot.
- Response: `ContentItem & { snapshot_id: string }`

### `POST /api/content/{id}/reject`
- Response: `ContentItem`

### `POST /api/content/{id}/reopen`
- Manager / Admin action. Unlocks item for edits.
- Response: `ContentItem`

---

## 5. Intelligence, Health & Insights

### `GET /api/guideline-health`
- Heuristic checks for ambiguous or overlapping rules.
- Response: `{ total_rules: number, flags: Array<{ rule_id: string, rule_name: string, issue: string, severity: string }> }`

### `GET /api/precedents`
- Approved precedents ledger.
- Response: `Array<Precedent>`

### `POST /api/fix-verify`
- Request: `{ original_text: string, proposed_fix: string, channel: string }`
- Response: `{ safe: boolean, intent_preserved: { purpose: string, cta: string, claims_changed: string[] }, analysis: string }`

### `GET /api/insights/summary`
- Aggregated workspace review trends and operational metrics.

