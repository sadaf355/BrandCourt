import asyncio

import httpx

from app.services.checking_engine import (
    extract_claims_regex,
    merge_overlapping_spans,
    reciprocal_rank_fusion,
)
from app.services.model_provider import (
    Adjudication,
    ClaimExtraction,
    ModelStepFailed,
    validated_json,
    verify_adjudication_quote,
)
from app.services.semantic_retrieval import (
    HashingEmbeddingProvider,
    OllamaEmbeddingProvider,
    embedding_provider_for,
    ollama_embeddings,
    ollama_nli,
)


def test_regex_claim_extraction_preserves_spans():
    text = "GlowSerum lasts 4 weeks. Gentle daily hydration."
    claims = extract_claims_regex(text)
    assert claims[0]["claim"] == "GlowSerum lasts 4 weeks."
    assert text[claims[0]["span_start"]:claims[0]["span_end"]] == claims[0]["claim"]


def test_regex_claim_extraction_keeps_no_one_superlative_together():
    claims = extract_claims_regex("India's No. 1 GlowSerum is here.")
    assert len(claims) == 1
    assert "No. 1" in claims[0]["claim"]


def test_rrf_returns_related_documents_with_top_k_limit():
    ranked = reciprocal_rank_fusion(
        "GlowSerum hydration lasts four weeks",
        [
            ("fact1", "GlowSerum hydration duration 4 weeks"),
            ("fact2", "Shipping carton is brown"),
        ],
        top_k=1,
    )
    assert len(ranked) == 1
    assert ranked[0][1] == "fact1"


def test_rrf_accepts_vectors_from_an_optional_provider():
    ranked = reciprocal_rank_fusion(
        "target",
        [("fact-a", "other words"), ("fact-b", "different terms")],
        query_vector=[1.0, 0.0],
        document_vectors={"fact-a": [0.0, 1.0], "fact-b": [1.0, 0.0]},
    )
    assert ranked[0][1] == "fact-b"


def test_embedding_provider_factory_keeps_hashing_fallback():
    local = embedding_provider_for("deterministic", "http://localhost:11434", "model")
    hosted = embedding_provider_for("ollama", "http://localhost:11434", "bge-m3")

    assert isinstance(local, HashingEmbeddingProvider)
    assert isinstance(hosted, OllamaEmbeddingProvider)
    result = asyncio.run(local.embed(["safe local text"]))
    assert result["status"] == "completed"
    assert len(result["embeddings"]) == 1


def test_unavailable_embedding_service_is_reported_for_human_review():
    result = asyncio.run(
        ollama_embeddings(["masked text"], "http://127.0.0.1:1", "test-model")
    )
    assert result["status"] == "needs_human_review"
    assert "unavailable" in result["reason"].lower() or "connect" in result["reason"].lower()


def test_ollama_nli_invalid_response_is_needs_human_review(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"response": "not-json"}

    class Client:
        def __init__(self, *, timeout):
            assert timeout == 12.0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            return Response()

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    result = asyncio.run(
        ollama_nli("masked claim", "masked fact", "http://ollama", "model")
    )
    assert result["status"] == "needs_human_review"
    assert result["label"] == "unknown"


def test_ollama_nli_timeout_is_needs_human_review(monkeypatch):
    class Client:
        def __init__(self, *, timeout):
            assert timeout == 12.0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr(httpx, "AsyncClient", Client)
    result = asyncio.run(
        ollama_nli("masked claim", "masked fact", "http://ollama", "model")
    )
    assert result["status"] == "needs_human_review"
    assert result["label"] == "unknown"
    assert "ReadTimeout" in result["reason"]


def test_overlapping_findings_merge_and_keep_strongest_severity():
    merged = merge_overlapping_spans([
        {"span_start": 2, "span_end": 8, "severity": "advisory", "evidence": [{"code": "A"}]},
        {"span_start": 6, "span_end": 10, "severity": "critical", "evidence": [{"code": "B"}]},
    ])
    assert len(merged) == 1
    assert (merged[0]["span_start"], merged[0]["span_end"]) == (2, 10)
    assert merged[0]["severity"] == "critical"
    assert len(merged[0]["evidence"]) == 2


def test_adjudication_requires_exact_quote_after_restoring_mask_tokens():
    good = Adjudication(
        verdict="supported",
        fact_id="fact-1",
        quote="Hydration lasts [PHONE_1]",
        reason="The duration matches.",
    )
    assert verify_adjudication_quote(
        good,
        expected_fact_id="fact-1",
        fact_text="Hydration lasts 28 days",
        masked_value_map={"[PHONE_1]": "28 days"},
    )
    bad = good.model_copy(update={"quote": "Hydration lasts 30 days"})
    assert not verify_adjudication_quote(
        bad, expected_fact_id="fact-1", fact_text="Hydration lasts 28 days"
    )


def test_model_json_validation_retries_once_and_fails_visibly():
    class InvalidProvider:
        name = "test"
        model = "test-model"

        def __init__(self):
            self.calls = 0

        async def complete_json(self, **_kwargs):
            self.calls += 1
            return {"invalid": "shape"}

    provider = InvalidProvider()
    statuses = []

    async def record(status, attempt):
        statuses.append((status, attempt))

    async def run():
        try:
            await validated_json(
                provider,
                system_prompt="test",
                user_prompt="masked",
                output_model=ClaimExtraction,
                on_call=record,
            )
        except ModelStepFailed:
            return
        raise AssertionError("Invalid model output should fail after one retry.")

    asyncio.run(run())
    assert provider.calls == 2
    assert statuses == [
        ("started", 0), ("failed", 0), ("started", 1), ("failed", 1)
    ]
