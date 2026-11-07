# BrandCourt A4 final completion audit

## Result

**A4 verdict: NOT PASS.** The variant controls, code-only measurement, expiry idempotency, and
local-model failure-path tests are implemented and verified. Retrieval+NLI and full-pipeline
comparative results are blocked because the configured Ollama endpoint was unreachable. The
Compose fact-expiry service parsed correctly, but Docker was unavailable, so its runtime startup
was not verified.

## Comparative evaluation evidence

The repeatable evaluation runner takes an admin-only variant selector, persists it in the
durable review job, checks the worker's completed result, and records the same GlowSerum JSONL
SHA-256 per prediction. The scorer reports exact-match accuracy, micro precision/recall/F1,
false positives/negatives, failures, and worker latency. Failed cases are not silently omitted.

Dataset: 52 fictional GlowSerum posts; SHA-256
`fb75f41fa6929f1a1c7b97c34828f3eaf345713c5a1ac36d8b9f9753b70b43b1`.

## Deterministic regression result: 52 cases, rules tuned on this set, not held-out accuracy

> **Note on evaluation split:** GC-042 and GC-043 rules were added after the evaluation split was defined, so the numbers are not a clean held-out result.

| Metric | Measured result |
|---|---:|
| Cases completed | 52 / 52 |
| Exact label match | 52 / 52 |
| Exact-match accuracy | 100% |
| Micro precision | 100% |
| Micro recall | 100% |
| Micro F1 | 100% |
| False flags | 0 |
| False negatives | 0 |
| Failed cases | 0 |
| Error findings | 19 |
| Error findings with a cited fact, approved fact, or active-rule source reference | 12 / 19 (63.16%) |
| Needs-human-review findings | 30 |
| Median worker processing time | 550.54 ms |
| Slowest worker processing time | 5487.33 ms |

## Historical, measured on the original 40 posts only

| Variant | Completed | Failures | Exact-match accuracy | Precision | Recall | F1 | False positives | False negatives | Median worker ms | Slowest worker ms |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Code-only | 40/40 | 0 | 37.5% | 100% | 16.13% | 27.78% | 0 | 26 | 96.97 | 136.85 |
| Retrieval + NLI | BLOCKED | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| Full pipeline | BLOCKED | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

The two blocked variants were preflighted separately. Both returned
`Ollama preflight failed: All connection attempts failed` before any predictions were written.
No historical deterministic result was reused as a variant score. Exact-match accuracy means
the fraction of posts whose complete set of predicted finding labels equals its expected set.

Reproduce from `backend/` after seeding the same data and starting API/worker:

```powershell
python scripts/evaluate_api.py --variant code_rules_only --token <admin-token>
python scripts/evaluate_api.py --variant retrieval_and_nli --token <admin-token>
python scripts/evaluate_api.py --variant full_pipeline --token <admin-token>
python scripts/score_eval.py --code-only ..\data\sample\glowserum_code_rules_only_predictions.jsonl --retrieval-nli ..\data\sample\glowserum_retrieval_and_nli_predictions.jsonl --full ..\data\sample\glowserum_full_pipeline_predictions.jsonl --evaluation-doc ..\docs\EVALUATION.md
```

The two model-dependent variants require a reachable Ollama server with both configured
`OLLAMA_MODEL` and `OLLAMA_EMBEDDING_MODEL` present. The runner reports BLOCKED and writes no
prediction file if preflight fails.

## Fact expiry

The expiry function was tested against expired and soon-to-expire facts. One pass marked the
expired fact and created one notice per active manager/admin for each applicable notice type;
a second pass created no notices and expired no additional facts. The expiry query and existing
notice lookup are workspace-scoped.

Docker Compose now runs the existing script in watch mode as `fact-expiry`, with a configurable
interval (`FACT_EXPIRY_INTERVAL_HOURS`, default 24) and dependencies on the healthy database and
API. Compose YAML was parsed and the service command, restart policy, and dependencies were
verified. Docker Compose execution and cron invocation were not verified because `docker` is
not installed in the environment. See `docs/EVALUATION.md` for Compose and one-shot cron examples.

## Local model evidence and limitations

- Admin model-mode switching is covered by API tests.
- A review-worker test simulates unavailable embeddings, checks the deterministic fallback, and
  verifies a visible `needs_human_review` finding.
- Mocked tests cover invalid NLI JSON and timeout; provider schema validation also retries once
  and fails visibly for invalid structured output.
- An unavailable local endpoint was observed during evaluator preflight; it did not provide live
  model inference.
- No OS/container-level network isolation test was run. No network-isolation claim is made.

## Validation performed

From `backend/`:

```powershell
python -m pytest -q tests/test_score_eval.py tests/test_analysis_golden.py tests/test_a4_services.py tests/test_checking_engine.py tests/test_intelligence_api.py
```

Result: **40 passed**, one pytest configuration warning (`asyncio_mode` is unknown to the
installed pytest-asyncio), 23.08 seconds.

```powershell
python -m pytest -s -q
```

Result: **134 passed, 1 skipped**, two warnings (unknown `asyncio_mode` config option and
Starlette's `httpx` TestClient deprecation), 74.93 seconds. The run printed the measured
40-case full deterministic path and a separate 40-job code-only result.

`git diff --check`: passed after the final documentation updates.

## Ownership review

No Person B-owned files (`backend/app/api/release.py`, `backend/app/api/workflow.py`,
`frontend/**`, or Person B report/notification modules) were changed for this sprint. Existing
worktree changes from earlier Person A A1–A3/A4 work remain; this audit does not claim they were
created in this final sprint.


## Follow-up production-readiness corrections (2026-11-07)

The current repository includes these corrections after the historical A4 audit above:

- The PostgreSQL `vector` extension is created in the foundation migration `0001_phase1`, before any later migration adds `VECTOR` columns. Migration `0008_schema_freeze` no longer owns extension creation. The PostgreSQL migration test asserts the extension exists and verifies vector columns after a clean upgrade.
- ESLint config sets `argsIgnorePattern: '^_'` for TypeScript unused-variable checks. The accessibility test no longer uses `@ts-ignore`; unused `useLocation`, icon, React/type and Node module imports called out in the cleanup review were removed.
- Direct OCR in the workflow endpoint uses `asyncio.to_thread`. The content analysis and legacy image-analysis endpoints also dispatch the synchronous `analyze_image` pipeline through `asyncio.to_thread`; that pipeline contains Tesseract and OpenCV operations.
- The 52-case evaluation dataset, `EVALUATION.md`, and `PHASE4_RUNBOOK.md` are retained. Historical 40-case measurements remain labelled as historical; no metrics are inferred for the expanded 52-case set.
- The Docker image defaults `PORT=8000` and binds Uvicorn to `${PORT:-8000}`. `render.yaml` explicitly configures `PORT=8000`, S3 environment keys, Neon connection string input, production CORS and the in-process worker.

Local verification in this environment: Python compilation passed; Neon URL normalization checks passed; a clean SQLite Alembic upgrade reached `0008_schema_freeze` and created 24 tables; Render and Compose YAML parsed successfully. A live PostgreSQL migration, npm installation/lint/test/build, Playwright GlowSerum flow, Ollama evaluation and hosted deployment were not run in this environment. The package registry was unreachable and required Python/Node dependencies were not available locally.
