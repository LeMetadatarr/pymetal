"""Tests for `pymetal.http.Client` cache + URL handling — no network."""
from __future__ import annotations

import time

from pymetal.http import Client, Response


class _StubResp:
    def __init__(self, content: bytes, url: str = "", status_code: int = 200) -> None:
        self.content = content
        self.text = content.decode("utf-8", errors="replace")
        self.url = url
        self.status_code = status_code


class _RecordingSession:
    """curl_cffi.Session stand-in: records calls, replays canned responses."""

    def __init__(self, responses=None) -> None:
        self.calls = []
        self.responses = list(responses or [])

    def get(self, url, params=None, headers=None):
        self.calls.append((url, dict(params or {}), dict(headers or {})))
        if self.responses:
            return self.responses.pop(0)
        return _StubResp(b"<html>ok</html>", url=url)


def _client_with_session(session: _RecordingSession, **kwargs) -> Client:
    c = Client(**kwargs)
    c.session = session
    return c


def test_cache_hit_skips_network():
    session = _RecordingSession([_StubResp(b"hello", url="https://x/a")])
    c = _client_with_session(session)
    r1 = c.get("a")
    r2 = c.get("a")
    assert r1.text == r2.text == "hello"
    assert r2.from_cache is True
    assert len(session.calls) == 1  # second call served from cache


def test_cache_disabled_per_call():
    session = _RecordingSession(
        [_StubResp(b"v1", url="https://x/a"), _StubResp(b"v2", url="https://x/a")]
    )
    c = _client_with_session(session)
    c.get("a", use_cache=False)
    c.get("a", use_cache=False)
    assert len(session.calls) == 2  # never short-circuits


def test_cache_keyed_on_params():
    session = _RecordingSession(
        [_StubResp(b"first", url="x"), _StubResp(b"second", url="x")]
    )
    c = _client_with_session(session)
    a = c.get("a", params={"q": 1})
    b = c.get("a", params={"q": 2})
    assert a.text == "first"
    assert b.text == "second"
    assert len(session.calls) == 2  # different params -> distinct cache keys


def test_cache_skips_non_200():
    session = _RecordingSession(
        [_StubResp(b"err", url="x", status_code=500), _StubResp(b"err2", url="x", status_code=500)]
    )
    c = _client_with_session(session)
    c.get("a")
    c.get("a")
    assert len(session.calls) == 2  # 500s aren't cached


def test_cache_ttl_expiry():
    session = _RecordingSession(
        [_StubResp(b"v1", url="x"), _StubResp(b"v2", url="x")]
    )
    c = _client_with_session(session, cache_ttl=0.01)
    c.get("a")
    time.sleep(0.02)
    r2 = c.get("a")
    assert r2.text == "v2"
    assert len(session.calls) == 2


def test_cache_eviction_under_capacity():
    session = _RecordingSession([_StubResp(f"v{i}".encode(), url="x") for i in range(5)])
    c = _client_with_session(session, cache_size=2)
    for i in range(5):
        c.get(f"path{i}", use_cache=True)
    # All 5 should hit network (cache evicts as new entries arrive)
    assert len(session.calls) == 5


def test_response_url_uses_redirect_target():
    """Curl_cffi returns the final URL on redirect; Client must propagate it."""
    session = _RecordingSession([_StubResp(b"x", url="https://final/redirected")])
    c = _client_with_session(session)
    r = c.get("https://start/here")
    assert r.url == "https://final/redirected"


def test_get_json_decodes_text():
    import json

    session = _RecordingSession([_StubResp(json.dumps({"k": [1, 2]}).encode(), url="x")])
    c = _client_with_session(session)
    assert c.get_json("a") == {"k": [1, 2]}


def test_response_dataclass_round_trip():
    r = Response(b"x", "x", url="u", from_cache=True)
    assert r.text == "x"
    assert r.url == "u"
    assert r.from_cache is True
