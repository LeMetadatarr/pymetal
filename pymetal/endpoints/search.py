"""metal-archives advanced-search endpoints — bands, albums, songs.

Mirrors every form field on `/search/advanced/searching/{bands,albums,songs}`.
Multi-valued filters (`country`, `status`, `release_type`, `release_format`)
accept a list. Status / release-type / release-format strings are mapped to
MA's numeric codes via tables in `pymetal.locators`.
"""
from __future__ import annotations

from typing import Iterable, Iterator, List, Optional, Sequence, Union

from pymetal.endpoints._common import ma_id_from_url
from pymetal.http import Client, default_client
from pymetal.locators import (
    BAND_STATUS_CODES,
    RELEASE_FORMAT_CODES,
    RELEASE_TYPE_CODES,
    RE_LYRIC_ID,
    URL_SEARCH_ALBUMS,
    URL_SEARCH_BANDS,
    URL_SEARCH_SONGS,
)
from pymetal.models import (
    AlbumSearchHit,
    BandSearchHit,
    ReleaseType,
    SongSearchHit,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _slice_anchor(anchor: str, marker_open: str, marker_close: str) -> str:
    i = anchor.find(marker_open)
    if i < 0:
        return ""
    i += len(marker_open)
    j = anchor.find(marker_close, i)
    return anchor[i:j] if j > i else anchor[i:]


def _strip_html_comment(s: str) -> str:
    """MA dates/relevance scores arrive as 'value <!-- raw -->'."""
    i = s.find("<!--")
    return s[:i].strip() if i >= 0 else s.strip()


def _coerce_codes(values: Optional[Iterable[Union[str, int]]], table: dict) -> List[int]:
    """Map status/release-type/format names to their MA numeric codes."""
    if not values:
        return []
    out: List[int] = []
    for v in values:
        if isinstance(v, int):
            out.append(v)
            continue
        key = v.strip()
        if key in table:
            out.append(table[key])
            continue
        # Case-insensitive fallback
        lower = key.lower()
        for k, code in table.items():
            if k.lower() == lower:
                out.append(code)
                break
    return out


def _add_multi(params: dict, key: str, values: Sequence) -> None:
    """MA accepts repeated `key[]=...` query params for multi-selects."""
    if values:
        params[f"{key}[]"] = list(values)


def _flag(params: dict, key: str, on: bool) -> None:
    if on:
        params[key] = 1


def _paginate(
    client: Client,
    url: str,
    params: dict,
    page_size: int,
    paginate: bool,
) -> Iterator[list]:
    """Yield raw `aaData` rows. Walks pages when `paginate=True`."""
    index = int(params.pop("iDisplayStart", 0))
    while True:
        params["iDisplayStart"] = index
        params["iDisplayLength"] = page_size
        data = client.get_json(url, params=params)
        rows = data.get("aaData") or []
        for row in rows:
            yield row
        if not paginate or not rows:
            break
        total = int(data.get("iTotalRecords") or 0)
        index += len(rows)
        if index >= total:
            break


# ---------------------------------------------------------------------------
# Bands
# ---------------------------------------------------------------------------


def search_bands(
    band_name: str = "",
    *,
    exact_band_match: bool = False,
    genre: str = "",
    country: Union[str, Sequence[str]] = "",
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    status: Optional[Sequence[Union[str, int]]] = None,
    themes: str = "",
    location: str = "",
    label: str = "",
    indie_label: bool = False,
    band_notes: str = "",
    index: int = 0,
    page_size: int = 200,
    paginate: bool = False,
    client: Optional[Client] = None,
) -> Iterator[BandSearchHit]:
    """Search bands. Mirrors every field on the bands advanced-search form.

    `country` accepts an MA code ('PT') or a list of codes.
    `status` accepts names ('active', 'split-up') or MA codes (1..6).
    """
    c = client or default_client
    params: dict = {
        "bandName": band_name,
        "genre": genre,
        "themes": themes,
        "location": location,
        "bandLabelName": label,
        "bandNotes": band_notes,
        "iDisplayStart": index,
    }
    _flag(params, "exactBandMatch", exact_band_match)
    _flag(params, "indieLabel", indie_label)
    if year_from is not None:
        params["yearCreationFrom"] = int(year_from)
    if year_to is not None:
        params["yearCreationTo"] = int(year_to)
    countries = [country] if isinstance(country, str) and country else list(country) if country else []
    _add_multi(params, "country", countries)
    _add_multi(params, "status", _coerce_codes(status, BAND_STATUS_CODES))

    for row in _paginate(c, URL_SEARCH_BANDS, params, page_size, paginate):
        url = _slice_anchor(row[0], 'href="', '">')
        name = _slice_anchor(row[0], '">', "</a>")
        yield BandSearchHit(
            ma_id=ma_id_from_url(url),
            name=name,
            url=url or None,
            genre=row[1] if len(row) > 1 else None,
            country=row[2] if len(row) > 2 else None,
            location=None,
        )


# ---------------------------------------------------------------------------
# Albums (NEW)
# ---------------------------------------------------------------------------


def search_albums(
    band_name: str = "",
    release_title: str = "",
    *,
    exact_band_match: bool = False,
    exact_release_match: bool = False,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    month_from: Optional[int] = None,
    month_to: Optional[int] = None,
    country: Union[str, Sequence[str]] = "",
    location: str = "",
    label: str = "",
    indie_label: bool = False,
    catalog_number: str = "",
    identifiers: str = "",  # barcode/ISRC
    recording_info: str = "",
    description: str = "",
    notes: str = "",
    genre: str = "",
    release_type: Optional[Sequence[Union[str, int, ReleaseType]]] = None,
    release_format: Optional[Sequence[Union[str, int]]] = None,
    index: int = 0,
    page_size: int = 200,
    paginate: bool = False,
    client: Optional[Client] = None,
) -> Iterator[AlbumSearchHit]:
    """Search releases. Covers every field on the albums advanced-search form."""
    c = client or default_client
    params: dict = {
        "bandName": band_name,
        "releaseTitle": release_title,
        "location": location,
        "releaseLabelName": label,
        "releaseCatalogNumber": catalog_number,
        "releaseIdentifiers": identifiers,
        "releaseRecordingInfo": recording_info,
        "releaseDescription": description,
        "releaseNotes": notes,
        "genre": genre,
        "iDisplayStart": index,
    }
    _flag(params, "exactBandMatch", exact_band_match)
    _flag(params, "exactReleaseMatch", exact_release_match)
    _flag(params, "indieLabel", indie_label)
    if year_from is not None:
        params["releaseYearFrom"] = int(year_from)
    if year_to is not None:
        params["releaseYearTo"] = int(year_to)
    if month_from is not None:
        params["releaseMonthFrom"] = int(month_from)
    if month_to is not None:
        params["releaseMonthTo"] = int(month_to)
    countries = [country] if isinstance(country, str) and country else list(country) if country else []
    _add_multi(params, "country", countries)
    rtypes: List[Union[str, int]] = []
    for v in release_type or []:
        rtypes.append(v.value if isinstance(v, ReleaseType) else v)
    _add_multi(params, "releaseType", _coerce_codes(rtypes, RELEASE_TYPE_CODES))
    _add_multi(params, "releaseFormat", _coerce_codes(release_format, RELEASE_FORMAT_CODES))

    for row in _paginate(c, URL_SEARCH_ALBUMS, params, page_size, paginate):
        # row layout: [band_anchor, release_anchor, genre_or_type, year]
        band_url = _slice_anchor(row[0], 'href="', '"')
        band_name_text = _slice_anchor(row[0], '">', "</a>")
        rel_url = _slice_anchor(row[1], 'href="', '"')
        rel_title = _slice_anchor(row[1], '">', "</a>")
        rel_genre_or_type = row[2] if len(row) > 2 else None
        date_raw = _strip_html_comment(row[3]) if len(row) > 3 else None
        try:
            rt = ReleaseType(rel_genre_or_type) if rel_genre_or_type else None
        except ValueError:
            rt = None
        yield AlbumSearchHit(
            ma_id=ma_id_from_url(rel_url),
            title=rel_title,
            url=rel_url or None,
            band_id=ma_id_from_url(band_url),
            band_name=band_name_text,
            genre=rel_genre_or_type if rt is None else None,
            type=rt,
            release_date=date_raw,
        )


# ---------------------------------------------------------------------------
# Songs
# ---------------------------------------------------------------------------


def search_songs(
    song_title: str = "",
    *,
    exact_song_match: bool = False,
    band_name: str = "",
    exact_band_match: bool = False,
    release_title: str = "",
    exact_release_match: bool = False,
    lyrics: str = "",
    genre: str = "",
    country: Union[str, Sequence[str]] = "",
    release_type: Optional[Sequence[Union[str, int, ReleaseType]]] = None,
    excluded_release_types: Optional[Iterable[str]] = None,
    index: int = 0,
    page_size: int = 200,
    paginate: bool = False,
    client: Optional[Client] = None,
) -> Iterator[SongSearchHit]:
    """Search songs with the full advanced-search field set.

    `lyrics` searches the lyrics text itself (MA full-text). Returns rich
    `SongSearchHit`s carrying band_id, release_id and lyrics_id — none of
    which the legacy flat `Track` exposed.
    """
    c = client or default_client
    excluded = set(excluded_release_types or [])
    params: dict = {
        "bandName": band_name,
        "releaseTitle": release_title,
        "songTitle": song_title,
        "lyrics": lyrics,
        "genre": genre,
        "iDisplayStart": index,
    }
    _flag(params, "exactSongMatch", exact_song_match)
    _flag(params, "exactBandMatch", exact_band_match)
    _flag(params, "exactReleaseMatch", exact_release_match)
    countries = [country] if isinstance(country, str) and country else list(country) if country else []
    _add_multi(params, "country", countries)
    rtypes: List[Union[str, int]] = []
    for v in release_type or []:
        rtypes.append(v.value if isinstance(v, ReleaseType) else v)
    _add_multi(params, "releaseType", _coerce_codes(rtypes, RELEASE_TYPE_CODES))

    for row in _paginate(c, URL_SEARCH_SONGS, params, page_size, paginate):
        # row layout: [band_anchor, release_anchor, release_type, song_title, lyrics_widget]
        band_url = _slice_anchor(row[0], 'href="', '"')
        band_name_text = _slice_anchor(row[0], '">', "</a>")
        rel_url = _slice_anchor(row[1], 'href="', '"')
        rel_title = _slice_anchor(row[1], '">', "</a>")
        rtype_raw = row[2] if len(row) > 2 else None
        if rtype_raw in excluded:
            continue
        try:
            rtype = ReleaseType(rtype_raw) if rtype_raw else None
        except ValueError:
            rtype = None
        song_title_text = row[3] if len(row) > 3 else ""
        lyrics_id: Optional[str] = None
        if len(row) > 4 and row[4]:
            m = RE_LYRIC_ID.search(row[4])
            if m:
                lyrics_id = m.group("id")
        yield SongSearchHit(
            song_id=lyrics_id or "",
            title=song_title_text,
            band_id=ma_id_from_url(band_url),
            band_name=band_name_text,
            release_id=ma_id_from_url(rel_url),
            release_title=rel_title,
            release_type=rtype,
            lyrics_id=lyrics_id,
        )


