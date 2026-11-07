"""Deterministic claim policy helpers for BrandCourt Claim Court v2."""
import re
from dataclasses import dataclass
from datetime import datetime, time, timezone

from app.models.entities import normalize_severity

_UNIT_FACTORS = {
    'duration_minutes': {'day':1440,'days':1440,'week':10080,'weeks':10080,'month':43200,'months':43200,'year':525600,'years':525600,'minute':1,'minutes':1,'min':1,'mins':1,'hour':60,'hours':60,'hr':60,'hrs':60},
    'percent': {'%':1,'percent':1,'percentage':1},
    'mass_g': {'mg':0.001,'milligram':0.001,'milligrams':0.001,'g':1,'gram':1,'grams':1,'kg':1000,'kilogram':1000,'kilograms':1000},
    'volume_ml': {'ml':1,'milliliter':1,'milliliters':1,'millilitre':1,'millilitres':1,'l':1000,'liter':1000,'liters':1000,'litre':1000,'litres':1000},
    'length_mm': {'mm':1,'millimeter':1,'millimeters':1,'millimetre':1,'millimetres':1,'cm':10,'centimeter':10,'centimeters':10,'centimetre':10,'centimetres':10,'m':1000,'meter':1000,'meters':1000,'metre':1000,'metres':1000},
}
_UNIT_ALIASES = {unit: (dimension, factor) for dimension, units in _UNIT_FACTORS.items() for unit, factor in units.items()}
_NUMBER_RE = re.compile(r'(?P<num>\d+(?:,\d{3})*(?:\.\d+)?)\s*(?P<unit>%|percent(?:age)?|days?|weeks?|months?|years?|hours?|hrs?|minutes?|mins?|mg|milligrams?|g|grams?|kg|kilograms?|ml|millilit(?:er|re)s?|l|lit(?:er|re)s?|mm|millimet(?:er|re)s?|cm|centimet(?:er|re)s?|m|met(?:er|re)s?)?', re.I)
_MONEY_RE = re.compile(
    r"(?:(?:₹|rs\.?|inr)\s*(?P<num>\d+(?:,\d{3})*(?:\.\d+)?)|"
    r"(?P<num_after>\d+(?:,\d{3})*(?:\.\d+)?)\s*(?:₹|rs\.?|inr)(?!\w))",
    re.I,
)
_RISKY_CLAIM_RE = re.compile(
    r"(?:"
    r"\d|₹|\brs\.?\s*\d|\binr\s*\d|\b(?:offer|discount|save|off|price|cost|"
    r"number\s*one|no\.?\s*1|#\s*1|best|better|most|only|fastest|"
    r"cures?|treats?|heals?|clinically|dermatologist|proven|"
    r"(?:cures?|treats?|heals?|clears?|prevents?|reduces?)\s+(?:\w+\s+){0,2}(?:acne|eczema|psoriasis|blemishes|wrinkles)\b|"
    r"results?|reduces?|improves?|increases?|decreases?|guaranteed|"
    r"lasts?|works?)\b"
    r")",
    re.I,
)


@dataclass(frozen=True)
class ExactComparison:
    verdict: str
    reason: str


def is_risky_claim(claim: str) -> bool:
    return bool(_RISKY_CLAIM_RE.search(claim))


def compare_claim_to_fact(claim: str, fact_value: str, fact_unit: str | None) -> bool | None:
    """Return exact numeric agreement, disagreement, or None when dimensions are unclear."""
    claim_money = _MONEY_RE.search(claim)
    fact_text = f"{fact_value} {fact_unit or ''}".strip()
    fact_money = _MONEY_RE.search(fact_text)
    if claim_money or fact_money or (fact_unit or "").strip().lower() in {
        "rs", "inr", "₹", "rupees", "rupee",
    }:
        fact_amount_match = fact_money
        if fact_amount_match is None and (fact_unit or "").strip().lower() in {
            "rs", "inr", "₹", "rupees", "rupee",
        }:
            fact_amount_match = _NUMBER_RE.search(fact_value)
        if not (claim_money and fact_amount_match):
            return None
        claim_amount = float(
            (claim_money.group("num") or claim_money.group("num_after")).replace(",", "")
        )
        fact_amount = float(
            (fact_amount_match.group("num") or fact_amount_match.group("num_after")).replace(",", "")
        )
        return abs(claim_amount - fact_amount) < 1e-6
    return _normalized_number_comparison(claim, fact_value, fact_unit)


def fact_outside_validity_window(
    valid_from: datetime | None,
    valid_to: datetime | None,
    now: datetime | None = None,
) -> bool:
    """Treat date-only midnight endpoints as inclusive calendar dates."""
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    start = valid_from
    end = valid_to
    if start and start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    if end and end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    starts_in_future = bool(
        start
        and (
            start.date() > current.date()
            if start.time() == time.min
            else start > current
        )
    )
    has_expired = bool(
        end
        and (
            end.date() < current.date()
            if end.time() == time.min
            else end < current
        )
    )
    return starts_in_future or has_expired

def _unit_value(number: float, unit: str | None, assumed_unit: str | None = None):
    unit=(unit or '').lower().strip()
    if not unit and assumed_unit:
        unit=assumed_unit.lower().strip()
    if not unit: return number, 'unitless'
    if unit in _UNIT_ALIASES:
        dimension,factor=_UNIT_ALIASES[unit]
        return number*factor,dimension
    # Accept a separate fact unit such as "weeks" when the numeric value is stored separately.
    if unit.endswith('s') and unit[:-1] in _UNIT_ALIASES: unit=unit[:-1]
    if unit in _UNIT_ALIASES:
        dimension,factor=_UNIT_ALIASES[unit]
        return number*factor,dimension
    return number, 'unknown:'+unit

def _number_with_unit(text: str):
    """Compatibility helper: return the first quantity normalized to a base unit."""
    match=_NUMBER_RE.search(text.lower())
    if not match: return None
    number=float(match.group('num').replace(',',''))
    return _unit_value(number,match.group('unit'))

def _normalized_number_comparison(claim: str, fact_value: str, fact_unit: str | None):
    """Compare any claim quantity compatible with the fact's dimension, with unit conversion.

    If the claim contains multiple quantities, prefer one with the same physical dimension as
    the approved fact. Return None rather than inventing a conversion across dimensions.
    """
    fact_match=_NUMBER_RE.search(f'{fact_value} {fact_unit or ""}'.strip().lower())
    if not fact_match: return None
    expected_number=float(fact_match.group('num').replace(',',''))
    expected_unit=fact_match.group('unit') or fact_unit
    expected=_unit_value(expected_number,expected_unit)
    candidates=[]
    for match in _NUMBER_RE.finditer(claim.lower()):
        number=float(match.group('num').replace(',',''))
        unit=match.group('unit')
        # An unqualified claim number may inherit the approved fact's unit only when no explicit
        # unit was present; this allows "lasts 4" to be compared only in a context-rich claim.
        candidates.append(_unit_value(number,unit))
    compatible=[candidate for candidate in candidates if candidate[1]==expected[1]]
    if not compatible and len(candidates)==1 and candidates[0][1]=='unitless' and expected[1]!='unitless':
        compatible=[_unit_value(float(fact_match.group('num').replace(',','')),fact_unit)]
    if not compatible: return None
    # When multiple quantities share the same dimension, an exact match wins; otherwise compare
    # the first compatible quantity to avoid selecting a later, unrelated number opportunistically.
    return abs(compatible[0][0]-expected[0]) < 1e-6

def _claim_builtin_policy(claim: str):
    lower=claim.lower()
    cure_patterns=[r'\bcures?\s+(?:acne|eczema|psoriasis|diabetes|cancer)\b',r'\bguaranteed\s+(?:cure|to cure)\b',r'\b(?:permanently|guaranteed to)\s+(?:remove|eliminate)\s+(?:acne|blemishes|wrinkles)\b']
    if any(re.search(pattern,lower) for pattern in cure_patterns):
        return ('unsupported','critical','IN-5','Potentially restricted cure or guaranteed-result claim. BrandCourt routes this to human/legal review; it is not a legal determination.')
    if re.search(r"\b(?:india['’]s|india is|the)\s*(?:#\s*1|number\s+one|no\.?\s*1|best|only)\b|\bindia['’]s\s+#\s*1\b",lower):
        return ('unsupported','critical','IN-2','A superlative or #1 claim needs specific, current evidence. No rank-specific proof was established by this baseline; unsupported is not a finding that the claim is false.')
    return None


def is_approval_blocker(
    verdict: str,
    severity: str,
    *,
    step_failed: bool = False,
) -> bool:
    """Advisories never block; failed checks and major/critical findings require review."""
    if step_failed:
        return True
    try:
        normalized_severity = normalize_severity(severity or "")
    except (AttributeError, ValueError):
        return True
    if normalized_severity == "advisory":
        return False
    if normalized_severity not in {"major", "critical"}:
        return False
    if (verdict or "").lower() == "needs_human_review":
        return True
    return True

def decision_clears_approval_block(action: str, evidence: list[dict] | None = None) -> bool:
    """Blocking findings need explicit resolution or an authorised override, not simple acceptance.

    IN-1..IN-6 policy-pack findings are especially conservative: the creator's Accept action
    acknowledges a finding but does not substitute for review/sign-off.
    """
    if action not in {'resolve', 'override'}:
        return False
    # India-pack overrides are separately role-gated to manager/admin in workflow.py.
    return True
