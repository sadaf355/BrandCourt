import pytest
from datetime import datetime, timezone
from fastapi import HTTPException

from app.models.entities import (
    ContentItem,
    ContentRevision,
    ClaimFinding,
    FindingDecision,
    AICall,
)
from app.services.reports import build_report_data, generate_pdf_report
from app.api.insights import (
    get_insights_summary,
    download_report_json,
    download_report_pdf,
    get_model_settings,
    update_model_settings,
    ModelSettingsUpdate,
)


def run_sync(coro):
    try:
        res = coro.send(None)
        while True:
            res = coro.send(res)
    except StopIteration as e:
        return e.value


class Immediate:
    def __init__(self, value):
        self.value = value

    def __await__(self):
        yield self.value
        return self.value


class MockUser:
    def __init__(self, user_id: str, workspace_id: str, role: str):
        self.id = user_id
        self.workspace_id = workspace_id
        self.role = role
        self.full_name = f"Test {role.capitalize()}"


class MockScalars:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class MockDB:
    def __init__(self, scalar_returns=None, scalars_returns=None):
        self._scalar_queue = list(scalar_returns or [])
        self._scalars_queue = list(scalars_returns or [])
        self.added = []

    def add(self, obj):
        if hasattr(obj, "created_at") and getattr(obj, "created_at", None) is None:
            obj.created_at = datetime.now(timezone.utc)
        self.added.append(obj)

    def scalar(self, stmt):
        val = self._scalar_queue.pop(0) if self._scalar_queue else None
        return Immediate(val)

    def scalars(self, stmt):
        val = self._scalars_queue.pop(0) if self._scalars_queue else []
        return Immediate(MockScalars(val))

    def commit(self):
        return Immediate(None)


def test_report_fails_if_content_not_approved():
    item = ContentItem(
        id="c1",
        workspace_id="ws1",
        title="Draft Reel",
        channel="instagram",
        status="in_review",
        current_revision=1,
        created_by="u1",
    )
    db = MockDB(scalar_returns=[item])

    with pytest.raises(ValueError, match="approved, locked"):
        run_sync(build_report_data(db, "ws1", "c1"))


def test_report_succeeds_for_approved_locked_content_with_pdf():
    item = ContentItem(
        id="c-app",
        workspace_id="ws1",
        title="Approved Reel",
        channel="instagram",
        campaign="Summer Glow",
        status="approved",
        current_revision=1,
        created_by="u1",
    )
    rev = ContentRevision(
        id="r1",
        workspace_id="ws1",
        content_id="c-app",
        version=1,
        caption="100% natural saffron extract for radiant skin.",
        locked_at=datetime.now(timezone.utc),
        approved_by="u2",
        approved_snapshot={"snapshot_version": 1, "status": "approved"},
        created_by="u1",
    )
    finding = ClaimFinding(
        id="f1",
        workspace_id="ws1",
        content_id="c-app",
        revision_id="r1",
        claim_text="100% natural saffron",
        verdict="supported",
        severity="advisory",
        rationale="Verified with Fact FACT-015",
        evidence=[{"code": "FACT-015", "version": 1}],
        state="accepted",
    )
    decision = FindingDecision(
        id="d1",
        workspace_id="ws1",
        finding_id="f1",
        user_id="u2",
        action="accept",
        reason="Matches approved consumer study.",
        created_at=datetime.now(timezone.utc),
    )
    call = AICall(
        id="call-1",
        workspace_id="ws1",
        revision_id="r1",
        provider="deterministic",
        model="deterministic_v1",
        purpose="rules_and_claim_policy",
        input_chars=120,
        masked_entities=0,
        status="completed",
        duration_ms=15,
        started_at=datetime.now(timezone.utc),
    )

    db = MockDB(
        scalar_returns=[item, rev],
        scalars_returns=[[finding], [decision], [], [call]],
    )

    data = run_sync(build_report_data(db, "ws1", "c-app"))
    assert data["report_id"].startswith("RPT-C-APP-V1")
    assert data["content"]["status"] == "approved"
    assert data["approved_revision"]["version"] == 1
    assert len(data["findings"]) == 1
    assert data["masking_status"]["is_masked"] is True
    assert "governance_notice" in data

    # PDF generation test
    pdf_bytes = generate_pdf_report(data)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF-1.4")
    assert b"BRANDCOURT COMPLIANCE GOVERNANCE REPORT" in pdf_bytes
    assert b"%%EOF" in pdf_bytes


def test_insights_summary_counts():
    user = MockUser("u1", "ws1", "manager")
    db = MockDB(
        scalar_returns=[5, 3, 8],  # total_items, approved_items, total_findings
        scalars_returns=[
            ["critical", "major", "advisory"],  # findings severity
            ["override", "override", "dispute"],  # decisions
            [],  # expiring facts
            [],  # audit events
        ],
    )

    summary = run_sync(get_insights_summary(user, db))
    assert summary["total_items"] == 5
    assert summary["approved_items"] == 3
    assert summary["total_findings"] == 8
    assert summary["severity_distribution"]["critical"] == 1
    assert summary["overrides_total"] == 2
    assert summary["disputes_total"] == 1


def test_model_settings_admin_only():
    manager = MockUser("u1", "ws1", "manager")
    admin = MockUser("u2", "ws1", "admin")
    db = MockDB()

    body = ModelSettingsUpdate(local_model_enabled=True)

    # Manager forbidden
    with pytest.raises(HTTPException) as exc:
        run_sync(update_model_settings(body, manager, db))
    assert exc.value.status_code == 403

    # Admin allowed
    res = run_sync(update_model_settings(body, admin, db))
    assert res["local_model_enabled"] is True

