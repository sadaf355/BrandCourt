# BrandCourt demo, user sessions and ship checklist

## Live demo path (8–10 minutes)
1. Register a throwaway workspace named `GlowSerum Demo`.
2. Run `python -m app.seed_glowserum --email <registered-admin-email>` from `backend/`.
3. Open Content reviews and choose a seeded GlowSerum post. State that the brand and content are fictional.
4. Run Claim Court and show the queued job progress, verdict, rule/fact evidence, detected language and privacy/model disclosure.
5. Show Image intelligence with an uploaded image; point out OCR boxes, palette distance, contrast and logo check states. Failed/unavailable checks must remain `needs_human_review`.
6. Submit content, open Reviewer queue, start review, resolve findings, and approve as a manager/admin. Show that the approved revision is locked.
7. Export both JSON and PDF and show the AI/service disclosure.
8. Show the Insights dashboard, expired/expiring facts, Guideline Health and Precedent Ledger.

## Fallback policy
If the API, database, OCR engine or local model is unavailable, open `data/sample/demo_fallback.json`. Read its label aloud: **“SIMULATED DEMO FALLBACK — FICTIONAL GLOWSERUM DATA; NOT LIVE CUSTOMER DATA.”** Never describe precomputed fallback findings as live inference. Record the failure and return to the live app if it recovers.

## Seeding a hosted instance

To seed a hosted deployment without generating broken image links:

1. Run the seed script from a local machine with `DATABASE_URL` pointing at the hosted database:
   ```bash
   DATABASE_URL="postgresql+asyncpg://user:pass@hosted-host/dbname" python -m app.seed_glowserum --email <admin-email> --skip-creatives
   ```
2. The `--skip-creatives` flag ensures seeded rows have `creative_filename` and `creative_storage_key` set to `None`, and no local image files are written.
3. Image posts must be uploaded live through the web UI so that image files are stored directly in the active environment's configured storage backend.

## Demo workspace

### Automatic path (recommended)

When `DEMO_LOGIN_ENABLED=true` (backend) and `VITE_DEMO_LOGIN_ENABLED=true` (frontend), the demo workspace is provisioned automatically at startup as an unblocked background task:
1. Visitors click the **GlowSerum Demo** button on `/login` or `/signup` and instantly land in the pre-filled fictional workspace without needing manual seed runs or passwords.
2. The demo accounts are mapped to `@glowserum.com` addresses (`demo-admin@glowserum.com`, `creator@glowserum.com`, `reviewer@glowserum.com`, `manager@glowserum.com`).
3. Inside the workspace, users can switch between **Admin**, **Creator**, **Reviewer**, and **Manager** roles using the top-bar role selector.
4. If `DEMO_RESET_ON_START=true`, only the workspace marked `is_demo` is safely re-initialized on startup.

### Manual CLI path (fallback)

To manually seed a repeatable demo workspace with extra roles, conflicting rules, expiring facts, and demo campaign drafts:

1. Run the seed script with the demo flags:
   ```bash
   python -m app.seed_glowserum --email <admin email> --skip-creatives --demo --demo-password <password>
   ```
2. The CLI `--demo` mode shares the exact same provisioning engine (`ensure_demo_workspace`) and creates both `@glowserum.com` and `@demo.local` role accounts idempotently without resetting passwords.
3. The demo workspace mode provisions:
   - Active role accounts for creator, reviewer, manager, and demo admin.
   - Facts including `FACT-DEMO-EXPIRING` (valid for 3 days) and the expired `FACT-OFFER`.
   - Conflicting rules (`DEMO-CONFLICT-A` and `DEMO-CONFLICT-B`) for Guideline Health testing.
   - Five drafts under "GlowSerum DEMO" exercising wrong numbers, regional language (Marathi), missing disclosures, clean approved content (locked and snapshotted), and fresh findings.
   - A disputed finding and pending precedent for the Precedent Ledger.

## 5–8 user feedback sessions
These sessions must be run with real participants; they cannot be honestly marked complete by a code-generation task. Obtain consent before recording. Do not use real customer claims or personal data. Suggested participants: 2 creators, 2 reviewers, 1 guideline owner/manager, and 1–3 additional marketers/compliance reviewers.

Tasks:
- Add or inspect an approved fact and its validity window.
- Review a post with a wrong number and identify the supporting evidence.
- Find the missing paid disclosure / unsupported superlative flags.
- Explain what “Needs human review” means.
- Make a revision, re-run checks, and compare versions.
- Complete review and explain why approval is blocked or allowed.
- Export and locate AI/service disclosure in the report.

Record for each session: participant role (no name required), task completion, time-on-task, misclicks, confidence (1–5), severity misunderstandings, and one quote only with explicit permission. Summarize recurring issues, not individual identities. Do not fabricate session results.

## Deployment checklist
- [ ] Set strong `SECRET_KEY`, database credentials, and production CORS allowlist.
- [ ] Provision managed PostgreSQL and persistent private file storage.
- [ ] Set `DATABASE_URL`, `UPLOAD_DIR`, `CORS_ORIGINS`, `MODEL_MODE`, and optional Ollama settings.
- [ ] Deploy API and frontend; confirm `/api/health`, `/docs`, login, upload, OCR, job polling, reports and export.
- [ ] Run migrations against an empty database before importing demo data.
- [ ] Enable HTTPS, backups, upload limits, log retention and an error tracker.
- [ ] Warm free-tier services before judging; keep the labelled fallback available.
- [ ] Record a real demo only after the live flow passes; store consent and avoid secrets/personal data in the recording.

No deployment, participant session, or video recording is considered completed until the team performs and documents it in the target environment.
