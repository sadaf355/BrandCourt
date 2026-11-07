from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from typing import ContextManager, Protocol

from app.core.config import settings


def _safe_key(key: str) -> PurePosixPath:
    normalized = key.replace("\\", "/")
    path = PurePosixPath(normalized)
    windows_absolute = len(normalized) >= 2 and normalized[1] == ":"
    if (
        not normalized
        or path.is_absolute()
        or windows_absolute
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise ValueError("Storage keys must be relative paths without traversal segments.")
    return path


class Storage(Protocol):
    def put_bytes(self, key: str, data: bytes, content_type: str) -> str: ...

    def get_bytes(self, key: str) -> bytes: ...

    def materialize(self, key: str) -> ContextManager[Path]: ...


class LocalStorage:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        destination = (self.root / Path(*_safe_key(key).parts)).resolve()
        try:
            destination.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("Storage key resolves outside the storage root.") from exc
        return destination

    def put_bytes(self, key: str, data: bytes, content_type: str) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return _safe_key(key).as_posix()

    def get_bytes(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    @contextmanager
    def materialize(self, key: str):
        yield self._path(key)


class S3CompatibleStorage:
    def __init__(
        self,
        bucket: str,
        endpoint_url: str | None = None,
        region: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
        client=None,
    ):
        if not bucket:
            raise ValueError("An S3 bucket is required.")
        if client is None:
            import boto3

            client = boto3.client(
                "s3",
                endpoint_url=endpoint_url,
                region_name=region,
                aws_access_key_id=access_key_id,
                aws_secret_access_key=secret_access_key,
            )
        self.bucket = bucket
        self.client = client

    def put_bytes(self, key: str, data: bytes, content_type: str) -> str:
        normalized_key = _safe_key(key).as_posix()
        self.client.put_object(
            Bucket=self.bucket,
            Key=normalized_key,
            Body=data,
            ContentType=content_type,
        )
        return normalized_key

    def get_bytes(self, key: str) -> bytes:
        response = self.client.get_object(
            Bucket=self.bucket,
            Key=_safe_key(key).as_posix(),
        )
        body = response["Body"]
        try:
            return body.read()
        finally:
            body.close()

    @contextmanager
    def materialize(self, key: str):
        suffix = Path(_safe_key(key).name).suffix
        with TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / f"stored-object{suffix}"
            path.write_bytes(self.get_bytes(key))
            yield path


def get_storage() -> Storage:
    if settings.storage_backend == "local":
        return LocalStorage(settings.upload_dir)
    return S3CompatibleStorage(
        bucket=settings.s3_bucket or "",
        endpoint_url=settings.s3_endpoint_url,
        region=settings.s3_region,
        access_key_id=settings.s3_access_key_id,
        secret_access_key=settings.s3_secret_access_key,
    )
