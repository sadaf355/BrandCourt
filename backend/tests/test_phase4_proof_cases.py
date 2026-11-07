"""Phase 4 proof-case regression checks (deterministic, no external model required)."""
from app.services.model_provider import Adjudication, verify_adjudication_quote


def test_forced_quote_rejects_paraphrase_not_present_in_fact():
    fact = "GlowSerum hydration lasts four weeks."
    accepted = Adjudication(
        verdict="supported", fact_id="fact-123",
        quote="GlowSerum hydration lasts four weeks.", reason="Exact evidence",
    )
    rejected = accepted.model_copy(update={"quote": "GlowSerum lasts for a month."})
    assert verify_adjudication_quote(accepted, expected_fact_id="fact-123", fact_text=fact)
    assert not verify_adjudication_quote(rejected, expected_fact_id="fact-123", fact_text=fact)


def test_forced_quote_rejects_wrong_fact_id():
    fact = "GlowSerum hydration lasts four weeks."
    candidate = Adjudication(
        verdict="supported", fact_id="other-fact",
        quote=fact, reason="Exact quote but wrong source",
    )
    assert not verify_adjudication_quote(candidate, expected_fact_id="fact-123", fact_text=fact)


def test_forced_quote_accepts_exact_unicode_quote():
    fact = "GlowSerum त्वचेला हायड्रेशन देते."
    candidate = Adjudication(
        verdict="supported", fact_id="fact-123", quote="त्वचेला हायड्रेशन देते.",
        reason="Exact Marathi substring",
    )
    assert verify_adjudication_quote(candidate, expected_fact_id="fact-123", fact_text=fact)
