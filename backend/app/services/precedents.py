"""Embedding-based matching for manager-approved reviewer precedents."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import math
import re
from typing import Any

from app.services.semantic_retrieval import cosine, embedding

PRECEDENT_MATCH_THRESHOLD = 0.85


def precedent_embedding(pattern_text: str) -> list[float]:
    vector = embedding(pattern_text)
    tokens = re.findall(r"[^\W_]+", pattern_text.casefold(), flags=re.UNICODE)
    for token in tokens:
        if token.isascii():
            continue
        features = [token]
        features.extend(token[index : index + 3] for index in range(max(1, len(token) - 2)))
        for feature in features:
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            number = int.from_bytes(digest, "big")
            vector[number % len(vector)] += 1.0 if (number >> 8) & 1 else -1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def matching_approved_precedents(
    precedents: list[Any],
    *,
    rule_id: str,
    channel: str,
    pattern_text: str,
    now: datetime | None = None,
) -> list[tuple[float, Any]]:
    current = now or datetime.now(timezone.utc)
    query_vector = precedent_embedding(pattern_text)
    matches = []
    for precedent in precedents:
        if precedent.status != "approved" or precedent.rule_id != rule_id:
            continue
        if precedent.channel not in {"all", channel}:
            continue
        valid_to = precedent.valid_to
        if valid_to and valid_to.replace(tzinfo=valid_to.tzinfo or timezone.utc) < current:
            continue
        vector = precedent.embedding or precedent_embedding(precedent.pattern_text)
        score = cosine(query_vector, vector)
        if score >= PRECEDENT_MATCH_THRESHOLD:
            matches.append((score, precedent))
    return sorted(matches, key=lambda match: match[0], reverse=True)


def precedent_suggestion(finding: Any, precedent: Any, score: float) -> dict[str, Any]:
    critical = str(finding.severity).lower() == "critical"
    return {
        "precedent_id": precedent.id,
        "rule_id": precedent.rule_id,
        "channel": precedent.channel,
        "reason": precedent.reason,
        "pattern_text": precedent.pattern_text,
        "similarity": round(score, 4),
        "suggested_severity": None if critical else "advisory",
        "requires_reviewer_confirmation": not critical,
        "message": (
            "Critical findings cannot be downgraded by precedent."
            if critical
            else "This approved precedent may support an advisory downgrade; a reviewer must confirm."
        ),
    }
