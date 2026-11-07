import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import select

from app.core.job_queue import enqueue_review_job
from app.core.job_worker import process_next_job
from app.models.entities import (
    BrandAsset,
    ContentItem,
    ContentRevision,
    Fact,
    ReviewJob,
    User,
)
from app.seed_glowserum import seed as seed_glowserum
from scripts.evaluate_api import labels_for, source_metrics
from app.services.image_intelligence import analyze_image
from scripts.score_eval import score as score_evaluation


GLOWSERUM_DATA = Path(__file__).resolve().parents[2] / "data" / "sample" / "glowserum_40_posts.jsonl"
PAID_GIFTED_DECLARATION_POST_IDS = {"GC-021", "GC-022", "GC-023", "GC-024", "GC-025"}


@pytest.mark.parametrize(
    ("caption", "fact", "expected_verdict"),
    [
        (
            "GlowSerum hydration lasts 7 days.",
            ("GlowSerum hydration duration", "4", "weeks", None),
            "contradicted",
        ),
        (
            "GlowSerum costs Rs 599.",
            ("GlowSerum price", "499", "INR", None),
            "contradicted",
        ),
        (
            "GlowSerum hydration lasts 4 weeks.",
            ("GlowSerum hydration duration", "4", "weeks", "2025-01-01T00:00:00+00:00"),
            "outdated",
        ),
        (
            "GlowSerum is India's #1 serum.",
            None,
            "unsupported",
        ),
        (
            "GlowSerum guarantees permanent results.",
            None,
            "unsupported",
        ),
        (
            "Enjoy a gentle daily ritual with GlowSerum.",
            None,
            None,
        ),
    ],
)
def test_golden_claims_run_through_durable_worker(
    caption, fact, expected_verdict, api_client, workspace_users,
    auth_headers, test_database,
):
    _users, content_id, workspace_ids = workspace_users

    async def prepare():
        async with test_database() as session:
            revision = await session.scalar(
                select(ContentRevision).where(
                    ContentRevision.content_id == content_id,
                    ContentRevision.workspace_id == workspace_ids[1],
                )
            )
            revision.caption = caption
            if fact:
                statement, value, unit, valid_to = fact
                session.add(
                    Fact(
                        workspace_id=workspace_ids[1],
                        code="GOLDEN-FACT",
                        statement=statement,
                        value=value,
                        unit=unit,
                        valid_to=datetime.fromisoformat(valid_to) if valid_to else None,
                        source_ref="Approved golden test source",
                        version=1,
                        status="active",
                        created_by=_users[(1, "creator")],
                    )
                )
            await session.commit()

    asyncio.run(prepare())
    queued = api_client(
        "POST",
        f"/api/content/{content_id}/analyze",
        headers=auth_headers(1, "creator"),
    )
    assert queued.status_code == 202
    job_id = queued.json()["job_id"]

    assert asyncio.run(
        process_next_job(test_database, worker_id="golden-worker")
    )

    async def load_result():
        async with test_database() as session:
            job = await session.get(ReviewJob, job_id)
            return job.status, job.result, job.error

    status, result, error = asyncio.run(load_result())
    assert status == "completed", error
    findings = result["findings"]
    verdicts = {finding["verdict"] for finding in findings}
    if expected_verdict is None:
        assert not findings
    else:
        assert expected_verdict in verdicts
    if expected_verdict == "unsupported":
        unsupported = next(f for f in findings if f["verdict"] == "unsupported")
        assert "not a finding that the claim is false" in unsupported["rationale"] or \
            "not a legal determination" in unsupported["rationale"]


def test_all_glowserum_seed_posts_run_through_durable_worker(
    workspace_users,
    test_database,
    tmp_path,
):
    """Run all sample rows with their explicit declaration metadata through the worker."""
    users, _content_id, workspace_ids = workspace_users
    upload_dir = tmp_path / "glowserum-uploads"
    posts = [
        json.loads(line)
        for line in GLOWSERUM_DATA.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(posts) == 52

    asyncio.run(
        seed_glowserum(
            "admin-1@example.com",
            sessions=test_database,
            upload_dir=upload_dir,
        )
    )

    async def prepare_and_enqueue():
        async with test_database() as session:
            user = await session.get(User, users[(1, "admin")])
            assert user is not None
            items = (
                await session.scalars(
                    select(ContentItem).where(
                        ContentItem.workspace_id == workspace_ids[1],
                        ContentItem.campaign == "GlowSerum fictional evaluation set",
                    )
                )
            ).all()
            items_by_title = {item.title: item for item in items}
            assert len(items_by_title) == len(posts)
            palette_asset = await session.scalar(
                select(BrandAsset).where(
                    BrandAsset.workspace_id == workspace_ids[1],
                    BrandAsset.kind == "palette",
                )
            )
            palette = palette_asset.data["colors"]
            job_ids = {}
            for post in posts:
                item = items_by_title[post["title"]]
                revision = await session.scalar(
                    select(ContentRevision).where(
                        ContentRevision.content_id == item.id,
                        ContentRevision.workspace_id == workspace_ids[1],
                    )
                )
                assert revision is not None
                assert revision.paid_gifted is (
                    post["id"] in PAID_GIFTED_DECLARATION_POST_IDS
                )
                if post["expected_findings"] == ["visual"]:
                    assert revision.creative_storage_key
                    image_path = upload_dir / revision.creative_storage_key
                    try:
                        image_result = analyze_image(image_path, palette)
                    except Exception as exc:
                        image_result = {
                            "overall_status": "needs_human_review",
                            "error": type(exc).__name__,
                            "message": "Image analysis failed; manual review is required.",
                            "ocr_boxes": [],
                            "palette_checks": [],
                            "contrast": {"status": "needs_human_review"},
                            "logo_check": {"status": "needs_human_review"},
                        }
                        revision.ocr_status = "failed"
                    else:
                        revision.ocr_status = (
                            "completed" if image_result.get("ocr_text") else "no_text_found"
                        )
                    revision.image_analysis = image_result
                job = await enqueue_review_job(session, user, item, revision)
                job_ids[post["id"]] = job.id
            await session.commit()
            return job_ids

    job_ids = asyncio.run(prepare_and_enqueue())

    async def drain_worker():
        for _ in posts:
            assert await process_next_job(test_database, worker_id="glowserum-acceptance")

    asyncio.run(drain_worker())

    async def load_results():
        async with test_database() as session:
            return {
                row.id: row
                for row in (
                    await session.scalars(
                        select(ReviewJob).where(
                            ReviewJob.id.in_(list(job_ids.values())),
                            ReviewJob.workspace_id == workspace_ids[1],
                        )
                    )
                ).all()
            }

    jobs = asyncio.run(load_results())
    assert len(jobs) == len(posts)
    expected_by_id = {post["id"]: set(post["expected_findings"]) for post in posts}
    measured_predictions = []
    for post_id, job_id in job_ids.items():
        job = jobs[job_id]
        assert job.status == "completed", job.error
        labels = set()
        for finding in (job.result or {}).get("findings", []):
            evidence = finding.get("evidence", [])
            codes = {str(entry.get("code", "")) for entry in evidence}
            types = {str(entry.get("type", "")) for entry in evidence}
            if "IN-2" in codes:
                labels.add("unsupported_superlative")
            if "IN-5" in codes:
                labels.add("restricted_health_claim")
            if "brand_term_list" in types:
                labels.add("banned_term")
            if "IN-4" in codes:
                labels.add("missing_disclosure")
            if finding.get("verdict") == "outdated":
                labels.add("expired_fact")
            if finding.get("verdict") == "contradicted":
                labels.add("wrong_number")
            if finding.get("analysis_method") == "image_intelligence_v1" or "visual_check" in types:
                labels.add("visual")

        expected = expected_by_id[post_id]
        assert labels == expected, f"{post_id}: expected {expected}, got {labels}"
        findings = (job.result or {}).get("findings", [])
        error_findings = [
            finding for finding in findings
            if finding.get("verdict") in {"unsupported", "contradicted", "outdated"}
        ]
        valid_source_errors = sum(
            any(
                evidence.get("type") in {"fact", "approved_fact", "active_rule"}
                and evidence.get("source_ref")
                for evidence in finding.get("evidence", [])
            )
            for finding in error_findings
        )
        elapsed_ms = (
            (job.finished_at - job.started_at).total_seconds() * 1000
            if job.finished_at and job.started_at else None
        )
        measured_predictions.append(
            {
                "id": post_id,
                "predicted_findings": sorted(labels),
                "error_findings": len(error_findings),
                "valid_source_error_findings": valid_source_errors,
                "needs_human_review_count": sum(
                    finding.get("verdict") == "needs_human_review"
                    for finding in findings
                ),
                "elapsed_ms": elapsed_ms,
            }
        )
        if post_id in PAID_GIFTED_DECLARATION_POST_IDS:
            disclosure = [
                finding
                for finding in job.result["findings"]
                if any(
                    entry.get("code") == "IN-4"
                    for entry in finding.get("evidence", [])
                )
            ]
            assert len(disclosure) == 1
            assert disclosure[0]["severity"] == "major"

    assert {
        post_id for post_id, expected in expected_by_id.items()
        if "missing_disclosure" in expected
    } == PAID_GIFTED_DECLARATION_POST_IDS
    print(
        "A4_GLOWSERUM_MEASURED="
        + json.dumps(score_evaluation(posts, measured_predictions), sort_keys=True)
    )

    async def enqueue_code_only():
        async with test_database() as session:
            user = await session.get(User, users[(1, "admin")])
            assert user is not None
            code_job_ids = {}
            for post in posts:
                full_job = await session.get(ReviewJob, job_ids[post["id"]])
                assert full_job is not None
                item = await session.get(ContentItem, full_job.content_id)
                revision = await session.get(ContentRevision, full_job.revision_id)
                assert item is not None and revision is not None
                job = await enqueue_review_job(session, user, item, revision)
                job.result = {"_evaluation_variant": "code_rules_only"}
                code_job_ids[post["id"]] = job.id
            await session.commit()
            return code_job_ids

    code_job_ids = asyncio.run(enqueue_code_only())

    async def drain_code_only():
        for _ in posts:
            assert await process_next_job(
                test_database, worker_id="glowserum-code-only"
            )

    asyncio.run(drain_code_only())

    async def load_code_only_results():
        async with test_database() as session:
            return {
                row.id: row
                for row in (
                    await session.scalars(
                        select(ReviewJob).where(
                            ReviewJob.id.in_(list(code_job_ids.values())),
                            ReviewJob.workspace_id == workspace_ids[1],
                        )
                    )
                ).all()
            }

    code_jobs = asyncio.run(load_code_only_results())
    dataset_sha256 = hashlib.sha256(GLOWSERUM_DATA.read_bytes()).hexdigest()
    code_only_predictions = []
    for post in posts:
        job = code_jobs[code_job_ids[post["id"]]]
        result = job.result or {}
        assert job.status == "completed", job.error
        assert result["evaluation_variant"] == "code_rules_only"
        metrics = source_metrics(result)
        elapsed_ms = (
            (job.finished_at - job.started_at).total_seconds() * 1000
            if job.finished_at and job.started_at else None
        )
        code_only_predictions.append({
            "id": post["id"],
            "variant": "code_rules_only",
            "dataset_sha256": dataset_sha256,
            "status": "completed",
            "predicted_findings": labels_for(result),
            "elapsed_ms": elapsed_ms,
            **metrics,
        })
    print(
        "A4_CODE_RULES_ONLY_MEASURED="
        + json.dumps(score_evaluation(posts, code_only_predictions), sort_keys=True)
    )


@pytest.mark.parametrize(
    "variant",
    ["code_rules_only", "retrieval_and_nli", "full_pipeline"],
)
def test_evaluation_variant_is_persisted_per_durable_job(
    variant,
    api_client,
    workspace_users,
    auth_headers,
    test_database,
):
    _users, content_id, _workspace_ids = workspace_users
    response = api_client(
        "POST",
        f"/api/content/{content_id}/analyze",
        params={"evaluation_variant": variant},
        headers=auth_headers(1, "admin"),
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    async def load_job():
        async with test_database() as session:
            return await session.get(ReviewJob, job_id)

    job = asyncio.run(load_job())
    assert job is not None
    assert job.result == {"_evaluation_variant": variant}

    if variant == "code_rules_only":
        assert asyncio.run(
            process_next_job(test_database, worker_id="evaluation-code-only")
        )

        async def load_completed():
            async with test_database() as session:
                return await session.get(ReviewJob, job_id)

        completed = asyncio.run(load_completed())
        assert completed.status == "completed", completed.error
        assert completed.result["evaluation_variant"] == variant


def test_only_workspace_admin_can_select_evaluation_variant(
    api_client,
    workspace_users,
    auth_headers,
):
    _users, content_id, _workspace_ids = workspace_users
    response = api_client(
        "POST",
        f"/api/content/{content_id}/analyze",
        params={"evaluation_variant": "code_rules_only"},
        headers=auth_headers(1, "creator"),
    )
    assert response.status_code == 403


def test_ollama_embedding_failure_falls_back_and_requires_human_review(
    api_client,
    workspace_users,
    auth_headers,
    test_database,
    monkeypatch,
):
    from app.models.entities import Workspace
    from app.services.model_provider import DisabledProvider

    _users, content_id, workspace_ids = workspace_users

    async def prepare_local_mode():
        async with test_database() as session:
            workspace = await session.get(Workspace, workspace_ids[1])
            revision = await session.scalar(
                select(ContentRevision).where(
                    ContentRevision.content_id == content_id,
                    ContentRevision.workspace_id == workspace_ids[1],
                )
            )
            workspace.settings = {"model_mode": "ollama", "secret_terms": []}
            revision.caption = "GlowSerum hydration lasts 10 days."
            await session.commit()

    asyncio.run(prepare_local_mode())

    class UnavailableEmbeddingProvider:
        name = "ollama"
        model = "test-embedding"

        async def embed(self, _texts):
            return {
                "status": "needs_human_review",
                "reason": "Ollama timeout",
            }

    monkeypatch.setattr(
        "app.api.content.embedding_provider_for",
        lambda *_args: UnavailableEmbeddingProvider(),
    )
    monkeypatch.setattr(
        "app.api.content.configured_provider",
        lambda *_args: DisabledProvider(),
    )
    queued = api_client(
        "POST",
        f"/api/content/{content_id}/analyze",
        headers=auth_headers(1, "admin"),
    )
    assert queued.status_code == 202
    job_id = queued.json()["job_id"]
    assert asyncio.run(
        process_next_job(test_database, worker_id="ollama-fallback-test")
    )

    async def load_job():
        async with test_database() as session:
            return await session.get(ReviewJob, job_id)

    job = asyncio.run(load_job())
    assert job.status == "completed", job.error
    findings = job.result["findings"]
    assert any(
        finding["verdict"] == "needs_human_review"
        and any(
            evidence.get("code") == "LOCAL-EMBEDDING-UNAVAILABLE"
            for evidence in finding.get("evidence", [])
        )
        for finding in findings
    )
