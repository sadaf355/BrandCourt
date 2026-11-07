# BrandCourt evaluation

## Historical deterministic baseline (not a variant result)

The following measurements came from
`pytest -s tests/test_analysis_golden.py::test_all_glowserum_seed_posts_run_through_durable_worker -q`
on the 40-row fictional GlowSerum sample. The test asserted exact equality between expected
and observed finding labels for every row. It includes 10 clean posts and covers English,
Hindi, Marathi, Hinglish, missing alt text, palette, contrast, logo, and an uncertain-OCR
fixture tag.

| Metric | Measured result |
|---|---:|
| Cases completed | 40 / 40 |
| Exact label match | 40 / 40 |
| Exact-match accuracy | 100% |
| Micro precision | 100% |
| Micro recall | 100% |
| Micro F1 | 100% |
| False flags | 0 |
| False negatives | 0 |
| Failed cases | 0 |
| Error findings | 20 |
| Error findings with a cited fact, approved fact, or active-rule source reference | 10 / 20 (50%) |
| Needs-human-review findings | 18 |
| Median worker processing time | 102.39 ms |
| Slowest worker processing time | 172.58 ms |

| Finding type | TP | FP | FN | Precision | Recall |
|---|---:|---:|---:|---:|---:|
| Banned term | 5 | 0 | 0 | 100% | 100% |
| Expired fact | 5 | 0 | 0 | 100% | 100% |
| Missing disclosure | 5 | 0 | 0 | 100% | 100% |
| Restricted health claim | 1 | 0 | 0 | 100% | 100% |
| Unsupported superlative | 5 | 0 | 0 | 100% | 100% |
| Visual | 5 | 0 | 0 | 100% | 100% |
| Wrong number | 5 | 0 | 0 | 100% | 100% |

No cases were misclassified in this measured run. The sample is synthetic and narrow; these
scores are not estimates of production accuracy.

### Measurement limitations

- The test prepared the five image-analysis results before enqueueing their jobs. Consequently,
  the reported timings measure worker processing of the prepared results, not image analysis,
  upload, or end-to-end API latency. The run does not verify that OCR itself ran inside those
  five jobs.
- The test used the deterministic workspace mode. It did not run an Ollama model or NLI.
- The source-share measure checks that an error finding cited a fact/approved-fact/active-rule
  evidence entry with a non-empty `source_ref`; it does not independently verify source authority.
- The uncertain-OCR row is labelled in the dataset, but this run does not establish a real
  low-confidence OCR outcome for that case.

## Reproducible evaluation variants

The worker accepts an admin-only `evaluation_variant` query parameter. The selected value is
persisted with the queued job, so a worker restart does not lose the setting:

- `code_rules_only`: deterministic policy rules only; skips claim retrieval, image/OCR and tone.
- `retrieval_and_nli`: deterministic rules plus fact retrieval, Ollama NLI and quote-validated
  adjudication. It skips model claim extraction and image/tone analysis.
- `full_pipeline`: the complete worker path, including Ollama extraction/embeddings/NLI,
  image/OCR checks, and tone analysis.

Run each variant separately against the same seeded 40 posts from `backend/`:

```powershell
python scripts/evaluate_api.py --variant code_rules_only --token <admin-token>
python scripts/evaluate_api.py --variant retrieval_and_nli --token <admin-token>
python scripts/evaluate_api.py --variant full_pipeline --token <admin-token>
python scripts/score_eval.py --code-only ..\data\sample\glowserum_code_rules_only_predictions.jsonl --retrieval-nli ..\data\sample\glowserum_retrieval_and_nli_predictions.jsonl --full ..\data\sample\glowserum_full_pipeline_predictions.jsonl --evaluation-doc ..\docs\EVALUATION.md
```

The runner records the same source-file SHA-256 on all case rows, validates that the worker
completed the requested variant, and captures all 40 expected case IDs. It measures worker
`started_at` to `finished_at`; failed jobs are recorded explicitly and score as empty predictions
(thus contributing false negatives), never as successful passes. Model-dependent runs first
verify that the configured Ollama model is live; a failed check marks that variant blocked and
writes no prediction file. Configure `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, and `OLLAMA_EMBEDDING_MODEL` consistently for
both the API/worker and the evaluation runner. Both configured Ollama model names must exist at
the configured endpoint before either model-dependent evaluation is started.

### Code-only: measured in this sprint

The full backend run executed 40 additional `code_rules_only` jobs with the same worker and
seeded records. Each result confirmed the persisted variant. Dataset SHA-256:
`9801e125d9912525d4562c2ad2901dc0b42ddb12712506c7414b50c6fbdbb6e2`.

| Cases | Failures | Exact-match accuracy | Precision | Recall | F1 | False positives | False negatives | Needs human review | Median worker ms | Slowest worker ms |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 40/40 | 0 | 37.5% | 100% | 16.13% | 27.78% | 0 | 26 | 11 | 96.97 | 136.85 |

| Finding type | TP | FP | FN | Precision | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| Banned term | 0 | 0 | 5 | 0% | 0% | 0% |
| Expired fact | 0 | 0 | 5 | 0% | 0% | 0% |
| Missing disclosure | 5 | 0 | 0 | 100% | 100% | 100% |
| Restricted health claim | 0 | 0 | 1 | 0% | 0% | 0% |
| Unsupported superlative | 0 | 0 | 5 | 0% | 0% | 0% |
| Visual | 0 | 0 | 5 | 0% | 0% | 0% |
| Wrong number | 0 | 0 | 5 | 0% | 0% | 0% |

Code-only deliberately excludes claim retrieval and visual analysis. Its 26 false negatives are
the expected cost of this ablation, not hidden failures; it found no false positives.

### Retrieval+NLI and full pipeline: blocked

Both variants ran the evaluator's Ollama model preflight and were blocked before any prediction
file was written: `All connection attempts failed` for the configured local endpoint. Therefore
there are no case runs, latency figures, precision/recall/F1, false-positive/negative counts, or
job-failure counts to report for either variant. The historical deterministic baseline above is
not substituted for these missing measurements.

Local-model code paths have automated mocked/service-failure coverage, but no real Ollama
inference was performed and these tests do not establish OS/container-level network isolation.
The tests cover admin model-mode changes, embedding-service fallback through the real review
worker, invalid NLI JSON, timeout handling, schema-invalid model responses/retry, and an
unavailable Ollama endpoint. Invalid-response and timeout cases use mocked HTTP clients; the
unavailable-endpoint case and evaluator preflight attempt the configured local endpoint but do
not perform inference.

## Fact-expiry scheduler

The repository's deployment setup is Docker Compose. The `fact-expiry` service runs
`python -m scripts.expire_facts --watch --interval-hours ${FACT_EXPIRY_INTERVAL_HOURS:-24}`
in the backend image, waits for both database and API health (the API applies migrations), and
restarts unless stopped. It runs one idempotent pass on startup, then repeats at the configured
interval. Set `FACT_EXPIRY_INTERVAL_HOURS=24` in the Compose environment for the default daily
schedule, then run `docker compose up -d fact-expiry` and verify `docker compose ps`.

For a one-shot host cron invocation using the same Compose deployment, add a daily entry such as:

```cron
0 2 * * * cd /path/to/BrandCourt && docker compose run --rm --entrypoint python fact-expiry -m scripts.expire_facts >> /var/log/brandcourt-fact-expiry.log 2>&1
```

`--notify-within-days` controls the expiring-soon window; `--interval-hours` or
`FACT_EXPIRY_INTERVAL_HOURS` controls watch-mode cadence. Facts at or before their expiration
time become `expired` and each active manager/admin receives one `fact_expired` notice. Facts
inside the notification window but not expired receive one `fact_expiring_soon` notice.
Repeated passes do not duplicate either notice. Docker was unavailable during this sprint, so
the Compose service configuration was parsed but container startup and cron execution were not
observed.
