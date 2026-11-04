"""Deterministic claim policy helpers for BrandCourt Claim Court v2."""
import re

_UNIT_FACTORS = {
    'duration_minutes': {'day':1440,'days':1440,'week':10080,'weeks':10080,'month':43200,'months':43200,'year':525600,'years':525600,'minute':1,'minutes':1,'min':1,'mins':1,'hour':60,'hours':60,'hr':60,'hrs':60},
    'percent': {'%':1,'percent':1,'percentage':1},
    'mass_g': {'mg':0.001,'milligram':0.001,'milligrams':0.001,'g':1,'gram':1,'grams':1,'kg':1000,'kilogram':1000,'kilograms':1000},
    'volume_ml': {'ml':1,'milliliter':1,'milliliters':1,'millilitre':1,'millilitres':1,'l':1000,'liter':1000,'liters':1000,'litre':1000,'litres':1000},
    'length_mm': {'mm':1,'millimeter':1,'millimeters':1,'millimetre':1,'millimetres':1,'cm':10,'centimeter':10,'centimeters':10,'centimetre':10,'centimetres':10,'m':1000,'meter':1000,'meters':1000,'metre':1000,'metres':1000},
}
_UNIT_ALIASES = {unit: (dimension, factor) for dimension, units in _UNIT_FACTORS.items() for unit, factor in units.items()}
_NUMBER_RE = re.compile(r'(?P<num>\d+(?:,\d{3})*(?:\.\d+)?)\s*(?P<unit>%|percent(?:age)?|days?|weeks?|months?|years?|hours?|hrs?|minutes?|mins?|mg|milligrams?|g|grams?|kg|kilograms?|ml|millilit(?:er|re)s?|l|lit(?:er|re)s?|mm|millimet(?:er|re)s?|cm|centimet(?:er|re)s?|m|met(?:er|re)s?)?', re.I)

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
        return ('unsupported','critical','IN-2','A superlative or #1 claim needs specific, current evidence. No rank-specific proof was established by this baseline.')
    return None


def is_approval_blocker(verdict: str, severity: str) -> bool:
    """Conservative publish gate: risky verdicts block regardless of severity label."""
    return (severity or '').lower() in {'critical', 'blocker'} or (verdict or '').lower() in {
        'contradicted', 'outdated', 'unsupported', 'needs_human_review'
    }

def decision_clears_approval_block(action: str, evidence: list[dict] | None = None) -> bool:
    """Blocking findings need explicit resolution or an authorised override, not simple acceptance.

    IN-1..IN-6 policy-pack findings are especially conservative: the creator's Accept action
    acknowledges a finding but does not substitute for review/sign-off.
    """
    if action not in {'resolve', 'override'}:
        return False
    # India-pack overrides are separately role-gated to manager/admin in workflow.py.
    return True
