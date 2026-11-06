import pytest
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException
from app.models.entities import ContentItem, ContentRevision, ClaimFinding, FindingDecision, Fact
from app.api.workflow import change_workflow, decide_finding, StateInput, DecisionInput
from app.api.release import reviewer_queue
from app.api.notifications import list_notifications

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
    def __init__(self, user_id: str, workspace_id: str, role: str, email: str = 'user@brand.com'):
        self.id = user_id
        self.workspace_id = workspace_id
        self.role = role
        self.email = email
        self.full_name = f'Test {role}'

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
        if hasattr(obj, 'created_at') and getattr(obj, 'created_at', None) is None:
            obj.created_at = datetime.now(timezone.utc)
        if hasattr(obj, 'id') and getattr(obj, 'id', None) is None:
            obj.id = 'gen-id-1'
        self.added.append(obj)

    def scalar(self, *args, **kwargs):
        val = self._scalar_queue.pop(0) if self._scalar_queue else None
        return Immediate(val)

    def scalars(self, *args, **kwargs):
        val = self._scalars_queue.pop(0) if self._scalars_queue else []
        return Immediate(MockScalars(val))

    def commit(self):
        return Immediate(None)

    def flush(self):
        return Immediate(None)

    def refresh(self, obj):
        if hasattr(obj, 'created_at') and getattr(obj, 'created_at', None) is None:
            obj.created_at = datetime.now(timezone.utc)
        if hasattr(obj, 'id') and getattr(obj, 'id', None) is None:
            obj.id = 'gen-id-1'
        return Immediate(obj)

class DummyBackgroundTasks:
    def add_task(self, *args, **kwargs):
        pass

def test_reviewer_queue_creator_forbidden():
    creator = MockUser("usr-creator", "ws-1", "creator")
    db = MockDB()
    with pytest.raises(HTTPException) as exc:
        run_sync(reviewer_queue(user=creator, db=db))
    assert exc.value.status_code == 403
    assert "Your workspace role does not permit this action" in exc.value.detail

def test_reviewer_queue_priority_sorting():
    reviewer = MockUser("usr-reviewer", "ws-1", "reviewer")

    # Content 1: has critical finding (score 100)
    c1 = ContentItem(id="c1", workspace_id="ws-1", title="Critical Item", channel="instagram", campaign="Q1", status="submitted", current_revision=1, created_by="u1", updated_at=datetime.now(timezone.utc))
    r1 = ContentRevision(id="r1", workspace_id="ws-1", content_id="c1", version=1, caption="Text", detected_language="en")
    f1 = ClaimFinding(id="f1", workspace_id="ws-1", content_id="c1", revision_id="r1", claim_text="Claim 1", verdict="unsupported", severity="critical", rationale="R", state="open")

    # Content 2: has disputed finding (score 50)
    c2 = ContentItem(id="c2", workspace_id="ws-1", title="Disputed Item", channel="instagram", campaign="Q1", status="submitted", current_revision=1, created_by="u1", updated_at=datetime.now(timezone.utc))
    r2 = ContentRevision(id="r2", workspace_id="ws-1", content_id="c2", version=1, caption="Text", detected_language="en")
    f2 = ClaimFinding(id="f2", workspace_id="ws-1", content_id="c2", revision_id="r2", claim_text="Claim 2", verdict="supported", severity="major", rationale="R", state="disputed")

    db = MockDB(
        scalar_returns=[r2, r1],
        scalars_returns=[[c2, c1], [f2], [f1]],
    )

    res = run_sync(reviewer_queue(user=reviewer, db=db))
    assert res["total"] == 2
    # Critical item must come first due to priority_score (100 > 50)
    assert res["items"][0]["id"] == "c1"
    assert res["items"][0]["critical_count"] == 1
    assert res["items"][1]["id"] == "c2"
    assert res["items"][1]["disputed_count"] == 1

def test_override_requires_written_reason():
    reviewer = MockUser("usr-reviewer", "ws-1", "reviewer")
    db = MockDB()
    bg = DummyBackgroundTasks()

    with pytest.raises(HTTPException) as exc:
        run_sync(decide_finding("fnd-1", DecisionInput(action="override", reason="   "), bg, reviewer, db))
    assert exc.value.status_code == 422
    assert "reason is required when overriding" in exc.value.detail

def test_india_pack_override_requires_manager_or_admin():
    reviewer = MockUser("usr-reviewer", "ws-1", "reviewer")
    manager = MockUser("usr-manager", "ws-1", "manager")
    bg = DummyBackgroundTasks()

    finding = ClaimFinding(
        id="fnd-india",
        workspace_id="ws-1",
        content_id="cnt-1",
        revision_id="rev-1",
        claim_text="India's #1 cosmetic",
        verdict="unsupported",
        severity="critical",
        rationale="ASCI Rule 2",
        evidence=[{"type": "policy_pack", "code": "IN-2"}],
        state="open"
    )
    content = ContentItem(id="cnt-1", workspace_id="ws-1", title="Title", channel="instagram", campaign="Q1", status="submitted", current_revision=1, created_by="u1")

    # Reviewer attempt must fail with 403
    db_rev = MockDB(scalar_returns=[finding, None, content])
    with pytest.raises(HTTPException) as exc:
        run_sync(decide_finding("fnd-india", DecisionInput(action="override", reason="Approved exception"), bg, reviewer, db_rev))
    assert exc.value.status_code == 403
    assert "Your workspace role does not permit this action" in exc.value.detail

    # Manager attempt succeeds
    db_mgr = MockDB(scalar_returns=[finding, None, content])
    res = run_sync(decide_finding("fnd-india", DecisionInput(action="override", reason="Manager authorised with retail audit"), bg, manager, db_mgr))
    assert res["state"] == "overridden"
    assert res["action"] == "override"

def test_reject_requires_written_reason():
    manager = MockUser("usr-manager", "ws-1", "manager")
    content = ContentItem(id="cnt-1", workspace_id="ws-1", title="Title", channel="instagram", campaign="C", status="submitted", current_revision=1, created_by="u1")
    db = MockDB(scalar_returns=[content])

    with pytest.raises(HTTPException) as exc:
        run_sync(change_workflow("cnt-1", StateInput(action="reject", reason="  "), manager, db))
    assert exc.value.status_code == 422
    assert "rejection reason is required" in exc.value.detail

def test_approval_blocked_when_unresolved_blockers_exist():
    manager = MockUser("usr-manager", "ws-1", "manager")
    content = ContentItem(id="cnt-1", workspace_id="ws-1", title="Title", channel="instagram", campaign="C", status="in_review", current_revision=1, created_by="u1")
    revision = ContentRevision(id="rev-1", workspace_id="ws-1", content_id="cnt-1", version=1, caption="Text")
    finding = ClaimFinding(id="f1", workspace_id="ws-1", content_id="cnt-1", revision_id="rev-1", claim_text="Cures acne", verdict="contradicted", severity="critical", rationale="R", state="open")

    db = MockDB(
        scalar_returns=[content, revision, None],
        scalars_returns=[[finding]]
    )

    with pytest.raises(HTTPException) as exc:
        run_sync(change_workflow("cnt-1", StateInput(action="approve"), manager, db))
    assert exc.value.status_code == 409
    assert "Approval blocked" in str(exc.value.detail)

def test_approval_locks_revision_with_snapshot_and_reopen_creates_new():
    manager = MockUser("usr-manager", "ws-1", "manager")
    content = ContentItem(id="cnt-1", workspace_id="ws-1", title="Title", channel="instagram", campaign="C", status="in_review", current_revision=1, created_by="u1")
    revision = ContentRevision(id="rev-1", workspace_id="ws-1", content_id="cnt-1", version=1, caption="Text")

    # Approval with no blockers: get_item, revision, findings=[]
    db = MockDB(
        scalar_returns=[content, revision],
        scalars_returns=[[]]
    )

    res = run_sync(change_workflow("cnt-1", StateInput(action="approve"), manager, db))
    assert res["status"] == "approved"
    assert res["locked_revision_id"] == "rev-1"
    assert revision.locked_at is not None
    assert revision.approved_snapshot is not None

    # Reopening creates a new draft revision without overwriting rev-1
    content.status = "approved"
    db_reopen = MockDB(scalar_returns=[content, revision])

    reopen_res = run_sync(change_workflow("cnt-1", StateInput(action="reopen"), manager, db_reopen))
    assert reopen_res["status"] == "draft"
    assert content.current_revision == 2
    # rev-1 remains locked
    assert revision.version == 1
    assert revision.locked_at is not None

def test_notifications_computes_review_and_fact_expiry():
    manager = MockUser("usr-manager", "ws-1", "manager")

    item = ContentItem(id="c1", workspace_id="ws-1", title="Festive Video", channel="instagram", campaign="Festive", status="submitted", current_revision=1, created_by="u1", updated_at=datetime.now(timezone.utc))
    fact = Fact(id="f1", workspace_id="ws-1", code="FACT-01", statement="Lab trial claim", status="active", valid_to=datetime.now(timezone.utc) + timedelta(days=10), created_by="u1")

    db = MockDB(scalars_returns=[[item], [fact]])

    notifs = run_sync(list_notifications(user=manager, db=db))
    assert len(notifs) == 2
    types = {n.type for n in notifs}
    assert "review_assigned" in types
    assert "fact_expiring_soon" in types
