"""Encyclopaedia Metallum (Metal Archives) band scraper.

Uses the public AJAX browse endpoint — no auth needed. Returns a DataTables
payload: ``{"iTotalRecords": N, "aaData": [["<a href=...>Name</a>", country,
genre, status], ...]}``. Pagination is offset-based (``iDisplayStart``), and
the authoritative end-of-catalog signal is ``iTotalRecords`` (not a short
page), so :meth:`fetch` is overridden directly, mirroring
``musicbrainz_artists``.

Run it::

    pymetal-harvest [--output DIR] [--limit N] [--delay SECS]
    python -m harvestkit metal_archives [--output DIR] [--limit N] [--delay SECS]
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from harvestkit.engine import PaginatedJSONSource, register, run_cli

BASE = "https://www.metal-archives.com"
PAGE_SIZE = 500


def _strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s).strip()


def _extract_url(s: str) -> Optional[str]:
    m = re.search(r'href="([^"]+)"', s)
    return m.group(1) if m else None


def _extract_id(url: Optional[str]) -> Optional[str]:
    if not url:
        return None
    m = re.search(r"/(\d+)$", url)
    return m.group(1) if m else None


@register
class MetalArchivesSource(PaginatedJSONSource):
    name = "metal_archives"
    id_field = "ma_id"
    default_delay = 3.0  # Metal Archives rate-limits aggressively

    base = f"{BASE}/browse/ajax-band/json/1"
    page_size = PAGE_SIZE
    accept = "application/json, text/javascript, */*; q=0.01"

    def session(self):
        if self._session is None:
            import requests
            s = requests.Session()
            s.headers.update({
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
                "Accept": self.accept,
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://www.metal-archives.com/browse/band",
            })
            self._session = s
        return self._session

    def initial_cursor(self) -> int:
        return 0

    def map_row(self, row: List[str]) -> Optional[Dict[str, Any]]:
        name_html, country, genre, status = row
        url = _extract_url(name_html)
        ma_id = _extract_id(url)
        name = _strip_html(name_html)
        if not ma_id:
            return None
        return {
            "ma_id": ma_id,
            "name": name,
            "url": url,
            "country": country or None,
            "genre": genre or None,
            "status": status or None,
        }

    def fetch(self, cursor: int):
        offset = int(cursor or 0)
        params = {
            "sEcho": (offset // PAGE_SIZE) + 1,
            "iColumns": 4,
            "iDisplayStart": offset,
            "iDisplayLength": PAGE_SIZE,
            "sSortDir_0": "asc",
        }
        data = self.get_json(self.base, params)
        total = data.get("iTotalRecords", 0)
        raw_rows = data.get("aaData") or []

        if not raw_rows:
            return [], None

        rows = []
        for r in raw_rows:
            mapped = self.map_row(r)
            if mapped is not None:
                rows.append(mapped)

        next_offset = offset + len(raw_rows)
        next_cursor = None if next_offset >= total else next_offset
        return rows, next_cursor


if __name__ == "__main__":
    raise SystemExit(run_cli(MetalArchivesSource))
