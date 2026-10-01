import uuid
from pathlib import Path
from typing import Protocol


class Storage(Protocol):
    def put(self, prefix: str, data: bytes, extension: str) -> str: ...

    def get(self, key: str) -> bytes: ...


class LocalStorage:
    """Filesystem storage for development and the pilot; S3 implements the same protocol."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError(f"storage key escapes root: {key}")
        return path

    def put(self, prefix: str, data: bytes, extension: str) -> str:
        key = f"{prefix}/{uuid.uuid4().hex}{extension}"
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()
