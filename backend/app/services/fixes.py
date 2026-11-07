"""Small deterministic fix suggestions and intent-preservation measurements."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from app.services.precedents import precedent_embedding
from app.services.semantic_retrieval import cosine

CTA_PATTERN = re.compile(
    r"\b(?:buy|shop|order|book|sign up|learn more|link in bio|visit|register)\b",
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


def generate_minimal_fix(
    caption: str,
    claim_text: str,
    facts: list[Any],
) -> FixSuggestion:
    """Replace a claim quantity from a relevant fact, otherwise remove only its sentence."""
    claim_lower = claim_text.casefold()
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
