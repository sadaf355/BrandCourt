"""Add the schema-freeze fields without rewriting released migrations."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = "0008_schema_freeze"
down_revision = "0007_r2_r7_content_metadata"
branch_labels = None
depends_on = None


class PostgreSQLVector(sa.types.UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **_kw):
        return "VECTOR"


def _column_type(bind):
    return PostgreSQLVector() if bind.dialect.name == "postgresql" else sa.JSON()


def _add_columns(table, columns):
    inspector = inspect(op.get_bind())
    if table not in inspector.get_table_names():
        raise RuntimeError(
            f"Cannot apply schema freeze: required table {table!r} is missing."
        )
    existing = {column["name"] for column in inspector.get_columns(table)}
    missing = [column for column in columns if column.name not in existing]
    if not missing:
        return
    with op.batch_alter_table(table) as batch:
        for column in missing:
            batch.add_column(column)


def _create_table_if_missing(name, *columns, indexes=()):
    inspector = inspect(op.get_bind())
    if name not in inspector.get_table_names():
        op.create_table(name, *columns)
        existing_indexes: set[str] = set()
    else:
        existing_indexes = {index["name"] for index in inspector.get_indexes(name)}
    for index_name, index_columns in indexes:
        if index_name not in existing_indexes:
            op.create_index(index_name, name, index_columns)


def _create_audit_triggers():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("""
            CREATE OR REPLACE FUNCTION brandcourt_reject_audit_event_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'audit_events is append-only';
            END;
            $$ LANGUAGE plpgsql
        """)
        op.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_trigger
                    WHERE tgname = 'audit_events_append_only'
                      AND tgrelid = 'audit_events'::regclass
                ) THEN
                    CREATE TRIGGER audit_events_append_only
                    BEFORE UPDATE OR DELETE ON audit_events
                    FOR EACH ROW EXECUTE FUNCTION brandcourt_reject_audit_event_mutation();
                END IF;
            END
            $$
        """)
    elif bind.dialect.name == "sqlite":
        triggers = {
            row[0]
            for row in bind.execute(
                text("SELECT name FROM sqlite_master WHERE type = 'trigger'")
            )
        }
        if "audit_events_no_update" not in triggers:
            op.execute("""
                CREATE TRIGGER audit_events_no_update
                BEFORE UPDATE ON audit_events
                BEGIN
                    SELECT RAISE(ABORT, 'audit_events is append-only');
                END
            """)
        if "audit_events_no_delete" not in triggers:
            op.execute("""
                CREATE TRIGGER audit_events_no_delete
                BEFORE DELETE ON audit_events
                BEGIN
                    SELECT RAISE(ABORT, 'audit_events is append-only');
                END
            """)


def upgrade() -> None:
    bind = op.get_bind()
    _add_columns(
        "workspaces",
        [
            sa.Column("settings", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        ],
    )
    _add_columns(
        "users",
        [
            sa.Column("team", sa.String(160), nullable=True),
            sa.Column("display_name", sa.String(160), nullable=True),
        ],
    )
    _add_columns("rules", [sa.Column("embedding", _column_type(bind), nullable=True)])
    _add_columns("facts", [sa.Column("embedding", _column_type(bind), nullable=True)])
    _add_columns(
        "assets",
        [sa.Column("storage_key", sa.String(500), nullable=True)],
    )
    _add_columns(
        "content_revisions",
        [
            sa.Column(
                "paid_gifted",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        ],
    )
    _add_columns(
        "claim_findings",
        [
            sa.Column("layer", sa.String(40), nullable=False, server_default="deterministic"),
            sa.Column("span_start", sa.Integer(), nullable=True),
            sa.Column("span_end", sa.Integer(), nullable=True),
            sa.Column("region", sa.JSON(), nullable=True),
            sa.Column("suggested_fix", sa.Text(), nullable=True),
            sa.Column("intent_check", sa.JSON(), nullable=True),
        ],
    )
    _add_columns(
        "review_comments",
        [
            sa.Column(
                "parent_id",
                sa.String(36),
                sa.ForeignKey(
                    "review_comments.id",
                    ondelete="CASCADE",
                    name="fk_review_comments_parent_id",
                ),
                nullable=True,
            ),
            sa.Column(
                "resolved",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        ],
    )
    _add_columns(
        "precedents",
        [
            sa.Column(
                "approved_by",
                sa.String(36),
                sa.ForeignKey("users.id", name="fk_precedents_approved_by_users"),
                nullable=True,
            ),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("embedding", _column_type(bind), nullable=True),
            sa.Column("scope_type", sa.String(40), nullable=False, server_default="workspace"),
            sa.Column("scope_id", sa.String(36), nullable=True),
            sa.Column("scope", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        ],
    )
    _add_columns(
        "review_jobs",
        [
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
            sa.Column("lease_owner", sa.String(160), nullable=True),
            sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="900"),
            sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        ],
    )

    _create_table_if_missing(
        "notifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("type", sa.String(80), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        indexes=(
            ("ix_notifications_workspace_id", ["workspace_id"]),
            ("ix_notifications_user_id", ["user_id"]),
        ),
    )
    _create_table_if_missing(
        "refresh_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "workspace_id",
            sa.String(36),
            sa.ForeignKey("workspaces.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "replaced_by",
            sa.String(36),
            sa.ForeignKey("refresh_tokens.id", name="fk_refresh_tokens_replaced_by"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        indexes=(
            ("ix_refresh_tokens_workspace_id", ["workspace_id"]),
            ("ix_refresh_tokens_user_id", ["user_id"]),
        ),
    )
    _create_table_if_missing(
        "login_rate_limits",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("failures", sa.Integer(), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
    )

    inspector = inspect(bind)
    if "rules" in inspector.get_table_names():
        rule_columns = {column["name"] for column in inspector.get_columns("rules")}
        if "severity" in rule_columns:
            op.execute("UPDATE rules SET severity = 'major' WHERE severity = 'warning'")
    if "claim_findings" in inspector.get_table_names():
        finding_columns = {
            column["name"] for column in inspector.get_columns("claim_findings")
        }
        if "severity" in finding_columns:
            op.execute(
                "UPDATE claim_findings SET severity = 'major' WHERE severity = 'warning'"
            )

    _create_audit_triggers()


def downgrade() -> None:
    raise RuntimeError(
        "Revision 0008 is intentionally irreversible: it normalizes persisted "
        "severity values and adds fields/tables that may contain production data. "
        "Do not downgrade; restore from a verified backup if rollback is required."
    )
