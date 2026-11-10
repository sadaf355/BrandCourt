# BrandCourt API contract

This contract describes the routes currently registered by the FastAPI application. Base path: `/api`, except `/`. JSON bodies use `application/json` unless noted. Protected routes require `Authorization: Bearer <access_token>`. Responses shown below describe the successful response body; error responses use FastAPI's `{"detail": ...}` envelope (or validation's `{"detail": [...]}`).

## Roles

- **creator**, **reviewer**, **manager**, **admin** are workspace roles.
- **Any authenticated role** means all four roles. Workspace data is scoped to the authenticated user's workspace.
- The API, not the client, enforces each listed permission. `admin` is the guideline-owner role in the UI.

## Shared response objects

- **User**: `{id, workspace_id, email, full_name, role, is_active, created_at}`.
- **Content item**: `{id, title, channel, campaign, status, current_revision, created_by, created_at, updated_at}`.
- **Revision**: `{id, content_id, version, caption, creative_filename, ocr_status, ocr_text, alt_text, is_ai_media, paid_gifted, detected_language, image_analysis, created_by, created_at}`. `paid_gifted` is an explicit declaration for that revision; its default is `false`, and it is never inferred from channel or caption.
- **Finding**: `{id, claim_text, verdict, rationale, evidence, severity, layer, span_start, span_end, region, suggested_fix, analysis_method, state, created_at}`. `region` is an optional pixel bounding box with `x`, `y`, `width`, `height`, `image_width`, and `image_height`.
- **Rule**: `{id, workspace_id, document_id, code, title, text, type, severity, channels, status, version, source_ref, created_by, confirmed_by, created_at, updated_at}`.
- **Fact**: `{id, workspace_id, code, statement, value, unit, valid_from, valid_to, source_ref, version, status, created_by, created_at}`.
- **Asset**: `{id, workspace_id, kind, name, data, created_by, updated_at}`.

## Routes

### Service and authentication

| Method and path | Request | Success response | Allowed roles |
|---|---|---|---|
| `GET /` | None | `{service, version, docs, health}` | Public |
| `GET /api/health` | None | `{status: "ok"|"degraded", service, version, timestamp, database: "connected"|"not_configured"|"unavailable"}` | Public |
| `POST /api/auth/register-workspace` | `{workspace_name, full_name, email, password}`; workspace/name 2–160 chars, password 8–128 chars | `201 {access_token, refresh_token, token_type: "bearer", user: User}` | Public |
| `POST /api/auth/login` | `{email, password, workspace_id?}`; `workspace_id` optionally selects the workspace when the email and password match users in multiple workspaces | `{access_token, refresh_token, token_type: "bearer", user: User}` | Public |
| `POST /api/auth/refresh` | `{refresh_token}` | `{access_token, refresh_token, token_type: "bearer", user: User}`; the submitted refresh token is revoked and replaced | Public |
| `POST /api/auth/logout` | `{refresh_token}` | `{revoked: boolean}` | Public |
| `GET /api/me` | None | `User` | Any authenticated role |
| `GET /api/users` | None | `User[]` for the caller's workspace | Any authenticated role |
| `POST /api/users` | `{full_name, email, password, role}`; role is creator/reviewer/manager/admin | `201 User` | admin |
| `PATCH /api/users/{user_id}/role` | Query: `role=creator|reviewer|manager|admin` | `User` | admin |
| `GET /api/workspace` | None | `{id, name, role}` | Any authenticated role |

### Guidelines and brand knowledge

| Method and path | Request | Success response | Allowed roles |
|---|---|---|---|
| `GET /api/guidelines` | None | `[{id, filename, content_type, uploaded_by, created_at, extracted_characters, proposed_rules}]` | Any authenticated role |
| `POST /api/guidelines` | Multipart: `file` (PDF, DOCX, TXT; non-empty; max 20 MiB) | `201 {id, filename, extracted_characters, proposed_rules, message}` | admin |
| `GET /api/guidelines/{document_id}/text` | None | `{id, filename, text}` | Any authenticated role |
| `GET /api/rules` | Optional query: `status` | `Rule[]` | Any authenticated role |
| `POST /api/rules` | `{code?, title, text, type?, severity?, channels?, source_ref?, document_id?}`. Type: brand_voice/claim/visual/disclosure/terminology/legal/other. Severity: critical/major/advisory (default major). | `201 Rule` (initial status `draft`) | admin |
| `PATCH /api/rules/{rule_id}` | Optional fields `{title, text, type, severity, channels, source_ref}`; edits create a new rule version | `Rule` (new version) | admin |
| `POST /api/rules/{rule_id}/confirm` | None | `Rule` | admin |
| `POST /api/rules/{rule_id}/retire` | None | `Rule` | admin |
| `GET /api/facts` | None | `Fact[]` | Any authenticated role |
| `POST /api/facts` | `{code?, statement, value, unit?, valid_from?, valid_to?, source_ref}` | `201 Fact` | admin |
| `PATCH /api/facts/{fact_id}` | Same fields as fact creation; creates a new fact version | `Fact` (new version) | admin |
| `GET /api/assets` | None | `Asset[]` | Any authenticated role |
| `POST /api/assets` | `{kind, name, data?}`; kind: palette/font/term_list/disclosure/other. Logos must be uploaded as image files. | `201 Asset` | admin |
| `POST /api/assets/logo` | Multipart: `name`, `file` (PNG/JPG/JPEG/WEBP/GIF; max 10 MiB; image content validated; original retained and a re-encoded image plus thumbnail stored) | `201 Asset` with generated storage keys and image dimensions in `data` | admin |
| `PATCH /api/assets/{asset_id}` | `{name?, data?}`; uploaded logo storage metadata is immutable | `Asset` | admin |
| `DELETE /api/assets/{asset_id}` | None | `204`, empty body | admin |
| `GET /api/audit-events` | Optional query: `limit` (clamped to 1–200; default 50) | `[{id, actor_id, type, payload, created_at}]` | reviewer, manager, admin |

### Content review and analysis

| Method and path | Request | Success response | Allowed roles |
|---|---|---|---|
| `GET /api/content` | None | `Content item[]` | Any authenticated role |
| `POST /api/content` | `{title, channel, campaign?, caption?, alt_text?, is_ai_media?, paid_gifted?}`. `paid_gifted` defaults to `false` and declares this revision's paid/gifted status. Channel: website/instagram/facebook/linkedin/email/paid_ad/packaging/other. | `201 Content item` with `revision: Revision` | creator, manager, admin |
| `GET /api/content/{content_id}` | None | `Content item` with `revisions: Revision[]` and current `findings: Finding[]` | Any authenticated role |
| `POST /api/content/{content_id}/revisions` | Optional fields `{title, channel, campaign, caption, alt_text, is_ai_media, paid_gifted}`. If omitted, `paid_gifted` is copied from the preceding revision; explicit `true` or `false` replaces it. | `201 Content item` with `revision: Revision` | creator, manager, admin |
| `GET /api/content/{content_id}/revisions` | None | `Revision[]` | Any authenticated role |
| `POST /api/content/{content_id}/creative` | Multipart: `file`; PNG/JPG/JPEG/WEBP/GIF; non-empty; max 10 MiB and 40 megapixels. Bytes and decoded image format are validated. The original is retained; a re-encoded WEBP and thumbnail are stored. | `201 Revision` with upload storage metadata in `image_analysis.upload` | creator, manager, admin |
| `POST /api/content/{content_id}/analyze` | Optional query `evaluation_variant=code_rules_only|retrieval_and_nli|full_pipeline`; evaluation selection is restricted to workspace admins. Normal requests omit it. | `202 {job_id, status, progress, stage, content_id, revision_id, poll_url}`; the durable job stores the selected variant and returns it in the completed result. `code_rules_only` runs deterministic policy rules without claim retrieval or image/tone analysis; `retrieval_and_nli` adds fact retrieval, Ollama NLI and quote-validated adjudication; `full_pipeline` also runs model extraction, image/OCR and tone checks. Model-dependent variants require a reachable configured Ollama model. Evaluation requests use a separate per-variant rate limit of 40 requests per configured analyze window; normal analysis retains its configured limit. Excess requests return `429` with `Retry-After`. | Any authenticated role for normal analysis; admin for evaluation variants |
| `GET /api/jobs/{job_id}` | None | `{job_id, content_id, revision_id, status, progress, stage, result, error, created_at, started_at, finished_at}`; `result` is `null` until completed | Any authenticated role |
| `GET /api/content/{content_id}/findings` | None | `Finding[]` for the current revision | Any authenticated role |
| `POST /api/content/{content_id}/ocr` | None | `{status, text, message, revision_id, revision_version}` | Any authenticated role |
| `POST /api/content/{content_id}/image-analysis` | None | Success: `{content_id, revision_id, width, height, dominant_colors, palette_checks, ocr_boxes, ocr_text, ocr_claim_text, ocr_confidence_threshold, ocr_uncertain_words, contrast, logo_check, overall_status, failure_policy}`. OCR boxes retain `{text, confidence, x, y, width, height, block_num, par_num, line_num, uncertain}`. Words below `OCR_CONFIDENCE_THRESHOLD` (default `0.70`, range `0`–`1`) remain in raw OCR text and boxes but their entire line is excluded from Claim Court and gets a region-highlighted `needs_human_review` finding. High-confidence lines continue through Claim Court. Palette checks are `{observed, nearest_brand_color, delta_e_2000, status}`. If analysis fails, the response is `{content_id, revision_id, overall_status: "needs_human_review", error, message, ocr_boxes: [], palette_checks: [], contrast, logo_check}`. | Any authenticated role |
| `GET /api/content/{content_id}/report` | Query: `format=json|pdf` (default `json`) | JSON: `{product, report_version, generated_at, content: {id, title, channel, campaign, status}, revision: {id, version, caption, alt_text, is_ai_media, language, ocr_status}, findings: [{id, claim_text, verdict, severity, rationale, evidence, analysis_method}], ai_and_service_disclosure: {calls, external_ai_called, notice}, limitations}`. Each call is `{provider, model, purpose, input_chars_after_masking, masked_entities, status, duration_ms}`. PDF: `application/pdf` attachment. | Any authenticated role |
| `GET /api/content/{content_id}/export` | None | `{product, content, revision, findings, decisions, approved_snapshot, approved_at, exported_at, notice}` | Any authenticated role; only approved content |

### Comments, finding decisions, and workflow

| Method and path | Request | Success response | Allowed roles |
|---|---|---|---|
| `GET /api/content/{content_id}/comments` | None | `[{id, content_id, finding_id, user_id, user_name, body, created_at}]` | Any authenticated role |
| `POST /api/content/{content_id}/comments` | `{body, finding_id?}`; body 1–5000 chars | `201 {id, content_id, finding_id, user_id, user_name, body, created_at}` | Any authenticated role |
| `POST /api/findings/{finding_id}/decision` | `{action, reason?, edited_text?}`. Action: accept/edit/dispute/override/resolve. `edited_text` required for edit; non-empty `reason` required for override. | `201 {id, finding_id, action, reason, user_id, state, created_at}`; edit also returns `new_revision_version`, `review_job_id`, `message` | accept/edit/dispute: all roles; override/resolve: reviewer/manager/admin; India-pack override: manager/admin |
| `GET /api/content/{content_id}/decisions` | None | `[{id, finding_id, action, reason, user_id, created_at}]` | Any authenticated role |
| `POST /api/content/{content_id}/workflow` | `{action, reason?}`. Action: submit/start_review/approve/reject/reopen. | `{content_id, status, action, locked_revision_id}` | submit: creator/manager/admin; start_review/reject: reviewer/manager/admin; approve/reopen: manager/admin |

### Guideline health, precedents, and insights

| Method and path | Request | Success response | Allowed roles |
|---|---|---|---|
| `GET /api/guideline-health` | None | `{active_rules, issue_count, issues, method, model_mode, notice}`. Issues include `issue_key`, `type`, `rule_id`, `code`, `explanation`, `suggestion`, and `analysis_status` where a model step ran. Active rules are embedded; candidate conflicts are screened by channel scope/similarity. Override-rate issues appear only after at least five findings for that rule. Findings are suggestions only; this route never changes a rule. | Any authenticated role |
| `POST /api/guideline-health/decisions` | `{issue_key, rule_id?, issue_type?, action: accept|edit|ignore, edited_wording?}`; edited_wording is required for `edit` | `201 {issue_key, action, rule_changed: false, draft_rule_id?, draft_version?}`; `accept` and `edit` on vague rules create a new `draft` rule version without activating it, and the decision is audit-logged | manager, admin |
| `PUT /api/workspace/model-mode` | `{mode: deterministic|disabled|ollama}` | `{model_mode}`; writes the workspace setting and audit event | admin |
| `GET /api/precedents` | None | `[{id, finding_id, rule_id, channel, pattern_text, reason, valid_to, status, created_by, approved_by, created_at}]` | Any authenticated role |
| `POST /api/precedents` | `{finding_id, rule_id?, channel?, pattern_text, reason, valid_to?}`; requires an existing reasoned reviewer override; omitted channel defaults to the overridden content's channel | `201 {id, finding_id, rule_id, channel, pattern_text, reason, status: pending, valid_to}`; embedding and workspace/rule/channel scope are stored | reviewer, manager, admin |
| `GET /api/findings/{finding_id}/precedent-suggestions` | None | `{finding_id, suggestions: [{precedent_id, rule_id, channel, reason, similarity, suggested_severity, requires_reviewer_confirmation, message}]}`; only approved, valid precedents matching the same rule/channel at similarity ≥0.85 are returned; critical findings have no downgrade suggestions | Any authenticated role |
| `POST /api/findings/{finding_id}/precedent-suggestions/{precedent_id}/confirm` | None | `{finding_id, severity: advisory, confirmed: true}`; reviewer confirmation is audit-logged; critical findings cannot be downgraded | reviewer, manager, admin |
| `POST /api/precedents/{precedent_id}/approve` | None | `{id, status, approved_by, approved_at}` | manager, admin |
| `POST /api/precedents/{precedent_id}/promote` | None | `{precedent_id, rule_id, code, status, message}`; creates a draft rule, not an active rule | manager, admin |
| `POST /api/content/{content_id}/verify-fix` | `{proposed_text, finding_id?}`; proposed_text is 1–20,000 chars | `{content_id, source_revision_id, source_revision_version, candidate_text, similarity, embedding_similarity, call_to_action_preserved, changed_claims, intent_check, intent_preserved, full_engine_rerun, candidate_findings, new_blocking_findings, safe_to_suggest, method, limitations}`; runs the full engine against a temporary revision, rejects newly introduced critical findings, and stores the intent check on the source finding when supplied | Any authenticated role |
| `POST /api/findings/{finding_id}/suggest-fix` | None | `{finding_id, suggested_fix, source_fact_id, method, accepted, model_status, rejection_reason, verification}`; a suggestion is retained only after a full-engine rerun, no new critical finding, and intent similarity ≥0.80 with CTA preservation | Any authenticated role |
| `GET /api/insights` | None | `{items_total, findings_total, decisions_total, overrides, disputes, by_status, by_channel, by_verdict, top_evidence_codes: [{code, count}], override_dispute_by_code: [{code, overrides, disputes}], approved_items_with_timing, average_upload_to_approval_seconds, average_review_rounds, active_rules, model_mode, note}` | Any authenticated role |
| `GET /api/review-queue` | Optional query: `status`, `channel`, `severity`, `creator`, `include_advisory` (default `false`), `limit` (1–100, default 20), `offset` (default 0) | `{items: [{id, title, channel, campaign, status, current_revision, language, finding_count, critical_count, major_count, disputed_count, has_blockers, priority_score, updated_at}], total, limit, offset}` | reviewer, manager, admin |

### Model disclosure

| Method and path | Request | Success response | Allowed roles |
|---|---|---|---|
| `GET /api/model-calls` | Optional query: `limit` (1–500; default 100) | `[{id, revision_id, provider, model, purpose, input_chars, masked_entities, started_at, duration_ms, status}]` | Any authenticated role |
| `GET /api/model-mode` | None | `{mode, provider, model, base_url_configured, notice}` | Any authenticated role |

### Analytics, reports, notifications, and model settings

| Method and path | Request | Success response | Allowed roles |
|---|---|---|---|
| `GET /api/insights/summary` | None | `{workspace_id, total_items, approved_items, total_findings, severity_distribution, overrides_total, disputes_total, expiring_facts_count, average_approval_hours, average_review_rounds, model_mode, is_seeded_reference}`. `average_approval_hours` and `average_review_rounds` are `null` when no approval or review history exists (`is_seeded_reference` is `false`). | Any authenticated role |
| `GET /api/insights/top-rules` | Query: `group_by=channel|creator|week` (default `channel`) | `{group_by, data: [{channel|creator|week, rule_code, count}]}` | Any authenticated role |
| `GET /api/insights/override-rates` | None | `{rules: [{rule_code, overrides, disputes, total, override_rate_pct, dispute_rate_pct}]}` | Any authenticated role |
| `GET /api/insights/expiring-facts` | None | `{facts: [{id, code, statement, valid_to, days_remaining, is_expired, requires_review}]}` | Any authenticated role |
| `GET /api/reports/content/{content_id}/json` | None | JSON report with report ID, approved content/revision, findings, decisions, and model-call disclosure; only approved, locked content is reportable | Any authenticated role |
| `GET /api/reports/content/{content_id}/pdf` | None | `application/pdf` attachment for approved, locked content | Any authenticated role |
| `GET /api/notifications` | None | `[{id, type, title, message, link, created_at, read}]`; review-queue notices are included for reviewer/manager/admin roles, and pending-precedent notices for manager/admin roles | Any authenticated role |
| `GET /api/settings/models` | None | `{local_model_enabled, active_models, data_flow_log, masking_policy}` | Any authenticated role |
| `PATCH /api/settings/models` | `{local_model_enabled, default_model?}`; `default_model` defaults to `deterministic_baseline_v1` | `{local_model_enabled, default_model, message}`; the change is audit-logged | admin |

## Common errors and state constraints

- `401`: missing, invalid, expired, inactive, or unknown credentials.
- `403`: the authenticated role is not permitted to perform the operation.
- `404`: the object does not exist in the caller's workspace.
- `409`: current workflow state, locked revision, or approval requirements prevent the operation.
- `413`: file or image exceeds the endpoint's size/dimension limit.
- `415`: unsupported or invalid upload content.
- `422`: request validation or extraction failure.
- `503`: an optional subsystem required by the requested operation is unavailable.
- `429`: the login failure threshold for the caller's IP/email pair has been reached; response includes `Retry-After`.
- A finding verdict is `supported`, `contradicted`, `outdated`, `unsupported`, or `needs_human_review`. Severity values are `critical`, `major`, or `advisory`; legacy model writes of `warning`, `blocker`, or `info` normalize to `major`, `critical`, and `advisory` respectively. The schema migration changes persisted `warning` values to `major`.

Refresh tokens are opaque, stored only as hashes, expire according to `REFRESH_TOKEN_DAYS`, and rotate on refresh. Logout revokes the submitted refresh token. Content analysis is queued durably in the database and processed by the worker process; queued jobs survive API restarts.
