import httpx

from scraplink.config import Settings
from scraplink.storage import VercelBlobStorage

TOKEN = "vercel_blob_rw_AbC123_secret"


def test_vercel_blob_round_trip():
    blobs: dict[str, bytes] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == f"Bearer {TOKEN}"
        if request.method == "PUT":
            assert request.headers["x-vercel-blob-access"] == "private"
            blobs[request.url.params["pathname"]] = request.content
            return httpx.Response(200, json={})
        assert request.url.host == "AbC123.private.blob.vercel-storage.com".lower()
        return httpx.Response(200, content=blobs[request.url.path.lstrip("/")])

    storage = VercelBlobStorage(TOKEN, httpx.Client(transport=httpx.MockTransport(handler)))
    key = storage.put("lots", b"photo", ".jpg")

    assert key.startswith("lots/") and key.endswith(".jpg")
    assert storage.get(key) == b"photo"


def test_hosted_postgres_urls_use_psycopg():
    settings = Settings(database_url="postgres://u:p@ep-x-pooler.neon.tech/db?sslmode=require")
    assert (
        settings.database_url == "postgresql+psycopg://u:p@ep-x-pooler.neon.tech/db?sslmode=require"
    )
