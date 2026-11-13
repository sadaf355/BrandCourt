# BrandCourt

<div align="center">

[![CI](https://github.com/sadaf355/BrandCourt/actions/workflows/ci.yml/badge.svg)](https://github.com/sadaf355/BrandCourt/actions)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/Frontend-React%2019-61DAFB.svg?logo=react&logoColor=black)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB.svg?logo=python&logoColor=white)](https://www.python.org)

**Evidence-led brand content governance, multi-modal automated compliance & approval gateway.**

[Key Features](#key-features) • [System Architecture](#system-architecture) • [Getting Started](#getting-started) • [Workflow & Roles](#workflow--roles) • [Configuration](#configuration-reference) • [Deployment](#production-deployment) • [Evaluation](#evaluation--benchmarks)

</div>

---

## Executive Overview

**BrandCourt** bridges the critical gap between high-velocity marketing execution and rigorous regulatory/brand compliance. Designed for brand owners, legal counsel, and compliance teams, BrandCourt provides a unified, auditable environment to:

1. **Ingest & Extract Brand Guidelines**: Turn static PDF, DOCX, and TXT guidelines into enforceable, versioned rules and approved fact libraries.
2. **Automate Pre-Publication Checks (Claim Court)**: Evaluate copy, captions, and creative images against active policies with transparent, evidence-backed findings.
3. **Enforce Human-in-the-Loop Governance**: Provide structured review queues, dispute resolution, documented overrides, and cryptographically snapshotted approvals.
4. **Prevent Brand Drift**: Leverage precedent ledgers, guideline contradiction detectors, and fact validity timers.

> **Decision Support Notice**: BrandCourt is a decision-support governance platform. Findings are evidence-led signals designed to assist human reviewers—not legal advice, statutory certification, or an absolute guarantee of regulatory compliance.

**Live Demo:** The frontend is deployed to Vercel and the backend to Render (see [render.yaml](render.yaml) and [vercel.json](vercel.json)). Configure `VITE_API_BASE_URL` in your Vercel environment to point at your deployed backend.

**Demo Access:** On the login page, click the **Demo** button. No password required. This logs you into the fictional GlowSerum workspace with pre-seeded content (5 demo drafts in `demo_mode: true`). The demo workspace is a shared public workspace — do not enter real brand or personal data.

---

## System Architecture

```mermaid
flowchart TD
    subgraph Client ["Frontend Client (React 19 + TypeScript + Vite)"]
        UI["Modern Dashboard & Review Workspace"]
        State["TanStack Query + Theme Manager"]
        ThreeCanvas["Three.js Interactive Visuals"]
    end

    subgraph API ["Backend API (FastAPI + Async Python)"]
        Auth["Tenant & RBAC Gateway (JWT)"]
        Router["API Routers (/auth, /content, /rules, /facts, /insights)"]
        
        subgraph ClaimCourt ["Claim Court Engine"]
            RulesEngine["Deterministic Rule Engine\n(Regex, Windowing, Thresholds)"]
            OCREngine["OCR Text Extraction\n(Tesseract - ENG/HIN/MAR)"]
            NLIEngine["Semantic Search & NLI\n(Ollama + pgvector)"]
        end
        
        Worker["Durable In-Process Job Worker\n(Lease-locked Async Queue)"]
    end

    subgraph Storage ["Persistence & Storage Layer"]
        DB[("PostgreSQL / SQLite\n(SQLAlchemy Async + Alembic)")]
        BlobStore["Object Storage\n(Local Disk / S3 / Cloudflare R2)"]
    end

    UI <-->|REST API + JWT| Auth
    Auth --> Router
    Router --> Worker
    Worker --> ClaimCourt
    ClaimCourt --> DB
    Router --> BlobStore
    Router --> DB
```

---

## Key Features

### 🏛️ Automated Claim Court & Evidence-Led Verification
- **Multi-Modal Review**: Analyzes drafted copy alongside attached creative graphics (extracting text from raster images via Tesseract OCR).
- **Explainable Findings**: Every finding provides a normalized severity (`critical`, `major`, `advisory`), source guideline/fact citation, matched excerpt, and inspection method.
- **Fact Expiry & Disclaimers**: Automatically flags statements relying on expired clinical facts, missing mandatory disclosures, or unauthorized comparative claims.

### 🛡️ Human-in-the-Loop Approval Gateway
- **Blocking Gates**: Campaigns cannot be finalized or signed off until all blocking violations are either resolved or explicitly overridden.
- **Audit-Logged Overrides**: Reviewers and managers must submit mandatory business justifications for any policy override.
- **Cryptographic Snapshotting**: Once approved, the campaign state, creative files, and review findings are snapshotted and permanently locked.

### 📚 Living Brand Knowledge Base
- **Guideline Ingestion**: Upload guidelines in PDF, DOCX, or TXT formats; the parser produces proposed rules for human confirmation.
- **Approved Fact Repository**: Manage claim substantiations with clinical trial citations, sample sizes, and validity date windows.
- **Precedent Ledger**: Maintains a historic record of past review determinations to ensure precedent consistency across campaigns.

### 🎨 Enterprise-Grade UI/UX
- **High-Contrast Design System**: Fully accessible light and dark themes with WCAG AA compliance.
- **Collapsible Navigation Rail**: One-click collapsible sidebar with icon rail mode and tooltip navigation.
- **Responsive Workspace**: Seamless, zero-overlap fluid layouts built for large campaign queues.

---

## Workflow & Roles

```
[ Creator ]              [ Claim Court ]             [ Reviewer / Manager ]
    │                           │                              │
    ├── 1. Submit Draft ───────>│                              │
    │   (Copy + Creative)       ├── 2. OCR & Rule Match        │
    │                           ├── 3. Produce Findings ──────>│
    │                           │                              ├── 4. Inspect Evidence
    │<── 5. Feedback / Edit ────┼──────────────────────────────┤   & Record Overrides
    │                           │                              │
    └── 6. Resubmit ───────────>├── 7. Re-verify               │
                                └── 8. Gate Cleared ──────────>├── 9. Sign-off & Lock
```

### Role-Based Access Control (RBAC)

| Role | Permissions & Responsibilities |
|---|---|
| **Creator** | Draft campaigns, attach creative media, review findings, submit for review, comment. |
| **Reviewer** | Inspect evidence citations, request copy adjustments, submit finding-level decisions and overrides. |
| **Manager** | Approve or reject campaigns, enforce approval gates, reopen signed-off campaigns with cause. |
| **Guideline Owner (`admin`)** | Full workspace authority: manage workspace members & roles, upload guidelines, confirm rules, configure facts and policies. |

---

## Repository Layout

```text
BrandCourt/
├── backend/
│   ├── alembic/              # Database migration versions
│   ├── app/
│   │   ├── api/              # FastAPI endpoints (auth, campaigns, guidelines, reviews)
│   │   ├── core/             # Configuration, database session, security, exceptions
│   │   ├── models/           # SQLAlchemy database models
│   │   ├── schemas/          # Pydantic validation schemas
│   │   ├── services/         # Claim Court engine, OCR, parser, durable worker
│   │   ├── seed_glowserum.py # Golden demo dataset seeder
│   │   └── main.py           # Application entrypoint & lifecycle
│   └── tests/                # Backend automated tests
├── frontend/
│   ├── src/
│   │   ├── components/       # UI library, AppShell, 3D Canvas, Review cards
│   │   ├── pages/            # Dashboard, Queue, Guidelines, Facts, Assets
│   │   ├── lib/              # API client, contracts, state hooks
│   │   └── styles.css        # Pure CSS design system & high-contrast tokens
│   └── tests/                # Vitest contract tests and Playwright E2E suites
├── data/
│   └── sample/               # GlowSerum 52-case regression test dataset
└── docs/                     # Comprehensive architecture, API contracts, and user guides
```

---

## Getting Started

### Prerequisites

- **Python**: 3.11 or newer (Python 3.12 recommended)
- **Node.js**: v20 LTS or higher (`npm` v10+)
- **Tesseract OCR** *(Optional for image OCR)*:
  - Ubuntu/Debian: `sudo apt-get install tesseract-ocr tesseract-ocr-hin tesseract-ocr-mar`
  - macOS: `brew install tesseract`
  - Windows: [UB-Mannheim Tesseract installer](https://github.com/UB-Mannheim/tesseract/wiki)
- **Database**: SQLite (built-in default) or PostgreSQL 15+ (Neon supported)

---

### Quick Start (Local Development)

#### 1. Start the Backend API

```bash
cd backend
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate
# On Windows PowerShell:
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
cp .env.example .env

# Apply database migrations
alembic upgrade head

# Seed the GlowSerum demo workspace (Optional)
# For a fresh workspace: python -m app.seed_glowserum --email <your-admin-email>
# For the demo workspace (press Demo button on login):
python -m app.seed_glowserum --email demo-admin@glowserum.com --demo --demo-password <choose-a-password>

# Start the development server
uvicorn app.main:app --reload --port 8000
```

- API Base URL: `http://localhost:8000`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`
- Health Endpoint: `http://localhost:8000/api/health`

#### 2. Start the Frontend Application

In a separate terminal:

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

- Web Application: `http://localhost:5173`
- Ensure `frontend/.env` contains:
  ```env
  VITE_API_BASE_URL=http://localhost:8000/api
  VITE_USE_MOCK=false
  ```

---

### Docker Compose (Full Stack)

To run the entire multi-service stack (PostgreSQL, FastAPI Backend, Frontend, and Fact-Expiry Scheduler) with a single command:

```bash
docker compose up --build
```

---

## Configuration Reference

Settings are loaded via environment variables or a local `.env` file via Pydantic Settings.

| Variable | Default / Safe Example | Purpose |
|---|---|---|
| `APP_ENV` | `production` | Environment mode (`production`, `staging`, `development`). In production, enforces strict DB and key validation. |
| `PORT` | `8000` | HTTP port for server binding in containerized deployments. |
| `SECRET_KEY` | *(required)* | Cryptographic signing secret for JWT access tokens (minimum 32 characters in production). |
| `DATABASE_URL` | `postgresql+asyncpg://user:pass@ep-xyz.region.neon.tech/neondb?ssl=require` | Neon PostgreSQL non-pooled connection URL (direct endpoint required for Alembic migrations). |
| `CORS_ORIGINS` | `https://brandcourt.vercel.app` | Comma-separated list of exact allowed browser origins without trailing slashes. |
| `STORAGE_BACKEND` | `s3` | Storage driver for uploaded creatives: `s3` for AWS S3 / Cloudflare R2, or `local` for disk filesystem. |
| `S3_BUCKET` | `brandcourt-creatives` | Target S3 or Cloudflare R2 bucket name for uploaded assets. |
| `S3_REGION` | `us-east-1` | S3 bucket region (or `auto` for Cloudflare R2). |
| `S3_ENDPOINT_URL` | `https://<account_id>.r2.cloudflarestorage.com` | Custom endpoint URL for S3-compatible object storage (omit for standard AWS S3). |
| `S3_ACCESS_KEY_ID` | `your-s3-access-key-id` | S3 or Cloudflare R2 API access key ID. |
| `S3_SECRET_ACCESS_KEY` | `your-s3-secret-access-key` | S3 or Cloudflare R2 API secret access key. |
| `JOB_WORKER_ENABLED` | `true` | Starts the async background review queue and 24-hour fact-expiry check within the API process. |
| `MODEL_MODE` | `deterministic` | Review engine mode: `deterministic` for rule-based Claim Court or `ollama` for local model embeddings. |
| `DEMO_LOGIN_ENABLED` | `true` | Enables one-click `POST /api/auth/demo-login` strictly for the fictional workspace marked `is_demo=true`. |
| `DEMO_RESET_ON_START` | `false` | When `true`, resets and re-seeds clean demo data on boot; must be `false` after initial deploy. |
| `LOGIN_MAX_FAILURES` | `10` | Maximum failed sign-in attempts per client IP before temporary rate-limit lockout. |
| `VITE_API_BASE_URL` | `https://brandcourt-api.onrender.com/api` | Vercel frontend setting pointing to the public backend API endpoint. |
| `VITE_USE_MOCK` | `false` | Vercel frontend setting to disable mock handlers and connect to the real API. |
| `VITE_DEMO_LOGIN_ENABLED` | `true` | Vercel frontend setting enabling the Demo button and helper cue on the login page. |

---

## Evaluation & Benchmarks

BrandCourt is continuously evaluated against a 52-case golden evaluation dataset (`data/sample/glowserum_40_posts.jsonl`) reflecting realistic skincare advertising claims, ASCI regulatory requirements, and edge cases.

### Deterministic Regression Benchmark (52 Golden Cases — deterministic mode, rules tuned on this set)

> **Important:** These results were measured in `MODEL_MODE=deterministic` on the 52-post GlowSerum sample corpus. Rules were iteratively tuned against this same corpus, so this is a regression result, **not** a held-out accuracy estimate. See [docs/EVALUATION.md](docs/EVALUATION.md) for full methodology and limitations.

| Metric | Measured result |
|---|---:|
| Cases completed | 52 / 52 |
| Exact label match | 52 / 52 |
| Exact-match accuracy (deterministic) | 100% |
| False flags | 0 |
| False negatives | 0 |
| Median worker processing time | 550.54 ms |
| Slowest worker processing time | 5487.33 ms |
| Ollama variants (retrieval_and_nli, full_pipeline) | **Not measured** — Ollama service not running |

To run the deterministic evaluation suite:

```bash
cd backend
python -m pytest -s tests/test_analysis_golden.py::test_all_glowserum_seed_posts_run_through_durable_worker -q
```

*For detailed evaluation metrics, historical comparisons, and methodology, see [docs/EVALUATION.md](docs/EVALUATION.md).*

---

## Testing & Quality Assurance

All pull requests and commits run through a strict automated CI verification pipeline:

```bash
# Frontend Unit & Contract Tests (19 passed across 5 files — measured 2026-11-13)
cd frontend
npm ci
npm run lint
npm test -- --run
npm run build

# Frontend Playwright End-to-End Suite (36 passed across 7 suites — measured 2026-11-13)
npx playwright install chromium
npm run test:e2e

# Backend Unit & Integration Tests (182 passed, 6 skipped — measured 2026-11-13)
cd backend
# Install dependencies first (required before pytest):
pip install -r requirements.txt
pytest -v
```

> **Note on frontend tests:** `npm test -- --run` is correct for Vitest 5.x (the `test.poolOptions` deprecation warning from `npm test` without `--run` is cosmetic and does not affect results).
>
> **Note on backend tests:** `pip install -r requirements.txt` must be run from the `backend/` directory before running `pytest`. Of the 6 skipped tests (measured 2026-11-13): 5 are in `tests/test_image_intelligence.py` and require an installed Tesseract executable; 1 is in `tests/test_migrations_clean.py` and requires `TEST_POSTGRES_URL` to be configured. None are failures.

---

## Round 3 Features

Three new intelligence features were added in Round 3. All run in `MODEL_MODE=deterministic`; Ollama-based NLI confirmation requires a configured Ollama service.

### Guideline Health (`/app/brand/guideline-health`)
Detects vague rules and potentially conflicting rule pairs within your active rule set. Conflict pairs are shown as `candidate_only` without Ollama. To accept a vague-rule fix, click **Accept** — this creates a draft rule version for admin confirmation before it goes live. See [docs/USER_GUIDE.md](docs/USER_GUIDE.md#7-round-3-features--where-to-find-them) for details.

### Precedent Ledger (`/app/intelligence/precedents`)
Records past reviewer override decisions. When similar copy is re-reviewed, matching precedents (similarity ≥ 0.85) surface on the finding card. Critical findings cannot be downgraded via precedent — a 409 error is returned if attempted.

### Fix Verification (`/app/intelligence/fix-verify`)
Test a proposed copy edit before resubmitting. The engine runs a full analysis on a temporary revision, checks intent similarity and CTA preservation, and shows whether the fix introduces any new Critical findings. Fixes that add new Critical findings are automatically rejected.

> **India rules pack:** The India rules pack provides starter guidance for internal compliance review workflows. It is not legal advice and must not be substituted for review by a qualified legal professional familiar with current ASCI, ASI, Drugs & Magic Remedies Act, and applicable advertising regulations.

---

## Known Limitations

- **Evaluation corpus:** The 52 GlowSerum posts are fictional and have historical exposure to rule development. The 100% exact-match result is a regression score, not a held-out accuracy estimate.
- **Ollama variants:** `retrieval_and_nli` and `full_pipeline` checks require a running Ollama service. They were not measured in this session.
- **Image analysis & OCR:** Five expected visual labels exist in the dataset, but corresponding source image files are not included. The three analysed images (`frontend/public/landing/skincare.webp`, `desk.webp`, `shield-poster.webp`) are landing-page stock images analysed with an arbitrary test palette, NOT real creatives or brand creatives. OCR was unavailable (Tesseract not installed locally), the result for each was `needs_human_review`, and this demonstrates the safe fallback only, not OCR or brand-colour accuracy. Do not claim anything about OCR accuracy.
- **Language coverage:** Hindi/Marathi and mixed-script (Hinglish) content has limited automated coverage. Human review by a fluent speaker is required.
- **Demo workspace:** The demo runs `MODEL_MODE=deterministic`. Uploaded files are lost on hosting restarts (local disk storage). The free-tier API may sleep when idle.
- **Workflow gaps:** Comment resolution, email invitations, member removal, and workspace deletion are not fully exposed as end-to-end product actions.
- **Accessibility:** `axe-core` is a dependency, not evidence of a completed accessibility audit.

---

## Production Deployment

### 1. Frontend on Vercel
1. Link your GitHub repository in [Vercel](https://vercel.com).
2. Set Root Directory to `./frontend` (or project root with the included `vercel.json`).
3. Set Environment Variables:
   - `VITE_API_BASE_URL`: `https://brandcourt-api.onrender.com/api`
   - `VITE_USE_MOCK`: `false`
   - `VITE_DEMO_LOGIN_ENABLED`: `true`

### 2. Backend on Render / AWS / Railway
1. Use the provided [render.yaml](render.yaml) or [Dockerfile](Dockerfile).
2. Set `DATABASE_URL` to your managed PostgreSQL instance (e.g., Neon direct endpoint).
3. Set `CORS_ORIGINS` to `https://brandcourt.vercel.app` (strictly without trailing slash).
4. Set `STORAGE_BACKEND=s3` and configure your S3 / Cloudflare R2 bucket credentials.
5. The container entrypoint automatically executes `alembic upgrade head` before booting Uvicorn with `--proxy-headers` and `--forwarded-allow-ips="*"`.

### Demo Workspace & Reset Behavior
1. The shared GlowSerum demo workspace (`is_demo: true`) is provisioned on startup with pre-seeded brand guidelines, active rules, clinical facts, and five demo review drafts.
2. Setting `DEMO_RESET_ON_START=true` purges stale demo records and completely re-creates demo rules with examples and reworded conflict rules.
3. With clean re-seeded rules, Guideline Health detects exactly 8 planted issues (4 conflict pairs and 4 vague rules) rather than unconstrained pairs.
4. After initial deployment, `DEMO_RESET_ON_START` must be set back to `false` in Render environment variables.
5. Keeping it `false` prevents the demo workspace from being wiped on container restarts, preserving reviewers' and judges' test data.

### Deployment Checklist

Follow these steps to deploy and verify BrandCourt in production:

1. **Set Render Environment Variables**:
   In your Render dashboard for `brandcourt-api`, configure:
   - `APP_ENV=production`
   - `PORT=8000`
   - `SECRET_KEY=<generate-32+-char-secret>`
   - `DATABASE_URL=postgresql+asyncpg://<user>:<password>@<neon-host>/<db>?ssl=require` (Neon direct non-pooled endpoint)
   - `CORS_ORIGINS=https://brandcourt.vercel.app`
   - `STORAGE_BACKEND=s3` along with `S3_BUCKET`, `S3_REGION`, `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`
   - `JOB_WORKER_ENABLED=true`
   - `MODEL_MODE=deterministic`
   - `DEMO_LOGIN_ENABLED=true`
   - `DEMO_RESET_ON_START=true` (for the first deploy only)
   - `LOGIN_MAX_FAILURES=10`

2. **Set Vercel Environment Variables**:
   In your Vercel project settings, configure:
   - `VITE_API_BASE_URL=https://brandcourt-api.onrender.com/api`
   - `VITE_USE_MOCK=false`
   - `VITE_DEMO_LOGIN_ENABLED=true`

3. **Deploy & Seed Demo Workspace**:
   - Trigger deployment on Render (the Dockerfile runs `alembic upgrade head` automatically and starts uvicorn with proxy headers).
   - Trigger deployment on Vercel.
   - Once the Render deployment succeeds and seeds the demo data, toggle `DEMO_RESET_ON_START=false` in Render so subsequent container restarts retain judge modifications.

4. **Verify Health & Demo Login**:
   - Confirm backend health: `curl -s https://brandcourt-api.onrender.com/api/health` returns `{"status":"ok","service":"BrandCourt API","database":"connected"}`.
   - Confirm demo readiness: `curl -s https://brandcourt-api.onrender.com/api/auth/demo-status` returns `{"enabled":true,"ready":true}`.
   - Confirm frontend access: Open `https://brandcourt.vercel.app/login`, click the **Demo** button, and verify instant login into the GlowSerum Demo workspace with 5 pre-loaded drafts and 8 Guideline Health issues.

---

## Documentation Index

| Guide | Description |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | In-depth system architecture, concurrency leases, and data flow. |
| [docs/API_CONTRACT.md](docs/API_CONTRACT.md) | Complete OpenAPI endpoint specifications and schema definitions. |
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | Step-by-step user journey, roles, and review workflows. |
| [docs/EVALUATION.md](docs/EVALUATION.md) | Regression benchmarks, scoring formulas, and test results. |
| [docs/DISCLOSURES.md](docs/DISCLOSURES.md) | Regulatory boundaries, model disclosures, and hosted demo limits. |
| [docs/DEMO_AND_USER_SESSIONS.md](docs/DEMO_AND_USER_SESSIONS.md) | Walkthrough script for live demonstrations and testing sessions. |
| [docs/ROUND_3_REPORT.md](docs/ROUND_3_REPORT.md) | Round 3 implementation report, evidence, and validation results. |
| [docs/ROADMAP.md](docs/ROADMAP.md) | Product roadmap: near-, medium-, and long-term feature plans. |

---

## License

No separate `LICENSE` file is included in this repository.
