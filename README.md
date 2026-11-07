# BrandCourt

**Evidence-led brand content governance, review and approval.**

BrandCourt gives marketing, compliance and brand teams one workspace to manage brand guidelines, approved product facts and creative assets; review campaign copy and images against that knowledge; resolve findings with human oversight; and retain an auditable record of decisions before content is published.

## What BrandCourt does

- **Brand knowledge:** upload PDF, DOCX or TXT guidelines; review extracted rule proposals; manage versioned rules, approved facts, validity dates, disclosures, terminology, logos, palettes and other brand assets.
- **Content workspace:** create campaign drafts, attach creative files, maintain caption revisions and compare changes.
- **Claim Court:** identify candidate claims and check them against active rules and approved facts. Findings include verdicts, severity, evidence references and the method used.
- **Creative checks:** extract text from supported raster images using OCR and include it in the next review. OCR requires the Tesseract system package.
- **Human review:** comment on drafts, make finding-level decisions, submit content for review, approve or reject with a reason, and reopen approved work when authorized.
- **Guideline intelligence:** inspect guideline health, maintain a workspace-scoped precedent ledger and verify whether a proposed edit preserves the original intent.
- **Reporting and accountability:** review operational insights, export supported reports and inspect an append-only audit trail.

BrandCourt is a decision-support system. Findings are evidence-led signals for human review, not a guarantee of truth, regulatory certification or legal advice. The India starter policy is advisory and must be reviewed against current law and the brand's own counsel.

## How a team uses it

1. A guideline owner creates a workspace and adds the team.
2. The team uploads brand guidelines, confirms the rule proposals it wants to enforce, and records approved facts with source references and validity dates.
3. A creator prepares a campaign draft and attaches the creative.
4. Claim Court checks copy and available OCR text against the workspace's active knowledge and returns findings with evidence and method disclosures.
5. The creator and reviewer discuss findings, accept or dispute them, and record overrides with a reason where permitted.
6. A manager or guideline owner approves only when the approval gate's blocking findings have been addressed. The approved revision is snapshotted and locked until reopened.
7. The team can inspect the audit trail, precedents, guideline health and available reports.

## Roles

| Role | Main responsibilities |
|---|---|
| Creator | Prepare drafts, review findings, comment and submit content |
| Reviewer | Inspect evidence, discuss content and record permitted finding decisions |
| Manager | Manage review operations, approve/reject and reopen content |
| Guideline owner (`admin`) | Manage workspace knowledge, members, governance settings and approvals |

Authorization is enforced by the API and workspace data is tenant-scoped. The exact actions available depend on the role and current review state.

## Technology

- **Frontend:** React 19, TypeScript, Vite, React Router, TanStack Query, a custom CSS design system and Vitest.
- **Backend:** Python, FastAPI, Pydantic Settings, SQLAlchemy async and Alembic.
- **Data:** PostgreSQL (including Neon) or SQLite for local development; pgvector-backed fields support optional retrieval features.
- **Files:** local storage for development or S3-compatible object storage for persistent deployments.
- **Analysis:** deterministic-first claim checks, optional local Ollama retrieval/NLI, and OCR through Tesseract.
- **Quality:** ESLint, Vitest, pytest and Playwright end-to-end tests.

## Repository layout

```text
backend/       FastAPI application, database models, migrations, services and tests
frontend/      React application, component tests and Playwright end-to-end tests
data/          Synthetic GlowSerum demo and regression-test data
docs/          Architecture, API, user, disclosure and demo documentation
```

## Run locally

### Prerequisites

- Python 3.11 or newer (CI uses Python 3.12)
- Node.js 20 and npm
- SQLite for a quick local start, or PostgreSQL for production-like testing
- Tesseract OCR executable if you want image text extraction

### 1. Start the backend

```bash
cd backend
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

On Windows PowerShell, use `Copy-Item .env.example .env` instead of `cp`.

The default local database is SQLite. The API is available at `http://localhost:8000`, interactive documentation at `http://localhost:8000/docs`, and health check at `http://localhost:8000/api/health`.

### 2. Start the frontend

In a second terminal:

```bash
cd frontend
cp .env.example .env
npm ci
npm run dev
```

Open `http://localhost:5173`. Set `VITE_API_BASE_URL` to the backend API base URL, including `/api`. Keep `VITE_USE_MOCK=false` when testing the real backend.

### 3. Create a workspace

Open the app, choose **Create workspace**, and register the first guideline owner. Add brand guidelines and approved facts before creating a campaign draft. For a repeatable demo dataset, see `backend/app/seed_glowserum.py` and the demo instructions in `docs/DEMO_AND_USER_SESSIONS.md`.

## Configuration

Backend settings are read from environment variables (or `backend/.env` for local development). See `backend/.env.example` for the complete list.

| Variable | Purpose |
|---|---|
| `APP_ENV` | Set to `production` in deployment |
| `SECRET_KEY` | Long random secret; production requires at least 32 bytes |
| `DATABASE_URL` | SQLite or PostgreSQL connection string; `postgres://` and `postgresql://` provider URLs are normalized to SQLAlchemy asyncpg URLs |
| `CORS_ORIGINS` | Comma-separated exact frontend origins, with scheme and host and no path |
| `STORAGE_BACKEND` | `local` for development or `s3` for persistent object storage |
| `S3_BUCKET` | Required when `STORAGE_BACKEND=s3` |
| `S3_ENDPOINT_URL` | Optional S3-compatible endpoint (for example, an R2 endpoint) |
| `S3_REGION` | Storage region |
| `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY` | Object-storage credentials; use the platform's workload identity where available |
| `JOB_WORKER_ENABLED` | Start the review-job worker inside the API process; enable for a single-container backend deployment |
| `MODEL_MODE`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, `OLLAMA_EMBEDDING_MODEL` | Optional local-model configuration; deterministic checks remain available without Ollama |

Never commit real `.env` files, database URLs, signing secrets or storage credentials. The frontend `VITE_*` variables are public build-time values; never put secrets in them.

## Deploying

### Frontend on Vercel

The repository includes `vercel.json` for the Vite single-page app. Import the repository into Vercel, set the project root to the repository root, and configure:

```env
VITE_API_BASE_URL=https://YOUR_BACKEND_HOST/api
VITE_USE_MOCK=false
```

Redeploy after changing build-time environment variables. The backend must allow the exact deployed Vercel origin in `CORS_ORIGINS`, for example `https://your-brandcourt.vercel.app` (no trailing slash or path).

### Backend container

The repository includes `render.yaml` for a single Render Docker web service. Set `PORT=8000` (also declared in the blueprint and Docker image), then provide the secrets and provider values below. The container binds to `$PORT`, applies Alembic migrations, and starts the API with its in-process review worker. For other container hosts, use the same environment variables:

```env
APP_ENV=production
PORT=8000
SECRET_KEY=<random-secret-at-least-32-bytes>
DATABASE_URL=<Neon-connection-string>
CORS_ORIGINS=https://your-brandcourt.vercel.app
STORAGE_BACKEND=s3
S3_BUCKET=<private-bucket-name>
S3_REGION=<bucket-region>
S3_ENDPOINT_URL=<optional-s3-compatible-endpoint>
S3_ACCESS_KEY_ID=<access-key>
S3_SECRET_ACCESS_KEY=<secret-key>
JOB_WORKER_ENABLED=true
```

The container entrypoint applies Alembic migrations before starting Uvicorn. With `JOB_WORKER_ENABLED=true`, the review-job worker runs as an asyncio task in the same API process, so a separate worker container is not required. Keep the API at one Uvicorn process per container when using this mode; scale horizontally by adding containers, with the database-backed job leases coordinating workers. Use a managed scheduler for periodic fact expiry if that task is required in your deployment.

For local multi-service development, `docker compose up --build` starts PostgreSQL, the API, the web container and the fact-expiry service. Configure a real `SECRET_KEY` and storage credentials before exposing any service publicly.

### Database and storage notes

- Neon PostgreSQL URLs using `postgres://` or `postgresql://` are normalized to `postgresql+asyncpg://`; `sslmode=require` is translated to asyncpg's `ssl=require` option.
- Use a Neon pooled connection string only if the selected Neon pooler supports the application's asyncpg connection pattern. Keep the direct connection string available for migrations if your provider requires it.
- S3-compatible storage is private object storage. Configure bucket access policies and lifecycle/retention rules in the storage provider; BrandCourt does not create the bucket or its IAM policy.
- Local `UPLOAD_DIR` storage is not suitable for ephemeral production containers.
- Set `CORS_ORIGINS` to the exact frontend origin(s). Do not use `*` with credentialed requests.

## Quality checks

Frontend:

```bash
cd frontend
npm ci
npm run lint
npm test
npm run build
npx playwright install chromium
npm run test:e2e
```

Backend:

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
pytest -q
```

The GlowSerum browser scenario is `frontend/e2e/glowserum-flow.spec.ts`. It expects a reachable backend with the GlowSerum demo workspace/data seeded and configured test users/roles as described in `docs/DEMO_AND_USER_SESSIONS.md`. Playwright starts the Vite dev server automatically; start the API separately and set `VITE_API_BASE_URL` to the local API.

CI runs backend tests against PostgreSQL and frontend lint, unit tests and production build on pushes and pull requests. A local pass does not prove a hosted deployment is healthy; verify the CI workflow and the deployed `/api/health` endpoint after release.

## Product and engineering documentation

- `docs/ARCHITECTURE.md` — application structure and data flow
- `docs/API_CONTRACT.md` — API behavior and request/response contracts
- `docs/USER_GUIDE.md` — user workflows and permissions
- `docs/DISCLOSURES.md` — implemented model, analysis and asset disclosures
- `docs/DEMO_AND_USER_SESSIONS.md` — demo setup and user-session walkthrough

## Known boundaries

- Extracted guideline content is a draft proposal and requires human confirmation.
- Deterministic checks are transparent heuristics; semantic retrieval/NLI requires configured Ollama models and must be disclosed as such.
- OCR depends on the system Tesseract executable and image support; an unavailable OCR engine is reported rather than silently treated as a clean image.
- Some administrative actions are intentionally not exposed in the current API and are not presented as available UI actions.
- External production services (Neon, Vercel, S3-compatible storage, DNS and secrets) must be provisioned and configured by the deploying team.
