# BrandCourt — Round 3 implementation and evidence report

**Report date:** 9 November 2026  
**Scope:** Phases 5–8  
**Status:** Partial implementation; external and environment-dependent evidence is explicitly outstanding.

## Phase 5 — Better fixes

Implemented deterministic safe-language substitutions for cure/guarantee and superiority wording in `backend/app/services/fixes.py`. The superlative set includes phrases such as “the best”, “best-in-class”, “number one”, “#1 rated”, “ultimate”, “miracle”, “most effective”, “unmatched”, “unbeatable”, “revolutionary” and “top-rated”. These are conservative copy suggestions, not evidence that the replacement is legally compliant in every context.

The existing verification endpoint runs a temporary candidate revision through the review engine, rolls the candidate back, and rejects it if a new Critical finding is raised or intent checks fail. The findings card now displays the rejection reason and new Critical finding details, claims changed, CTA retention and similarity. The Fix Verification screen also displays the changed-claim list and similarity.

Regression tests were added for six GlowSerum phrase patterns. A direct Python smoke run of those six phrase cases passed. The pytest suite could not be executed because `aiosqlite` is absent and package installation is blocked by unavailable network access. The Fix Verification screen includes a **Load Critical-rejection example** button; a real API-level GlowSerum accepted-fix/rejected-fix proof has **not** been run here. Use the steps in `docs/EVALUATION.md` and capture actual response JSON before claiming that proof complete.

## Phase 6 — Honest evaluation

The project contains a 52-post fictional GlowSerum JSONL corpus and an evaluation runner/scorer for `code_rules_only`, `retrieval_and_nli`, and `full_pipeline`. Historical documentation records a deterministic 52-case golden regression but also records rule-tuning leakage and a separate 40-case ablation. These historical figures are not a blind holdout estimate and must not be described as independent generalisation performance.

The current execution environment has no reachable Ollama service/model and cannot install missing Python dependencies. Therefore all three variants have **not** been rerun on the current 52-post corpus. No new precision, recall, F1, missed-claim count or model latency is asserted. Five real creative-image fixtures are also not present in the sample corpus; image labels in JSONL are expected outcomes, not real image files. The five image cases must be supplied and processed through the real upload/OCR/image pipeline before reporting image-analysis results.

A defensible holdout requires a fresh, never-before-used set. The existing 52 rows have historical rule-development exposure; relabelling a subset now would not make it a clean holdout. Freeze the rules and evaluate on newly collected, adjudicated posts instead.

## Phase 7 — Remaining product items

- The admin local-model toggle is present in `ModelSettingsPage` and uses the model-settings API. It still requires a live admin-session integration test.
- Existing insights support channel, creator and week groupings, and calculate approval duration from audit events. The current schema has no team entity/team membership dimension, so a genuine team breakdown is not available yet. The dashboard also uses a clearly marked seeded fallback when no approval history exists; it is not a measured time-to-approve value.
- Fact expiry is implemented as a Docker Compose scheduled service; deployment execution was not possible in this environment.
- The new-review form now warns that Devanagari / mixed-language content has limited automated coverage and requires a fluent human reviewer.
- `axe-core` is already listed as a frontend dependency, but a complete axe-core audit across all routes and states has not been run. No accessibility-pass claim is made.
- The review workflow has comment creation but not comment-resolution API/UI. Member creation is an admin-only create-user operation, not an email invitation flow; member removal and workspace deletion are not exposed. Corresponding invitation/removal/deletion controls are not presented as working features in the member/workspace screens. A future pass should implement these workflows end-to-end or keep them hidden.
- Text review under 15 seconds and image review under 30 seconds are acceptance targets, not verified measurements. No production-like latency run was available.

## Phase 8 — Evidence and submission

- The competitor evidence pack is added at `docs/COMPETITOR_EVIDENCE.md`; it compares public vendor-described capabilities and is not a hands-on benchmark.
- The user-session protocol and manual-vs-product timing worksheet are in `docs/DEMO_AND_USER_SESSIONS.md`. No participant sessions or timing study were performed in this environment; results must be collected from 5–8 consenting participants and 10 timed posts.
- No demo recording is included. The 3-minute walkthrough and additional 1-minute precedent demonstration must be recorded from a running deployment with fictional data.
- This report and the disclosure updates are included. Known limitations and a roadmap are documented rather than presenting unperformed work as complete.

## Validation performed for this ZIP

- `python -m compileall -q backend/app backend/tests`: passed.
- Six direct GlowSerum safe-replacement smoke cases: passed.
- Targeted pytest run: blocked at test collection by `ModuleNotFoundError: aiosqlite`.
- Attempt to install `aiosqlite`: blocked because the environment could not reach the package index.
- Frontend build, frontend tests, axe audit, API integration, Ollama inference, real image analysis, user sessions, timing study and demo recording: not run.

This is a partial delivery, not a claim that every requested acceptance criterion has passed. See `docs/EVALUATION.md` for the repeatable evaluation commands and exact evidence gaps.
