import asyncio
import os
import sqlite3
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.engine import make_url
import pytest


def _run_alembic(backend, env, *args, check=True):
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=backend,
        env=env,
        check=check,
        capture_output=True,
        text=True,
    )


def test_alembic_upgrade_on_clean_sqlite_database(tmp_path):
    backend=Path(__file__).resolve().parents[1]
    db_path=tmp_path/'clean.db'
    env=os.environ.copy(); env['DATABASE_URL']=f'sqlite:///{db_path.as_posix()}'
    _run_alembic(backend, env, "upgrade", "0007_r2_r7_content_metadata")
    with sqlite3.connect(db_path) as connection:
        connection.execute("INSERT INTO workspaces (id, name, settings, created_at) VALUES ('w1', 'Workspace', '{}', '2026-01-01')")
        connection.execute("INSERT INTO users (id, workspace_id, email, full_name, password_hash, role, is_active, created_at) VALUES ('u1', 'w1', 'user@example.test', 'User', 'hash', 'admin', 1, '2026-01-01')")
        connection.execute("INSERT INTO rules (id, workspace_id, code, title, text, type, severity, channels, status, version, created_by, created_at, updated_at) VALUES ('r1', 'w1', 'R1', 'Rule', 'Text', 'claim', 'warning', '[]', 'active', 1, 'u1', '2026-01-01', '2026-01-01')")
        connection.execute("INSERT INTO content_items (id, workspace_id, title, channel, campaign, status, current_revision, created_by, created_at, updated_at) VALUES ('c1', 'w1', 'Content', 'website', '', 'draft', 1, 'u1', '2026-01-01', '2026-01-01')")
        connection.execute("INSERT INTO content_revisions (id, workspace_id, content_id, version, caption, created_by, created_at, ocr_text, ocr_status, locked_at, approved_by, approved_snapshot, alt_text, is_ai_media, detected_language, image_analysis) VALUES ('v1', 'w1', 'c1', 1, '', 'u1', '2026-01-01', '', 'not_run', NULL, NULL, NULL, '', 0, 'unknown', NULL)")
        connection.execute("INSERT INTO claim_findings (id, workspace_id, content_id, revision_id, claim_text, verdict, rationale, evidence, severity, analysis_method, state, layer, created_at) VALUES ('f1', 'w1', 'c1', 'v1', 'claim', 'unsupported', 'reason', '[]', 'warning', 'test', 'open', 'deterministic', '2026-01-01')")
        connection.commit()
    _run_alembic(backend, env, "upgrade", "head")
    with sqlite3.connect(db_path) as connection:
        tables={row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {'review_jobs','ai_calls','check_cache','reports','embeddings','rule_examples','notifications','refresh_tokens'} <= tables
        assert connection.execute("SELECT severity FROM rules WHERE id='r1'").fetchone()[0] == "major"
        assert connection.execute("SELECT severity FROM claim_findings WHERE id='f1'").fetchone()[0] == "major"
        assert connection.execute(
            "SELECT paid_gifted FROM content_revisions WHERE id='v1'"
        ).fetchone()[0] == 0
        revision_columns={row[1] for row in connection.execute('PRAGMA table_info(content_revisions)')}
        assert {'alt_text','is_ai_media','detected_language','image_analysis','locked_at','approved_snapshot','paid_gifted'} <= revision_columns
        finding_columns={row[1] for row in connection.execute('PRAGMA table_info(claim_findings)')}
        assert {'state','layer','span_start','span_end','region','suggested_fix','intent_check'} <= finding_columns
        assert {'team','display_name'} <= {
            row[1] for row in connection.execute('PRAGMA table_info(users)')
        }
        assert 'settings' in {
            row[1] for row in connection.execute('PRAGMA table_info(workspaces)')
        }
        assert {'parent_id','resolved'} <= {
            row[1] for row in connection.execute('PRAGMA table_info(review_comments)')
        }
        assert {'approved_by','approved_at','embedding','scope_type','scope_id','scope'} <= {
            row[1] for row in connection.execute('PRAGMA table_info(precedents)')
        }
        assert {'storage_key','json_summary','revision_id'} <= {
            row[1] for row in connection.execute('PRAGMA table_info(reports)')
        }
        assert 'storage_key' in {
            row[1] for row in connection.execute('PRAGMA table_info(assets)')
        }
        assert {'attempts','max_attempts','lease_owner','lease_expires_at','timeout_seconds','heartbeat_at'} <= {
            row[1] for row in connection.execute('PRAGMA table_info(review_jobs)')
        }
        rule_columns={row[1] for row in connection.execute('PRAGMA table_info(rules)')}
        fact_columns={row[1] for row in connection.execute('PRAGMA table_info(facts)')}
        assert {'severity','embedding'} <= rule_columns
        assert 'embedding' in fact_columns
        assert {'audit_events_no_update','audit_events_no_delete'} <= {
            row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='trigger'")
        }
        connection.execute("INSERT INTO audit_events (id, workspace_id, type, payload, created_at) VALUES ('a1', 'w1', 'test', '{}', '2026-01-01')")
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("UPDATE audit_events SET type='changed' WHERE id='a1'")
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            connection.execute("DELETE FROM audit_events WHERE id='a1'")
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0008_schema_freeze"

    downgrade = _run_alembic(
        backend,
        env,
        "downgrade",
        "0007_r2_r7_content_metadata",
        check=False,
    )
    assert downgrade.returncode != 0
    assert "intentionally irreversible" in downgrade.stderr
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0008_schema_freeze"
        assert connection.execute("SELECT severity FROM rules WHERE id='r1'").fetchone()[0] == "major"


def test_fresh_empty_sqlite_database_upgrades_to_head(tmp_path):
    backend = Path(__file__).resolve().parents[1]
    db_path = tmp_path / "empty-to-head.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    _run_alembic(backend, env, "upgrade", "head")

    with sqlite3.connect(db_path) as connection:
        assert connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()[0] == "0008_schema_freeze"
        revision_columns = {
            row[1]: row
            for row in connection.execute("PRAGMA table_info(content_revisions)")
        }
        assert "paid_gifted" in revision_columns
        assert revision_columns["paid_gifted"][3] == 1
        assert revision_columns["paid_gifted"][4] == "0"
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {"notifications", "refresh_tokens", "login_rate_limits"} <= tables


def test_existing_stamps_0001_through_0007_upgrade_without_losing_data(tmp_path):
    backend = Path(__file__).resolve().parents[1]
    revision_ids = (
        "0001_phase1",
        "0002_phase2_3",
        "0003_content_claim_court",
        "0004_image_workflow",
        "0005_intelligence_finish",
        "0006_jobs_snapshots_support",
        "0007_r2_r7_content_metadata",
    )

    for index, revision in enumerate(revision_ids):
        db_path = tmp_path / f"stamped-{revision}.db"
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
        _run_alembic(backend, env, "upgrade", revision)
        with sqlite3.connect(db_path) as connection:
            if revision == "0001_phase1":
                connection.execute(
                    "INSERT INTO app_metadata (key, value, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                    (f"sentinel-{index}", "preserve", "migration regression", "2026-01-01", "2026-01-01"),
                )
            else:
                connection.execute(
                    "INSERT INTO workspaces (id, name, settings, created_at) VALUES (?, ?, ?, ?)",
                    (f"workspace-{index}", f"Workspace {index}", "{}", "2026-01-01"),
                )
            connection.commit()
            if revision == "0007_r2_r7_content_metadata":
                for table, columns in {
                    "workspaces": ("settings",),
                    "users": ("team", "display_name"),
                    "rules": ("embedding",),
                    "facts": ("embedding",),
                    "assets": ("storage_key",),
                    "claim_findings": (
                        "layer",
                        "span_start",
                        "span_end",
                        "region",
                        "suggested_fix",
                        "intent_check",
                    ),
                    "review_comments": ("resolved",),
                    "precedents": ("embedding", "scope_type", "scope_id", "scope"),
                    "review_jobs": (
                        "attempts",
                        "max_attempts",
                        "lease_owner",
                        "lease_expires_at",
                        "timeout_seconds",
                        "heartbeat_at",
                    ),
                }.items():
                    existing = {
                        row[1]
                        for row in connection.execute(f"PRAGMA table_info({table})")
                    }
                    for column in columns:
                        if column in existing:
                            connection.execute(
                                f"ALTER TABLE {table} DROP COLUMN {column}"
                            )
                for table in ("notifications", "refresh_tokens", "login_rate_limits"):
                    if table in {
                        row[0]
                        for row in connection.execute(
                            "SELECT name FROM sqlite_master WHERE type='table'"
                        )
                    }:
                        connection.execute(f"DROP TABLE {table}")
                connection.commit()

        _run_alembic(backend, env, "upgrade", "head")
        with sqlite3.connect(db_path) as connection:
            assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "0008_schema_freeze"
            if revision == "0001_phase1":
                assert connection.execute(
                    "SELECT value FROM app_metadata WHERE key = ?",
                    (f"sentinel-{index}",),
                ).fetchone()[0] == "preserve"
            else:
                assert connection.execute(
                    "SELECT name FROM workspaces WHERE id = ?",
                    (f"workspace-{index}",),
                ).fetchone()[0] == f"Workspace {index}"


def test_legacy_sqlite_schema_at_revision_0005_upgrades_and_preserves_rows(tmp_path):
    backend = Path(__file__).resolve().parents[1]
    db_path = tmp_path / "legacy-0005.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
    _run_alembic(backend, env, "upgrade", "0005_intelligence_finish")

    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            "INSERT INTO workspaces (id, name, settings, created_at) VALUES ('legacy-w', 'Legacy workspace', '{}', '2026-01-01')"
        )
        connection.execute(
            "INSERT INTO users (id, workspace_id, email, full_name, password_hash, role, is_active, created_at) VALUES ('legacy-u', 'legacy-w', 'legacy@example.test', 'Legacy', 'hash', 'admin', 1, '2026-01-01')"
        )
        connection.execute(
            "INSERT INTO content_items (id, workspace_id, title, channel, campaign, status, current_revision, created_by, created_at, updated_at) VALUES ('legacy-c', 'legacy-w', 'Legacy content', 'website', '', 'draft', 1, 'legacy-u', '2026-01-01', '2026-01-01')"
        )
        connection.execute(
            "INSERT INTO content_revisions (id, workspace_id, content_id, version, caption, created_by, created_at, ocr_text, ocr_status, locked_at, approved_by, approved_snapshot, alt_text, is_ai_media, detected_language, image_analysis) VALUES ('legacy-r', 'legacy-w', 'legacy-c', 1, 'keep this caption', 'legacy-u', '2026-01-01', '', 'not_run', NULL, NULL, NULL, '', 0, 'unknown', NULL)"
        )
        connection.commit()
        connection.execute("""
            CREATE TABLE content_revisions_legacy (
                id VARCHAR(36) PRIMARY KEY,
                workspace_id VARCHAR(36) NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
                content_id VARCHAR(36) NOT NULL REFERENCES content_items(id) ON DELETE CASCADE,
                version INTEGER NOT NULL,
                caption TEXT NOT NULL,
                creative_filename VARCHAR(255),
                creative_storage_key VARCHAR(500),
                created_by VARCHAR(36) NOT NULL REFERENCES users(id),
                created_at DATETIME NOT NULL,
                ocr_text TEXT NOT NULL,
                ocr_status VARCHAR(30) NOT NULL
            )
        """)
        connection.execute("""
            INSERT INTO content_revisions_legacy
                (id, workspace_id, content_id, version, caption, creative_filename,
                 creative_storage_key, created_by, created_at, ocr_text, ocr_status)
            SELECT id, workspace_id, content_id, version, caption, creative_filename,
                   creative_storage_key, created_by, created_at, ocr_text, ocr_status
            FROM content_revisions
        """)
        connection.execute("DROP TABLE content_revisions")
        connection.execute("ALTER TABLE content_revisions_legacy RENAME TO content_revisions")
        connection.execute("ALTER TABLE workspaces DROP COLUMN settings")
        connection.commit()

    _run_alembic(backend, env, "upgrade", "head")
    with sqlite3.connect(db_path) as connection:
        columns = {
            row[1] for row in connection.execute("PRAGMA table_info(content_revisions)")
        }
        assert {"locked_at", "approved_by", "approved_snapshot", "alt_text", "paid_gifted"} <= columns
        assert connection.execute(
            "SELECT name FROM workspaces WHERE id='legacy-w'"
        ).fetchone()[0] == "Legacy workspace"
        assert connection.execute(
            "SELECT caption FROM content_revisions WHERE id='legacy-r'"
        ).fetchone()[0] == "keep this caption"
        assert connection.execute(
            "SELECT paid_gifted FROM content_revisions WHERE id='legacy-r'"
        ).fetchone()[0] == 0


@pytest.mark.skipif(not os.getenv("TEST_POSTGRES_URL"), reason="TEST_POSTGRES_URL is not configured")
def test_alembic_upgrade_on_clean_postgresql_database():
    import asyncpg

    backend = Path(__file__).resolve().parents[1]
    admin_url = make_url(os.environ["TEST_POSTGRES_URL"])
    database_name = f"brandcourt_migrate_{uuid.uuid4().hex[:12]}"
    admin_database_url = admin_url.set(database="postgres")
    target_url = admin_url.set(database=database_name)

    async def create_database():
        connection = await asyncpg.connect(
            host=admin_database_url.host,
            port=admin_database_url.port or 5432,
            user=admin_database_url.username,
            password=admin_database_url.password,
            database=admin_database_url.database,
        )
        try:
            await connection.execute(f'CREATE DATABASE "{database_name}"')
        finally:
            await connection.close()

    async def drop_database():
        connection = await asyncpg.connect(
            host=admin_database_url.host,
            port=admin_database_url.port or 5432,
            user=admin_database_url.username,
            password=admin_database_url.password,
            database=admin_database_url.database,
        )
        try:
            await connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = $1 AND pid <> pg_backend_pid()",
                database_name,
            )
            await connection.execute(f'DROP DATABASE IF EXISTS "{database_name}"')
        finally:
            await connection.close()

    async def verify_postgresql_schema():
        connection = await asyncpg.connect(
            host=target_url.host,
            port=target_url.port or 5432,
            user=target_url.username,
            password=target_url.password,
            database=database_name,
        )
        try:
            vector_extension = await connection.fetchval(
                "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"
            )
            vector_type = await connection.fetchval(
                """
                SELECT format_type(attribute.atttypid, attribute.atttypmod)
                FROM pg_attribute AS attribute
                JOIN pg_class AS relation ON relation.oid = attribute.attrelid
                WHERE relation.relname = 'rules' AND attribute.attname = 'embedding'
                """
            )
            fact_vector_type = await connection.fetchval(
                """
                SELECT format_type(attribute.atttypid, attribute.atttypmod)
                FROM pg_attribute AS attribute
                JOIN pg_class AS relation ON relation.oid = attribute.attrelid
                WHERE relation.relname = 'facts' AND attribute.attname = 'embedding'
                """
            )
            precedent_vector_type = await connection.fetchval(
                """
                SELECT format_type(attribute.atttypid, attribute.atttypmod)
                FROM pg_attribute AS attribute
                JOIN pg_class AS relation ON relation.oid = attribute.attrelid
                WHERE relation.relname = 'precedents' AND attribute.attname = 'embedding'
                """
            )
            paid_gifted_column = await connection.fetchrow(
                """
                SELECT column_default, is_nullable
                FROM information_schema.columns
                WHERE table_schema = current_schema()
                  AND table_name = 'content_revisions'
                  AND column_name = 'paid_gifted'
                """
            )
            alembic_revision = await connection.fetchval(
                "SELECT version_num FROM alembic_version"
            )
            trigger_count = await connection.fetchval(
                """
                SELECT COUNT(*)
                FROM pg_trigger AS trigger_info
                JOIN pg_class AS relation ON relation.oid = trigger_info.tgrelid
                WHERE relation.relname = 'audit_events'
                  AND trigger_info.tgname = 'audit_events_append_only'
                  AND NOT trigger_info.tgisinternal
                """
            )
            assert alembic_revision == "0008_schema_freeze"
            assert vector_extension is True
            assert vector_type.startswith("vector"), vector_type
            assert fact_vector_type.startswith("vector"), fact_vector_type
            assert precedent_vector_type.startswith("vector"), precedent_vector_type
            assert paid_gifted_column["column_default"] == "false"
            assert paid_gifted_column["is_nullable"] == "NO"
            assert trigger_count == 1

            workspace_id = str(uuid.uuid4())
            audit_event_id = str(uuid.uuid4())
            await connection.execute(
                """
                INSERT INTO workspaces (id, name, created_at)
                VALUES ($1, $2, $3)
                """,
                workspace_id,
                "PostgreSQL migration test",
                datetime.now(timezone.utc),
            )
            await connection.execute(
                """
                INSERT INTO audit_events
                    (id, workspace_id, actor_id, type, payload, created_at)
                VALUES ($1, $2, NULL, $3, '{}', $4)
                """,
                audit_event_id,
                workspace_id,
                "test.append_only",
                datetime.now(timezone.utc),
            )
            with pytest.raises(
                asyncpg.PostgresError, match="audit_events is append-only"
            ):
                await connection.execute(
                    "UPDATE audit_events SET type = 'test.changed' WHERE id = $1",
                    audit_event_id,
                )
            with pytest.raises(
                asyncpg.PostgresError, match="audit_events is append-only"
            ):
                await connection.execute(
                    "DELETE FROM audit_events WHERE id = $1",
                    audit_event_id,
                )
            assert await connection.fetchval(
                "SELECT type FROM audit_events WHERE id = $1", audit_event_id
            ) == "test.append_only"
        finally:
            await connection.close()

    asyncio.run(create_database())
    try:
        env = os.environ.copy()
        env["DATABASE_URL"] = target_url.render_as_string(hide_password=False)
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=backend,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        asyncio.run(verify_postgresql_schema())
    finally:
        asyncio.run(drop_database())
