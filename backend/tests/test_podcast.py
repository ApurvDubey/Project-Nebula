"""Tests for the podcast router, focused on the path-traversal fix:
notebook_id must be a valid UUID before it's used to build any filesystem path.

Note on HTTP-level traversal payloads: httpx (and browsers, and most HTTP
clients/frameworks) normalize `../` dot-segments and decode `%2F` client-side
or during ASGI routing, so a literal `../../etc` never survives to reach the
FastAPI handler as a raw path-parameter value — it either gets collapsed
into a different URL entirely or fails to match the route (404) before our
code ever runs. That's a real, separate layer of protection, but it means
the precise way to test `_validate_uuid` itself is to call it directly.
"""

import uuid
from unittest.mock import AsyncMock

import pytest

from app.api.podcast import _validate_uuid
from fastapi import HTTPException


@pytest.fixture(autouse=True)
def _stub_generation(monkeypatch):
    """POST triggers a BackgroundTask which runs synchronously under
    ASGITransport. Stub it so tests don't hit a real LLM/TTS pipeline."""
    monkeypatch.setattr("app.api.podcast.generate_podcast_task", AsyncMock(return_value=None))


@pytest.mark.parametrize(
    "malicious_id",
    ["../../etc", "../../etc/passwd", "not-a-uuid", "'; DROP TABLE notebooks;--", ""],
)
def test_validate_uuid_rejects_non_uuid_values(malicious_id):
    with pytest.raises(HTTPException) as exc_info:
        _validate_uuid(malicious_id)
    assert exc_info.value.status_code == 400


def test_validate_uuid_accepts_a_real_uuid():
    _validate_uuid(str(uuid.uuid4()))  # should not raise


async def test_generate_podcast_rejects_non_uuid_notebook_id(client):
    resp = await client.post("/api/notebooks/not-a-uuid/podcast/")
    assert resp.status_code == 400


async def test_get_podcast_rejects_non_uuid_notebook_id(client):
    resp = await client.get("/api/notebooks/not-a-uuid/podcast/")
    assert resp.status_code == 400


async def test_generate_podcast_accepts_a_real_uuid(client, notebook_id):
    resp = await client.post(f"/api/notebooks/{notebook_id}/podcast/")
    assert resp.status_code == 200
    assert resp.json() == {"status": "processing"}


async def test_get_podcast_404_when_not_generated_yet(client, notebook_id):
    resp = await client.get(f"/api/notebooks/{notebook_id}/podcast/")
    assert resp.status_code == 404


async def test_get_podcast_returns_file_once_generated(client, tmp_data_dir):
    notebook_id = str(uuid.uuid4())
    podcast_dir = tmp_data_dir / "notebooks" / notebook_id / "podcast"
    podcast_dir.mkdir(parents=True)
    (podcast_dir / "podcast.mp3").write_bytes(b"fake-mp3-bytes")

    resp = await client.get(f"/api/notebooks/{notebook_id}/podcast/")
    assert resp.status_code == 200
    assert resp.content == b"fake-mp3-bytes"
    assert resp.headers["content-type"] == "audio/mpeg"
