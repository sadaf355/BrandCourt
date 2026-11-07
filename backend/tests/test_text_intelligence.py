from app.services.text_intelligence import mask_sensitive, detect_language, layer1_checks, advisory_tone
from types import SimpleNamespace

def test_mask_sensitive_patterns():
    text,count=mask_sensitive('Email me at test@example.com or call 9876543210; api_key=secret123')
    assert count==3
    assert 'test@example.com' not in text and '9876543210' not in text and 'secret123' not in text

def test_language_detection_english_and_hinglish():
    assert detect_language('GlowSerum is a lightweight moisturiser')['language']=='en'
    assert detect_language('GlowSerum bahut accha hai')['language']=='hinglish'

def test_paid_ai_alt_and_india_disclosures():
    checks=layer1_checks('A new creator post about GlowSerum', 'paid_ad', '', True)
    codes={c['code'] for c in checks}
    assert {'IN-6','A11Y-ALT'} <= codes
    assert 'IN-4' not in codes


def test_c2pa_manifest_reminder_is_advisory_and_absence_is_not_a_finding():
    manifest_checks = layer1_checks(
        "A calm brand story.",
        "website",
        "Product bottle",
        c2pa_data={"status": "extracted", "manifest": {"active_manifest": "test"}},
    )
    reminder = next(check for check in manifest_checks if check["code"] == "IN-6")
    assert reminder["severity"] == "advisory"

    absent_checks = layer1_checks(
        "A calm brand story.",
        "website",
        "Product bottle",
        c2pa_data={"status": "no_manifest"},
    )
    assert not any(check["code"] == "IN-6" for check in absent_checks)


def test_disclaimer_conflict_and_advisory_tone():
    checks=layer1_checks('Guaranteed permanent results. Results may vary.', 'website', 'Product bottle')
    assert any(c['code']=='IN-3' for c in checks)
    assert advisory_tone('GUARANTEED RESULTS!!!')[0]['code']=='TONE-ABSOLUTE'


def test_paid_gifted_disclosure_uses_explicit_declaration():
    checks = layer1_checks(
        "A creator introduces GlowSerum", "website", paid_gifted=True
    )
    assert any(check["code"] == "IN-4" and check["severity"] == "major" for check in checks)
    assert not any(
        check["code"] == "IN-4"
        for check in layer1_checks(
            "A creator introduces GlowSerum", "paid_ad", paid_gifted=False
        )
    )


def test_rule_required_text_must_be_near_trigger_phrase():
    rule = SimpleNamespace(
        status="active",
        channels=[],
        type="required_text",
        text='{"trigger_phrase":"clinically proven","required_text":"See study"}',
        code="CUSTOM-1",
        severity="major",
        title="Study disclosure",
        source_ref="Approved guideline",
    )
    checks = layer1_checks(
        "Clinically proven. " + ("ordinary copy " * 20) + "See study.",
        "website",
        "Product bottle",
        rules=[rule],
    )
    finding = next(check for check in checks if check["code"] == "CUSTOM-1")
    assert finding["span_start"] == 0
    assert finding["source_note"] == "Approved guideline"


def test_cure_claims_multilingual_positive_and_clean_negative():
    # English
    pos_en = layer1_checks("GlowSerum cures acne permanently.", "website", "Product bottle")
    neg_en = layer1_checks("GlowSerum hydrates skin gently.", "website", "Product bottle")
    assert any(c["code"] == "IN-5" for c in pos_en)
    assert not any(c["code"] == "IN-5" for c in neg_en)

    # Hindi
    pos_hi = layer1_checks("GlowSerum से मुहांसों का इलाज होता है.", "website", "Product bottle")
    neg_hi = layer1_checks("GlowSerum त्वचा को नमी देता है.", "website", "Product bottle")
    assert any(c["code"] == "IN-5" for c in pos_hi)
    assert not any(c["code"] == "IN-5" for c in neg_hi)

    # Marathi
    pos_mr = layer1_checks("GlowSerum मुळे मुरुम पूर्णपणे बरे होतात.", "website", "Product bottle")
    neg_mr = layer1_checks("GlowSerum त्वचेला हलके हायड्रेशन देते.", "website", "Product bottle")
    assert any(c["code"] == "IN-5" for c in pos_mr)
    assert not any(c["code"] == "IN-5" for c in neg_mr)

    # Hinglish
    pos_hinglish = layer1_checks("GlowSerum se acne theek ho jata hai.", "website", "Product bottle")
    neg_hinglish = layer1_checks("GlowSerum daily routine ke liye accha hai.", "website", "Product bottle")
    assert any(c["code"] == "IN-5" for c in pos_hinglish)
    assert not any(c["code"] == "IN-5" for c in neg_hinglish)


def test_superlative_claims_multilingual_positive_and_clean_negative():
    # English
    pos_en = layer1_checks("GlowSerum is number one.", "website", "Product bottle")
    neg_en = layer1_checks("GlowSerum is a quality serum.", "website", "Product bottle")
    assert any(c["code"] == "IN-2" for c in pos_en)
    assert not any(c["code"] == "IN-2" for c in neg_en)

    # Hindi
    pos_hi = layer1_checks("GlowSerum सबसे अच्छा सीरम है.", "website", "Product bottle")
    neg_hi = layer1_checks("GlowSerum अच्छा सीरम है.", "website", "Product bottle")
    assert any(c["code"] == "IN-2" for c in pos_hi)
    assert not any(c["code"] == "IN-2" for c in neg_hi)

    # Marathi
    pos_mr = layer1_checks("GlowSerum नंबर एक सीरम आहे.", "website", "Product bottle")
    neg_mr = layer1_checks("GlowSerum रोज वापरण्यासाठी छान आहे.", "website", "Product bottle")
    assert any(c["code"] == "IN-2" for c in pos_mr)
    assert not any(c["code"] == "IN-2" for c in neg_mr)

    # Hinglish
    pos_hinglish = layer1_checks("Yeh India ka number one serum hai!", "website", "Product bottle")
    neg_hinglish = layer1_checks("GlowSerum bahut accha hai.", "website", "Product bottle")
    assert any(c["code"] == "IN-2" for c in pos_hinglish)
    assert not any(c["code"] == "IN-2" for c in neg_hinglish)
