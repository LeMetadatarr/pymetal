"""Transport selection for :class:`pymetal.http.Client`.

metal-archives.com is heavily defended against scrapers (Cloudflare, TLS
fingerprinting, basic UA filtering). The recommended transport is
``curl_cffi``, which impersonates a real browser's TLS handshake. Because
``curl_cffi`` ships native binaries and isn't always installable on every
target, it is an *optional* dependency:

    pip install pymetal[stealth]

Selection rules for :func:`default_client`:

* If the caller passes ``session=...`` to :class:`pymetal.http.Client`,
  no auto-selection happens — the injected session is used as-is.
* Otherwise, when ``PYMETAL_TRANSPORT=curl_cffi`` is set in the env *and*
  ``curl_cffi`` is importable, a curl_cffi-backed Client is returned.
* In all other cases a plain ``requests``-backed Client is returned and a
  :class:`RuntimeWarning` is emitted noting that metal-archives.com is
  likely to block plain requests.
"""
from __future__ import annotations

import os
import warnings
from typing import Any

from pymetal.http import Client


def _curl_cffi_available() -> bool:
    try:
        import curl_cffi  # noqa: F401
        return True
    except Exception:
        return False


def _make_requests_session() -> Any:
    """Build a stdlib-``requests`` session. No impersonation."""
    import requests as _requests
    return _requests.Session()


def _make_curl_cffi_session(impersonate: str = "chrome123") -> Any:
    from curl_cffi import requests as _curl_requests
    return _curl_requests.Session(impersonate=impersonate)


def default_client(
    *,
    impersonate: str = "chrome123",
    cache_ttl: float = 300.0,
    cache_size: int = 512,
) -> Client:
    """Construct a :class:`Client` using the env-var-selected transport.

    See module docstring for the selection rules.
    """
    requested = (os.environ.get("PYMETAL_TRANSPORT") or "").strip().lower()
    want_curl = requested in ("curl_cffi", "curl-cffi", "curlcffi")

    if want_curl and _curl_cffi_available():
        session = _make_curl_cffi_session(impersonate=impersonate)
        return Client(
            cache_ttl=cache_ttl,
            cache_size=cache_size,
            session=session,
        )

    if want_curl and not _curl_cffi_available():
        warnings.warn(
            "PYMETAL_TRANSPORT=curl_cffi was requested but `curl_cffi` is "
            "not installed; falling back to plain `requests`. metal-"
            "archives.com is likely to block plain requests. Install with "
            "`pip install pymetal[stealth]`.",
            RuntimeWarning,
            stacklevel=2,
        )
    else:
        warnings.warn(
            "pymetal is using plain `requests` as its HTTP transport. "
            "metal-archives.com is heavily defended and is likely to block "
            "these requests. Set PYMETAL_TRANSPORT=curl_cffi and install "
            "`pip install pymetal[stealth]` to enable browser-impersonated "
            "TLS via curl_cffi.",
            RuntimeWarning,
            stacklevel=2,
        )

    session = _make_requests_session()
    return Client(
        cache_ttl=cache_ttl,
        cache_size=cache_size,
        session=session,
    )
