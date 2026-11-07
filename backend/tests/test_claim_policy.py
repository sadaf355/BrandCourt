from app.services.claim_policy import (
    _claim_builtin_policy,
    _normalized_number_comparison,
    is_risky_claim,
)


def test_common_duration_units_are_normalized():
    assert _normalized_number_comparison('GlowSerum works for 28 days', '4', 'weeks') is True
    assert _normalized_number_comparison('GlowSerum works for 7 days', '4', 'weeks') is False


def test_incompatible_units_are_not_called_a_contradiction():
    assert _normalized_number_comparison('A 5% improvement', '5', 'days') is None


def test_india_number_one_claim_is_unsupported():
    result = _claim_builtin_policy("GlowSerum is India's #1 serum")
    assert result and result[0] == 'unsupported' and result[2] == 'IN-2'


def test_cure_acne_claim_is_blocked_for_human_review():
    result = _claim_builtin_policy('GlowSerum cures acne in 7 days')
    assert result and result[0] == 'unsupported' and result[1] == 'critical' and result[2] == 'IN-5'


def test_harmless_acne_reference_is_not_a_risky_claim():
    assert not is_risky_claim("Designed for acne-prone skin.")
    assert is_risky_claim("Reduces acne.")


def test_quantity_comparison_skips_unrelated_incompatible_quantity():
    assert _normalized_number_comparison('The 30 ml bottle keeps hydration for 28 days', '4', 'weeks') is True
    assert _normalized_number_comparison('The 30 ml bottle keeps hydration for 7 days', '4', 'weeks') is False
    assert _normalized_number_comparison('A 5% improvement', '5', 'days') is None

def test_common_mass_volume_and_length_units():
    assert _normalized_number_comparison('Contains 1000 mg active ingredient', '1', 'g') is True
    assert _normalized_number_comparison('A 1 litre bottle', '1000', 'ml') is True
    assert _normalized_number_comparison('A 2 cm strip', '20', 'mm') is True


def test_approval_gate_blocks_risky_verdict_even_when_severity_is_warning():
    from app.services.claim_policy import is_approval_blocker, decision_clears_approval_block
    assert is_approval_blocker('contradicted', 'warning') is True
    assert is_approval_blocker('needs_human_review', 'warning') is True
    assert is_approval_blocker('supported', 'advisory') is False
    assert is_approval_blocker('needs_human_review', 'advisory') is False
    assert is_approval_blocker('supported', 'advisory', step_failed=True) is True
    assert decision_clears_approval_block('accept', [{'type':'policy_pack','code':'IN-2'}]) is False
    assert decision_clears_approval_block('resolve', [{'type':'policy_pack','code':'IN-2'}]) is True
    assert decision_clears_approval_block('override', []) is True


def test_currency_values_compare_when_fact_unit_carries_currency():
    from app.services.claim_policy import compare_claim_to_fact

    assert compare_claim_to_fact("GlowSerum costs Rs 499", "499", "INR") is True
    assert compare_claim_to_fact("GlowSerum costs Rs 599", "499", "INR") is False
    assert compare_claim_to_fact("GlowSerum costs 599", "499", "INR") is None


def test_date_only_fact_validity_end_is_inclusive():
    from datetime import datetime, timezone
    from app.services.claim_policy import fact_outside_validity_window

    today = datetime(2026, 11, 6, 12, tzinfo=timezone.utc)
    assert not fact_outside_validity_window(
        None, datetime(2026, 11, 6, 0, tzinfo=timezone.utc), today
    )
    assert fact_outside_validity_window(
        None, datetime(2026, 11, 5, 0, tzinfo=timezone.utc), today
    )
