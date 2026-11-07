"""Deterministic privacy, language, declaration and tone checks for BrandCourt.
These are explainable heuristics; they are not a general-purpose language model.
"""
from __future__ import annotations
import re
from collections import defaultdict
import json

EMAIL = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I)
PHONE = re.compile(r"(?<!\w)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\w)")
AADHAAR = re.compile(r"(?<!\d)\d{4}[ -]?\d{4}[ -]?\d{4}(?!\d)")
PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b", re.I)
SECRET = re.compile(r"\b(?:api[_ -]?key|access[_ -]?token|password)\s*[:=]\s*[^\s,;]+", re.I)

class MaskingFailure(RuntimeError):
    pass


def mask_sensitive_with_map(
    text: str,
    secret_terms: list[str] | None = None,
) -> tuple[str, int, dict[str, str]]:
    """Mask PII and workspace secrets with stable, per-document pseudonyms."""
    try:
        candidates: list[tuple[int, int, str, str]] = []
        patterns = (
            (EMAIL, "EMAIL"),
            (PHONE, "PHONE"),
            (AADHAAR, "AADHAAR"),
            (PAN, "PAN"),
            (SECRET, "SECRET"),
        )
        for pattern, kind in patterns:
            candidates.extend(
                (match.start(), match.end(), kind, match.group())
                for match in pattern.finditer(text)
            )
        for secret in secret_terms or []:
            if isinstance(secret, str) and secret.strip():
                candidates.extend(
                    (match.start(), match.end(), "SECRET_TERM", match.group())
                    for match in re.finditer(re.escape(secret.strip()), text, re.I)
                )

        try:
            from presidio_analyzer import AnalyzerEngine
        except ImportError:
            AnalyzerEngine = None
        if AnalyzerEngine is not None:
            try:
                recognizer_results = AnalyzerEngine().analyze(
                    text=text,
                    language="en",
                )
                for result in recognizer_results:
                    candidates.append(
                        (
                            result.start,
                            result.end,
                            str(result.entity_type).upper(),
                            text[result.start : result.end],
                        )
                    )
            except Exception as exc:
                raise MaskingFailure("Optional Presidio analysis failed.") from exc

        candidates.sort(key=lambda candidate: (candidate[0], -(candidate[1] - candidate[0])))
        chosen: list[tuple[int, int, str, str]] = []
        last_end = -1
        for candidate in candidates:
            if candidate[0] >= last_end:
                chosen.append(candidate)
                last_end = candidate[1]

        counts: defaultdict[str, int] = defaultdict(int)
        local_map: dict[str, str] = {}
        output: list[str] = []
        cursor = 0
        for start, end, kind, value in chosen:
            output.append(text[cursor:start])
            counts[kind] += 1
            token = f"[{kind}_{counts[kind]}]"
            local_map[token] = value
            output.append(token)
            cursor = end
        output.append(text[cursor:])
        return "".join(output), len(chosen), local_map
    except MaskingFailure:
        raise
    except Exception as exc:
        raise MaskingFailure("Sensitive-data masking failed.") from exc


def mask_sensitive(
    text: str,
    secret_terms: list[str] | None = None,
) -> tuple[str, int]:
    """Compatibility wrapper; the reversible map stays local to the checking call."""
    masked, count, _local_map = mask_sensitive_with_map(text, secret_terms)
    return masked, count

def detect_language(text: str) -> dict:
    devanagari = len(re.findall(r"[\u0900-\u097F]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    words = set(re.findall(r"[a-z]+", text.lower()))
    hindi_roman = {"hai", "hain", "kya", "aap", "mera", "meri", "ke", "liye", "bahut", "accha", "achha", "nahi", "nahin", "kaise", "kar", "karo", "se", "mein", "par"}
    roman_hit = len(words & hindi_roman)
    if devanagari and latin and roman_hit >= 2:
        language, support = "hinglish", "limited"
    elif devanagari:
        # Devanagari is shared by Hindi and Marathi; Marathi lexicon only provides a hint.
        mr = {"आहे", "आणि", "नाही", "माझा", "माझी", "करा", "तुम्ही", "साठी", "होते"}
        language = "mr" if any(w in text for w in mr) else "hi"
        support = "limited" if language == "mr" else "supported"
    elif latin and roman_hit >= 2:
        language, support = "hinglish", "limited"
    elif latin:
        language, support = "en", "supported"
    else:
        language, support = "unknown", "limited"
    return {"language": language, "support": support, "method": "script_and_lexicon_heuristic"}

PAID_CHANNELS = {"paid_ad", "instagram", "facebook", "linkedin"}
PAID_LABELS = ("#ad", "#sponsored", "paid partnership", "paid promotion", "gifted", "advertisement", "sponsored by")
AI_LABELS = ("ai-generated", "ai generated", "made with ai", "synthetic media", "generated by ai", "#aigenerated")
FACTUAL_MARKERS = re.compile(r"\b(\d+(?:\.\d+)?\s*(?:%|percent|days?|weeks?|months?|years?|hours?)|clinically proven|dermatologist tested|tested by|reduces|improves|increases|decreases|contains)\b", re.I)
ABSOLUTES = re.compile(r"\b(always|never|guaranteed|100%|zero risk|no side effects|permanent results)\b", re.I)
IN5_CURE_PATTERNS = re.compile(
    r"(?:"
    r"\bcures?\s+(?:acne|eczema|psoriasis|diabetes|cancer)\b|"
    r"\bguaranteed\s+(?:cure|to cure)\b|"
    r"\b(?:permanently|guaranteed to)\s+(?:remove|eliminate)\s+(?:acne|blemishes|wrinkles)\b|"
    r"\b(?:cure|theek)\s*(?:ho\s*ja(?:ta|te|ti)|karta|karega)\b|"
    r"(?:बरे\s*होतात|ठीक\s*होतात|इलाज|पूर्णपणे|ठीक\s*हो\s*जा(?:ता|ते|ती))"
    r")",
    re.I,
)
IN2_SUPERLATIVE_PATTERNS = re.compile(
    r"(?:"
    r"\b(?:india['’]s\s+|india\s+is\s+|the\s+|india\s*ka\s+)?(?:#\s*1|number\s+one|no\.?\s*1|nambar\s+ek|sabse\s+acc?h?a)\b|"
    r"\b(?:india['’]s|india is|the)\s*(?:best|only)\b|"
    r"(?:सबसे\s*अच्छा|नंबर\s*(?:एक|1|वन)|नं\.?\s*1)"
    r")",
    re.I,
)

def layer1_checks(
    text: str,
    channel: str,
    alt_text: str | None = None,
    is_ai_media: bool = False,
    *,
    paid_gifted: bool = False,
    c2pa_data: dict | None = None,
    india_pack_enabled: bool = True,
    rules: list | None = None,
) -> list[dict]:
    lower = text.lower()
    findings: list[dict] = []

    def add(code, kind, severity, message, start=None, end=None, fix=None, source_note=None):
        findings.append({
            "code": code, "type": kind, "severity": severity,
            "verdict": "needs_human_review", "message": message,
            "span_start": start, "span_end": end, "suggested_fix": fix,
            "source_note": source_note,
        })

    if india_pack_enabled:
        if paid_gifted and not any(label in lower for label in PAID_LABELS):
            add("IN-4", "disclosure", "major",
                "The revision is declared paid or gifted but has no clear disclosure such as #ad or Paid partnership.",
                fix="Add the appropriate paid-partnership disclosure.")
        has_c2pa_manifest = bool(
            c2pa_data and c2pa_data.get("status") == "extracted"
        )
        if is_ai_media or has_c2pa_manifest:
            c2pa_note = (
                " C2PA provenance data was read."
                if has_c2pa_manifest
                else " No C2PA provenance data was found."
            )
            add("IN-6", "disclosure", "advisory",
                "AI-generated or synthetic media may need a platform label." + c2pa_note,
                fix="Check current platform disclosure guidance.")
        marker = FACTUAL_MARKERS.search(text)
        if marker and not re.search(r"\b(source|terms apply|results may vary|according to|study|report)\b", lower):
            add("IN-1", "required_text", "advisory",
                "A factual or performance claim may need a traceable approved source; no source is attached. This is not a finding that it is false.",
                marker.start(), marker.end(), "Attach an approved source for the factual claim.")
        absolute = ABSOLUTES.search(text)
        if re.search(r"\b(disclaimer|terms apply|results may vary)\b", lower) and absolute:
            add("IN-3", "disclosure", "critical",
                "Absolute wording appears alongside disclaimer language. A disclaimer does not necessarily cure a misleading main claim.",
                absolute.start(), absolute.end(),
                "Revise the absolute claim; do not rely on a disclaimer to qualify it.")
        in5_match = IN5_CURE_PATTERNS.search(text)
        if in5_match:
            add("IN-5", "term", "critical",
                "Potentially restricted cure or guaranteed-result claim. BrandCourt routes this to human/legal review; it is not a legal determination.",
                in5_match.start(), in5_match.end(),
                "Revise cure or guaranteed-result wording.",
                "BrandCourt India starter policy pack (advisory; not legal advice)")
        in2_match = IN2_SUPERLATIVE_PATTERNS.search(text)
        if in2_match:
            add("IN-2", "pattern", "critical",
                "A superlative or #1 claim needs specific, current evidence. No rank-specific proof was established by this baseline; unsupported is not a finding that the claim is false.",
                in2_match.start(), in2_match.end(),
                "Provide verifiable proof for ranking claim.",
                "BrandCourt India starter policy pack (advisory; not legal advice)")
    if not (alt_text or "").strip():
        add("A11Y-ALT", "alt_text", "advisory",
            "No image alt text is recorded. Add concise, meaningful alternative text for informative imagery.",
            fix="Add concise alt text describing informative visual content.")

    for rule in rules or []:
        if rule.status != "active" or (rule.channels and channel not in rule.channels):
            continue
        kind = str(rule.type).lower()
        try:
            config = json.loads(rule.text)
        except (TypeError, ValueError):
            config = {}
        if not isinstance(config, dict):
            config = {}
        if kind in {"term", "banned_term", "terminology"}:
            term = str(config.get("term", rule.text))
            found = re.search(re.escape(term), text, re.I) if term else None
            if found:
                add(rule.code, kind, rule.severity,
                    str(config.get("explanation", rule.title)),
                    found.start(), found.end(), config.get("suggested_fix"), rule.source_ref)
        elif kind == "pattern":
            try:
                pattern = re.compile(str(config.get("pattern", rule.text)), re.I)
            except re.error:
                add(rule.code, kind, "major", f"Rule {rule.code} has an invalid pattern and needs human review.")
                continue
            found = pattern.search(text)
            if found:
                add(rule.code, kind, rule.severity, str(config.get("explanation", rule.title)),
                    found.start(), found.end(), config.get("suggested_fix"), rule.source_ref)
        elif kind in {"required_text", "disclosure"}:
            trigger = str(config.get("trigger_phrase", ""))
            required = str(config.get("required_text", rule.text if kind == "disclosure" else ""))
            found = re.search(re.escape(trigger), text, re.I) if trigger else None
            distance = config.get("distance", 120)
            if not isinstance(distance, int) or distance < 0:
                distance = 120
            nearby_text = (
                text[max(0, found.start() - distance):min(len(text), found.end() + distance)]
                if found else ""
            )
            if found and required and required.casefold() not in nearby_text.casefold():
                add(rule.code, kind, rule.severity, str(config.get("explanation", rule.title)),
                    found.start(), found.end(), f"Add the required text near this phrase: {required}",
                    rule.source_ref)
        elif kind == "approved_spelling":
            approved = str(config.get("approved", ""))
            variants = config.get("variants", [])
            for variant in variants if isinstance(variants, list) else []:
                found = re.search(rf"\b{re.escape(str(variant))}\b", text, re.I)
                if found:
                    add(rule.code, kind, rule.severity, rule.title,
                        found.start(), found.end(), f"Use approved spelling: {approved}", rule.source_ref)
        elif kind == "alt_text" and not (alt_text or "").strip():
            add(rule.code, kind, rule.severity, rule.title,
                fix=str(config.get("suggested_fix", "Add concise alt text.")),
                source_note=rule.source_ref)
    return findings


def advisory_tone(text: str, examples: list[str] | None = None) -> list[dict]:
    flags=[]
    if ABSOLUTES.search(text):
        flags.append({"code":"TONE-ABSOLUTE", "severity":"advisory", "message":"Absolute or guaranteed language detected; verify it is supportable and on-brand."})
    if text.count("!") >= 3 or text.isupper() and len(text) > 20:
        flags.append({"code":"TONE-INTENSITY", "severity":"advisory", "message":"High-intensity punctuation or all-caps wording may conflict with a calm brand voice."})
    if examples:
        words = set(re.findall(r"[a-z0-9]+", text.lower()))
        example_words = {
            word for example in examples
            for word in re.findall(r"[a-z0-9]+", example.lower())
        }
        similarity = len(words & example_words) / max(1, len(words))
        confidence = round(min(0.99, 1 - similarity), 2)
        if confidence >= 0.8:
            flags.append({
                "code": "TONE-BRAND-VOICE",
                "severity": "advisory",
                "confidence": confidence,
                "message": "This copy differs from the workspace's approved brand-voice examples. Advisory only; a person decides.",
            })
    return flags
