from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(value: str) -> str:
    """Normalize provider PostgreSQL URLs for SQLAlchemy's asyncpg driver.

    Neon commonly supplies ``postgres://`` or ``postgresql://`` URLs with
    ``sslmode=require``. The application uses SQLAlchemy asyncio, so the
    driver scheme must be ``postgresql+asyncpg`` and asyncpg expects ``ssl``.
    """
    raw = value.strip()
    if not raw:
        return raw
    parsed = urlsplit(raw)
    scheme = parsed.scheme.lower()
    if scheme in {"postgres", "postgresql"}:
        scheme = "postgresql+asyncpg"
    elif scheme != "postgresql+asyncpg":
        return raw

    query_items = parse_qsl(parsed.query, keep_blank_values=True)
    normalized_query: list[tuple[str, str]] = []
    for key, item in query_items:
        if key == "sslmode":
            normalized_query.append(("ssl", "require" if item in {"require", "verify-ca", "verify-full"} else item))
        elif key == "channel_binding":
            # libpq-only option; asyncpg negotiates channel binding itself.
            continue
        else:
            normalized_query.append((key, item))
    return urlunsplit((scheme, parsed.netloc, parsed.path, urlencode(normalized_query), parsed.fragment))


class Settings(BaseSettings):
    app_name: str = "BrandCourt API"
    app_env: str = "development"
    app_version: str = "2.0.0"
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    database_url: str = "sqlite+aiosqlite:///./brandcourt.db"
    secret_key: str = "CHANGE_ME_TO_A_LONG_RANDOM_SECRET_BEFORE_DEPLOYMENT"
    access_token_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_days: int = Field(default=30, ge=1, le=90)
    login_max_failures: int = Field(default=10, ge=1, le=100)
    login_window_minutes: int = Field(default=15, ge=1, le=1440)
    analyze_max_requests: int = Field(default=20, ge=1, le=1000)
    analyze_window_minutes: int = Field(default=10, ge=1, le=1440)
    ocr_confidence_threshold: float = Field(default=0.7, ge=0, le=1)
    upload_dir: str = "./uploads"
    storage_backend: str = "local"
    s3_bucket: str | None = None
    s3_endpoint_url: str | None = None
    s3_region: str | None = None
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    job_worker_enabled: bool = False
    job_poll_seconds: float = Field(default=2.0, gt=0, le=60)
    job_lease_seconds: int = Field(default=60, ge=10, le=3600)
    job_heartbeat_seconds: int = Field(default=15, ge=1, le=600)
    job_max_attempts: int = Field(default=3, ge=1, le=20)
    job_timeout_seconds: int = Field(default=900, ge=1, le=86400)
    demo_login_enabled: bool = False
    demo_admin_email: str = "demo-admin@glowserum.com"
    demo_reset_on_start: bool = False
    model_mode: str = "deterministic"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:3b"
    ollama_embedding_model: str = "nomic-embed-text"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore", case_sensitive=False)

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url_field(cls, value: str) -> str:
        return normalize_database_url(value)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        origins = []
        for raw in str(value).split(","):
            origin = raw.strip()
            if not origin:
                continue
            origin = origin.rstrip("/")
            parsed = urlsplit(origin)
            if (
                origin == "*"
                or parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or parsed.path
                or parsed.query
                or parsed.fragment
                or parsed.username
                or parsed.password
            ):
                raise ValueError("CORS origins must be explicit HTTP(S) origins without paths or credentials.")
            origins.append(origin)
        return ",".join(origins)

    @model_validator(mode="after")
    def validate_production_settings(self):
        if self.app_env.lower() == "production":
            if self.secret_key.startswith("CHANGE_ME") or len(self.secret_key.encode()) < 32:
                raise ValueError("Production requires a secret key of at least 32 bytes.")
            if not self.database_url.startswith("postgresql+asyncpg://"):
                raise ValueError("Production requires a PostgreSQL DATABASE_URL (Neon URLs are normalized automatically).")
            if self.storage_backend != "s3":
                raise ValueError("Production requires STORAGE_BACKEND=s3 so uploads survive container replacement.")
            if not self.allowed_origins or any("localhost" in origin or "127.0.0.1" in origin for origin in self.allowed_origins):
                raise ValueError("Production CORS_ORIGINS must contain the exact deployed frontend origin(s), not localhost.")
        return self

    @field_validator("storage_backend")
    @classmethod
    def validate_storage_backend(cls, value: str) -> str:
        backend = value.lower()
        if backend not in {"local", "s3"}:
            raise ValueError("STORAGE_BACKEND must be 'local' or 's3'.")
        return backend

    @model_validator(mode="after")
    def require_s3_bucket(self):
        if self.storage_backend == "s3" and not self.s3_bucket:
            raise ValueError("S3_BUCKET is required when STORAGE_BACKEND=s3.")
        if self.job_heartbeat_seconds >= self.job_lease_seconds:
            raise ValueError("JOB_HEARTBEAT_SECONDS must be less than JOB_LEASE_SECONDS.")
        return self

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
