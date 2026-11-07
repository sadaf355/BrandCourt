import asyncio

from sqlalchemy import select

from app.models.entities import (
    AuditEvent,
    ClaimFinding,
    ContentRevision,
    Fact,
    FindingDecision,
    Rule,
    RuleExample,
    Workspace,
)


def test_guideline_review_decisions_and_admin_model_setting(
    api_client, workspace_users, auth_headers, test_database
):
    users, _content_id, workspace_ids = workspace_users

    async def create_rule():
        async with test_database() as db:
            rule = Rule(
                workspace_id=workspace_ids[1],
                code="A4-VAGUE",
                title="Use a professional quality tone",
                text="Use a professional tone where appropriate.",
                type="brand_voice",
                severity="major",
                channels=["website"],
                status="active",
                version=1,
                created_by=users[(1, "admin")],
            )
            db.add(rule)
            await db.flush()
            db.add(
                RuleExample(
                    rule_id=rule.id,
                    kind="positive",
                    text="Use short, direct sentences.",
                )
            )
            await db.commit()
            return rule.id

    rule_id = asyncio.run(create_rule())
    health = api_client(
        "GET", "/api/guideline-health", headers=auth_headers(1, "manager")
    )
    assert health.status_code == 200
    issue = next(row for row in health.json()["issues"] if row.get("rule_id") == rule_id)
    assert issue["type"] == "vague_rule"
    assert issue["has_example"] is True
    assert len(issue["issue_key"]) == 64

    async def has_embedding():
        async with test_database() as db:
            rule = await db.get(Rule, rule_id)
            return bool(rule.embedding)

    assert asyncio.run(has_embedding())

    denied = api_client(
        "PUT",
        "/api/workspace/model-mode",
        headers=auth_headers(1, "manager"),
        json={"mode": "ollama"},
    )
    assert denied.status_code == 403
    changed = api_client(
        "PUT",
        "/api/workspace/model-mode",
        headers=auth_headers(1, "admin"),
        json={"mode": "ollama"},
    )
    assert changed.status_code == 200
    assert changed.json() == {"model_mode": "ollama"}

    decision = api_client(
        "POST",
        "/api/guideline-health/decisions",
        headers=auth_headers(1, "admin"),
        json={
            "issue_key": issue["issue_key"],
            "action": "edit",
            "edited_wording": "Use sentences no longer than 20 words.",
        },
    )
    assert decision.status_code == 201
    assert decision.json()["rule_changed"] is False

    async def check_audit_and_settings():
        async with test_database() as db:
            workspace = await db.get(Workspace, workspace_ids[1])
            events = (
                await db.scalars(
                    select(AuditEvent).where(
                        AuditEvent.workspace_id == workspace_ids[1],
                        AuditEvent.type == "guideline_health.issue_decided",
                    )
                )
            ).all()
            return workspace.settings, events

    settings, events = asyncio.run(check_audit_and_settings())
    assert settings["model_mode"] == "ollama"
    assert len(events) == 1
    assert events[0].payload["action"] == "edit"


def test_precedent_requires_reasoned_override_and_reviewer_confirmation(
    api_client, workspace_users, auth_headers, test_database
):
    users, content_id, workspace_ids = workspace_users

    async def create_finding():
        async with test_database() as db:
            rule = Rule(
                workspace_id=workspace_ids[1],
                code="A4-STYLE",
                title="Approved style",
                text="Use approved terminology.",
                type="term",
                severity="major",
                channels=["website"],
                status="active",
                version=1,
                created_by=users[(1, "admin")],
            )
            db.add(rule)
            await db.flush()
            finding = ClaimFinding(
                workspace_id=workspace_ids[1],
                content_id=content_id,
                revision_id=(
                    await db.scalar(
                        select(ContentRevision.id).where(
                            ContentRevision.content_id == content_id,
                            ContentRevision.workspace_id == workspace_ids[1],
                        )
                    )
                ),
                claim_text="Use approved terminology in GlowSerum posts.",
                verdict="needs_human_review",
                rationale="test finding",
                evidence=[{"type": "active_rule", "rule_id": rule.id, "code": rule.code}],
                severity="major",
            )
            db.add(finding)
            await db.commit()
            return finding.id, rule.id

    finding_id, rule_id = asyncio.run(create_finding())
    no_override = api_client(
        "POST",
        "/api/precedents",
        headers=auth_headers(1, "reviewer"),
        json={
            "finding_id": finding_id,
            "rule_id": rule_id,
            "channel": "website",
            "pattern_text": "Use approved terminology in GlowSerum posts.",
            "reason": "The phrase is allowed in this context.",
        },
    )
    assert no_override.status_code == 409

    async def add_override():
        async with test_database() as db:
            db.add(
                FindingDecision(
                    workspace_id=workspace_ids[1],
                    finding_id=finding_id,
                    user_id=users[(1, "reviewer")],
                    action="override",
                    reason="The current item uses an approved trademark.",
                )
            )
            await db.commit()

    asyncio.run(add_override())
    created = api_client(
        "POST",
        "/api/precedents",
        headers=auth_headers(1, "reviewer"),
        json={
            "finding_id": finding_id,
            "rule_id": rule_id,
            "channel": "website",
            "pattern_text": "Use approved terminology in GlowSerum posts.",
            "reason": "The phrase is allowed in this context.",
        },
    )
    assert created.status_code == 201
    precedent_id = created.json()["id"]
    approved = api_client(
        "POST",
        f"/api/precedents/{precedent_id}/approve",
        headers=auth_headers(1, "manager"),
    )
    assert approved.status_code == 200
    suggestions = api_client(
        "GET",
        f"/api/findings/{finding_id}/precedent-suggestions",
        headers=auth_headers(1, "reviewer"),
    )
    assert suggestions.status_code == 200
    assert suggestions.json()["suggestions"][0]["suggested_severity"] == "advisory"
    confirmed = api_client(
        "POST",
        f"/api/findings/{finding_id}/precedent-suggestions/{precedent_id}/confirm",
        headers=auth_headers(1, "reviewer"),
    )
    assert confirmed.status_code == 200
    assert confirmed.json()["severity"] == "advisory"


def test_generated_fix_uses_fact_and_is_verified_by_full_engine(
    api_client, workspace_users, auth_headers, test_database
):
    users, content_id, workspace_ids = workspace_users
    caption = "GlowSerum hydration lasts 7 days. Shop now."

    async def setup():
        async with test_database() as db:
            revision = await db.scalar(
                select(ContentRevision).where(
                    ContentRevision.content_id == content_id,
                    ContentRevision.workspace_id == workspace_ids[1],
                )
            )
            revision.caption = caption
            db.add(
                Fact(
                    workspace_id=workspace_ids[1],
                    code="HYDRATION",
                    statement="GlowSerum hydration duration",
                    value="4",
                    unit="weeks",
                    source_ref="Approved product test",
                    version=1,
                    status="active",
                    created_by=users[(1, "admin")],
                )
            )
            finding = ClaimFinding(
                workspace_id=workspace_ids[1],
                content_id=content_id,
                revision_id=revision.id,
                claim_text="GlowSerum hydration lasts 7 days.",
                verdict="contradicted",
                rationale="Approved fact says four weeks.",
                evidence=[],
                severity="major",
            )
            db.add(finding)
            await db.commit()
            return finding.id

    finding_id = asyncio.run(setup())
    response = api_client(
        "POST",
        f"/api/findings/{finding_id}/suggest-fix",
        headers=auth_headers(1, "creator"),
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["source_fact_id"]
    assert result["verification"]["full_engine_rerun"] is True
    assert result["accepted"] is True
    assert result["suggested_fix"] == "GlowSerum hydration lasts 4 weeks. Shop now."

    async def check_finding():
        async with test_database() as db:
            return await db.get(ClaimFinding, finding_id)

    saved_finding = asyncio.run(check_finding())
    assert saved_finding.intent_check["embedding_similarity"] >= 0.8
    assert saved_finding.suggested_fix == result["suggested_fix"]


def test_fix_that_introduces_a_new_critical_finding_is_rejected(
    api_client, workspace_users, auth_headers, test_database
):
    _users, content_id, workspace_ids = workspace_users

    async def set_caption():
        async with test_database() as db:
            revision = await db.scalar(
                select(ContentRevision).where(
                    ContentRevision.content_id == content_id,
                    ContentRevision.workspace_id == workspace_ids[1],
                )
            )
            revision.caption = "A gentle GlowSerum routine. Shop now."
            await db.commit()

    asyncio.run(set_caption())
    response = api_client(
        "POST",
        f"/api/content/{content_id}/verify-fix",
        headers=auth_headers(1, "creator"),
        json={"proposed_text": "India's #1 serum. Shop now."},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["new_blocking_findings"]
    assert result["safe_to_suggest"] is False


def test_guideline_health_runs_bidirectional_local_nli_and_strict_rubric(
    api_client, workspace_users, auth_headers, test_database, monkeypatch
):
    from app.models.entities import AICall, Workspace

    users, _content_id, workspace_ids = workspace_users
    directions = []

    async def fake_nli(claim, evidence, _base_url, _model):
        directions.append((claim, evidence))
        return {"label": "contradicted", "reason": "opposing requirement", "status": "completed"}

    class LocalRubricProvider:
        name = "ollama"
        model = "local-rubric"

        async def complete_json(self, *, system_prompt, user_prompt, schema):
            assert "incompatibility" in system_prompt
            assert "RULE A" in user_prompt
            return {
                "contradiction": True,
                "conflicting_requirements": ["Always use the mark", "Never use the mark"],
                "rationale": "The two same-channel rules cannot both be followed.",
            }

    monkeypatch.setattr("app.api.intelligence.ollama_nli", fake_nli)
    monkeypatch.setattr(
        "app.api.intelligence.configured_provider",
        lambda *_args, **_kwargs: LocalRubricProvider(),
    )

    async def setup():
        async with test_database() as db:
            workspace = await db.get(Workspace, workspace_ids[1])
            workspace.settings = {"model_mode": "ollama", "secret_terms": []}
            for code, text in (
                ("A4-ALLOW", "Always use the GlowSerum mark in website captions."),
                ("A4-BLOCK", "Never use the GlowSerum mark in website captions."),
            ):
                db.add(
                    Rule(
                        workspace_id=workspace_ids[1],
                        code=code,
                        title=code,
                        text=text,
                        type="brand_voice",
                        severity="major",
                        channels=["website"],
                        status="active",
                        version=1,
                        created_by=users[(1, "admin")],
                    )
                )
            await db.commit()

    asyncio.run(setup())
    response = api_client(
        "GET", "/api/guideline-health", headers=auth_headers(1, "manager")
    )
    assert response.status_code == 200
    conflict = next(
        issue for issue in response.json()["issues"]
        if issue["type"] == "possible_conflict"
        and "A4-ALLOW" in issue["code"]
    )
    assert conflict["model_rubric"]["contradiction"] is True
    assert len(directions) == 2
    assert directions[0] == tuple(reversed(directions[1]))

    async def calls():
        async with test_database() as db:
            return (
                await db.scalars(
                    select(AICall).where(
                        AICall.workspace_id == workspace_ids[1],
                        AICall.purpose.in_(
                            ["guideline_nli", "guideline_conflict_rubric"]
                        ),
                    )
                )
            ).all()

    logged = asyncio.run(calls())
    assert len(logged) == 3
