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
from pymetal.http import Client
from pymetal.transport import default_client
from pymetal.locators import (
    GENRES,
    URL_BROWSE_COUNTRY,
    URL_BROWSE_GENRE,
    URL_BROWSE_LABELS_COUNTRY,
    URL_BROWSE_LABELS_LETTER,
    URL_BROWSE_LETTER,
    URL_COUNTRY_INDEX,
    URL_BAND_REVIEWS,
    URL_REVIEW_BROWSE,
    URL_RIP_ARTISTS,
    URL_UPCOMING_RELEASES,
)
from pymetal.models import (
    BandSearchHit,
    BandStatus,
    Label,
    Review,
    RIPArtist,
    UpcomingRelease,
)


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
    """Remove HTML tags + decode the few entities MA emits in table cells."""
    if not s:
        return ""
    cleaned = re.sub(r"<[^>]+>", "", s)
    # MA pads cells with literal `&nbsp;` and the unicode NBSP \xa0 — strip both.
    cleaned = cleaned.replace("&nbsp;", " ").replace("\xa0", " ").replace("&amp;", "&")
    return re.sub(r"\s+", " ", cleaned).strip()


def _clean_or_none(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    out = _strip_tags(s)
    return out or None


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
    c = client or default_client()
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
    c = client or default_client()
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
    c = client or default_client()
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
    c = client or default_client()
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


def _label_status_from_span(html_str: str) -> Optional[str]:
    """'<span class="active">active</span>&nbsp;' -> 'active'."""
    return _clean_or_none(html_str)


def _website_from_anchor(html_str: str) -> Optional[str]:
    m = _HREF_RE.search(html_str or "")
    return m.group(1) if m else None


def browse_labels_by_country(
    country_code: str,
    *,
    paginate: bool = True,
    page_size: int = 500,
    client: Optional[Client] = None,
) -> Iterator[Label]:
    """Every label MA lists for a country (e.g. 338 PT labels).

    Walks `label/ajax-list/c/{code}/json/1`. Returns lightweight `Label`
    rows — call `get_label(label.ma_id)` for full detail (address,
    sub-labels, audit, etc.).
    """
    c = client or default_client()
    for row in _walk(
        c,
        URL_BROWSE_LABELS_COUNTRY.format(country=country_code),
        page_size=page_size,
        paginate=paginate,
    ):
        # cols: [edit_link, label_anchor, specialty, status_span, website, online_shopping]
        href, name = _parse_anchor(row[1]) if len(row) > 1 else (None, "")
        yield Label(
            ma_id=ma_id_from_url(href),
            name=name,
            url=href or None,
            country=country_code,
            styles=_clean_or_none(row[2]) if len(row) > 2 else None,
            status=_label_status_from_span(row[3]) if len(row) > 3 else None,
            website=_website_from_anchor(row[4]) if len(row) > 4 else None,
            online_shopping="Yes" if len(row) > 5 and "Yes" in row[5] else None,
        )


def browse_labels_by_letter(
    letter: str,
    *,
    paginate: bool = True,
    page_size: int = 500,
    client: Optional[Client] = None,
) -> Iterator[Label]:
    """Every label whose name starts with `letter` ('A'..'Z', 'NBR', '~').

    Same shape as `browse_labels_by_country`; the row layout adds a
    country column at index 4.
    """
    c = client or default_client()
    for row in _walk(
        c,
        URL_BROWSE_LABELS_LETTER.format(letter=letter),
        page_size=page_size,
        paginate=paginate,
    ):
        # cols: [edit_link, label_anchor, specialty, status_span, country, website, online_shopping]
        href, name = _parse_anchor(row[1]) if len(row) > 1 else (None, "")
        yield Label(
            ma_id=ma_id_from_url(href),
            name=name,
            url=href or None,
            country=_clean_or_none(row[4]) if len(row) > 4 else None,
            styles=_clean_or_none(row[2]) if len(row) > 2 else None,
            status=_label_status_from_span(row[3]) if len(row) > 3 else None,
            website=_website_from_anchor(row[5]) if len(row) > 5 else None,
            online_shopping="Yes" if len(row) > 6 and "Yes" in row[6] else None,
        )


def list_countries(client: Optional[Client] = None) -> dict[str, str]:
    """Return MA's full country index as `{code: name}`.

    Parsed from `/label/country`. Codes are ISO 3166-1 alpha-2 plus
    `ZZ` ("Unknown") and `0` ("(no country)") which MA uses as buckets.
    """
    from lxml import html as lxml_html

    c = client or default_client()
    resp = c.get(URL_COUNTRY_INDEX)
    tree = lxml_html.fromstring(resp.content)
    out: dict[str, str] = {}
    for a in tree.xpath('//a[contains(@href,"/c/")]'):
        href = a.get("href", "")
        idx = href.rfind("/c/")
        if idx < 0:
            continue
        code = href[idx + 3 :].rstrip("/")
        name = (a.text_content() or "").strip()
        if code and name and code not in out:
            out[code] = name
    return out


def list_genre_slugs() -> list[str]:
    """Return MA's coarse 23-bucket genre taxonomy.

    These are the slugs accepted by `browse_bands_by_genre(slug)` — they
    are *not* the free-text genre strings on band pages.
    """
    return list(GENRES)


_REVIEW_URL_RE = re.compile(r"/reviews/[^/]+/[^/]+/(\d+)/[^/]+/(\d+)")
_TITLE_ATTR_RE = re.compile(r'title="([^"]*)"')
_DAY_RE = re.compile(r"(\d{1,2})")


def browse_reviews(
    year: Optional[int] = None,
    month: Optional[int] = None,
    *,
    paginate: bool = True,
    page_size: int = 500,
    client: Optional[Client] = None,
) -> Iterator[Review]:
    """Browse reviews posted in a given month.

    Defaults to the current month. metal-archives' review browser is
    organised by year-month — no all-time iterator exists upstream.
    """
    import datetime

    today = datetime.date.today()
    y = year or today.year
    m = month or today.month
    period = f"{y:04d}-{m:02d}"

    c = client or default_client()
    for row in _walk(
        c,
        URL_REVIEW_BROWSE.format(year_month=period),
        page_size=page_size,
        paginate=paginate,
    ):
        # cols: [day_label, review_anchor (with title), band_anchor,
        #        release_anchor, "NN%", user_anchor, "HH:MM"]
        review_anchor = row[1] if len(row) > 1 else ""
        href_m = _HREF_RE.search(review_anchor)
        review_url = href_m.group(1) if href_m else None
        title_m = _TITLE_ATTR_RE.search(review_anchor)
        review_title = title_m.group(1) if title_m else None

        rel_id = review_id = None
        if review_url:
            rm = _REVIEW_URL_RE.search(review_url)
            if rm:
                rel_id = int(rm.group(1))
                review_id = int(rm.group(2))

        band_href, band_name = _parse_anchor(row[2]) if len(row) > 2 else (None, "")
        release_href, release_title = _parse_anchor(row[3]) if len(row) > 3 else (None, "")
        score_raw = row[4] if len(row) > 4 else None
        score = int(score_raw.rstrip("%")) if score_raw and score_raw.rstrip("%").isdigit() else None
        _, username = _parse_anchor(row[5]) if len(row) > 5 else (None, None)
        time_raw = row[6] if len(row) > 6 else None

        # Combine day-of-month + period + time into a single timestamp string.
        posted_on = None
        day_match = _DAY_RE.search(row[0]) if len(row) > 0 and row[0] else None
        if day_match:
            day = int(day_match.group(1))
            if time_raw:
                posted_on = f"{period}-{day:02d} {time_raw}"
            else:
                posted_on = f"{period}-{day:02d}"

        yield Review(
            review_id=review_id,
            review_url=review_url,
            title=review_title,
            band_id=ma_id_from_url(band_href),
            band_name=band_name,
            release_id=rel_id or ma_id_from_url(release_href),
            release_title=release_title,
            score_percent=score,
            username=username,
            posted_on=posted_on,
        )


def get_band_reviews(
    band_id: int,
    *,
    paginate: bool = True,
    page_size: int = 500,
    client: Optional[Client] = None,
) -> Iterator[Review]:
    """Every review of every release by a band.

    metal-archives' default sort triggers a server-side SQL error
    (`Unknown column 'review_date DESC'`) — we sort by rating-desc
    instead, which works.
    """
    c = client or default_client()
    # Override the broken default sort.
    index = 0
    while True:
        data = c.get_json(
            URL_BAND_REVIEWS.format(band_id=band_id),
            params={
                "sEcho": 1,
                "iDisplayStart": index,
                "iDisplayLength": page_size,
                "iSortCol_0": 2,        # column 2 = Rating
                "sSortDir_0": "desc",
            },
        )
        rows = data.get("aaData") or []
        for row in rows:
            # cols: [release_anchor (href has review_id), score%, user_anchor, date]
            release_anchor = row[0] if len(row) > 0 else ""
            href_m = _HREF_RE.search(release_anchor)
            review_url = href_m.group(1) if href_m else None
            release_id = review_id = None
            if review_url:
                rm = _REVIEW_URL_RE.search(review_url)
                if rm:
                    release_id = int(rm.group(1))
                    review_id = int(rm.group(2))
            release_title_m = _TEXT_RE.search(release_anchor)
            release_title = release_title_m.group(1) if release_title_m else ""
            score_raw = row[1] if len(row) > 1 else None
            score = (
                int(score_raw.rstrip("%"))
                if score_raw and score_raw.rstrip("%").isdigit()
                else None
            )
            _, username = _parse_anchor(row[2]) if len(row) > 2 else (None, None)
            date_raw = row[3] if len(row) > 3 else None
            yield Review(
                review_id=review_id,
                review_url=review_url,
                band_id=band_id,
                band_name="",  # MA doesn't echo it on this endpoint
                release_id=release_id,
                release_title=release_title,
                score_percent=score,
                username=username,
                posted_on=date_raw,
            )
        if not paginate or not rows:
            break
        total = int(data.get("iTotalRecords") or 0)
        index += len(rows)
        if index >= total:
            break


def get_upcoming_releases(
    *,
    paginate: bool = True,
    page_size: int = 500,
    client: Optional[Client] = None,
) -> Iterator[UpcomingRelease]:
    """All releases scheduled for the future on MA."""
    c = client or default_client()
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
