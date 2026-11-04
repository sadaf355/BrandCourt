# BrandCourt R2–R7 audit note

## Implemented in this code update
- Claim Court v2 unit normalization, unsupported and needs-human-review verdicts, rule-derived severity, India IN-1 to IN-6 checks, disclosure/alt-text reminders, language heuristic, sensitive-pattern masking and model-call log.
- Async review job records and polling, finding states, edit-to-new-revision/re-check, approved revision snapshot lock, reviewer queue, and manager/admin sign-off for India-pack overrides.
- Image analysis service with CIEDE2000 palette distance, estimated contrast ratio, OCR bounding boxes, configurable logo reference comparison, and human-review routing for failed/unavailable checks.
- JSON/PDF report endpoints with model/service disclosure, Recharts dashboard, three-panel findings workbench, expiry visibility and role-aware nav.
- Hashing/trigram fallback retrieval embeddings, optional batched Ollama embeddings and local Ollama NLI adapter, full-engine candidate fix verification with Intent Preserved claim count, and precedent-to-draft-rule promotion.
- Fictional GlowSerum seed script, 40-post JSONL evaluation set, precision/recall scoring script, Playwright end-to-end smoke test covering content creation and the Claim Court verdict path, Docker Compose stack, labelled fallback and real-user session/deployment runbook.

## Verification actually performed in this environment
- `python -m compileall -q app alembic tests`: passed.
- Focused backend tests for claim policy/approval gating, masking/language/declarations, image metrics, retrieval and security: 18 passed.
- Clean SQLite migration through Alembic head: passed using `DATABASE_URL=sqlite:////tmp/brandcourt_clean.db alembic upgrade head`.
- Frontend package installation did not complete in this environment because package registry/network access timed out. Production Vite build, ESLint and Playwright browser execution are therefore not claimed as passed.
- The full API runtime suite was not executed here because `aiosqlite` and `asyncpg` are not installed in the execution environment. They are declared in `backend/requirements.txt`.
- No cloud deployment, live user sessions, or live demo recording has been performed from this environment. Follow `docs/DEMO_AND_USER_SESSIONS.md` and record actual results.

## Important limitations
- Language detection is script/lexicon-based and cannot reliably disambiguate all Hindi/Marathi/Hinglish.
- The default retrieval vector is deterministic hashing/trigram, not a pretrained semantic model. Optional Ollama embeddings and NLI require downloading and testing the configured models locally; an unavailable embedding service creates an explicit Needs human review finding.
- Image contrast is estimated from OCR regions; logo comparison is approximate pixel distance and only works with a configured internal reference path. These checks never constitute a certified brand/accessibility audit.
- Intent preservation uses text similarity, claim-text matching and CTA retention, not a guarantee of semantic equivalence.
- The India pack is starter guidance, not legal advice. Human review and current jurisdiction/platform policy checks remain required.
