import uuid
from pathlib import Path
from typing import Protocol
from urllib.parse import quote

import httpx

from .config import Settings


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


class VercelBlobStorage:
    """A private Vercel Blob store, for deployments on Vercel, whose functions have no lasting
    disk. Keys are blob pathnames, so the database holds the same kind of key either way; files
    are only ever read back through the API, never linked to directly."""

    API_URL = "https://vercel.com/api/blob/"
    API_VERSION = "13"

    def __init__(self, token: str, client: httpx.Client | None = None):
        # A read-write token is vercel_blob_rw_<store id>_<secret>.
        parts = token.split("_")
        if len(parts) < 5 or not parts[3]:
            raise ValueError("BLOB_READ_WRITE_TOKEN is not a Vercel Blob read-write token")
        self._store_id = parts[3]
        self._auth = {"authorization": f"Bearer {token}"}
        self._client = client or httpx.Client(timeout=30)

    def put(self, prefix: str, data: bytes, extension: str) -> str:
        key = f"{prefix}/{uuid.uuid4().hex}{extension}"
        response = self._client.put(
            self.API_URL,
            params={"pathname": key},
            content=data,
            headers={
                **self._auth,
                "x-api-version": self.API_VERSION,
                "x-vercel-blob-access": "private",
                "x-add-random-suffix": "0",
            },
        )
        response.raise_for_status()
        return key

    def get(self, key: str) -> bytes:
        url = f"https://{self._store_id}.private.blob.vercel-storage.com/{quote(key)}"
        response = self._client.get(url, headers=self._auth)
        response.raise_for_status()
        return response.content


def storage_from_settings(settings: Settings) -> Storage:
    if settings.blob_read_write_token:
        return VercelBlobStorage(settings.blob_read_write_token)
    return LocalStorage(settings.media_dir)
