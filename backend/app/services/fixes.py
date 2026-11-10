"""Small deterministic fix suggestions and intent-preservation measurements."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from app.services.precedents import precedent_embedding
from app.services.semantic_retrieval import cosine

SAFE_REPLACEMENTS = {
    "guaranteed to cure acne": "designed to support skin health",
    "guaranteed to cure": "designed to support",
    "guaranteed cure": "potential skincare benefit",
    "guaranteed results": "results may vary depending on the individual",
    "cures acne": "may help improve the appearance of blemish-prone skin",
    "permanently removes": "helps reduce the appearance of",
    "guaranteed": "designed to",
    "cures": "may help support",
    "cure": "support",
    # Unsupported superiority / absolute-performance language. These edits
    # remove the ranking or certainty, rather than replacing it with another
    # unsubstantiated comparison.
    "world's best and most powerful": "a serum",
    "world’s best and most powerful": "a serum",
    "the best": "a",
    "best-in-class": "everyday",
    "best in class": "everyday",
    "number one": "a",
    "#1 rated": "a skincare option",
    "#1": "a skincare option",
    "world's best": "a",
    "world’s best": "a",
    "ultimate": "everyday",
    "miracle formula": "skincare formula",
    "miracle": "skincare",
    "most effective": "a",
    "most powerful": "a",
    "unmatched": "everyday",
    "unbeatable": "everyday",
    "revolutionary": "everyday",
    "top-rated": "a",
}

CTA_PATTERN = re.compile(
    r"\b(?:buy|shop|order|book|sign up|learn more|link in bio|visit|register)\b",
    re.IGNORECASE,
)


RANKING_CLAIM_PATTERN = re.compile(
    r"(?:\b(?:is|are)\s+)?(?P<rank>(?:india['’]s|indian)\s+(?:#\s?1|number\s+one|no\.?\s*1|best|top[- ]rated|leading|most\s+trusted)"
    r"(?:\s+(?:rated|brand|serum|skincare\s+brand))?)\b(?P<tail>\s*(?:,|and|&)\s+)?",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class FixSuggestion:
    candidate_text: str
    source_fact_id: str | None
    method: str


class ModelFixSuggestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_text: str = Field(min_length=1, max_length=20000)
    source_fact_id: str | None = None


def _apply_remaining_safe_replacements(candidate: str, claim_lower: str) -> str:
    """Apply additional explicitly flagged phrase edits without touching unrelated copy."""
    for risky_phrase, safe_phrase in SAFE_REPLACEMENTS.items():
        if risky_phrase in claim_lower and risky_phrase in candidate.casefold():
            candidate = re.sub(re.escape(risky_phrase), safe_phrase, candidate, count=1, flags=re.I)
    return candidate


def generate_minimal_fix(
    caption: str,
    claim_text: str,
    facts: list[Any],
) -> FixSuggestion:
    """Replace a claim quantity from a relevant fact, otherwise remove only its sentence."""
    claim_lower = claim_text.casefold()
    # Unsupported ranking claims such as "India's #1" need proof, so the safest minimal
    # edit removes the claim instead of swapping in another comparison (Round 1 plan).
    ranking_match = RANKING_CLAIM_PATTERN.search(caption)
    if ranking_match and ranking_match.group("rank").casefold() in claim_lower:
        if ranking_match.group("tail"):
            # "X is India's #1 and cures acne" -> "X cures acne"; the next clause keeps its own verb.
            candidate = caption[: ranking_match.start()] + caption[ranking_match.end() :]
            candidate = re.sub(r"\s{2,}", " ", candidate).strip()
            return FixSuggestion(candidate, None, "remove_unsupported_ranking_claim")
        sentences = re.split(r"(?<=[.!?])\s+", caption)
        matched_sentence = next((x for x in sentences if ranking_match.group("rank").casefold() in x.casefold()), None)
        if matched_sentence:
            candidate = re.sub(r"\s{2,}", " ", caption.replace(matched_sentence, "", 1)).strip()
            return FixSuggestion(candidate, None, "remove_unsupported_ranking_claim")
    # Replace high-risk cure/guarantee language with cautious, non-medical wording.
    risky_timed_result = re.compile(
        r"\bguaranteed\s+results?(?:\s+(?:in|within)\s+\d+\s+(?:days?|weeks?|months?|years?))?\b",
        re.I,
    )
    timed_match = risky_timed_result.search(caption)
    if timed_match and (
        timed_match.group(0).casefold() in claim_lower
        or timed_match.group(0).split(" in ")[0].casefold() in claim_lower
        or timed_match.group(0).split(" within ")[0].casefold() in claim_lower
    ):
        candidate = caption[:timed_match.start()] + (
            "individual results may vary; no specific outcome or timeframe is promised"
        ) + caption[timed_match.end():]
        return FixSuggestion(candidate, None, "safe_claim_language_replacement")
    # Handle superlatives in predicate position without producing broken grammar
    # (for example, "is unbeatable" -> "is designed for everyday use").
    predicate_superlative = re.compile(
        r"\b(is|are|was|were)\s+(?:the\s+)?(?:best|best-in-class|best in class|number one|#1(?: rated)?|top-rated|ultimate|unmatched|unbeatable|most effective|most powerful)\b",
        re.I,
    )
    predicate_match = predicate_superlative.search(caption)
    if predicate_match and predicate_match.group(0).casefold() in claim_lower:
        verb = predicate_match.group(1)
        replacement = "are designed for everyday use" if verb.casefold() in {"are", "were"} else "is designed for everyday use"
        candidate = caption[:predicate_match.start()] + replacement + caption[predicate_match.end():]
        candidate = _apply_remaining_safe_replacements(candidate, claim_lower)
        return FixSuggestion(candidate, None, "safe_claim_language_replacement")

    # When a ranking adjective modifies a noun, remove the unsupported ranking
    # and retain the noun and its article ("the best serum" -> "the serum").
    noun_superlative = re.compile(
        r"\b(?P<article>the|our|this|a|an)\s+(?:world['’]s\s+)?(?:best(?:-in-class| in class)?(?:\s+and\s+most\s+(?:effective|powerful))?|number one|#1(?: rated)?|top-rated|ultimate|unmatched|unbeatable|most effective|most powerful)\s+(?P<noun>[a-z][a-z-]*)\b",
        re.I,
    )
    noun_match = noun_superlative.search(caption)
    if noun_match and any(
        term in claim_lower
        for term in ("best", "number one", "#1", "top-rated", "ultimate", "unmatched", "unbeatable", "most effective", "most powerful")
    ):
        candidate = caption[:noun_match.start()] + f"{noun_match.group('article')} {noun_match.group('noun')}" + caption[noun_match.end():]
        candidate = _apply_remaining_safe_replacements(candidate, claim_lower)
        return FixSuggestion(candidate, None, "safe_claim_language_replacement")

    for risky_phrase, safe_phrase in SAFE_REPLACEMENTS.items():
        if risky_phrase in caption.casefold() and risky_phrase in claim_lower:
            candidate = re.sub(re.escape(risky_phrase), safe_phrase, caption, count=1, flags=re.I)
            return FixSuggestion(candidate, None, "safe_claim_language_replacement")
    for fact in facts:
        tokens = {
            token
            for token in re.findall(r"[a-z0-9]+", f"{fact.statement} {fact.code}".casefold())
            if len(token) > 2
        }
        claim_tokens = set(re.findall(r"[a-z0-9]+", claim_lower))
        if not tokens.intersection(claim_tokens):
            continue
        fact_text = " ".join(part for part in (str(fact.value), str(fact.unit or "")) if part)
        quantities = list(
            re.finditer(r"(?:₹|rs\.?\s*)?\d+(?:,\d{3})*(?:\.\d+)?\s*(?:%|percent|days?|weeks?|months?|years?|hours?)?", claim_text, re.I)
        )
        if not quantities:
            continue
        matched_claim = next(
            (match.group(0) for match in re.finditer(re.escape(claim_text), caption, re.I)),
            None,
        )
        source = matched_claim or claim_text
        quantity = next(
            re.finditer(r"(?:₹|rs\.?\s*)?\d+(?:,\d{3})*(?:\.\d+)?\s*(?:%|percent|days?|weeks?|months?|years?|hours?)?", source, re.I),
            None,
        )
        if quantity:
            corrected = source[: quantity.start()] + fact_text + source[quantity.end() :]
            return FixSuggestion(
                candidate_text=caption.replace(source, corrected, 1),
                source_fact_id=fact.id,
                method="approved_fact_quantity_substitution",
            )
    sentences = re.split(r"(?<=[.!?])\s+", caption)
    matched_sentence = next(
        (sentence for sentence in sentences if claim_text.casefold() in sentence.casefold()),
        None,
    )
    if matched_sentence:
        candidate = caption.replace(matched_sentence, "", 1)
        candidate = re.sub(r"\s{2,}", " ", candidate).strip()
        return FixSuggestion(candidate, None, "remove_flagged_sentence")
    return FixSuggestion("", None, "no_safe_minimal_edit")


def measure_intent(original: str, candidate: str) -> dict[str, Any]:
    similarity = cosine(precedent_embedding(original), precedent_embedding(candidate))
    original_ctas = {match.group(0).casefold() for match in CTA_PATTERN.finditer(original)}
    candidate_ctas = {match.group(0).casefold() for match in CTA_PATTERN.finditer(candidate)}
    return {
        "embedding_similarity": round(similarity, 4),
        "threshold": 0.80,
        "call_to_action_present": not original_ctas or bool(original_ctas & candidate_ctas),
        "intent_preserved": similarity >= 0.80
        and (not original_ctas or bool(original_ctas & candidate_ctas)),
    }
