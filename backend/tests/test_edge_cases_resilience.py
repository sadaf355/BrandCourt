import asyncio
from datetime import datetime, timedelta, timezone
import jwt
import pytest
from app.core.config import settings
from app.core.job_worker import process_next_job
from app.models.entities import Precedent


def _register(api_client, email: str, org: str):
    resp = api_client(
        "POST",
        "/api/auth/register-workspace",
        json={
            "workspace_name": org,
            "full_name": "Edge Case Tester",
            "email": email,
            "password": "StrongEdgePassword!2026",
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_text_edge_cases_empty_20k_emoji_punctuation_and_multilingual(api_client, test_database):
    auth = _register(api_client, "edge-text@example.com", "Edge Text Org")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    cases = [
        ("Empty caption", ""),
        ("Long 20k caption", "GlowSerum daily hydration. " * 800),  # 20,000 chars
        ("Emoji only", "🎉🔥✨💧🌸"),
        ("Punctuation only", "!!! ??? --- ..."),
        ("Hindi", "ग्लोसीरम आपकी त्वचा को नमी देता है।"),
        ("Marathi", "GlowSerum मुळे त्वचा मऊ राहते."),
        ("Hinglish", "Yeh GlowSerum daily hydration ke liye best hai #ad"),
    ]

    for title, caption in cases:
        created = api_client(
            "POST",
            "/api/content",
            headers=headers,
            json={"title": title, "channel": "instagram", "campaign": "Edge", "caption": caption},
        )
        assert created.status_code == 201, f"{title}: {created.text}"
        cid = created.json()["id"]

        analyze = api_client("POST", f"/api/content/{cid}/analyze", headers=headers)
        assert analyze.status_code == 202, f"{title}: {analyze.text}"
        job_id = analyze.json()["job_id"]
        assert asyncio.run(process_next_job(sessions=test_database, worker_id="edge-worker")) is True

        job = api_client("GET", f"/api/jobs/{job_id}", headers=headers)
        assert job.status_code == 200
        assert job.json()["status"] == "completed", f"{title}: {job.json()}"


def test_bad_image_uploads_empty_corrupt_12mb_and_exe_renamed_png(api_client):
    auth = _register(api_client, "edge-img@example.com", "Edge Image Org")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    created = api_client(
        "POST",
        "/api/content",
        headers=headers,
        json={"title": "Bad Image Host", "channel": "instagram", "caption": "Daily hydration"},
    )
    assert created.status_code == 201
    cid = created.json()["id"]

    # Empty 0-byte image
    empty_resp = api_client(
        "POST",
        f"/api/content/{cid}/creative",
        headers=headers,
        files={"file": ("empty.png", b"", "image/png")},
    )
    assert empty_resp.status_code == 400

    # Corrupt image bytes
    corrupt_resp = api_client(
        "POST",
        f"/api/content/{cid}/creative",
        headers=headers,
        files={"file": ("corrupt.png", b"\x89PNG\r\n\x1a\nCORRUPTED_DATA", "image/png")},
    )
    assert corrupt_resp.status_code == 415

    # .exe renamed to .png (MZ header)
    exe_resp = api_client(
        "POST",
        f"/api/content/{cid}/creative",
        headers=headers,
        files={"file": ("malware.png", b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00", "image/png")},
    )
    assert exe_resp.status_code == 415

    # 12 MB image (> 10 MB limit)
    oversized_bytes = b"\x89PNG\r\n\x1a\n" + (b"\x00" * (12 * 1024 * 1024))
    oversized_resp = api_client(
        "POST",
        f"/api/content/{cid}/creative",
        headers=headers,
        files={"file": ("huge.png", oversized_bytes, "image/png")},
    )
    assert oversized_resp.status_code == 413


def test_missing_cross_workspace_and_invalid_tokens(api_client):
    ws1 = _register(api_client, "ws1-owner@example.com", "WS One")
    ws2 = _register(api_client, "ws2-owner@example.com", "WS Two")
    h1 = {"Authorization": f"Bearer {ws1['access_token']}"}
    h2 = {"Authorization": f"Bearer {ws2['access_token']}"}

    created = api_client(
        "POST",
        "/api/content",
        headers=h1,
        json={"title": "WS1 Private Draft", "channel": "instagram", "caption": "Private draft"},
    )
    assert created.status_code == 201
    cid = created.json()["id"]

    # Non-existent review -> 404
    assert api_client("GET", "/api/content/nonexistent-id-999", headers=h1).status_code == 404
    # Cross-workspace review -> 404
    assert api_client("GET", f"/api/content/{cid}", headers=h2).status_code == 404

    # Tampered token -> 401
    assert api_client("GET", "/api/me", headers={"Authorization": "Bearer tampered.jwt.token"}).status_code == 401

    # Expired token -> 401
    expired_token = jwt.encode(
        {
            "sub": ws1["user"]["id"],
            "ws": ws1["user"]["workspace_id"],
            "role": "admin",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=5),
        },
        settings.secret_key,
        algorithm="HS256",
    )
    assert api_client("GET", "/api/me", headers={"Authorization": f"Bearer {expired_token}"}).status_code == 401


def test_repeat_actions_are_safe_and_explicit(api_client, test_database):
    auth = _register(api_client, "repeat-owner@example.com", "Repeat Org")
    headers = {"Authorization": f"Bearer {auth['access_token']}"}

    # 1. Confirming a rule twice is safe (200)
    rule = api_client(
        "POST",
        "/api/rules",
        headers=headers,
        json={
            "code": "REP-RULE-1",
            "title": "Repeat rule test",
            "text": "Every headline must cite an active fact.",
            "severity": "advisory",
        },
    )
    assert rule.status_code == 201
    rid = rule.json()["id"]
    assert api_client("POST", f"/api/rules/{rid}/confirm", headers=headers).status_code == 200
    assert api_client("POST", f"/api/rules/{rid}/confirm", headers=headers).status_code == 200

    # 2. Approving an already approved content item -> clear 409
    created = api_client(
        "POST",
        "/api/content",
        headers=headers,
        json={"title": "Clean Approval", "channel": "instagram", "caption": "Gentle daily routine."},
    )
    cid = created.json()["id"]
    assert api_client("POST", f"/api/content/{cid}/workflow", headers=headers, json={"action": "submit"}).status_code == 200
    assert api_client("POST", f"/api/content/{cid}/workflow", headers=headers, json={"action": "start_review"}).status_code == 200
    assert api_client("POST", f"/api/content/{cid}/workflow", headers=headers, json={"action": "approve"}).status_code == 200
    second_approve = api_client("POST", f"/api/content/{cid}/workflow", headers=headers, json={"action": "approve"})
    assert second_approve.status_code == 409
    assert "already approved" in second_approve.json()["detail"].lower()

    # 3. Approving an already approved precedent twice -> clear 409
    async def insert_pending_precedent() -> str:
        async with test_database() as db:
            p = Precedent(
                workspace_id=auth["user"]["workspace_id"],
                finding_id="f-dummy",
                rule_id=rid,
                channel="instagram",
                pattern_text="Gentle daily routine.",
                reason="Test repeat approval.",
                status="pending",
                created_by=auth["user"]["id"],
            )
            db.add(p)
            await db.commit()
            return p.id

    pid = asyncio.run(insert_pending_precedent())
    assert api_client("POST", f"/api/precedents/{pid}/approve", headers=headers).status_code == 200
    second_prec = api_client("POST", f"/api/precedents/{pid}/approve", headers=headers)
    assert second_prec.status_code == 409
    assert "already approved" in second_prec.json()["detail"].lower()

