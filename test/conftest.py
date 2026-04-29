"""Shared fixtures: a fake `Client` that serves captured HTML/JSON.

Lets endpoint tests run offline without monkey-patching the network.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Optional

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "html"


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
