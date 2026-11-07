import asyncio
import base64
import hashlib
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from app.core.security import create_access_token, hash_password
from app.core.job_worker import process_next_job
from app.models.entities import ReviewJob, User


def _legacy_password_hash(password: str) -> str:
    salt = b"legacy-test-salt"
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    encoded_salt = base64.urlsafe_b64encode(salt).rstrip(b"=").decode()
    encoded_digest = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return f"pbkdf2_sha256${encoded_salt}${encoded_digest}"


def test_role_matrix_for_rule_creation(api_client, auth_headers):
    body = {
        "title": "Use clear evidence",
        "text": "Claims must be connected to an approved source.",
        "type": "claim",
        "severity": "major",
        "channels": [],
    }

    for role in ("creator", "reviewer", "manager"):
        response = api_client(
            "POST",
            "/api/rules",
            headers=auth_headers(1, role),
            json=body,
        )
        assert response.status_code == 403

    response = api_client(
        "POST",
        "/api/rules",
        headers=auth_headers(1, "admin"),
        json=body,
    )
    assert response.status_code == 201
    assert response.json()["status"] == "draft"
    assert response.json()["severity"] == "major"

    legacy_severity = api_client(
        "POST",
        "/api/rules",
        headers=auth_headers(1, "admin"),
        json={**body, "severity": "warning"},
    )
    assert legacy_severity.status_code == 422


def test_workspace_isolation_for_facts(api_client, auth_headers):
    for workspace_number in (1, 2):
        for role in ("creator", "reviewer", "manager", "admin"):
            response = api_client(
                "GET",
                "/api/facts",
                headers=auth_headers(workspace_number, role),
            )
            assert response.status_code == 200
            assert [fact["statement"] for fact in response.json()] == [
                f"Workspace {workspace_number} fact"
            ]


def test_workspace_two_roles_cannot_read_workspace_one_content(
    api_client, workspace_users, auth_headers
):
    _users, content_id, workspace_ids = workspace_users

    for role in ("creator", "reviewer", "manager", "admin"):
        response = api_client(
            "GET",
            f"/api/content/{content_id}",
            headers=auth_headers(2, role),
        )
        assert response.status_code == 404


def test_paid_gifted_declaration_is_revision_explicit_and_preserved(
    api_client, auth_headers
):
    created = api_client(
        "POST",
        "/api/content",
        headers=auth_headers(1, "creator"),
        json={
            "title": "Paid creator post",
            "channel": "website",
            "caption": "A calm product introduction.",
            "paid_gifted": True,
        },
    )
    assert created.status_code == 201
    content_id = created.json()["id"]
    first_revision = created.json()["revision"]
    assert first_revision["paid_gifted"] is True

    inherited = api_client(
        "POST",
        f"/api/content/{content_id}/revisions",
        headers=auth_headers(1, "creator"),
        json={"caption": "Updated copy without a declaration change."},
    )
    assert inherited.status_code == 201
    assert inherited.json()["revision"]["paid_gifted"] is True

    explicitly_cleared = api_client(
        "POST",
        f"/api/content/{content_id}/revisions",
        headers=auth_headers(1, "creator"),
        json={"paid_gifted": False},
    )
    assert explicitly_cleared.status_code == 201
    assert explicitly_cleared.json()["revision"]["paid_gifted"] is False

    explicitly_declared = api_client(
        "POST",
        f"/api/content/{content_id}/revisions",
        headers=auth_headers(1, "creator"),
        json={"paid_gifted": True},
    )
    assert explicitly_declared.status_code == 201
    assert explicitly_declared.json()["revision"]["paid_gifted"] is True

    revisions = api_client(
        "GET",
        f"/api/content/{content_id}/revisions",
        headers=auth_headers(1, "reviewer"),
    )
    assert revisions.status_code == 200
    assert [revision["paid_gifted"] for revision in revisions.json()] == [
        True,
        False,
        True,
        True,
    ]

    detail = api_client(
        "GET",
        f"/api/content/{content_id}",
        headers=auth_headers(1, "reviewer"),
    )
    assert detail.status_code == 200
    assert [revision["paid_gifted"] for revision in detail.json()["revisions"]] == [
        True,
        False,
        True,
        True,
    ]


def test_login_and_authenticated_me(api_client, workspace_users, auth_headers):
    login_response = api_client(
        "POST",
        "/api/auth/login",
        json={"email": "creator-1@example.com", "password": "test-password-123"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["token_type"] == "bearer"

    me_response = api_client(
        "GET",
        "/api/me",
        headers={"Authorization": f"Bearer {login_response.json()['access_token']}"},
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "creator-1@example.com"


def test_login_rehashes_legacy_pbkdf2_password(api_client, test_database, workspace_users):
    async def set_legacy_hash():
        async with test_database() as session:
            user = await session.scalar(
                select(User).where(User.email == "creator-1@example.com")
            )
            user.password_hash = _legacy_password_hash("safe-password-123")
            await session.commit()

    asyncio.run(set_legacy_hash())
    response = api_client(
        "POST",
        "/api/auth/login",
        json={"email": "creator-1@example.com", "password": "safe-password-123"},
    )
    assert response.status_code == 200

    async def read_hash():
        async with test_database() as session:
            user = await session.scalar(
                select(User).where(User.email == "creator-1@example.com")
            )
            return user.password_hash

    assert asyncio.run(read_hash()).startswith("$argon2id$")


def test_login_scopes_duplicate_email_to_requested_workspace(
    api_client, test_database, workspace_users
):
    users, _content_id, workspace_ids = workspace_users

    async def add_duplicate_email():
        async with test_database() as session:
            session.add(
                User(
                    workspace_id=workspace_ids[2],
                    email="creator-1@example.com",
                    full_name="Other Workspace User",
                    password_hash=hash_password("other-workspace-password"),
                    role="creator",
                )
            )
            await session.commit()

    asyncio.run(add_duplicate_email())

    response = api_client(
        "POST",
        "/api/auth/login",
        json={
            "email": "creator-1@example.com",
            "password": "other-workspace-password",
            "workspace_id": workspace_ids[2],
        },
    )
    assert response.status_code == 200
    assert response.json()["user"]["id"] != users[(1, "creator")]
    assert response.json()["user"]["workspace_id"] == workspace_ids[2]

    wrong_workspace = api_client(
        "POST",
        "/api/auth/login",
        json={
            "email": "creator-1@example.com",
            "password": "other-workspace-password",
            "workspace_id": workspace_ids[1],
        },
    )
    assert wrong_workspace.status_code == 401


def test_access_token_workspace_claim_must_match_user_workspace(
    api_client, workspace_users
):
    users, _content_id, workspace_ids = workspace_users
    mismatched_token = create_access_token(
        users[(1, "creator")],
        workspace_ids[2],
        "creator",
    )

    response = api_client(
        "GET",
        "/api/me",
        headers={"Authorization": f"Bearer {mismatched_token}"},
    )

    assert response.status_code == 401


def test_login_rate_limit_is_database_backed(api_client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "login_max_failures", 2)
    body = {"email": "missing@example.com", "password": "wrong-password"}

    assert api_client("POST", "/api/auth/login", json=body).status_code == 401
    assert api_client("POST", "/api/auth/login", json=body).status_code == 401
    response = api_client("POST", "/api/auth/login", json=body)

    assert response.status_code == 429
    assert response.headers["Retry-After"]


def test_refresh_rotates_and_logout_revokes_refresh_tokens(api_client, workspace_users):
    login = api_client(
        "POST",
        "/api/auth/login",
        json={"email": "creator-1@example.com", "password": "test-password-123"},
    ).json()
    old_refresh_token = login["refresh_token"]

    rotated = api_client(
        "POST",
        "/api/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )
    assert rotated.status_code == 200
    new_refresh_token = rotated.json()["refresh_token"]
    assert new_refresh_token != old_refresh_token

    logout = api_client(
        "POST",
        "/api/auth/logout",
        json={"refresh_token": new_refresh_token},
    )
    assert logout.status_code == 200
    assert logout.json() == {"revoked": True}
    replay = api_client(
        "POST",
        "/api/auth/refresh",
        json={"refresh_token": old_refresh_token},
    )
    assert replay.status_code == 401
    assert api_client(
        "POST",
        "/api/auth/refresh",
        json={"refresh_token": new_refresh_token},
    ).status_code == 401


def test_refresh_token_reuse_revokes_active_user_tokens(api_client, workspace_users):
    credentials = {
        "email": "creator-1@example.com",
        "password": "test-password-123",
    }
    original = api_client("POST", "/api/auth/login", json=credentials).json()
    separate_session = api_client("POST", "/api/auth/login", json=credentials).json()
    rotated = api_client(
        "POST",
        "/api/auth/refresh",
        json={"refresh_token": original["refresh_token"]},
    )
    assert rotated.status_code == 200

    replay = api_client(
        "POST",
        "/api/auth/refresh",
        json={"refresh_token": original["refresh_token"]},
    )
    assert replay.status_code == 401

    for token in (rotated.json()["refresh_token"], separate_session["refresh_token"]):
        response = api_client(
            "POST",
            "/api/auth/refresh",
            json={"refresh_token": token},
        )
        assert response.status_code == 401


def test_creative_upload_checks_file_content(api_client, workspace_users, auth_headers):
    _users, content_id, workspace_ids = workspace_users
    response = api_client(
        "POST",
        f"/api/content/{content_id}/creative",
        headers=auth_headers(1, "creator"),
        files={"file": ("creative.png", b"not a PNG image", "image/png")},
    )

    assert response.status_code == 415


def test_creative_upload_rejects_oversized_file_before_decoding(
    api_client, workspace_users, auth_headers
):
    _users, content_id, _workspace_ids = workspace_users
    response = api_client(
        "POST",
        f"/api/content/{content_id}/creative",
        headers=auth_headers(1, "creator"),
        files={"file": ("creative.png", b"x" * (10 * 1024 * 1024 + 1), "image/png")},
    )

    assert response.status_code == 413


def test_analysis_job_survives_api_process_exit_and_completes_in_worker_process(
    api_client, workspace_users, auth_headers, test_database
):
    _users, content_id, _workspace_ids = workspace_users
    response = api_client(
        "POST",
        f"/api/content/{content_id}/analyze",
        headers=auth_headers(1, "creator"),
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    async def queued_state():
        async with test_database() as session:
            return await session.scalar(
                select(ReviewJob.status).where(ReviewJob.id == job_id)
            )

    assert asyncio.run(queued_state()) == "queued"
    database_url = str(test_database.kw["bind"].url)
    worker_environment = os.environ.copy()
    worker_environment["DATABASE_URL"] = database_url
    subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import asyncio; from app.core.job_worker import process_next_job; "
                "asyncio.run(process_next_job(worker_id='restarted-worker'))"
            ),
        ],
        cwd=Path(__file__).resolve().parents[1],
        env=worker_environment,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )

    async def completed_state():
        async with test_database() as session:
            job = await session.get(ReviewJob, job_id)
            return job.status, job.attempts, job.result

    status, attempts, result = asyncio.run(completed_state())
    assert status == "completed"
    assert attempts == 1
    assert result["content_id"] == content_id


def test_analysis_job_retries_after_worker_failure(
    api_client, workspace_users, auth_headers, test_database
):
    _users, content_id, _workspace_ids = workspace_users
    response = api_client(
        "POST",
        f"/api/content/{content_id}/analyze",
        headers=auth_headers(1, "creator"),
    )
    job_id = response.json()["job_id"]

    async def failing_processor(_session, _job):
        raise RuntimeError("simulated failure")

    assert asyncio.run(
        process_next_job(
            test_database,
            worker_id="retry-worker",
            processor=failing_processor,
        )
    )

    async def state():
        async with test_database() as session:
            job = await session.get(ReviewJob, job_id)
            return job.status, job.attempts, job.error

    assert asyncio.run(state()) == (
        "queued",
        1,
        "Analysis attempt failed (RuntimeError).",
    )
    assert asyncio.run(
        process_next_job(
            test_database,
            worker_id="retry-worker",
            processor=lambda _session, _job: _completed_result(content_id),
        )
    )
    assert asyncio.run(state())[:2] == ("completed", 2)


async def _completed_result(content_id):
    return {"content_id": content_id}


def test_worker_recovers_an_expired_lease(
    api_client, workspace_users, auth_headers, test_database
):
    _users, content_id, _workspace_ids = workspace_users
    response = api_client(
        "POST",
        f"/api/content/{content_id}/analyze",
        headers=auth_headers(1, "creator"),
    )
    job_id = response.json()["job_id"]

    async def expire_lease():
        async with test_database() as session:
            job = await session.get(ReviewJob, job_id)
            job.status = "running"
            job.attempts = 1
            job.lease_owner = "dead-worker"
            job.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            await session.commit()

    asyncio.run(expire_lease())
    assert asyncio.run(
        process_next_job(
            test_database,
            worker_id="replacement-worker",
            processor=lambda _session, _job: _completed_result(content_id),
        )
    )

    async def recovered_state():
        async with test_database() as session:
            job = await session.get(ReviewJob, job_id)
            return job.status, job.attempts, job.lease_owner

    assert asyncio.run(recovered_state()) == ("completed", 2, None)


def test_worker_timeout_schedules_retry(
    api_client, workspace_users, auth_headers, test_database
):
    _users, content_id, _workspace_ids = workspace_users
    response = api_client(
        "POST",
        f"/api/content/{content_id}/analyze",
        headers=auth_headers(1, "creator"),
    )
    job_id = response.json()["job_id"]

    async def set_short_timeout():
        async with test_database() as session:
            job = await session.get(ReviewJob, job_id)
            job.timeout_seconds = 0.01
            await session.commit()

    async def processor(_session, _job):
        await asyncio.sleep(0.1)
        return {"content_id": content_id}

    asyncio.run(set_short_timeout())
    assert asyncio.run(
        process_next_job(
            test_database,
            worker_id="timeout-worker",
            processor=processor,
        )
    )

    async def state():
        async with test_database() as session:
            job = await session.get(ReviewJob, job_id)
            return job.status, job.attempts, job.error

    assert asyncio.run(state()) == ("queued", 1, "Analysis timed out.")


def test_analyze_endpoint_rate_limits_per_workspace_user(
    api_client, workspace_users, auth_headers, monkeypatch
):
    from app.core.config import settings

    _users, content_id, _workspace_ids = workspace_users
    monkeypatch.setattr(settings, "analyze_max_requests", 1)

    def analyze():
        return api_client(
            "POST",
            f"/api/content/{content_id}/analyze",
            headers=auth_headers(1, "creator"),
        )

    assert analyze().status_code == 202
    limited = analyze()
    assert limited.status_code == 429
    assert limited.headers["Retry-After"]


def test_guideline_upload_validates_content_and_uses_shared_storage(
    api_client, workspace_users, auth_headers, tmp_path, monkeypatch
):
    from pathlib import Path

    from app.core.config import settings

    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    invalid = api_client(
        "POST",
        "/api/guidelines",
        headers=auth_headers(1, "admin"),
        files={"file": ("guideline.pdf", b"not a PDF", "application/pdf")},
    )
    assert invalid.status_code == 415

    uploaded = api_client(
        "POST",
        "/api/guidelines",
        headers=auth_headers(1, "admin"),
        files={
            "file": (
                "guideline.txt",
                b"Claims must have traceable evidence.",
                "text/plain",
            )
        },
    )
    assert uploaded.status_code == 201
    files = list(Path(tmp_path).rglob("*.txt"))
    assert len(files) == 1
    assert files[0].read_bytes() == b"Claims must have traceable evidence."


def test_creative_upload_persists_through_shared_storage(
    api_client, workspace_users, auth_headers, test_database, tmp_path, monkeypatch
):
    import io
    from pathlib import Path

    from PIL import Image

    from app.core.config import settings
    from app.core.storage import LocalStorage
    from app.models.entities import ContentRevision

    _users, content_id, workspace_ids = workspace_users
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    storage = LocalStorage(tmp_path)
    monkeypatch.setattr("app.api.content.get_storage", lambda: storage)
    image = Image.new("RGB", (4, 4), color="blue")
    image_bytes = io.BytesIO()
    image.save(image_bytes, format="PNG")

    response = api_client(
        "POST",
        f"/api/content/{content_id}/creative",
        headers=auth_headers(1, "creator"),
        files={"file": ("creative.png", image_bytes.getvalue(), "image/png")},
    )
    assert response.status_code == 201

    async def get_upload_metadata():
        async with test_database() as session:
            revision = await session.scalar(
                select(ContentRevision).where(
                    ContentRevision.content_id == content_id
                )
            )
            return revision.creative_storage_key, revision.image_analysis["upload"]

    storage_key, upload = asyncio.run(get_upload_metadata())
    assert storage_key.startswith(f"{workspace_ids[1]}/creatives/")
    assert storage_key.endswith(".webp")
    assert Image.open(Path(tmp_path) / storage_key).format == "WEBP"
    assert storage.get_bytes(upload["original_storage_key"]) == image_bytes.getvalue()
    assert Image.open(Path(tmp_path) / upload["thumbnail_storage_key"]).size == (4, 4)


def test_logo_asset_requires_real_image_upload(
    api_client, workspace_users, auth_headers, tmp_path, monkeypatch
):
    from app.core.config import settings
    from app.core.storage import LocalStorage
    from PIL import Image
    import io

    _users, _content_id, workspace_ids = workspace_users
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    storage = LocalStorage(tmp_path)
    monkeypatch.setattr("app.api.knowledge.get_storage", lambda: storage)
    image = Image.new("RGB", (40, 20), "white")
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")

    response = api_client(
        "POST",
        "/api/assets/logo",
        headers=auth_headers(1, "admin"),
        data={"name": "Primary logo"},
        files={"file": ("logo.png", buffer.getvalue(), "image/png")},
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["storage_key"].startswith(f"{workspace_ids[1]}/brand-assets/")
    assert data["aspect_ratio"] == 2.0
    assert Image.open(io.BytesIO(storage.get_bytes(data["storage_key"]))).format == "WEBP"
    assert storage.get_bytes(data["original_storage_key"]) == buffer.getvalue()


def test_security_headers_are_added_to_api_responses(
    api_client, monkeypatch
):
    from app.core.config import settings

    monkeypatch.setattr(settings, "app_env", "production")
    response = api_client("GET", "/api/health")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Strict-Transport-Security"].startswith("max-age=")
