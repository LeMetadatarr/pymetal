"""HTTP layer: curl_cffi (TLS fingerprint bypass) + small in-process cache.

`requests_cache` doesn't wrap curl_cffi sessions, so we keep a tiny LRU-ish
dict keyed on (method, url, sorted-params). Good enough for a scraper —
metal-archives is mostly idempotent and we want to avoid hammering it from
tests and notebooks.
"""
from __future__ import annotations

import time
from threading import Lock
from typing import Any, Dict, Mapping, Optional, Tuple

from curl_cffi import requests

from pymetal.locators import SITE_URL
from pymetal.util import get_random_user_agent


_CacheKey = Tuple[str, str, Tuple[Tuple[str, str], ...]]


class Client:
    """Thin wrapper around curl_cffi with optional response-body cache."""

    def __init__(
        self,
        base_url: str = SITE_URL,
        impersonate: str = "chrome123",
        cache_ttl: float = 300.0,
        cache_size: int = 512,
    ) -> None:
        self.base_url = base_url.rstrip("/") + "/"
        self.session = requests.Session(impersonate=impersonate)
        self.cache_ttl = cache_ttl
        self.cache_size = cache_size
        self._cache: Dict[_CacheKey, Tuple[float, bytes, str]] = {}
        self._lock = Lock()

    def _key(self, method: str, url: str, params: Optional[Mapping[str, Any]]) -> _CacheKey:
        items = tuple(sorted((k, str(v)) for k, v in (params or {}).items()))
        return (method.upper(), url, items)

    def _cache_get(self, key: _CacheKey) -> Optional[Tuple[bytes, str]]:
        with self._lock:
            hit = self._cache.get(key)
        if hit is None:
            return None
        ts, content, text = hit
        if self.cache_ttl and (time.time() - ts) > self.cache_ttl:
            with self._lock:
                self._cache.pop(key, None)
            return None
        return content, text

    def _cache_put(self, key: _CacheKey, content: bytes, text: str) -> None:
        with self._lock:
            if len(self._cache) >= self.cache_size:
                # naive eviction — drop oldest by timestamp
                oldest = min(self._cache.items(), key=lambda kv: kv[1][0])[0]
                self._cache.pop(oldest, None)
            self._cache[key] = (time.time(), content, text)

    def get(
        self,
        path: str,
        params: Optional[Mapping[str, Any]] = None,
        use_cache: bool = True,
    ) -> "Response":
        url = path if path.startswith("http") else self.base_url + path.lstrip("/")
        key = self._key("GET", url, params)
        if use_cache:
            cached = self._cache_get(key)
            if cached is not None:
                return Response(*cached, url=url, from_cache=True)
        r = self.session.get(
            url,
            params=params,
            headers={"User-Agent": get_random_user_agent()},
        )
        content, text = r.content, r.text
        final_url = getattr(r, "url", url) or url
        if use_cache and r.status_code == 200:
            self._cache_put(key, content, text)
        return Response(content, text, url=final_url, from_cache=False)

    def get_json(self, path: str, params: Optional[Mapping[str, Any]] = None) -> Any:
        import json

        resp = self.get(path, params=params)
        try:
            return json.loads(resp.text)
        except json.JSONDecodeError as e:
            # metal-archives sometimes returns HTML (a Cloudflare challenge,
            # a 404 page, or a throttle response) where we expected JSON.
            # Surface this with the URL and the first bytes so callers can
            # tell what actually came back.
            preview = resp.text[:120].replace("\n", " ")
            raise RuntimeError(
                f"expected JSON from {resp.url!r} but got non-JSON response "
                f"(MA may be rate-limiting). First bytes: {preview!r}"
            ) from e


class Response:
    __slots__ = ("content", "text", "url", "from_cache")

    def __init__(self, content: bytes, text: str, url: str, from_cache: bool) -> None:
        self.content = content
        self.text = text
        self.url = url
        self.from_cache = from_cache


# Module-level default client — endpoints use this unless given another.
default_client = Client()
