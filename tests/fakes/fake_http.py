"""
tests/fakes/fake_http.py — Fake HTTP responses/session for testing
────────────────────────────────────────────────────────────────
Avoids any real network calls while exercising provider HTTP
error mapping, redirect handling, and download bounds checks.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FakeResponse:
    """Mimics the parts of requests.Response that providers use."""

    status_code: int = 200
    content: bytes = b""
    headers: dict = field(default_factory=dict)
    url: str = "https://example.com/img.png"
    history: list = field(default_factory=list)
    encoding: str = "utf-8"
    reason: str = "OK"

    def raise_for_status(self):
        if self.status_code >= 400:
            raise FakeHTTPError(self.status_code, self.reason, self.url)

    @property
    def text(self) -> str:
        try:
            return self.content.decode(self.encoding)
        except Exception:
            return ""

    def json(self):
        import json
        return json.loads(self.text)

    def iter_content(self, chunk_size: int = 8192):
        for i in range(0, max(len(self.content), 1), chunk_size):
            chunk = self.content[i : i + chunk_size]
            if chunk:
                yield chunk
        if not self.content:
            yield b""


class FakeHTTPError(Exception):
    def __init__(self, status_code: int, reason: str, url: str = ""):
        self.status_code = status_code
        self.reason = reason
        self.url = url
        super().__init__(f"HTTP {status_code} {reason} @ {url}")


class FakeSession:
    """
    Records every request and returns scripted responses.

    Usage::

        session = FakeSession()
        session.enqueue(FakeResponse(status_code=429, headers={"Retry-After": "1"}))
        session.enqueue(FakeResponse(status_code=200, content=b"ok"))
    """

    def __init__(self):
        self._queue: list[FakeResponse | Exception] = []
        self.requests: list[dict[str, Any]] = []
        self._default_response = FakeResponse(status_code=200, content=b"\x89PNG\r\n")

    def enqueue(self, response: FakeResponse | Exception):
        """Push the next response or exception to return."""
        self._queue.append(response)

    def enqueue_many(self, responses: list[FakeResponse | Exception]):
        self._queue.extend(responses)

    def _pop(self) -> FakeResponse:
        if self._queue:
            item = self._queue.pop(0)
            if isinstance(item, Exception):
                raise item
            return item
        return self._default_response

    def get(self, url, **kwargs) -> FakeResponse:
        self.requests.append({"method": "GET", "url": url, **kwargs})
        return self._pop()

    def post(self, url, **kwargs) -> FakeResponse:
        self.requests.append({"method": "POST", "url": url, **kwargs})
        return self._pop()

    def mount(self, prefix, adapter):
        pass  # no-op for fake

    def close(self):
        pass


def make_image_response(
    width: int = 64,
    height: int = 64,
    color: tuple = (255, 0, 0),
    fmt: str = "png",
) -> FakeResponse:
    """Generate a real PNG/JPEG image as a FakeResponse."""
    from io import BytesIO
    from PIL import Image

    img = Image.new("RGB", (width, height), color)
    buf = BytesIO()
    img.save(buf, format=fmt.upper())
    content_type = f"image/{fmt}"
    return FakeResponse(
        status_code=200,
        content=buf.getvalue(),
        headers={"Content-Type": content_type, "Content-Length": str(buf.tell())},
    )
