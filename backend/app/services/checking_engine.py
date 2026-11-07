"""Deterministic claim extraction, retrieval fusion, and span utilities."""
from __future__ import annotations

import math
import os
import re
from typing import Any

from app.services.semantic_retrieval import embedding, cosine
from app.services.model_provider import ModelStepFailed


def extract_claims_regex(text: str) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for match in re.finditer(
        r"[^.!?\n]+(?:\.(?=\s*\d)[^.!?\n]*)?(?:[.!?]+|$)",
        text,
    ):
        raw = match.group()
        claim = re.sub(r"\s+", " ", raw).strip(" •\t")
        if len(claim) < 12:
            continue
        start = match.start() + len(raw) - len(raw.lstrip())
        claims.append({"claim": claim, "span_start": start, "span_end": start + len(claim)})
    return claims[:100]


def reciprocal_rank_fusion(
    query: str,
    documents: list[tuple[str, str]],
    *,
    top_k: int = 8,
    rerank: bool = True,
    query_vector: list[float] | None = None,
    document_vectors: dict[str, list[float]] | None = None,
) -> list[tuple[float, str]]:
    """Fuse BM25-like lexical and hashing-vector rankings with standard RRF."""
    query_terms = re.findall(r"[a-z0-9]+", query.lower())
    query_set = set(query_terms)
    if not query_set:
        return []
    lexical_scores: list[tuple[float, str]] = []
    vector_scores: list[tuple[float, str]] = []
    average_length = max(
        1.0,
        sum(len(re.findall(r"[a-z0-9]+", text.lower())) for _, text in documents)
        / max(1, len(documents)),
    )
    document_frequency = {
        term: sum(
            term in set(re.findall(r"[a-z0-9]+", text.lower()))
            for _, text in documents
        )
        for term in query_set
    }
    query_vector = query_vector or embedding(query)
    document_vectors = document_vectors or {}
    for identifier, text in documents:
        terms = re.findall(r"[a-z0-9]+", text.lower())
        frequencies = {term: terms.count(term) for term in query_set}
        score = 0.0
        for term, frequency in frequencies.items():
            if not frequency:
                continue
            inverse_document_frequency = math.log(
                1 + (len(documents) - document_frequency[term] + 0.5)
                / (document_frequency[term] + 0.5)
            )
            denominator = frequency + 1.2 * (
                1 - 0.75 + 0.75 * len(terms) / average_length
            )
            score += inverse_document_frequency * frequency * 2.2 / denominator
        lexical_scores.append((score, identifier))
        vector = document_vectors.get(identifier) or embedding(text)
        vector_scores.append((cosine(query_vector, vector), identifier))

    lexical_scores.sort(reverse=True)
    vector_scores.sort(reverse=True)
    fused: dict[str, float] = {}
    for rank, (_, identifier) in enumerate(lexical_scores, 1):
        fused[identifier] = fused.get(identifier, 0.0) + 1 / (60 + rank)
    for rank, (_, identifier) in enumerate(vector_scores, 1):
        fused[identifier] = fused.get(identifier, 0.0) + 1 / (60 + rank)
    return sorted(((score, identifier) for identifier, score in fused.items()), reverse=True)[:top_k]


async def optional_rerank(query: str, documents: list[tuple[str, str]]) -> list[tuple[float, str]] | None:
    """Use a configured reranker; no endpoint means deterministic RRF order is retained."""
    endpoint = os.environ.get("RERANKER_URL", "").strip()
    if not endpoint:
        return None
    import httpx

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                endpoint,
                json={
                    "query": query,
                    "documents": [{"id": identifier, "text": text} for identifier, text in documents],
                },
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.HTTPError as exc:
        raise ModelStepFailed("Configured reranker service is unavailable.") from exc
    scores = payload.get("scores") if isinstance(payload, dict) else None
    if not isinstance(scores, list):
        raise ModelStepFailed("Configured reranker returned invalid JSON.")
    parsed = []
    for row in scores:
        if (
            not isinstance(row, dict)
            or row.get("id") not in {identifier for identifier, _ in documents}
            or not isinstance(row.get("score"), (int, float))
        ):
            raise ModelStepFailed("Configured reranker returned an invalid score.")
        parsed.append((float(row["score"]), row["id"]))
    if len(parsed) != len(documents):
        raise ModelStepFailed("Configured reranker returned an incomplete ranking.")
    return sorted(parsed, reverse=True)[:3]


def merge_overlapping_spans(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge overlapping findings without downgrading the strongest severity or rule."""
    ordered = sorted(
        (dict(finding) for finding in findings),
        key=lambda finding: (
            finding.get("span_start") is None,
            finding.get("span_start") or 0,
            finding.get("span_end") or 0,
        ),
    )
    merged: list[dict[str, Any]] = []
    ranks = {"advisory": 1, "major": 2, "critical": 3}
    for finding in ordered:
        if finding.get("id"):
            finding.setdefault("finding_ids", [finding["id"]])
        if not merged or finding.get("span_start") is None:
            merged.append(finding)
            continue
        previous = merged[-1]
        if (
            previous.get("span_end") is None
            or finding.get("span_start") > previous["span_end"]
        ):
            merged.append(finding)
            continue
        previous["span_end"] = max(previous["span_end"], finding["span_end"])
        previous.setdefault("finding_ids", [previous["id"]] if previous.get("id") else [])
        previous["finding_ids"].extend(finding.get("finding_ids", [finding.get("id")]))
        layers = {
            part for part in (str(previous.get("layer", "")) + "," + str(finding.get("layer", ""))).split(",")
            if part
        }
        previous["layer"] = ",".join(sorted(layers))
        if ranks.get(finding.get("severity"), 0) > ranks.get(previous.get("severity"), 0):
            previous["severity"] = finding["severity"]
            previous["verdict"] = finding.get("verdict", previous.get("verdict"))
            previous["rationale"] = finding.get("rationale", previous.get("rationale"))
            previous["suggested_fix"] = finding.get("suggested_fix")
        previous["evidence"] = list(previous.get("evidence") or []) + list(
            finding.get("evidence") or []
        )
    return merged
