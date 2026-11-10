import asyncio
from pathlib import Path
import pytest
from sqlalchemy import select
from app.core.config import settings
from app.models.entities import Workspace, User, LoginRateLimit
from app.services.demo_workspace import ensure_demo_workspace, set_demo_ready, is_demo_ready
from app.core.storage import LocalStorage


def test_ensure_demo_workspace_idempotency_and_no_duplicate_workspaces(test_database, tmp_path: Path):
    storage = LocalStorage(tmp_path / "uploads")

    # Run 1
    res1 = asyncio.run(
        ensure_demo_workspace(
            sessions=test_database,
            storage=storage,
            upload_dir=tmp_path / "uploads",
            demo_password="demo-test-pw-1234",
            skip_creatives=True,
        )
    )
    assert res1["demo_mode"] is True
    ws_id = res1["workspace_id"]

    # Verify workspace and users exist
    async def verify_run1():
        async with test_database() as session:
            ws_count = len((await session.scalars(select(Workspace))).all())
            assert ws_count == 1
            ws = await session.get(Workspace, ws_id)
            assert ws.settings.get("is_demo") is True

            users = (await session.scalars(select(User).where(User.workspace_id == ws_id))).all()
            emails = {u.email for u in users}
            assert "demo-admin@glowserum.com" in emails
            assert "creator@glowserum.com" in emails
            assert "reviewer@glowserum.com" in emails
            assert "manager@glowserum.com" in emails
            assert "creator@demo.local" in emails

    asyncio.run(verify_run1())

    # Run 2 on same database (idempotent - no duplicate workspaces or users)
    res2 = asyncio.run(
        ensure_demo_workspace(
            sessions=test_database,
            storage=storage,
            upload_dir=tmp_path / "uploads",
            demo_password="demo-test-pw-1234",
            skip_creatives=True,
        )
    )
    assert res2["workspace_id"] == ws_id

    async def verify_run2():
        async with test_database() as session:
            ws_count = len((await session.scalars(select(Workspace))).all())
            assert ws_count == 1
            users = (await session.scalars(select(User).where(User.workspace_id == ws_id))).all()
            assert len(users) == 7  # 4 @glowserum.com + 3 @demo.local

    asyncio.run(verify_run2())


def test_demo_reset_on_start_only_deletes_demo_workspace(test_database, tmp_path: Path):
    storage = LocalStorage(tmp_path / "uploads")

    # Create a non-demo workspace first
    async def create_normal_ws():
        async with test_database() as session:
            normal_ws = Workspace(name="Real Client Brand", settings={"is_demo": False})
            session.add(normal_ws)
            await session.commit()
            return normal_ws.id

    normal_ws_id = asyncio.run(create_normal_ws())

    # Ensure demo workspace
    res1 = asyncio.run(
        ensure_demo_workspace(
            sessions=test_database,
            storage=storage,
            upload_dir=tmp_path / "uploads",
            demo_password="demo-test-pw-1234",
            skip_creatives=True,
        )
    )
    demo_ws_id = res1["workspace_id"]
    assert demo_ws_id != normal_ws_id

    # Now run with reset_on_start=True
    res_reset = asyncio.run(
        ensure_demo_workspace(
            sessions=test_database,
            storage=storage,
            upload_dir=tmp_path / "uploads",
            demo_password="demo-test-pw-1234",
            skip_creatives=True,
            reset_on_start=True,
        )
    )

    async def verify_reset():
        async with test_database() as session:
            # Normal workspace must still exist!
            normal_ws = await session.get(Workspace, normal_ws_id)
            assert normal_ws is not None
            assert normal_ws.name == "Real Client Brand"

            # Demo workspace exists
            demo_ws = await session.get(Workspace, res_reset["workspace_id"])
            assert demo_ws is not None
            assert demo_ws.settings.get("is_demo") is True

    asyncio.run(verify_reset())


def test_demo_status_and_disabled_login(api_client, monkeypatch):
    monkeypatch.setattr(settings, "demo_login_enabled", False)
    set_demo_ready(False)

    # Status when disabled
    status_resp = api_client("GET", "/api/auth/demo-status")
    assert status_resp.status_code == 200
    assert status_resp.json() == {"enabled": False, "ready": False}

    # Demo login when disabled returns 404
    login_resp = api_client("POST", "/api/auth/demo-login", json={"role": "admin"})
    assert login_resp.status_code == 404


def test_demo_login_not_ready_returns_503(api_client, monkeypatch):
    monkeypatch.setattr(settings, "demo_login_enabled", True)
    set_demo_ready(False)

    login_resp = api_client("POST", "/api/auth/demo-login", json={"role": "admin"})
    assert login_resp.status_code == 503
    assert "Demo is preparing" in login_resp.json()["detail"]


def test_demo_login_roles_and_token(api_client, test_database, tmp_path: Path, monkeypatch):
    storage = LocalStorage(tmp_path / "uploads")
    asyncio.run(
        ensure_demo_workspace(
            sessions=test_database,
            storage=storage,
            upload_dir=tmp_path / "uploads",
            skip_creatives=True,
        )
    )

    monkeypatch.setattr(settings, "demo_login_enabled", True)
    set_demo_ready(True)

    # Check demo-status is ready
    status_resp = api_client("GET", "/api/auth/demo-status")
    assert status_resp.status_code == 200
    assert status_resp.json() == {"enabled": True, "ready": True}

    # Test login for each role, passing spoofed email to ensure it's ignored
    for role, expected_email in [
        ("admin", "demo-admin@glowserum.com"),
        ("creator", "creator@glowserum.com"),
        ("reviewer", "reviewer@glowserum.com"),
        ("manager", "manager@glowserum.com"),
    ]:
        resp = api_client(
            "POST",
            "/api/auth/demo-login",
            json={"role": role, "email": "attacker@outside.com", "password": "wrong"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["role"] == role
        assert data["user"]["email"] == expected_email

    # Invalid role returns 422
    invalid_resp = api_client("POST", "/api/auth/demo-login", json={"role": "superadmin"})
    assert invalid_resp.status_code == 422


def test_demo_auto_created_users_cannot_login_with_random_password(api_client, test_database, tmp_path: Path, monkeypatch):
    storage = LocalStorage(tmp_path / "uploads")
    # Provision without specifying demo_password -> gets long random secret
    asyncio.run(
        ensure_demo_workspace(
            sessions=test_database,
            storage=storage,
            upload_dir=tmp_path / "uploads",
            skip_creatives=True,
        )
    )

    # Try logging in via standard /auth/login with obvious passwords
    for pw in ["admin", "password", "12345678", "demo", "GlowSerum"]:
        resp = api_client(
            "POST",
            "/api/auth/login",
            json={"email": "demo-admin@glowserum.com", "password": pw},
        )
        assert resp.status_code == 401


def test_demo_login_rate_limiting(api_client, test_database, tmp_path: Path, monkeypatch):
    storage = LocalStorage(tmp_path / "uploads")
    asyncio.run(
        ensure_demo_workspace(
            sessions=test_database,
            storage=storage,
            upload_dir=tmp_path / "uploads",
            skip_creatives=True,
        )
    )

    monkeypatch.setattr(settings, "demo_login_enabled", True)
    monkeypatch.setattr(settings, "login_max_failures", 3)
    set_demo_ready(True)

    # First 3 attempts succeed
    for _ in range(3):
        r = api_client("POST", "/api/auth/demo-login", json={"role": "admin"})
        assert r.status_code == 200

    # 4th attempt is rate-limited
    r_blocked = api_client("POST", "/api/auth/demo-login", json={"role": "admin"})
    assert r_blocked.status_code == 429
    assert "Too many sign-in attempts" in r_blocked.json()["detail"]


def test_demo_login_never_issues_token_for_non_demo_workspace(
    api_client, test_database, monkeypatch
):
    from app.services.demo_workspace import get_demo_workspace_id

    # Register a regular (non-demo) workspace whose admin uses the same email configured as demo_admin_email
    reg_resp = api_client(
        "POST",
        "/api/auth/register-workspace",
        json={
            "workspace_name": "Real Customer Org",
            "full_name": "Customer Admin",
            "email": "real-owner@customer.example",
            "password": "StrongCustomerPassword!2026",
        },
    )
    assert reg_resp.status_code == 201, reg_resp.text
    real_ws_id = reg_resp.json()["user"]["workspace_id"]

    # Also test a non-demo workspace holding a demo email without is_demo=True
    async def create_non_demo_with_demo_email():
        async with test_database() as db:
            non_demo_ws = Workspace(
                name="Non-Demo Collision",
                settings={"is_demo": False},
            )
            db.add(non_demo_ws)
            await db.flush()
            db.add(
                User(
                    workspace_id=non_demo_ws.id,
                    email=settings.demo_admin_email,
                    full_name="Not Demo",
                    password_hash="x",
                    role="admin",
                    is_active=True,
                )
            )
            await db.commit()
            return await get_demo_workspace_id(db), non_demo_ws.id

    detected_demo_ws, non_demo_ws_id = asyncio.run(create_non_demo_with_demo_email())
    assert detected_demo_ws is None
    assert non_demo_ws_id != real_ws_id

    monkeypatch.setattr(settings, "demo_login_enabled", True)
    set_demo_ready(True)
    resp = api_client("POST", "/api/auth/demo-login", json={"role": "admin"})
    assert resp.status_code == 503
    assert "access_token" not in resp.json()

