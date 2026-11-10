import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from sqlalchemy import select

from app.models.entities import Fact, Notification, Rule
from app.services.fixes import generate_minimal_fix, measure_intent
from app.services.guideline_health import (
    override_rate_issue,
    rule_pair_candidates,
    vague_rule_issue,
)
from app.services.precedents import (
    matching_approved_precedents,
    precedent_embedding,
    precedent_suggestion,
)


def test_guideline_health_embedding_candidates_and_vagueness():
    first = SimpleNamespace(
        id="rule-1",
        code="R1",
        title="Use a professional tone",
        text="Use a professional tone on each channel.",
        channels=["website"],
        embedding=None,
    )
    second = SimpleNamespace(
        id="rule-2",
        code="R2",
        title="Use a professional tone",
        text="Use a professional tone on each channel.",
        channels=["website"],
        embedding=None,
    )
    assert rule_pair_candidates([first, second])[0]["similarity"] == 1
    issue = vague_rule_issue(first, [])
    assert issue is not None
    assert issue["testable_condition"] is False
    assert issue["has_example"] is False
    assert override_rate_issue(first, 4, 4) is None
    assert override_rate_issue(first, 5, 3)["override_rate"] == 0.6


def test_precedent_matching_requires_approved_same_rule_and_channel():
    pattern = "GlowSerum hydration lasts 7 days"
    approved = SimpleNamespace(
        id="p-approved",
        rule_id="rule-1",
        channel="instagram",
        status="approved",
        valid_to=None,
        pattern_text=pattern,
        reason="This repeated wording is approved in context.",
        embedding=precedent_embedding(pattern),
    )
    pending = SimpleNamespace(**{**approved.__dict__, "id": "p-pending", "status": "pending"})
    other_rule = SimpleNamespace(**{**approved.__dict__, "id": "p-other", "rule_id": "rule-2"})
    matches = matching_approved_precedents(
        [approved, pending, other_rule],
        rule_id="rule-1",
        channel="instagram",
        pattern_text=pattern,
    )
    assert [row.id for _score, row in matches] == ["p-approved"]
    finding = SimpleNamespace(severity="critical")
    assert precedent_suggestion(finding, approved, 1)["suggested_severity"] is None
    finding.severity = "major"
    assert precedent_suggestion(finding, approved, 1)["suggested_severity"] == "advisory"


def test_minimal_fix_uses_fact_and_intent_threshold():
    fact = SimpleNamespace(
        id="fact-1",
        code="HYDRATION",
        statement="GlowSerum hydration duration",
        value="4",
        unit="weeks",
    )
    original = "GlowSerum hydration lasts 7 days. Shop now."
    suggestion = generate_minimal_fix(
        original, "GlowSerum hydration lasts 7 days.", [fact]
    )
    assert suggestion.source_fact_id == "fact-1"
    assert suggestion.candidate_text == "GlowSerum hydration lasts 4 weeks. Shop now."
    assert measure_intent(original, suggestion.candidate_text)["intent_preserved"] is True
    assert measure_intent(original, "")["intent_preserved"] is False


def test_local_model_provider_never_targets_a_hosted_endpoint(monkeypatch):
    import httpx

    from app.services.model_provider import OllamaProvider

    observed = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": '{"ok": true}'}}

    class FakeClient:
        def __init__(self, *, timeout):
            observed["timeout"] = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, json):
            observed["url"] = url
            observed["payload"] = json
            return FakeResponse()

    monkeypatch.setattr(httpx, "AsyncClient", FakeClient)
    provider = OllamaProvider("http://127.0.0.1:11434", "local-test-model")
    response = asyncio.run(
        provider.complete_json(
            system_prompt="Return JSON.",
            user_prompt="Private workspace text.",
            schema={"type": "object"},
        )
    )
    assert response == {"ok": True}
    assert observed["url"].startswith("http://127.0.0.1:11434/")
    assert "Private workspace text." in str(observed["payload"])


def test_evaluation_data_has_required_language_and_visual_cases():
    import json
    from pathlib import Path

    source = (
        Path(__file__).resolve().parents[2]
        / "data"
        / "sample"
        / "glowserum_40_posts.jsonl"
    )
    rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines()]
    assert len(rows) >= 40
    assert sum(not row["expected_findings"] for row in rows) >= 10
    assert {"hindi", "marathi", "hinglish"} <= {
        row.get("language") for row in rows
    }
    assert {
        "off_brand_color", "low_contrast", "missing_logo", "low_confidence_ocr"
    } <= {row.get("visual_case") for row in rows}
    assert any(not row["alt_text"] for row in rows)


def test_daily_fact_expiry_and_notifications_are_idempotent(
    test_database, workspace_users
):
    from scripts.expire_facts import process_fact_expiry

    users, _content_id, workspace_ids = workspace_users
    now = datetime(2026, 11, 7, tzinfo=timezone.utc)

    async def insert_facts():
        async with test_database() as db:
            for code, valid_to in (
                ("A4-EXPIRED", now - timedelta(days=1)),
                ("A4-SOON", now + timedelta(days=5)),
            ):
                db.add(
                    Fact(
                        workspace_id=workspace_ids[1],
                        code=code,
                        statement=f"{code} test fact",
                        value="1",
                        valid_to=valid_to,
                        source_ref="test",
                        version=1,
                        status="active",
                        created_by=users[(1, "admin")],
                    )
                )
            await db.commit()

    asyncio.run(insert_facts())
    first = asyncio.run(process_fact_expiry(test_database, now=now))
    second = asyncio.run(process_fact_expiry(test_database, now=now))
    assert first == {"facts_expired": 1, "notifications_created": 4}
    assert second == {"facts_expired": 0, "notifications_created": 0}

    async def check_rows():
        async with test_database() as db:
            rows = (
                await db.scalars(
                    select(Notification).where(
                        Notification.workspace_id == workspace_ids[1],
                        Notification.type.in_(("fact_expiring_soon", "fact_expired")),
                    )
                )
            ).all()
            expired = await db.scalar(
                select(Fact).where(
                    Fact.workspace_id == workspace_ids[1],
                    Fact.code == "A4-EXPIRED",
                )
            )
            return rows, expired

    notifications, expired_fact = asyncio.run(check_rows())
    assert len(notifications) == 4
    assert expired_fact.status == "expired"
    expired = [row for row in notifications if row.type == "fact_expired"]
    expiring = [row for row in notifications if row.type == "fact_expiring_soon"]
    assert len(expired) == len(expiring) == 2
    assert all(row.payload["fact_code"] == "A4-EXPIRED" for row in expired)
    assert all(row.payload["fact_code"] == "A4-SOON" for row in expiring)
    assert {row.user_id for row in notifications} == {
        users[(1, "admin")],
        users[(1, "manager")],
    }


def test_safe_replacements_for_cure_and_guaranteed_result_claims():
    cure = generate_minimal_fix(
        "Our serum cures acne. Shop now.", "cures acne", []
    )
    guarantee = generate_minimal_fix(
        "Guaranteed results in 7 days. Learn more.", "Guaranteed results", []
    )
    assert "cures acne" not in cure.candidate_text.lower()
    assert "may help improve the appearance" in cure.candidate_text.lower()
    assert "guaranteed results" not in guarantee.candidate_text.lower()
    assert "results may vary" in guarantee.candidate_text.lower()
