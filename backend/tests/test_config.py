from app.core.config import normalize_database_url


def test_normalize_neon_postgres_url_and_sslmode():
    value = "postgres://user:pass@host.example/db?sslmode=require&channel_binding=require"
    assert normalize_database_url(value) == (
        "postgresql+asyncpg://user:pass@host.example/db?ssl=require"
    )


def test_normalize_postgresql_url_without_query():
    assert normalize_database_url("postgresql://user:pass@host/db") == (
        "postgresql+asyncpg://user:pass@host/db"
    )


def test_leave_sqlite_url_unchanged():
    value = "sqlite+aiosqlite:///./brandcourt.db"
    assert normalize_database_url(value) == value


def test_documented_access_token_setting_is_within_supported_range():
    from pydantic import ValidationError
    from app.core.config import Settings

    assert Settings(_env_file=None, access_token_minutes=30).access_token_minutes == 30
    try:
        Settings(_env_file=None, access_token_minutes=720)
    except ValidationError:
        pass
    else:
        raise AssertionError("ACCESS_TOKEN_MINUTES above 60 must be rejected")
