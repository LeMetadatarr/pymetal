"""Browse endpoints — full alphabetical / country / genre listings.

These are MA's `browse/ajax-*` JSON endpoints. They return the entire
catalog for a slice (every band in a country, every band in a genre,
every band starting with a letter) rather than paged search results,
so they're the right tool for enumerate-everything workflows.

Each function paginates internally via `iDisplayStart` / `iDisplayLength`.
"""
from __future__ import annotations

import re
from typing import Iterator, Optional

from pymetal.endpoints._common import ma_id_from_url
from pymetal.endpoints.releases import _coerce_release_type
from pymetal.http import Client, default_client
from pymetal.locators import (
    URL_BROWSE_COUNTRY,
    URL_BROWSE_GENRE,
    URL_BROWSE_LETTER,
    URL_RIP_ARTISTS,
    URL_UPCOMING_RELEASES,
)
from pymetal.models import BandSearchHit, BandStatus, RIPArtist, UpcomingRelease


_HREF_RE = re.compile(r"href=['\"]([^'\"]+)['\"]")
_TEXT_RE = re.compile(r">([^<]*)</a>")


def _parse_anchor(html_str: str) -> tuple[Optional[str], str]:
    href = (_HREF_RE.search(html_str) or [None, None])[1] if _HREF_RE.search(html_str) else None
    m = _HREF_RE.search(html_str)
    href = m.group(1) if m else None
    m2 = _TEXT_RE.search(html_str)
    text = m2.group(1) if m2 else ""
    return href, text


def _strip_tags(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s).strip()


def _walk(
    client: Client,
    url: str,
    page_size: int = 500,
    paginate: bool = True,
) -> Iterator[list]:
    index = 0
    while True:
        data = client.get_json(
            url,
            params={"sEcho": 1, "iDisplayStart": index, "iDisplayLength": page_size},
        )
        rows = data.get("aaData") or []
        for row in rows:
            yield row
        if not paginate or not rows:
            break
        total = int(data.get("iTotalRecords") or 0)
        index += len(rows)
        if index >= total:
            break


def _band_status_from_span(html_str: str) -> Optional[BandStatus]:
    raw = _strip_tags(html_str)
    if not raw:
        return None
    try:
        return BandStatus(raw.strip())
    except ValueError:
        return None


def browse_bands_by_country(
    country_code: str,
    *,
    paginate: bool = True,
    page_size: int = 500,
    client: Optional[Client] = None,
) -> Iterator[BandSearchHit]:
    """Every band MA lists for a country (e.g. 'PT', 'NO', 'US').

    Returns more rows than `search_bands(country=...)` because it walks
    the dedicated browse endpoint rather than the search index.
    """
    c = client or default_client
    for row in _walk(
        c,
        URL_BROWSE_COUNTRY.format(country=country_code),
        page_size=page_size,
        paginate=paginate,
    ):
        # cols: [band_anchor, genre, location, status_span]
        href, name = _parse_anchor(row[0])
        yield BandSearchHit(
            ma_id=ma_id_from_url(href),
            name=name,
            url=href or None,
            genre=row[1] if len(row) > 1 else None,
            country=country_code,
        )


def browse_bands_by_genre(
    genre_slug: str,
    *,
    paginate: bool = True,
    page_size: int = 500,
    client: Optional[Client] = None,
) -> Iterator[BandSearchHit]:
    """Every band in a genre slug (lowercase: 'black', 'death', 'heavy', ...).

    The genre slugs are MA's coarse 23-bucket taxonomy (see
    `pymetal.locators.GENRES`); they are *not* the free-text genre
    strings shown on each band page.
    """
    c = client or default_client
    for row in _walk(
        c,
        URL_BROWSE_GENRE.format(genre=genre_slug),
        page_size=page_size,
        paginate=paginate,
    ):
        # cols: [band_anchor, country, free_text_genre, status_span]
        href, name = _parse_anchor(row[0])
        yield BandSearchHit(
            ma_id=ma_id_from_url(href),
            name=name,
            url=href or None,
            country=row[1] if len(row) > 1 else None,
            genre=row[2] if len(row) > 2 else None,
        )


def browse_bands_by_letter(
    letter: str,
    *,
    paginate: bool = True,
    page_size: int = 500,
    client: Optional[Client] = None,
) -> Iterator[BandSearchHit]:
    """Every band whose name starts with `letter` ('A'..'Z', 'NBR', '~').

    'NBR' covers names starting with a digit; '~' covers symbols/non-Latin.
    """
    c = client or default_client
    for row in _walk(
        c,
        URL_BROWSE_LETTER.format(letter=letter),
        page_size=page_size,
        paginate=paginate,
    ):
        # cols: [band_anchor, country, genre, status_span]
        href, name = _parse_anchor(row[0])
        yield BandSearchHit(
            ma_id=ma_id_from_url(href),
            name=name,
            url=href or None,
            country=row[1] if len(row) > 1 else None,
            genre=row[2] if len(row) > 2 else None,
        )


def get_rip_artists(
    *,
    paginate: bool = True,
    page_size: int = 500,
    client: Optional[Client] = None,
) -> Iterator[RIPArtist]:
    """Every deceased artist MA tracks (~10k rows when fully paginated)."""
    c = client or default_client
    for row in _walk(
        c,
        URL_RIP_ARTISTS,
        page_size=page_size,
        paginate=paginate,
    ):
        # cols: [artist_anchor, country, band_anchor, died_on, cause]
        artist_href, artist_name = _parse_anchor(row[0])
        band_href, band_name = _parse_anchor(row[2]) if len(row) > 2 else (None, None)
        died = row[3] if len(row) > 3 else None
        cause = row[4] if len(row) > 4 else None
        yield RIPArtist(
            artist_id=ma_id_from_url(artist_href),
            artist_name=artist_name,
            country=row[1] if len(row) > 1 else None,
            band_id=ma_id_from_url(band_href) if band_href else None,
            band_name=band_name or None,
            died_on=died if died and died != "N/A" else None,
            cause=cause if cause and cause != "Unknown" else None,
        )


def get_upcoming_releases(
    *,
    paginate: bool = True,
    page_size: int = 500,
    client: Optional[Client] = None,
) -> Iterator[UpcomingRelease]:
    """All releases scheduled for the future on MA."""
    c = client or default_client
    for row in _walk(
        c,
        URL_UPCOMING_RELEASES,
        page_size=page_size,
        paginate=paginate,
    ):
        # cols: [band_anchor, release_anchor, type, genre, date, last_modified]
        band_href, band_name = _parse_anchor(row[0])
        rel_href, rel_title = _parse_anchor(row[1])
        yield UpcomingRelease(
            band_id=ma_id_from_url(band_href),
            band_name=band_name,
            release_id=ma_id_from_url(rel_href),
            release_title=rel_title,
            type=_coerce_release_type(row[2]) if len(row) > 2 and row[2] else None,
            genre=row[3] if len(row) > 3 else None,
            release_date=row[4] if len(row) > 4 else None,
        )
