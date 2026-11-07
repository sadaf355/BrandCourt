"""Deterministic guideline screening with optional local NLI enrichment."""
from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from app.services.precedents import precedent_embedding
from app.services.semantic_retrieval import cosine

VAGUE_TERMS = (
    "appropriate",
    "as needed",
    "good quality",
    "professional",
    "suitable",
    "high quality",
    "best possible",
)


def rule_vector(rule: Any) -> list[float]:
    text = f"{rule.title} {rule.text}"
    vector = rule.embedding
    if not vector or len(vector) != 96:
        vector = precedent_embedding(text)
        rule.embedding = vector
    return vector


def overlapping_channel_scope(left: Any, right: Any) -> bool:
    left_channels = set(left.channels or [])
    right_channels = set(right.channels or [])
    return not left_channels or not right_channels or bool(left_channels & right_channels)


def rule_pair_candidates(rules: list[Any], similarity_threshold: float = 0.55):
    candidates = []
    for index, left in enumerate(rules):
        left_vector = rule_vector(left)
        for right in rules[index + 1 :]:
            right_vector = rule_vector(right)
            similarity = cosine(left_vector, right_vector)
            scope_overlap = overlapping_channel_scope(left, right)
            if similarity < similarity_threshold and not scope_overlap:
                continue
            candidates.append(
                {
                    "rule": left,
                    "other_rule": right,
                    "similarity": round(similarity, 4),
                    "scope_overlap": scope_overlap,
                }
            )
    return candidates


def vague_rule_issue(rule: Any, examples: Iterable[Any]) -> dict[str, Any] | None:
    text = f"{rule.title} {rule.text}".lower()
    vague_hits = [term for term in VAGUE_TERMS if term in text]
    has_testable_condition = bool(
        re.search(r"\b(?:at least|at most|within|exactly|must|must not|no more than)\b|\d", text)
    )
    example_rows = list(examples)
    has_example = any(str(getattr(example, "text", "")).strip() for example in example_rows)
    if not vague_hits and has_testable_condition and has_example:
        return None
    if not vague_hits and len(rule.text.strip()) >= 24 and has_testable_condition and has_example:
        return None
    explanation = []
    if vague_hits:
        explanation.append(f"subjective wording: {', '.join(vague_hits)}")
    if not has_testable_condition:
        explanation.append("no testable condition was found")
    if not has_example:
        explanation.append("no positive or negative example is attached")
    return {
        "type": "vague_rule",
        "rule_id": rule.id,
        "code": rule.code,
        "title": rule.title,
        "explanation": "; ".join(explanation) or "The rule may not be sufficiently testable.",
        "suggestion": "State an observable condition and add at least one concrete example.",
        "testable_condition": has_testable_condition,
        "has_example": has_example,
    }


def override_rate_issue(rule: Any, total_flags: int, overrides: int) -> dict[str, Any] | None:
    if total_flags < 5:
        return None
    return {
        "type": "override_rate",
        "rule_id": rule.id,
        "code": rule.code,
        "title": rule.title,
        "flag_count": total_flags,
        "override_count": overrides,
        "override_rate": round(overrides / total_flags, 4),
        "explanation": f"{overrides} of {total_flags} findings for this rule were overridden.",
        "suggestion": "Review the rule's scope, examples, and triggering conditions with its owner.",
    }


def conflict_rubric_prompt(rule_a: Any, rule_b: Any) -> str:
    return (
        "Assess only whether these two active brand rules can both be followed in the same "
        "content item. Ignore stylistic differences. Return contradiction=true only when their "
        "requirements are logically incompatible in an overlapping channel. Identify the exact "
        "conflicting requirements; otherwise return false. Do not propose changing either rule.\n"
        f"RULE A ({rule_a.code}): {rule_a.text[:3000]}\n"
        f"RULE B ({rule_b.code}): {rule_b.text[:3000]}"
    )
