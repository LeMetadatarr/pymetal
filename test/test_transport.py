"""Tests for ``pymetal.transport.default_client`` and ``Client`` injection."""
from __future__ import annotations

import sys
import warnings

import pytest

from pymetal.http import Client
from pymetal import transport as _transport


class _StubSession:
    def __init__(self) -> None:
        self.calls = []

    def get(self, url, params=None, headers=None):
        self.calls.append(url)

        class _R:
            content = b"<html>ok</html>"
            text = "<html>ok</html>"
            status_code = 200

            def __init__(self, u):
                self.url = u

        return _R(url)


def test_client_accepts_injected_session_no_curl_cffi_needed():
    """Constructing Client with session=... must not import curl_cffi."""
    sess = _StubSession()
    c = Client(session=sess)
    assert c.session is sess
    r = c.get("foo")
    assert r.text == "<html>ok</html>"
    assert sess.calls and sess.calls[0].endswith("/foo")


def test_default_client_requests_path_emits_warning(monkeypatch):
    """Without env-var set: plain requests + RuntimeWarning."""
    monkeypatch.delenv("PYMETAL_TRANSPORT", raising=False)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        client = _transport.default_client()
    assert isinstance(client, Client)
    msgs = [str(x.message) for x in w if issubclass(x.category, RuntimeWarning)]
    assert any("plain `requests`" in m for m in msgs)
    # The session is a requests.Session, not curl_cffi.
    import requests as _requests
    assert isinstance(client.session, _requests.Session)


def test_default_client_env_var_requests_explicit(monkeypatch):
    """PYMETAL_TRANSPORT=requests: same as unset — plain requests + warning."""
    monkeypatch.setenv("PYMETAL_TRANSPORT", "requests")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        client = _transport.default_client()
    msgs = [str(x.message) for x in w if issubclass(x.category, RuntimeWarning)]
    assert any("plain `requests`" in m for m in msgs)
    import requests as _requests
    assert isinstance(client.session, _requests.Session)


def test_default_client_env_var_curl_cffi_when_available(monkeypatch):
    """PYMETAL_TRANSPORT=curl_cffi: returns curl_cffi-backed Client."""
    pytest.importorskip("curl_cffi")
    monkeypatch.setenv("PYMETAL_TRANSPORT", "curl_cffi")
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        client = _transport.default_client()
    # No "plain requests" warning when curl_cffi is in use.
    plain = [
        x for x in w
        if issubclass(x.category, RuntimeWarning) and "plain `requests`" in str(x.message)
    ]
    assert not plain
    from curl_cffi import requests as _curl_requests
    assert isinstance(client.session, _curl_requests.Session)


def test_default_client_env_var_curl_cffi_missing_falls_back(monkeypatch):
    """PYMETAL_TRANSPORT=curl_cffi but module unavailable → warn + requests."""
    monkeypatch.setenv("PYMETAL_TRANSPORT", "curl_cffi")
    monkeypatch.setattr(_transport, "_curl_cffi_available", lambda: False)
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        client = _transport.default_client()
    msgs = [str(x.message) for x in w if issubclass(x.category, RuntimeWarning)]
    assert any("curl_cffi was requested" in m for m in msgs)
    import requests as _requests
    assert isinstance(client.session, _requests.Session)
