import pytest

from scripts.score_eval import render_evaluation, score


def test_api_label_mapping_distinguishes_health_claims_from_banned_terms():
    from scripts.evaluate_api import labels_for

    labels = labels_for(
        {
            "findings": [
                {
                    "verdict": "unsupported",
                    "analysis_method": "deterministic_v2",
                    "evidence": [
                        {"code": "IN-5", "type": "policy_pack"},
                        {"code": "BRAND-BANNED-TERM", "type": "brand_term_list"},
                    ],
                },
                {
                    "verdict": "needs_human_review",
                    "analysis_method": "image_heuristic",
                    "evidence": [{"code": "text_contrast", "type": "visual_check"}],
                },
            ]
        }
    )
    assert labels == ["banned_term", "restricted_health_claim", "visual"]


def test_scorer_reports_types_sources_false_flags_review_and_latency():
    gold = [
        {"id": "A", "title": "wrong number", "expected_findings": ["wrong_number"]},
        {"id": "B", "title": "clean", "expected_findings": []},
    ]
    predictions = [
        {
            "id": "A",
            "predicted_findings": ["wrong_number"],
            "elapsed_ms": 50,
            "error_findings": 1,
            "valid_source_error_findings": 1,
            "needs_human_review_count": 0,
        },
        {
            "id": "B",
            "predicted_findings": ["banned_term"],
            "elapsed_ms": 150,
            "error_findings": 0,
            "valid_source_error_findings": 0,
            "needs_human_review_count": 1,
        },
    ]
    result = score(gold, predictions)
    assert result["by_label"]["wrong_number"]["precision"] == 1
    assert result["by_label"]["banned_term"]["fp"] == 1
    assert result["false_flags"] == 1
    assert result["share_error_findings_with_valid_source"] == 1
    assert result["needs_human_review_count"] == 1
    assert result["median_check_time_ms"] == 100
    assert result["slowest_check_time_ms"] == 150
    assert result["wrong_cases"][0]["id"] == "B"


def test_report_requires_complete_results_for_three_variants():
    gold = [{"id": "A", "title": "case", "expected_findings": []}]
    dataset_hash = "a" * 64

    def predictions(variant):
        return [{
            "id": "A",
            "variant": variant,
            "dataset_sha256": dataset_hash,
            "status": "completed",
            "predicted_findings": [],
            "elapsed_ms": 10,
        }]

    with pytest.raises(ValueError, match="exactly all"):
        render_evaluation(
            gold,
            {
                "code_rules_only": predictions("code_rules_only"),
                "retrieval_and_nli": predictions("retrieval_and_nli"),
                "full_pipeline": [],
            },
        )


def test_scorer_counts_failed_cases_and_is_reproducible():
    gold = [
        {"id": "A", "title": "positive", "expected_findings": ["wrong_number"]},
        {"id": "B", "title": "clean", "expected_findings": []},
    ]
    predictions = [
        {
            "id": "A",
            "variant": "code_rules_only",
            "dataset_sha256": "b" * 64,
            "status": "completed",
            "predicted_findings": ["wrong_number"],
            "elapsed_ms": 12,
        },
        {
            "id": "B",
            "variant": "code_rules_only",
            "dataset_sha256": "b" * 64,
            "status": "failed",
            "failure": "worker failed",
            "predicted_findings": [],
            "elapsed_ms": None,
        },
    ]
    first = score(gold, predictions)
    second = score(gold, predictions)
    assert first == second
    assert first["micro_f1"] == 1
    assert first["exact_match_accuracy"] == 0.5
    assert first["false_negatives"] == 0
    assert first["failed_cases"] == 1
    assert first["failures"] == [{"id": "B", "failure": "worker failed"}]


def test_variant_report_rejects_mixed_datasets():
    gold = [{"id": "A", "title": "case", "expected_findings": []}]

    def predictions(variant, digest):
        return [{
            "id": "A",
            "variant": variant,
            "dataset_sha256": digest,
            "status": "completed",
            "predicted_findings": [],
        }]

    with pytest.raises(ValueError, match="same dataset SHA-256"):
        render_evaluation(gold, {
            "code_rules_only": predictions("code_rules_only", "a" * 64),
            "retrieval_and_nli": predictions("retrieval_and_nli", "a" * 64),
            "full_pipeline": predictions("full_pipeline", "b" * 64),
        })


def test_model_dependent_variant_preflight_blocks_without_results(monkeypatch, tmp_path, capsys):
    import asyncio
    from argparse import Namespace

    from scripts import evaluate_api

    async def unavailable(*_args):
        raise RuntimeError("Ollama is unreachable")

    monkeypatch.setattr(evaluate_api, "ollama_preflight", unavailable)
    output = tmp_path / "must-not-exist.jsonl"
    args = Namespace(
        variant="retrieval_and_nli",
        ollama_base_url="http://127.0.0.1:11434",
        ollama_model="missing-model",
        ollama_embedding_model="missing-embedding",
        out=str(output),
    )
    with pytest.raises(SystemExit) as exc:
        asyncio.run(evaluate_api.main(args))
    assert exc.value.code == 2
    assert "blocked" in capsys.readouterr().out
    assert not output.exists()
