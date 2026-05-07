"""Shared fixtures: a fake `Client` that serves captured HTML/JSON.

Lets endpoint tests run offline without monkey-patching the network.

Cassette-backed tests live under ``test/test_*_vcr.py`` and use
``cassette_client`` — a record/replay wrapper around the real
``pymetal.http.Client``. Cassettes are stored under
``test/cassettes/<module>/<test>/`` keyed by an MD5 of (method, url, params).

Re-record::

    PYMETAL_CASSETTE_MODE=once pytest test/test_*_vcr.py
    PYMETAL_CASSETTE_MODE=all  pytest test/test_*_vcr.py

(VCRpy proper does not intercept curl_cffi, which is why we roll our own.)
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "html"
CASSETTES = Path(__file__).parent / "cassettes"


class _FakeResponse:
    __slots__ = ("content", "text", "url", "from_cache")

    def __init__(self, content: bytes, url: str = "") -> None:
        self.content = content
        self.text = content.decode("utf-8", errors="replace")
        self.url = url
        self.from_cache = True


class FakeClient:
    """Routes path substrings to fixture files. First match wins."""

    def __init__(self, routes: Dict[str, str]) -> None:
        self.routes = routes

    def _resolve(self, path: str) -> bytes:
        for needle, fname in self.routes.items():
            if needle in path:
                return (FIXTURES / fname).read_bytes()
        raise AssertionError(f"no fixture mapped for path {path!r}")

    def get(self, path: str, params: Optional[dict] = None, use_cache: bool = True):
        return _FakeResponse(self._resolve(path), url=path)

    def get_json(self, path: str, params: Optional[dict] = None):
        return json.loads(self._resolve(path).decode("utf-8"))


@pytest.fixture
def fake_client():
    return FakeClient


# ---------------------------------------------------------------------------
# Cassette client: record/replay against metal-archives.com
# ---------------------------------------------------------------------------


class _CassetteResponse:
    __slots__ = ("content", "text", "url", "from_cache")

    def __init__(self, content: bytes, text: str, url: str) -> None:
        self.content = content
        self.text = text
        self.url = url
        self.from_cache = True


class CassetteClient:
    """Record/replay HTTP client mimicking ``pymetal.http.Client``.

    Modes (set via ``PYMETAL_CASSETTE_MODE`` env var):
      * ``none`` (default): replay only; missing cassette raises.
      * ``once``: replay if present, otherwise record.
      * ``all``:  always re-record (used by nightly-live workflow).
    """

    def __init__(self, cassette_dir: Path, mode: str = "none") -> None:
        self.dir = Path(cassette_dir)
        self.mode = mode
        self._real = None

    def _real_client(self):
        if self._real is None:
            from pymetal.http import Client
            self._real = Client()
        return self._real

    def _key(self, method: str, url: str, params: Optional[Mapping[str, Any]]) -> str:
        items = sorted((str(k), str(v)) for k, v in (params or {}).items())
        raw = f"{method}|{url}|{items}".encode("utf-8")
        return hashlib.md5(raw).hexdigest()[:16]

    def _slot(self, key: str) -> Path:
        self.dir.mkdir(parents=True, exist_ok=True)
        return self.dir / f"{key}.json"

    def _record(self, method: str, full_url: str, params, slot: Path):
        c = self._real_client()
        if method == "GET":
            r = c.get(full_url, params=params, use_cache=False)
            payload = {
                "method": method,
                "url": r.url,
                "request_url": full_url,
                "params": dict(params or {}),
                "text": r.text,
            }
        else:
            raise NotImplementedError(method)
        slot.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return payload

    def _load(self, slot: Path) -> dict:
        return json.loads(slot.read_text(encoding="utf-8"))

    def _full_url(self, path: str) -> str:
        from pymetal.locators import SITE_URL
        if path.startswith("http"):
            return path
        base = SITE_URL.rstrip("/") + "/"
        return base + path.lstrip("/")

    def get(self, path: str, params: Optional[Mapping[str, Any]] = None,
            use_cache: bool = True):
        full_url = self._full_url(path)
        key = self._key("GET", full_url, params)
        slot = self._slot(key)
        if self.mode == "all" or (self.mode == "once" and not slot.exists()):
            payload = self._record("GET", full_url, params, slot)
        else:
            if not slot.exists():
                raise AssertionError(
                    f"no cassette for GET {full_url} params={dict(params or {})} "
                    f"(expected {slot}). Re-record with PYMETAL_CASSETTE_MODE=once."
                )
            payload = self._load(slot)
        text = payload["text"]
        return _CassetteResponse(text.encode("utf-8"), text, payload["url"])

    def get_json(self, path: str, params: Optional[Mapping[str, Any]] = None):
        resp = self.get(path, params=params)
        return json.loads(resp.text)


@pytest.fixture
def cassette_client(request):
    mode = os.environ.get("PYMETAL_CASSETTE_MODE", "none")
    cdir = CASSETTES / Path(request.module.__file__).stem / request.node.name
    return CassetteClient(cdir, mode=mode)
