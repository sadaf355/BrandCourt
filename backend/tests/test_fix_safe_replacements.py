"""Deterministic GlowSerum fix phrase tests; no external model is required."""
import pytest

from app.services.fixes import generate_minimal_fix


@pytest.mark.parametrize(("caption", "claim", "expected"), [
    ("This serum is guaranteed to cure acne.", "guaranteed to cure acne", "designed to support skin health"),
    ("Guaranteed results in 7 days.", "Guaranteed results", "individual results may vary"),
    ("The best serum for glowing skin.", "The best serum", "The serum"),
    ("Our miracle formula is unbeatable.", "miracle formula is unbeatable", "Our skincare formula is designed for everyday use"),
    ("The world's best and most powerful serum.", "world's best and most powerful serum", "The serum"),
    ("GlowSerum is #1 rated.", "#1 rated", "a skincare option"),
])
def test_glowserum_safe_replacement_phrases(caption, claim, expected):
    result = generate_minimal_fix(caption, claim, [])
    assert result.candidate_text
    assert expected.casefold() in result.candidate_text.casefold()
    assert result.method == "safe_claim_language_replacement"


@pytest.mark.parametrize(("caption", "claim", "expected", "forbidden"), [
    ("Our new GlowSerum is India's #1 and cures acne in 7 days!", "India's #1",
     "Our new GlowSerum cures acne in 7 days!", "India's"),
    ("GlowSerum is India's best skincare brand. Link in bio.", "India's best skincare brand",
     "Link in bio.", "India's"),
    ("Try the number one serum in India, India's #1 rated, today", "India's #1 rated",
     "", "India's #1"),
])
def test_unsupported_ranking_claims_are_removed_not_replaced(caption, claim, expected, forbidden):
    result = generate_minimal_fix(caption, claim, [])
    assert result.method == "remove_unsupported_ranking_claim"
    assert forbidden.casefold() not in result.candidate_text.casefold()
    assert expected.casefold() in result.candidate_text.casefold()
    assert "a skincare option" not in result.candidate_text
