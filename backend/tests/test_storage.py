from io import BytesIO

import pytest

from app.core.config import Settings
from app.core.storage import LocalStorage, S3CompatibleStorage


def test_local_storage_round_trips_bytes_and_materializes_file(tmp_path):
    storage = LocalStorage(tmp_path)

    key = storage.put_bytes("workspace-1/files/document.txt", b"evidence", "text/plain")

    assert key == "workspace-1/files/document.txt"
    assert storage.get_bytes(key) == b"evidence"
    with storage.materialize(key) as path:
        assert path.read_bytes() == b"evidence"


@pytest.mark.parametrize("key", ["../outside", "workspace/../../outside", r"C:\outside"])
def test_storage_rejects_traversal_keys(tmp_path, key):
    storage = LocalStorage(tmp_path)

    with pytest.raises(ValueError, match="relative paths"):
        storage.put_bytes(key, b"blocked", "text/plain")


def test_s3_compatible_storage_uses_object_key_and_content_type():
    class FakeS3:
        def __init__(self):
            self.objects = {}
            self.put_args = None

        def put_object(self, **kwargs):
            self.put_args = kwargs
            self.objects[(kwargs["Bucket"], kwargs["Key"])] = kwargs["Body"]

        def get_object(self, **kwargs):
            return {
                "Body": BytesIO(
                    self.objects[(kwargs["Bucket"], kwargs["Key"])]
                )
            }

    client = FakeS3()
    storage = S3CompatibleStorage("brandcourt-test", client=client)
    key = storage.put_bytes("workspace-1/report.json", b"{}", "application/json")

    assert key == "workspace-1/report.json"
    assert client.put_args["ContentType"] == "application/json"
    assert storage.get_bytes(key) == b"{}"
    with storage.materialize(key) as path:
        assert path.read_bytes() == b"{}"


def test_s3_storage_requires_bucket():
    with pytest.raises(ValueError, match="required"):
        Settings(storage_backend="s3")
