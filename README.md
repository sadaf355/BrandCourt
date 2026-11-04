# BrandCourt — Phases 1–10

BrandCourt is an evidence-led brand governance platform. This repository contains a hackathon prototype for Phases 1–10: foundation, workspace roles, brand knowledge, content revisions, Claim Court, image OCR integration, human review workflow, guideline health, precedent capture, fix verification, and operational insights. Features that depend on optional system OCR binaries or production deployment services are explicitly reported rather than silently simulated.

## Included scope

### Phase 1 — Foundation
- React + Vite + TypeScript single-page app.
- Responsive BrandCourt application shell and reusable design tokens.
- Persistent light/dark theme toggle; first visit follows the operating-system preference.
- FastAPI service, CORS configuration, environment-based settings, API health route and interactive API docs.
- SQLAlchemy async database setup and Alembic migrations.
- Frontend API client and setup documentation.

### Phase 2 — Authentication, workspace and roles
- Workspace registration creates a workspace and the first guideline-owner account.
- Email/password sign-in, signed bearer access tokens, `/api/me`, and sign-out.
- Passwords hashed with PBKDF2-HMAC-SHA256; passwords are never stored in plain text.
- Workspace membership management and role changes (guideline owner only).
- Roles: `creator`, `reviewer`, `manager`, `admin` (shown in the UI as Guideline owner).
- Server-side authorization; every knowledge query is filtered by the authenticated user's workspace.
- Audit events for workspace creation, member creation, and role changes.

### Phase 3 — Brand Knowledge Centre
- Upload guideline files in PDF, DOCX, or TXT format (20 MB maximum).
- Extract document text and create proposed rule drafts from suitable paragraphs/bullets. Extraction is a convenience, not a claim of perfect semantic parsing.
- Manual rule creation, severity/type/channel fields, confirm-to-activate and retire actions.
- Rule edits create a new version and preserve the old version as retired.
- Approved facts with statement, value, unit, source reference, validity start/end, and versions.
- Expired facts are automatically presented as `expired`; expired facts are not deleted.
- Brand assets for logo references, palettes, fonts, terminology/term lists, disclosures and other JSON configuration.
- Chronological audit trail for governance changes.
- Search, empty states, loading states, validation messages, responsive layouts, and light/dark support.

### Phase 4 — Content review workspace
- Create content drafts with channel/campaign metadata, attach creative images, and preserve caption revisions.
- Compare the latest caption with its previous revision.

### Phase 5 — Claim Court baseline
- Split caption text into candidate claims and compare against workspace facts and active claim/disclosure/legal/terminology rules.
- Normalize common duration units (for example, 28 days and 4 weeks) before comparing values; incompatible units remain unverifiable rather than being called contradicted.
- The deterministic India starter checks flag unsupported “India’s #1” claims (IN-2) and cure/guaranteed-result wording such as “cures acne” (IN-5) for human/legal review. These are advisory policy flags, not legal determinations.
- Persist findings with evidence references and explicit heuristic-method disclosure. This is not semantic proof or legal advice.

### Phase 6 — Image intelligence (OCR integration)
- Run OCR against the current revision's attached raster creative and store OCR text/status on that revision.
- OCR text is included in the next Claim Court analysis. SVG is not OCR-processed.
- Python bindings (Pillow/pytesseract) are listed as dependencies; the Tesseract executable must also be installed on the machine. If OCR is unavailable or fails, the API returns an explicit status. This is OCR integration, not a trained image-understanding model.

### Phase 7 — Review workflow
- Workspace-scoped comments, per-finding decisions (accept, dispute, override, resolve), and audit events.
- State flow: draft/analyzed → submitted → in_review → approved or rejected; manager/guideline-owner approval and reopen permissions.
- Approval is blocked by unresolved critical findings and by contradicted, outdated, or unsupported findings, regardless of an incorrectly low severity label. A finding must be explicitly accepted, overridden with a reason, or resolved before approval can proceed.
- Approval stores an immutable JSON snapshot on the approved revision; editing, re-analysis, OCR and finding decisions are blocked until a manager reopens the item. Export reads the stored approval snapshot.
- Claim Court runs as a background review job. `POST /api/content/{id}/analyze` returns a job ID; poll `GET /api/jobs/{job_id}` for queued/running/completed/failed state and progress.
- Creators can accept, edit or dispute findings. Override and resolve remain reviewer/manager/admin actions; overrides require a non-empty reason.

### Phase 8–10 — Intelligence and fix verification
- Guideline Health heuristic checks, workspace-scoped Precedent Ledger, fix verification and operational insights.
- Approved, unexpired precedents may be attached as advisory evidence when their channel and wording match.
- Supporting schema includes `review_jobs`, `ai_calls`, `check_cache`, `reports`, `embeddings`, and `rule_examples`. The table presence does not imply that every optional AI/cache/report pipeline is fully wired.

## Repository layout

```text
BrandCourt-Phase1/
  frontend/                 React + Vite app
    src/pages/AuthPage.tsx
    src/pages/KnowledgePage.tsx
    src/lib/api.ts
    src/providers/ThemeProvider.tsx
  backend/                  FastAPI service
    app/api/auth.py         registration, login, users, current user
    app/api/knowledge.py    guidelines, rules, facts, assets, audit
    app/models/entities.py  SQLAlchemy data model
    app/core/security.py    password hashing and signed access tokens
    alembic/versions/       database migrations
    tests/
```

## Requirements

- Python 3.11+ recommended.
- Node.js 20+ and npm.
- SQLite works as the default local database. PostgreSQL is supported by setting `DATABASE_URL`.

## Run locally (Windows PowerShell)

### 1. Backend

```powershell
cd BrandCourt-Phase1\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Review `backend/.env`. The default is an easy local SQLite database:

```env
DATABASE_URL=sqlite+aiosqlite:///./brandcourt.db
SECRET_KEY=replace-this-with-a-long-random-secret
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
UPLOAD_DIR=./uploads
```

Then apply migrations and start the API:

```powershell
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

API: <http://localhost:8000>

Interactive API documentation: <http://localhost:8000/docs>

Health check: <http://localhost:8000/api/health>

### 2. Frontend (a second terminal)

```powershell
cd BrandCourt-Phase1\frontend
Copy-Item .env.example .env
npm install
npm run dev
```

Open <http://localhost:5173>. `VITE_API_BASE_URL` defaults to `http://localhost:8000/api`.

### 3. First login

1. Select **Create a workspace** on the sign-in screen.
2. Enter a workspace name, your full name, email and a password of at least 8 characters.
3. The first account is assigned the **Guideline owner** (`admin`) role.
4. Use **Members & roles** to create accounts for creators, reviewers, managers and additional guideline owners.
5. Upload a guideline under **Guidelines**, review the proposed rules under **Brand rules**, then choose **Confirm & activate** for each rule that is ready.
6. Add facts with clear source references and validity dates under **Approved facts**. Add palette/logo/font/terminology/disclosure configuration under **Brand assets**.

## Database configuration

Default local SQLite:

```env
DATABASE_URL=sqlite+aiosqlite:///./brandcourt.db
```

PostgreSQL example:

```env
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/DATABASE
```

For a production deployment, use a managed PostgreSQL instance, set a strong random `SECRET_KEY`, configure exact trusted CORS origins, and put uploads on persistent private object storage. The included local upload directory is suitable for development/demo only.

Run migrations whenever schema migrations are added:

```bash
alembic upgrade head
```

To inspect migration state:

```bash
alembic current
alembic history
```

## Roles and permissions

| Capability | Creator | Reviewer | Manager | Guideline owner |
|---|---:|---:|---:|---:|
| Sign in and read workspace knowledge | Yes | Yes | Yes | Yes |
| Create/edit guideline rules, facts and assets | No | No | No | Yes |
| Upload guideline documents | No | No | No | Yes |
| Confirm/activate or retire rules | No | No | No | Yes |
| Create and manage workspace members | No | No | No | Yes |
| Read governance audit trail | No | Yes | Yes | Yes |

Content editing is restricted to creators, managers and guideline owners; creators may accept, edit or dispute findings; override and resolve require reviewer, manager or guideline-owner access; final approval and reopening require manager or guideline-owner access. Overrides require a reason. Each action is checked by the API and written to the audit trail.

## API routes in this build

- `POST /api/auth/register-workspace`
- `POST /api/auth/login`
- `GET /api/me`
- `GET /api/workspace`
- `GET /api/users`, `POST /api/users`, `PATCH /api/users/{user_id}/role`
- `GET /api/guidelines`, `POST /api/guidelines`, `GET /api/guidelines/{document_id}/text`
- `GET /api/rules`, `POST /api/rules`, `PATCH /api/rules/{rule_id}`, `POST /api/rules/{rule_id}/confirm`, `POST /api/rules/{rule_id}/retire`
- `GET /api/facts`, `POST /api/facts`, `PATCH /api/facts/{fact_id}` (PATCH creates a new fact version; the request contains the full new fact)
- `GET /api/assets`, `POST /api/assets`, `PATCH /api/assets/{asset_id}`, `DELETE /api/assets/{asset_id}`
- `GET /api/audit-events`
- `GET /api/health`

All protected routes require `Authorization: Bearer <access_token>`.

## Important behavior and limitations

- Extracted rules always begin in `draft`. They are not used as active rules until explicitly confirmed by a guideline owner.
- Document parsing is text extraction plus a conservative paragraph/bullet proposal heuristic. It is not an AI policy interpretation system and may miss rules or propose unsuitable fragments; review every proposal.
- The `source_ref` field records the source label/reference supplied with a fact/rule. It does not independently verify the source.
- Workspace boundaries are enforced in the API; do not bypass the API or expose the database to the browser.
- Claim Court and image analysis are decision-support tools, not truth guarantees or legal advice. OCR requires the Tesseract system executable in addition to Python packages. CIEDE2000 palette distance, estimated contrast, OCR boxes, JSON/PDF reporting, async review jobs and approval snapshots are implemented. Logo comparison is a rough screening signal, and local semantic embeddings/NLI require an explicitly configured Ollama service and downloaded models. Production deployment and real participant sessions are external release tasks.
- Token storage in localStorage is convenient for a local hackathon prototype. For production, consider an HttpOnly secure cookie, refresh/revocation strategy, rate limiting, email verification and account recovery.
- Uploaded files are stored on the backend's local `UPLOAD_DIR`; do not use ephemeral storage for a deployed service.

## Verification

Backend syntax check:

```bash
python -m compileall -q app alembic tests
```

Backend tests (after installing requirements and applying migrations):

```bash
pytest -q
```

Frontend checks:

```bash
npm run build
npm run lint
```

## Troubleshooting

- **Frontend cannot connect:** verify the backend is running on port 8000 and `frontend/.env` has the correct `VITE_API_BASE_URL`; restart Vite after editing `.env`.
- **Database/table errors:** activate the backend virtual environment, check `DATABASE_URL`, then run `alembic upgrade head` from the backend directory.
- **Upload returns 415:** only PDF, DOCX and TXT are supported.
- **PDF extracts no text:** scanned/image-only PDFs need OCR, which is not part of Phase 3. Use a text-based PDF or DOCX/TXT for this phase.
- **403 response:** the signed-in role does not have permission for that operation. Rule/fact/asset/member management is restricted to guideline owners.
- **Forgotten local data:** SQLite data is in `backend/brandcourt.db`; uploaded files are in `backend/uploads/`. Back these up before deleting or resetting them.

## Phase 4 — Content Review Workspace

The `/reviews` screen supports creating content items with a title, channel, campaign and caption. Each content item starts as a draft with an immutable revision record. Saving edits creates the next revision and preserves previous copy; the version ledger can compare the latest caption with the previous revision. Image creatives (PNG, JPG/JPEG, WEBP, GIF, SVG) can be attached to the current revision up to 10 MB. Raster image bytes and dimensions are validated; SVG is parsed as XML and active/embedded content is rejected. Uploads are stored under the configured `UPLOAD_DIR` (default `./uploads`); configure persistent private storage before deploying.

Content API endpoints (all require a bearer token):

- `GET /api/content` — list workspace content.
- `POST /api/content` — create a draft and revision 1.
- `GET /api/content/{content_id}` — fetch content, revisions and latest-revision findings.
- `POST /api/content/{content_id}/revisions` — create a new revision.
- `GET /api/content/{content_id}/revisions` — list revision history.
- `POST /api/content/{content_id}/creative` — attach an image to the latest revision.

## Phase 5 — Claim Court baseline

Open `/claim-court` or select **Run Claim Court** on a content item. The baseline splits caption text into candidate claims, compares claim vocabulary and numbers against workspace facts marked active, checks fact validity dates, and attaches relevant active claim/disclosure/legal/terminology rules as context. Results are stored against the exact content revision and can be retrieved with `GET /api/content/{content_id}/findings`. Re-running analysis replaces findings for that revision, making the baseline repeatable.

- `POST /api/content/{content_id}/analyze` — queue analysis and return a review job ID (HTTP 202).
- `GET /api/jobs/{job_id}` — poll job status, progress, stage, and final result.
- `GET /api/content/{content_id}/findings`
- `POST /api/content/{content_id}/ocr` (Phase 6)
- `GET|POST /api/content/{content_id}/comments` (Phase 7)
- `GET /api/content/{content_id}/decisions`
- `POST /api/findings/{finding_id}/decision`
- `POST /api/content/{content_id}/workflow` (`submit`, `start_review`, `approve`, `reject`, `reopen`)
- `GET /api/content/{content_id}/export` — approved items only; returns a JSON report from the immutable approval snapshot.

Verdicts are **Supported**, **Contradicted**, **Outdated**, **Unverifiable**, and **Unsupported**. This is a transparent deterministic baseline (`deterministic_v2`), not a semantic verifier or legal advice. Common duration units are normalized before comparison; incompatible dimensions remain unverifiable. The starter policy flags unsupported “India’s #1” claims (IN-2) and cure/guaranteed-result language such as “cures acne” (IN-5) as critical human-review items. Human review is required before publication. Phase 6 OCR is optional and requires the Tesseract executable. Approval blocks unresolved critical/blocker findings and unresolved contradicted/outdated/unsupported findings. Approval stores a revision snapshot; the locked revision cannot be changed until reopened. PDF export and live notifications are not included.

## Database migration after updating

From the `backend` directory, activate the virtual environment and run:

```bash
alembic upgrade head
```

The dependency list includes `aiosqlite` for the default local SQLite database. For PostgreSQL, configure `DATABASE_URL` in `backend/.env` and run the same migration command. Keep `.env`, user uploads, and production secrets out of source control. Change the default `SECRET_KEY` before deployment.

## Phases 8–10 — Round 3 reliability features

### Phase 8: Guideline Health
- `GET /api/guideline-health` scans active workspace rules for subjective/vague wording, very short rules, and lexically overlapping rule pairs.
- Results include a type, severity, explanation, and suggested clarification.
- This is a heuristic triage aid, not semantic contradiction detection; a guideline owner must confirm any issue.

### Phase 9: Precedent Ledger
- `GET /api/precedents` lists workspace precedents.
- `POST /api/precedents` creates a pending precedent from a finding, scope/channel, pattern, and reviewer rationale. Reviewer/manager/admin roles may create.
- `POST /api/precedents/{id}/approve` requires manager/admin and changes pending to approved. Workspace-scoped queries and audit events are applied.
- `valid_to` is stored as an optional expiry. Approved precedents are attached as advisory evidence to future lexically matching findings when the channel and validity window match. Approved precedents can be promoted into draft rules; a guideline owner must confirm a promoted rule before it becomes active.

### Phase 10: Fix verification and insights
- `POST /api/content/{content_id}/verify-fix` runs the Claim Court engine against a temporary candidate revision, reports new blocking findings, and calculates an `intent_preserved_claim_count` using claim-text matching and CTA retention. It is advisory and does not guarantee semantic equivalence.
- `GET /api/insights` returns workspace-scoped counts by channel, workflow state and verdict, top evidence codes, override/dispute counts by code, and average upload-to-approval time/review rounds where audit history is available.
- The UI exposes Guideline Health, Precedent Ledger, Fix verification, and Insights & model pages. The default mode is deterministic; optional Ollama embeddings and NLI require local model setup. The India pack is a starter set, not a verified legal rules database, and evaluation metrics must be generated from actual predictions.

### Apply migrations
Run `alembic upgrade head` from the backend directory. The latest migration is `0007_r2_r7_content_metadata`; the migration chain adds content metadata and finding states after the job/snapshot/support-table migration.

### New API routes
- `GET /api/jobs/{job_id}`
- `GET /api/guideline-health`
- `GET /api/precedents`
- `POST /api/precedents`
- `POST /api/precedents/{precedent_id}/approve`
- `POST /api/content/{content_id}/verify-fix`
- `GET /api/insights`


## Final implementation audit

The Phase 1–10 navigation and API routes are present. Clean SQLite migration through `0007_r2_r7_content_metadata` and 18 focused backend tests have been verified in this environment. Production frontend build and browser-based Playwright execution remain unverified because npm dependencies could not be installed here. Image checks, semantic retrieval, India starter checks and intent-preservation metrics are advisory and must not be described as legal or semantic guarantees. Deployment, real participant sessions and a live demo recording remain team-run release tasks.

### Verification commands

Run these from the indicated folders after installing dependencies:

```powershell
# backend
cd backend
pip install -r requirements.txt
python -m compileall -q app alembic tests
alembic upgrade head
pytest -q

# frontend (new terminal)
cd frontend
npm install
npm run build
npm run lint
```

A successful syntax compilation alone is not an end-to-end pass. The repository should only be called fully verified after the migration, test suite, frontend build/lint and manual/API workflow tests pass in an environment with dependencies installed.

---

## R2–R7 implementation update (v2.0.0)

### R2 — Claim Court v2
- Unit-aware quantity comparison covers common duration, percent, mass, volume and length units. Incompatible dimensions return `unverifiable` instead of a fabricated contradiction.
- Verdicts include `supported`, `contradicted`, `outdated`, `unverifiable`, `unsupported`, and `needs_human_review`.
- The India starter checks IN-1 to IN-6 are represented across policy checks, disclosure reminders, seeded rule records and explanations. These are advisory product checks, not legal advice.
- Severity follows matching rule severity, with the most severe applicable rule taking precedence.
- Layer 1 checks include banned workspace terms, paid disclosure, AI-generated media declaration, missing alt text and disclaimer/absolute-claim conflicts. The tone layer is advisory.
- Obvious email, Indian phone, 12-digit ID-like and credential patterns are masked before optional local model input. The model-call log records provider, model, purpose, masked entity count, input length and status.
- Language detection supports English and heuristic Hindi/Marathi/Hinglish labels; Hindi/Marathi/Hinglish detection is limited and must be reviewed.

### R3 — Workflow completion
- Analysis is queued as a `review_jobs` record and the frontend polls progress.
- Finding state is stored (`open`, `accepted`, `edited`, `disputed`, `overridden`, `resolved`). Editing a finding creates a new revision and queues a re-check.
- Approval snapshots and locks the approved revision. Approval blocks unresolved critical/blocker findings and unresolved `contradicted`, `outdated`, `unsupported`, or `needs_human_review` verdicts.
- Reviewer queue is available at `/reviewer-queue` and `/api/review-queue`.
- Overrides of IN-1 to IN-6 policy findings require a manager/admin role and a reason. A simple Accept decision does not clear a blocking finding; it must be resolved or explicitly overridden.

### R4 — Image intelligence
- `POST /api/content/{id}/image-analysis` returns OCR boxes, dominant colors, CIEDE2000 palette distances, estimated WCAG contrast ratios and a logo-check status.
- Contrast values are estimates based on OCR regions and adjacent pixels; they are not a certified accessibility audit.
- Logo comparison is only attempted when a workspace logo asset is configured with an internal `reference_image_path`. Otherwise it is explicitly `needs_human_review`.
- Failed or unavailable image checks are stored on the revision and surface as a `needs_human_review` finding during Claim Court.

### R5 — Findings, reports and dashboard
- Findings workbench: `/findings-workbench` (three panels for findings, evidence, and revision diff).
- Reviewer queue: `/reviewer-queue`.
- Insights dashboard: `/insights-dashboard` uses Recharts.
- JSON/PDF reports: `GET /api/content/{id}/report?format=json|pdf`. Reports include model/provider disclosures and limitations.
- Facts returned by `/api/facts` show expired/scheduled validity states; the dashboard highlights dated facts.

### R6 — Round 3 upgrade
- Deterministic hashing/trigram vectors are stored in `embeddings` and used as one signal in hybrid lexical retrieval. These are **not** pretrained semantic embeddings.
- Optional Ollama embeddings and NLI can be enabled with `MODEL_MODE=ollama`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, and `OLLAMA_EMBEDDING_MODEL` (default `nomic-embed-text`). Only masked claim/evidence text is sent to the local Ollama service. Embedding calls are batched and logged; invalid/offline model results are surfaced as `needs_human_review` while deterministic retrieval remains available.
- Fix verification creates a temporary candidate revision, re-runs the Claim Court engine, reports new blocking findings, and calculates `intent_preserved_claim_count` by claim-text matching plus CTA retention. This remains a deterministic proxy for intent, not semantic proof.
- Approved precedents can be promoted to a **draft** rule; a guideline owner must confirm it before activation.

### R7 — Proof and ship
- Fictional GlowSerum seed data and a 40-post JSONL evaluation set are in `data/sample/`.
- Seed a workspace after registering an admin: `cd backend` then `python -m app.seed_glowserum --email admin@example.com`.
- `backend/scripts/score_eval.py --predictions predictions.jsonl` computes precision/recall by label. Predictions must be generated by an actual run; the scorer does not fabricate scores.
- Playwright smoke test: from `frontend/`, run `npm install`, `npx playwright install chromium`, `npm run dev` in one terminal and `npm run test:e2e` in another (or let Playwright launch the web server).
- Docker Compose local stack: copy `.env.example` to `.env`, set secrets, then `docker compose up --build`. For optional Ollama: `docker compose --profile local-model up --build` and pull the configured model in Ollama.
- `docs/DEMO_AND_USER_SESSIONS.md` contains the demo path, participant-session protocol, deployment checklist and fallback policy. Real deployment, 5–8 participant sessions and recording a live demo must be completed by the team in its target environment; this repository does not claim those external activities have already happened.
- `data/sample/demo_fallback.json` is labelled as simulated fictional data and must never be presented as live inference.

### Migrations and tests
The migration chain currently ends at `0007_r2_r7_content_metadata`. Verify from a clean SQLite database with:

```bash
cd backend
DATABASE_URL=sqlite:////tmp/brandcourt_clean.db alembic upgrade head
pytest -q tests/test_claim_policy.py tests/test_text_intelligence.py tests/test_image_intelligence.py tests/test_semantic_retrieval.py
```

The full async API suite requires the dependencies in `backend/requirements.txt`, including `aiosqlite` for local SQLite and `asyncpg` for PostgreSQL. Install frontend dependencies before running the production build and Playwright suite.
