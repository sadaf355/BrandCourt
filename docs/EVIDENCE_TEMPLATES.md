# Evidence templates (fill with real results only)

## 1. Guideline Health: planted issues found vs missed
Model mode: `deterministic` (`MODEL_MODE=ollama` **BLOCKED** — Ollama CLI/service is not installed and `http://localhost:11434` timed out; Docker Desktop daemon is stopped)  Model: `None (deterministic screening only)`  Date: `2026-11-10`

| Planted issue | Type | Found? | Status shown | Notes |
|---|---|---|---|---|
| DEMO-CONFLICT-A/B | conflict | Yes (rank 2, sim 0.8263) | `candidate_only` | `Rules have similar wording or overlapping channel scope. This is a candidate, not proof of contradiction.` (Ollama NLI/ConflictRubric BLOCKED) |
| DEMO-CONFLICT-C/D | conflict | Yes (sim 0.756) | `candidate_only` | `Rules have similar wording or overlapping channel scope. This is a candidate, not proof of contradiction.` (Ollama NLI/ConflictRubric BLOCKED) |
| DEMO-CONFLICT-E/F | conflict | Yes (sim 0.6382) | `candidate_only` | `Rules have similar wording or overlapping channel scope. This is a candidate, not proof of contradiction.` (Ollama NLI/ConflictRubric BLOCKED) |
| DEMO-CONFLICT-G/H | conflict | Yes (rank 1, sim 0.8816) | `candidate_only` | `Rules have similar wording or overlapping channel scope. This is a candidate, not proof of contradiction.` (Ollama NLI/ConflictRubric BLOCKED) |
| DEMO-VAGUE-1 | vague | Yes | `not set` (deterministic) | `subjective wording: appropriate; no testable condition was found; no positive or negative example is attached` (Ollama VagueRuleRubric BLOCKED) |
| DEMO-VAGUE-2 | vague | Yes | `not set` (deterministic) | `subjective wording: good quality; no testable condition was found; no positive or negative example is attached` (Ollama VagueRuleRubric BLOCKED) |
| DEMO-VAGUE-3 | vague | Yes | `not set` (deterministic) | `subjective wording: professional; no testable condition was found; no positive or negative example is attached` (Ollama VagueRuleRubric BLOCKED) |
| DEMO-VAGUE-4 | vague | Yes | `not set` (deterministic) | `subjective wording: suitable; no testable condition was found; no positive or negative example is attached` (Ollama VagueRuleRubric BLOCKED) |

Found **8** of 8 planted items (`issue_count=151` across `18` active rules). False alarms (issues that are not planted): **143** total (`129` non-planted `possible_conflict` pairs down to similarity `-0.2084`, plus `14` non-planted `vague_rule` issues on `DEMO-CONFLICT-A..H` and `IN-1..IN-6` due to missing examples).

- Draft-version lifecycle (`DEMO-VAGUE-1`): `POST /api/guideline-health/decisions` (`action=accept`, `issue_type=vague_rule`) returned `201` with `rule_changed: true`, `new_rule_id: "943732e2-f83c-45f6-87c4-b716b35c4995"`, `new_rule_version: 2`, `new_rule_status: "draft"`, while v1 (`a93f9cb6-315c-4f9b-a3f4-7f1c6d69114b`) remained `active`. Note: `DEMO-VAGUE-1` in the seeded demo workspace had 0 attached `RuleExample` rows (`has_example: false`); example-copying on a rule with attached examples is covered by `backend/tests/test_intelligence_api.py::test_vague_rule_wording_creates_a_draft_version_and_old_rule_stays_active_until_confirmed`. `POST /api/rules/{new_id}/confirm` returned `200`, activating v2 and retiring v1 (`docs/evidence/1_guideline_health.json`, `1_guideline_decision_draft.json`, `1_rules_after_decision.json`, `1_rule_confirm.json`, `1_rules_after_confirm.json`).

## 2. Precedent Ledger: repeated false flag
- Rule and channel: `EVID-TERM-MAJOR` (`severity="major"`, channel `instagram`). Note: overriding India-pack `IN-4` (`Demo: missing disclosure`) as `reviewer` returned `403` because India-pack `IN-*` overrides require `manager`/`admin`, so a workspace `major` rule was used for the reviewer-override proof.
- Finding before any precedent (id, text): `b81a0f84-ea9b-42dc-aa7c-df078f1952f4`, `"Discover our winter glow secret with GlowSerum."`
- Reviewer override reason: `"Seasonal Instagram campaign approved this slogan for Q4."` (`POST /api/findings/{id}/decision` → `201`, `state="overridden"`)
- Precedent created / approved by / date: `b168545b-7018-4ab1-adb5-8c8d36a624f8` (`status="pending"` → `"approved"`) / approved by `a0490904-c1da-4f3c-8a97-573f3e8f1d5f` (`manager`) / `2026-11-10T10:22:28.998267+00:00`
- Same content re-reviewed: precedent shown on the finding? **Yes** (similarity `1.0`; `approved_precedent` attached in `finding_after_rerun.evidence` with `match_score: 1.0`, and `GET /api/findings/74538398-7b33-4052-b045-540b15613a92/precedent-suggestions` returned `similarity: 1.0`, `suggested_severity: "advisory"`, `requires_reviewer_confirmation: true`)
- Critical finding stayed un-downgraded? **Yes** — for Critical finding `40758ab5-9580-437c-9c05-1ae9ef0c0a83` (`"India's #1 serum for glowing skin."`), `GET /precedent-suggestions` returned `[]` and `POST /api/findings/40758ab5-9580-437c-9c05-1ae9ef0c0a83/precedent-suggestions/8c312149-477e-40f3-8a73-a27372f76f32/confirm` returned HTTP `409` (`{"detail": "Critical findings cannot be downgraded by precedent."}`)
- Screenshot or JSON saved at: `docs/evidence/2_precedent_noncritical_decision.json`, `docs/evidence/2_precedent_created.json`, `docs/evidence/2_precedent_approved.json`, `docs/evidence/2_precedent_rerun_suggestions.json`, `docs/evidence/2_precedent_critical_rejected.json`

## 3. Fix verification
*(Collected in `MODEL_MODE=deterministic` on the GlowSerum Launch Instagram Reel post `"Experience India's #1 radiant skin formula! Our clinically proven GlowSerum cures acne and lightens dark spots in just 28 days with 100% natural organic saffron extracts. Dermatologist tested and guaranteed results. Shop now."` and `Clean sample 1`; `MODEL_MODE=ollama` model fix generation is **BLOCKED**.)*

| Case | Proposed fix | Accepted? | Claims changed | CTA kept | Similarity | New Critical? |
|---|---|---|---|---|---|---|
| India's #1 (`docs/evidence/3_fix_india_no1.json`) | `"Our clinically proven GlowSerum cures acne and lightens dark spots in just 28 days with 100% natural organic saffron extracts. Dermatologist tested and guaranteed results. Shop now."` (`remove_unsupported_ranking_claim`) | Yes (`true`) | `["Experience India's #1 radiant skin formula!"]` | Yes (`true`) | `0.9101` | None (`[]`) |
| cures acne (`docs/evidence/3_fix_cures_acne.json`) | `"Experience India's #1 radiant skin formula! Our clinically proven GlowSerum may help improve the appearance of blemish-prone skin and lightens dark spots in just 28 days with 100% natural organic saffron extracts. Dermatologist tested and guaranteed results. Shop now."` (`safe_claim_language_replacement`) | Yes (`true`) | `["Our clinically proven GlowSerum cures acne and lightens dark spots in just 28 days with 100% natural organic saffron extracts."]` | Yes (`true`) | `0.8744` | None (`[]`) |
| 7 days vs FACT-014 | | *(not measured in this run)* | | | | |
| Bad fix (adds a Critical claim) (`docs/evidence/3_verify_fix_critical_rejected.json`) | `"GlowSerum cures eczema and guarantees results. Shop now."` | Rejected (`safe_to_suggest: false`) | `[]` (`original_claim_count: 0`, `candidate_claim_count: 1`) | Yes (`true`) | `0.1879` | Yes (`"GlowSerum cures eczema and guarantees results."`, `IN-5`, `critical`) |

## 4. User sessions and timing
| Participant | Role | Manual time (10 posts) | BrandCourt time (10 posts) | Order | Decisions matched answer key |
|---|---|---|---|---|---|

Report median and range, and say plainly if results vary a lot. Keep direct quotes.
