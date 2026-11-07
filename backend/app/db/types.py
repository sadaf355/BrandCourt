from sqlalchemy import JSON
from sqlalchemy.types import TypeDecorator, UserDefinedType


class _PostgreSQLVector(UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **_kw) -> str:
        return "VECTOR"


class EmbeddingVector(TypeDecorator):
    """Use pgvector on PostgreSQL and a JSON array on local SQLite."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(_PostgreSQLVector())
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        vector = [float(component) for component in value]
        if dialect.name == "postgresql":
            return "[" + ",".join(repr(component) for component in vector) + "]"
        return vector

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            if isinstance(value, str):
                return [float(component) for component in value.strip("[]").split(",") if component]
            return [float(component) for component in value]
        return [float(component) for component in value]
