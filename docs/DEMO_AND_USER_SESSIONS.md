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
