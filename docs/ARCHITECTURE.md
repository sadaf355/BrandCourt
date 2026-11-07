# BrandCourt architecture

BrandCourt is a multi-workspace application for governing brand knowledge, checking campaign content against approved evidence, and recording human review decisions.

## Runtime components

- **Web client:** React 19, TypeScript, Vite, React Router and a custom CSS design system.
- **API:** FastAPI, Pydantic Settings and SQLAlchemy's asynchronous ORM.
- **Database:** PostgreSQL (including Neon) for deployment; SQLite is supported for local development and tests. Alembic owns schema migrations. PostgreSQL deployments use pgvector for vector columns.
- **Object storage:** local filesystem for development or S3-compatible storage for durable deployments.
- **Background processing:** an optional asyncio review-job worker runs in the API process when `JOB_WORKER_ENABLED=true`. Database leases coordinate job claims.
- **Analysis:** deterministic checks are the baseline. Retrieval uses local hashing/trigram vectors by default; Ollama embeddings and NLI are optional. Model output is schema-validated and evidence quotes are checked against stored facts.
- **Image text:** Tesseract OCR is optional and requires the system executable.

## Request and review flow

1. The browser authenticates against the API and sends a bearer token with workspace-scoped requests.
2. The API checks role permissions and workspace ownership before reading or changing data.
3. Guideline and approved-fact records provide the governed evidence used by Claim Court.
4. Content revisions are analyzed with deterministic checks first. Optional retrieval/model steps can add context but must not silently replace deterministic findings.
5. Findings retain evidence and method metadata. Uncertain or unavailable model results remain subject to human review.
6. Review decisions, approvals and changes are recorded in the audit trail. Approved revisions are snapshotted and locked until an authorized reopen action.

## Deployment topology

The supported production topology is a Vercel-hosted static frontend and a persistent FastAPI container connected to Neon PostgreSQL and private S3-compatible object storage. The API container applies Alembic migrations before Uvicorn starts. Set exact frontend origins in `CORS_ORIGINS`; do not use wildcard origins with credentialed requests.

For local development, `docker compose up --build` starts PostgreSQL, the API, the web container, and a fact-expiry scheduler. The API's review worker is enabled by default in Compose. In production, run one Uvicorn process per API container when the in-process worker is enabled; scale with additional containers and database-backed job leases.

## Security boundaries

- Every workspace-owned record is queried within its workspace context.
- Role checks are enforced by API dependencies, not only by frontend visibility.
- Uploaded files use validated storage keys; production files belong in private object storage.
- Secrets are read from environment variables and must not be committed or exposed as `VITE_*` values.
- Claim Court findings are decision-support signals, not legal advice or a guarantee of factual truth.
