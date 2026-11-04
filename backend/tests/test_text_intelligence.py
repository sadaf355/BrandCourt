from app.services.text_intelligence import mask_sensitive, detect_language, layer1_checks, advisory_tone

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
    assert {'IN-4','IN-6','A11Y-ALT'} <= codes

def test_disclaimer_conflict_and_advisory_tone():
    checks=layer1_checks('Guaranteed permanent results. Results may vary.', 'website', 'Product bottle')
    assert any(c['code']=='IN-3' for c in checks)
    assert advisory_tone('GUARANTEED RESULTS!!!')[0]['code']=='TONE-ABSOLUTE'
