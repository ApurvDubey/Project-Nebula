"""Unit tests for the SSRF protections in app.ingestion.web.fetch_url_to_markdown:
private/loopback/reserved IP blocking, redirect blocking, response size cap,
and title sanitization."""

import socket

import httpx
import pytest

from app.ingestion.web import MAX_BYTES, fetch_url_to_markdown


def _fake_getaddrinfo(ip: str):
    """Build a socket.getaddrinfo-shaped return value resolving to `ip`."""

    def _impl(host, port):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))]

    return _impl


class _FakeResponse:
    def __init__(self, status_code=200, body=b"<html><head><title>Hi</title></head><body>text</body></html>"):
        self.status_code = status_code
        self._body = body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)

    async def aiter_bytes(self):
        yield self._body


class _FakeStreamCM:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, *exc):
        return False


class _FakeAsyncClient:
    def __init__(self, response):
        self._response = response

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def stream(self, method, url):
        return _FakeStreamCM(self._response)


def _patch_http(monkeypatch, response: _FakeResponse):
    monkeypatch.setattr(
        "app.ingestion.web.httpx.AsyncClient",
        lambda **kwargs: _FakeAsyncClient(response),
    )


@pytest.mark.parametrize(
    "blocked_ip",
    [
        "127.0.0.1",       # loopback
        "10.0.0.5",        # private
        "192.168.1.1",     # private
        "169.254.169.254", # link-local / cloud metadata
    ],
)
async def test_rejects_private_and_metadata_ips(monkeypatch, blocked_ip):
    monkeypatch.setattr("app.ingestion.web.socket.getaddrinfo", _fake_getaddrinfo(blocked_ip))
    with pytest.raises(ValueError, match="Blocked private/reserved IP|Invalid target host"):
        await fetch_url_to_markdown("http://internal.example.com/")


async def test_rejects_when_dns_resolution_fails(monkeypatch):
    def _raise(host, port):
        raise socket.gaierror("Name or service not known")

    monkeypatch.setattr("app.ingestion.web.socket.getaddrinfo", _raise)
    with pytest.raises(ValueError, match="Invalid target host"):
        await fetch_url_to_markdown("http://does-not-resolve.invalid/")


async def test_allows_public_ip_and_extracts_content(monkeypatch):
    monkeypatch.setattr("app.ingestion.web.socket.getaddrinfo", _fake_getaddrinfo("8.8.8.8"))
    _patch_http(monkeypatch, _FakeResponse())

    title, content = await fetch_url_to_markdown("https://example.com/")
    assert title == "Hi"
    assert "text" in content


async def test_rejects_redirect_responses(monkeypatch):
    monkeypatch.setattr("app.ingestion.web.socket.getaddrinfo", _fake_getaddrinfo("8.8.8.8"))
    _patch_http(monkeypatch, _FakeResponse(status_code=302))

    with pytest.raises(ValueError, match="Redirects are blocked"):
        await fetch_url_to_markdown("https://example.com/")


async def test_rejects_response_over_size_limit(monkeypatch):
    monkeypatch.setattr("app.ingestion.web.socket.getaddrinfo", _fake_getaddrinfo("8.8.8.8"))
    oversized_body = b"x" * (MAX_BYTES + 1)
    _patch_http(monkeypatch, _FakeResponse(body=oversized_body))

    with pytest.raises(ValueError, match="exceeds maximum size limit"):
        await fetch_url_to_markdown("https://example.com/")


async def test_title_sanitization_strips_symbols_and_truncates(monkeypatch):
    monkeypatch.setattr("app.ingestion.web.socket.getaddrinfo", _fake_getaddrinfo("8.8.8.8"))
    body = b"<html><head><title>Hello!!! <script>alert(1)</script> World</title></head><body>x</body></html>"
    _patch_http(monkeypatch, _FakeResponse(body=body))

    title, _ = await fetch_url_to_markdown("https://example.com/")
    assert "<" not in title
    assert "!" not in title


async def test_title_falls_back_to_untitled_when_symbols_only(monkeypatch):
    monkeypatch.setattr("app.ingestion.web.socket.getaddrinfo", _fake_getaddrinfo("8.8.8.8"))
    body = "<html><head><title>☃☃☃</title></head><body>x</body></html>".encode("utf-8")
    _patch_http(monkeypatch, _FakeResponse(body=body))

    title, _ = await fetch_url_to_markdown("https://example.com/")
    assert title == "Untitled Webpage"
