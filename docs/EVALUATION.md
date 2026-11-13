# BrandCourt evaluation

> **Measurement conditions (2026-11-12 session):** All results below were produced in `MODEL_MODE=deterministic`. The 52-post GlowSerum dataset was used to tune rules; it is therefore a regression corpus, **not a held-out accuracy estimate**. Ollama variants (`retrieval_and_nli`, `full_pipeline`) were not run in this session as the Ollama service was unavailable; their metrics are **not measured**, not zero, and not claimed to pass. No fresh holdout exists. Historical source-citation result is **12/19 = 63.16%**, leaving **7/19 = 36.84%** without the required cited source.

## Deterministic regression result: 52 cases, rules tuned on this set, not held-out accuracy

The following measurements came from
`pytest -s tests/test_analysis_golden.py::test_all_glowserum_seed_posts_run_through_durable_worker -q`
on the 52-row fictional GlowSerum sample. The test asserted exact equality between expected
and observed finding labels for every row. It includes 14 clean posts and covers English,
Hindi, Marathi, Hinglish, missing alt text, palette, contrast, logo, and an uncertain-OCR
fixture tag.

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

## Image evaluation status

The corpus includes five visual expected-finding labels, but the repository sample does not
contain five corresponding source creative images. A label or precomputed image-analysis result
is not a real image-analysis run. Therefore the five-image requirement remains unmeasured.
Provide the five original image files, upload each through the API, verify OCR and image-analysis
execution in the persisted revision/job records, and report per-image TP/FP/FN plus failures.
Do not use landing-page stock artwork as a substitute for the intended GlowSerum test cases.

## Holdout integrity

The existing 52-row set has already informed rule development and regression work. A split made
after that exposure would not be a valid untouched holdout. Freeze the rule set and collect a new,
independently adjudicated batch for the never-used holdout. The current 52 remain a regression
corpus only.

## Reproducible evaluation variants

The worker accepts an admin-only `evaluation_variant` query parameter. The selected value is
persisted with the queued job, so a worker restart does not lose the setting:

- `code_rules_only`: deterministic policy rules only; skips claim retrieval, image/OCR and tone.
- `retrieval_and_nli`: deterministic rules plus fact retrieval, Ollama NLI and quote-validated
  adjudication. It skips model claim extraction and image/tone analysis.
- `full_pipeline`: the complete worker path, including Ollama extraction/embeddings/NLI,
  image/OCR checks, and tone analysis.

Run each variant separately against the same seeded 52 posts from `backend/`:

```powershell
python scripts/evaluate_api.py --variant code_rules_only --token <admin-token>
python scripts/evaluate_api.py --variant retrieval_and_nli --token <admin-token>
python scripts/evaluate_api.py --variant full_pipeline --token <admin-token>
python scripts/score_eval.py --code-only ..\data\sample\glowserum_code_rules_only_predictions.jsonl --retrieval-nli ..\data\sample\glowserum_retrieval_and_nli_predictions.jsonl --full ..\data\sample\glowserum_full_pipeline_predictions.jsonl --evaluation-doc ..\docs\EVALUATION.md
```

The runner records the same source-file SHA-256 on all case rows, validates that the worker
completed the requested variant, and captures all 52 expected case IDs. It measures worker
`started_at` to `finished_at`; failed jobs are recorded explicitly and score as empty predictions
(thus contributing false negatives), never as successful passes. Model-dependent runs first
verify that the configured Ollama model is live; a failed check marks that variant blocked and
writes no prediction file. Configure `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, and `OLLAMA_EMBEDDING_MODEL` consistently for
both the API/worker and the evaluation runner. Both configured Ollama model names must exist at
the configured endpoint before either model-dependent evaluation is started.

## Historical, measured on the original 40 posts only

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


## Expanded multilingual and uncertainty set (52 cases)

The current `data/sample/glowserum_40_posts.jsonl` retains its historical filename for
backward compatibility but now contains 52 labelled cases. Twelve additional synthetic
cases cover Hindi, Marathi, Hinglish, paid disclosure, AI declaration, missing alt text,
contrast uncertainty, OCR uncertainty, and clean controls. The new rows are not included
in the historical 40-case measurements above. Re-run all three variants against this
52-row dataset before publishing new comparative metrics. The scorer requires exact
coverage and a shared SHA-256, so old 40-row prediction files cannot be mixed with this set.

## Provider choice and forced-quote safeguard

The selected evaluation provider is **Ollama** for local model inference. The configured
default model path uses `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, and
`OLLAMA_EMBEDDING_MODEL`; the API and evaluator must point to the same Ollama instance.
The deterministic rules remain the fallback. Model adjudication is accepted only when
its quoted evidence is an exact substring of the stored fact after restoring masked
tokens, and the fact identifier matches the retrieved fact. Invalid or unsupported
quotes are discarded and routed to human review. This safeguard is covered by
`tests/test_checking_engine.py`; no hosted provider is selected by default.

## Round 3 proof-case test plan

The following proof cases are specified as repeatable acceptance scenarios, not claimed
as live measured outcomes:

1. **Guideline Health conflict:** add two active rules for the same channel whose
   requirements conflict (for example, "never use exclamation marks" and "use an
   exclamation mark in every headline"). Run Guideline Health; verify the pair is
   surfaced with both rule IDs and suggested wording. A human owner decides whether
   to edit or retire either rule.
2. **Precedent removes a repeated false flag:** create a false-positive finding, dispute
   it with a reason, save a scoped precedent for the same rule/channel, obtain manager
   approval, then repeat the content. Verify the precedent is shown as advisory evidence
   and the finding is no longer treated as a fresh unsupported error. The precedent must
   not silently change the underlying rule.
3. **Rejected fix:** propose a fix that removes the risky claim but also removes the
   required product identity or key claim intent. Run the full verification engine;
   assert the new Critical finding blocks acceptance and the Intent Preserved count
   decreases. Keep the original revision unchanged.

## Current execution status

The original deterministic 40-case run and the 40-case code-only ablation above are
historical recorded results. The retrieval+NLI and full-pipeline runs remain blocked
until the configured Ollama service and both configured models are available. The
expanded 52-case set has not yet been run through the API. Do not infer or extrapolate
precision/recall for the new cases from historical results. Generate fresh outputs for
all three variants and use `score_eval.py` to replace the results only after all three
complete against the identical 52-case dataset hash.

## GlowSerum fix acceptance/rejection proof (manual API/UI run still required)

Use a seeded fictional GlowSerum content item whose current revision is safe or has no existing
Critical finding for the same claim. Open Fix Verification, enter that content item's ID, and
use **Load Critical-rejection example** to load:

```text
GlowSerum cures eczema and guarantees results. Shop now.
```

Run Verify Candidate Copy. The expected acceptance condition is `safe_to_suggest: false` when
the candidate introduces a new Critical finding; the result should include that finding in
`new_blocking_findings`, and the UI should show the red rejection panel. This is an acceptance
scenario, not a recorded result from this environment. Save the actual API response and a
screenshot before marking the rejection proof complete.

For an accepted example, use a GlowSerum finding for an unsupported superlative such as
“the best serum”, request a minimal fix, and confirm the candidate retains the product noun and
CTA while no new Critical finding is introduced. Capture `changed_claims`,
`call_to_action_preserved`, `embedding_similarity`, `intent_preserved`,
`new_blocking_findings`, and `safe_to_suggest` from the real API response. Do not infer an
accepted result from the phrase-level unit smoke test alone.
