# BrandCourt — Round 3 implementation and evidence report

**Report date:** 12 November 2026  
**Scope:** Phases 5–8  
**Status:** Validated in `MODEL_MODE=deterministic`. Core features, API integration, and test suites operational. External model and environment-dependent evidence (Ollama inference, real image fixtures, user timing sessions) are explicitly recorded as outstanding or not measured.

---

## 1. Round 3 Feature Implementation & Real Evidence

All evidence below was gathered under `MODEL_MODE=deterministic`. Ollama-based NLI and generation were **BLOCKED** because no local Ollama service was reachable (`http://localhost:11434` timed out).

### 1.1 Guideline Health: Planted Issues Screening & Lifecycle
- **Model mode:** `deterministic` (screening heuristics)
- **Active rules screened:** 18 active rules
- **Planted issues evaluated:** 8 of 8 planted issues successfully identified (`issue_count=151` total candidate issues, including 143 non-planted candidate pairs and vague rule warnings due to missing attached examples):

| Planted issue | Type | Found? | Status shown | Notes |
|---|---|---|---|---|
| DEMO-CONFLICT-A/B | conflict | Yes (rank 2, sim 0.8263) | `candidate_only` | Overlapping scope candidate (Ollama NLI/ConflictRubric blocked) |
| DEMO-CONFLICT-C/D | conflict | Yes (sim 0.7560) | `candidate_only` | Overlapping scope candidate |
| DEMO-CONFLICT-E/F | conflict | Yes (sim 0.6382) | `candidate_only` | Overlapping scope candidate |
| DEMO-CONFLICT-G/H | conflict | Yes (rank 1, sim 0.8816) | `candidate_only` | Overlapping scope candidate |
| DEMO-VAGUE-1 | vague | Yes | `not set` (deterministic) | Subjective wording: 'appropriate'; no testable condition or example |
| DEMO-VAGUE-2 | vague | Yes | `not set` (deterministic) | Subjective wording: 'good quality'; no testable condition or example |
| DEMO-VAGUE-3 | vague | Yes | `not set` (deterministic) | Subjective wording: 'professional'; no testable condition or example |
| DEMO-VAGUE-4 | vague | Yes | `not set` (deterministic) | Subjective wording: 'suitable'; no testable condition or example |

- **Draft-Version Lifecycle Evidence (`DEMO-VAGUE-1`):**
  - Calling `POST /api/guideline-health/decisions` (`action=accept`, `issue_type=vague_rule`) returned HTTP `201` with `rule_changed: true`, `new_rule_id: "943732e2-f83c-45f6-87c4-b716b35c4995"`, `new_rule_version: 2`, `new_rule_status: "draft"`, while v1 (`a93f9cb6-315c-4f9b-a3f4-7f1c6d69114b`) remained `active`.
  - Calling `POST /api/rules/{new_id}/confirm` returned HTTP `200`, activating v2 and archiving/retiring v1.

### 1.2 Precedent Ledger: Repeated Overrides & Critical Non-Downgrade
- **Rule and channel tested:** `EVID-TERM-MAJOR` (`severity="major"`, channel `instagram`).
- **Initial finding:** `b81a0f84-ea9b-42dc-aa7c-df078f1952f4`, `"Discover our winter glow secret with GlowSerum."`
- **Reviewer override:** Overridden with reason `"Seasonal Instagram campaign approved this slogan for Q4."` (`POST /api/findings/{id}/decision` → `201`, `state="overridden"`).
- **Precedent creation & approval:** Precedent `b168545b-7018-4ab1-adb5-8c8d36a624f8` transitioned from `pending` to `approved` by manager `a0490904-c1da-4f3c-8a97-573f3e8f1d5f`.
- **Precedent match on re-review:** When identical copy was re-analyzed, precedent suggestion was surfaced on finding `74538398-7b33-4052-b045-540b15613a92` with `similarity: 1.0`, `suggested_severity: "advisory"`, `requires_reviewer_confirmation: true`.
- **Critical finding protection (Anti-Downgrade Invariant):**
  - For Critical finding `40758ab5-9580-437c-9c05-1ae9ef0c0a83` (`"India's #1 serum for glowing skin."`), `GET /precedent-suggestions` returned `[]`.
  - Attempting to force confirm a precedent downgrade via `POST /api/findings/{id}/precedent-suggestions/{precedent_id}/confirm` returned HTTP `409 Conflict`: `{"detail": "Critical findings cannot be downgraded by precedent."}`.

### 1.3 Fix Verification & Safe Candidate Replacement
Tested on GlowSerum Instagram Reel copy (`"Experience India's #1 radiant skin formula! Our clinically proven GlowSerum cures acne and lightens dark spots in just 28 days with 100% natural organic saffron extracts. Dermatologist tested and guaranteed results. Shop now."`):

| Case | Proposed fix | Accepted? | Claims changed | CTA kept | Similarity | New Critical? |
|---|---|---|---|---|---|---|
| India's #1 | `"Our clinically proven GlowSerum cures acne and lightens dark spots in just 28 days with 100% natural organic saffron extracts. Dermatologist tested and guaranteed results. Shop now."` | Accepted (`true`) | `["Experience India's #1 radiant skin formula!"]` | Yes (`true`) | `0.9101` | None (`[]`) |
| cures acne | `"Experience India's #1 radiant skin formula! Our clinically proven GlowSerum may help improve the appearance of blemish-prone skin and lightens dark spots in just 28 days with 100% natural organic saffron extracts. Dermatologist tested and guaranteed results. Shop now."` | Accepted (`true`) | `["Our clinically proven GlowSerum cures acne and lightens dark spots in just 28 days with 100% natural organic saffron extracts."]` | Yes (`true`) | `0.8744` | None (`[]`) |
| Bad fix (adds a Critical claim) | `"GlowSerum cures eczema and guarantees results. Shop now."` | Rejected (`safe_to_suggest: false`) | `[]` | Yes (`true`) | `0.1879` | Yes (`"GlowSerum cures eczema and guarantees results."`, `IN-5`, `critical`) |

---

## 2. Evaluation & Benchmark Disclosures

### Deterministic Golden Regression Benchmark (52 Posts)
- **Model mode:** `MODEL_MODE=deterministic`
- **Result:** 52 / 52 cases completed with 100% exact label match.
- **Important Disclosure:** The rules were iteratively tuned against this exact 52-post GlowSerum sample dataset during development. Therefore, this result represents a **regression test**, **not a held-out accuracy estimate**.
- **Ollama Variants:** `retrieval_and_nli` and `full_pipeline` require a live Ollama daemon and model weights. Because Ollama was not running in this environment, their metrics were **not measured** (not zero, not passed).
- **Source Citation:** 12 of 19 error findings (63.16%) had an explicit citation reference; 7 of 19 (36.84%) lacked a cited source.

---

## 3. Product & Governance Scope

- **India Rules Pack:** Starter heuristic guidance for internal marketing review. It is **not legal advice** and does not substitute for review by a qualified attorney under ASCI, ASI, or the Drugs & Magic Remedies Act.
- **Workflow Boundaries:** The current product implements comment creation, but comment resolution, email invitation workflows, member deletion, and workspace deletion are not yet exposed as full end-to-end features.
- **Language Coverage:** Hindi, Marathi, and Hinglish content have limited automated coverage and require review by a fluent human reviewer.
- **Accessibility:** `axe-core` is present as a dependency; a complete formal accessibility audit was not conducted.

---

## 4. Model-Based Checks & Image Analysis Status (12 November 2026)

### 4.1 Ollama Model-Based Checks: BLOCKED
- **Condition:** Tested local execution for `MODEL_MODE=ollama` requiring `llama3.2:3b` and `nomic-embed-text`.
- **Status:** **BLOCKED**.
- **Reason:**
  1. Ollama executable is not installed on the Windows system (`where.exe ollama` exited with code 1; default user appdata path `C:\Users\Dell\AppData\Local\Programs\Ollama\ollama.exe` returned `False`).
  2. Windows package manager `winget` failed with `ApplicationFailedException: The file cannot be accessed by the system`.
  3. Docker daemon is stopped/unreachable (`failed to connect to docker API at npipe:////./pipe/docker_engine`).
  4. Per instructions ("If setup takes more than one hour, STOP and report BLOCKED"), Ollama setup cannot be completed quickly without external administrative installation. Consequently, model-based checks for `GET /api/guideline-health`, `suggest-fix`, and `verify-fix` in `MODEL_MODE=ollama` were stopped and marked **BLOCKED**.

### 4.2 Landing-Page Stock Image Analysis — Safe-Fallback Demonstration Only

> **Important:** The three images analysed here (`skincare.webp`, `desk.webp`, `shield-poster.webp`) are **landing-page stock images** shipped with the repository at `frontend/public/landing/`. They are **not** GlowSerum brand creatives or campaign assets, and the palette `['#FF7A59', '#1A202C']` supplied to the call is an **arbitrary test palette** that does not correspond to any configured brand. These results demonstrate that the safe-fallback degradation paths work correctly; they say nothing about OCR accuracy or brand-colour accuracy on real brand content.

Command run (in `backend/` on 12 November 2026):
```python
from app.services.image_intelligence import analyze_image
from pathlib import Path
import json
for name in ['skincare.webp', 'desk.webp', 'shield-poster.webp']:
    res = analyze_image(Path(f'../frontend/public/landing/{name}'), palette=['#FF7A59', '#1A202C'])
    # (summarised below)
```

| Image | OCR result | Dominant colour ΔE to test palette (CIEDE2000) | Contrast | Logo | Overall |
|---|---|---|---|---|---|
| `skincare.webp` | `unavailable` — Tesseract executable not installed; text empty; `ocr_unavailable` finding raised | `#F0F1F1` ΔE 33.35, `#3A3463` ΔE 15.15, `#BBBBBB` ΔE 27.42, `#787795` ΔE 31.60 — all exceed threshold 5.0 → `review` | `needs_human_review` (approximate heuristic only) | `needs_human_review` (no logo reference uploaded) | `needs_human_review` |
| `desk.webp` | `unavailable` — same reason | `#1B1C17` ΔE 11.45, `#E9E8E5` ΔE 31.93, `#8E5B2B` ΔE 27.14, `#B0A89F` ΔE 24.66 — all → `review` | `needs_human_review` | `needs_human_review` | `needs_human_review` |
| `shield-poster.webp` | `unavailable` — same reason | `#050D10` ΔE 8.47, `#25AB9A` ΔE 50.16, `#396871` ΔE 26.05, `#C9EBE8` ΔE 42.71 — all → `review` | `needs_human_review` | `needs_human_review` | `needs_human_review` |

**What this confirms:** Every inconclusive check produces `needs_human_review` with specific finding codes (`ocr_unavailable`, `brand_color_mismatch`, `logo_detection_unavailable`), and no technical failure produces a false approval. **What this does not confirm:** OCR accuracy, brand-colour accuracy on real creatives, or passing any image finding against GlowSerum's actual palette.

---

## 5. Verification Performed in This Session (12 November 2026)

All commands were directly executed in the workspace with recorded outputs:

1. **Database Migrations:**
   - Command: `python -m alembic upgrade head` (from `backend/`)
   - Result: **PASSED** — Migrations `0001` through `0008` applied cleanly to SQLite.
2. **Demo Seeding:**
   - Command: `python -m app.seed_glowserum --email demo-admin@glowserum.com --demo --demo-password DemoSecret123!`
   - Result: **PASSED** — 5 demo drafts seeded with status `completed` and 0 failures.
3. **Frontend Dependencies & Build:**
   - Commands: `npm install` and `npm run build` (from `frontend/`)
   - Result: **PASSED** — 3,118 modules transformed, clean production build in `dist/`.
4. **Frontend Unit & Contract Tests:**
   - Command: `npm test -- --run` (Vitest 5.1.0)
   - Result: **PASSED** — 5 test files, **19 passed** (0 failed).
5. **Backend Automated Tests:**
   - Command: `pytest -rs -q` (from `backend/`)
   - Result: **PASSED** — **181 passed, 6 skipped** in 317.36s.
   - Skip reasons (exact, from `-rs` output):
     - 5 skipped — `tests/test_image_intelligence.py:38`: `Real OCR integration requires an installed Tesseract executable.`
     - 1 skipped — `tests/test_migrations_clean.py:282`: `TEST_POSTGRES_URL is not configured`
