"""Release detail + discography endpoints."""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from pymetal.endpoints._common import (
    collect_stats,
    extract_audit,
    first,
    ma_id_from_url,
    parse_html,
    parse_int,
)
from pymetal.http import Client, default_client
from pymetal.locators import (
    URL_BAND_TAB_DISCOGRAPHY,
    URL_RELEASE,
    URL_RELEASE_VERSIONS,
    XPATHS,
)
from pymetal.models import (
    CreditSection,
    Release,
    ReleaseFormat,
    ReleaseLineup,
    ReleaseType,
    Song,
    TrackAppearance,
)


def _parse_reviews(text: Optional[str]) -> Tuple[Optional[int], Optional[int]]:
    """'23 reviews (avg. 85%)' -> (23, 85). '2 (85%)' (discography) -> (2, 85)."""
    if not text:
        return None, None
    count_m = re.search(r"(\d+)", text)
    avg_m = re.search(r"(\d+)\s*%", text)
    count = int(count_m.group(1)) if count_m else None
    avg = int(avg_m.group(1)) if avg_m else None
    # If the count regex picked up the percent number, prefer the one before "review" or "("
    pre_m = re.match(r"\s*(\d+)\s*(?:review|\()", text)
    if pre_m:
        count = int(pre_m.group(1))
    return count, avg


def _coerce_release_type(raw: Optional[str]) -> ReleaseType:
    if not raw:
        return ReleaseType.FULL_LENGTH
    raw = raw.strip()
    for rt in ReleaseType:
        if rt.value.lower() == raw.lower():
            return rt
    if "split" in raw.lower():
        return ReleaseType.SPLIT
    if "live" in raw.lower():
        return ReleaseType.LIVE
    if "demo" in raw.lower():
        return ReleaseType.DEMO
    return ReleaseType.FULL_LENGTH


# Split-track titles are rendered as "BAND - Song title" within one <td>.
_SPLIT_TITLE_RE = re.compile(r"^\s*([^\n\-][^\-\n]*?)\s+-\s+(.*)$", re.DOTALL)


def _split_band_and_title(raw: str) -> Tuple[Optional[str], str]:
    """Pull the leading 'BAND - ' prefix off a split-release track title.

    Returns (band_name_or_None, clean_title). If the dash separator isn't
    present, returns (None, raw_stripped).
    """
    s = re.sub(r"\s+", " ", raw).strip()
    m = _SPLIT_TITLE_RE.match(s)
    if not m:
        return None, s
    return m.group(1).strip(), m.group(2).strip()


def get_release(
    release_id: int, client: Optional[Client] = None
) -> Tuple[Release, List[Song], List[TrackAppearance]]:
    """Fetch a release page and return (release, songs, appearances).

    For split releases, MA renders track titles as "BAND - Title" within a
    single cell rather than inserting band-link header rows; we parse the
    prefix and surface it via `TrackAppearance.title_override` plus the
    raw band string in lieu of an ma_id (callers can resolve with the
    H1 band-link list).
    """
    c = client or default_client
    resp = c.get(URL_RELEASE.format(release_id=release_id))
    tree = parse_html(resp.content)

    title = first(tree.xpath(XPATHS.release_title)) or ""
    stats = collect_stats(tree, XPATHS.release_stats_dl)
    type_raw = stats.get("Type")
    rtype = _coerce_release_type(type_raw)
    label_href = stats.get("Label :href")

    fmt_raw = stats.get("Format")
    fmt: Optional[ReleaseFormat] = None
    if fmt_raw:
        head = fmt_raw.split(",", 1)[0].strip()
        try:
            fmt = ReleaseFormat(head)
        except ValueError:
            fmt = None

    reviews_count, reviews_avg = _parse_reviews(stats.get("Reviews"))

    notes_text = None
    notes_nodes = tree.xpath('//*[@id="album_tabs_notes"]')
    if notes_nodes:
        raw = re.sub(r"\s+\n", "\n", notes_nodes[0].text_content() or "")
        notes_text = raw.strip() or None

    band_ids: list = []
    for a in tree.xpath('//*[@class="band_name"]//a'):
        bid = ma_id_from_url(a.get("href"))
        if bid and bid not in band_ids:
            band_ids.append(bid)

    cover_url = first(
        tree.xpath('//a[@id="cover"]/@href')
        + tree.xpath('//a[@id="cover"]//img/@src')
    )

    release = Release(
        ma_id=release_id,
        title=title,
        type=rtype,
        release_date=stats.get("Release date"),
        label_id=ma_id_from_url(label_href),
        label_name=stats.get("Label"),
        catalog_no=stats.get("Catalog ID"),
        format=fmt,
        format_raw=fmt_raw,
        version_description=stats.get("Version desc."),
        limitation=stats.get("Limitation"),
        reviews_count=reviews_count,
        reviews_avg_percent=reviews_avg,
        notes=notes_text,
        band_ids=band_ids,
        cover_url=cover_url,
        audit=extract_audit(tree),
    )

    is_split = rtype is ReleaseType.SPLIT

    # band_id resolution for splits: index by lowercased name from H1's band links.
    split_bands: dict = {}
    if is_split:
        for a in tree.xpath('//*[@class="band_name"]//a'):
            href = a.get("href")
            bid = ma_id_from_url(href)
            if bid:
                split_bands[a.text_content().strip().lower()] = bid

    songs: List[Song] = []
    appearances: List[TrackAppearance] = []

    for tr in tree.xpath(XPATHS.track_rows):
        cls = tr.get("class", "")
        if "sideRow" in cls:
            # Side-A / Side-B label row — purely decorative.
            continue

        no_text = (first(tr.xpath(XPATHS.track_no)) or "").rstrip(".").strip()
        title_text_raw = "".join(tr.xpath(XPATHS.track_title)).strip()
        length = first(tr.xpath(XPATHS.track_length))
        lyrics_link = first(tr.xpath(XPATHS.track_lyrics_link))

        try:
            track_no = int(no_text)
        except ValueError:
            continue

        band_id_for_track: Optional[int] = None
        clean_title = re.sub(r"\s+", " ", title_text_raw).strip()
        title_override: Optional[str] = None
        if is_split:
            band_name, stripped = _split_band_and_title(title_text_raw)
            if band_name:
                clean_title = stripped
                title_override = stripped
                band_id_for_track = split_bands.get(band_name.lower())

        song_id = ma_id_from_url(lyrics_link) if lyrics_link else None
        if song_id is None:
            song_id = release_id * 1000 + track_no

        is_instrumental = "(instrumental)" in clean_title.lower()
        songs.append(Song(ma_id=song_id, title=clean_title, length=length))
        appearances.append(
            TrackAppearance(
                release_id=release_id,
                song_id=song_id,
                band_id=band_id_for_track or 0,
                track_no=track_no,
                length=length,
                title_override=title_override,
                is_instrumental=is_instrumental,
            )
        )
    release.total_length = _sum_lengths(a.length for a in appearances)
    return release, songs, appearances


def _sum_lengths(lengths) -> Optional[str]:
    """Sum 'MM:SS' / 'HH:MM:SS' strings into a single 'HH:MM:SS' (or 'MM:SS')."""
    total = 0
    any_seen = False
    for s in lengths:
        if not s:
            continue
        parts = s.split(":")
        try:
            nums = [int(p) for p in parts]
        except ValueError:
            continue
        if len(nums) == 2:
            total += nums[0] * 60 + nums[1]
        elif len(nums) == 3:
            total += nums[0] * 3600 + nums[1] * 60 + nums[2]
        else:
            continue
        any_seen = True
    if not any_seen:
        return None
    h, rem = divmod(total, 3600)
    m, sec = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{sec:02d}" if h else f"{m:02d}:{sec:02d}"


def get_release_lineup(
    release_id: int, client: Optional[Client] = None
) -> List[ReleaseLineup]:
    """Parse the per-release lineup tab — band members, guests, staff.

    Walks `#album_tabs_lineup` and tags each row with the section header
    that preceded it (`Band members`, `Guest/session musicians`,
    `Miscellaneous staff`).
    """
    c = client or default_client
    resp = c.get(URL_RELEASE.format(release_id=release_id))
    tree = parse_html(resp.content)

    section_map = {
        "band members": CreditSection.BAND,
        "guest/session musicians": CreditSection.GUEST,
        "guest / session musicians": CreditSection.GUEST,
        "miscellaneous staff": CreditSection.STAFF,
    }
    seen: set = set()
    rows: List[ReleaseLineup] = []
    current_section = CreditSection.BAND

    for tr in tree.xpath('//*[@id="album_tabs_lineup"]//tr'):
        cls = tr.get("class", "")
        if "lineupHeaders" in cls:
            label = re.sub(r"\s+", " ", tr.text_content() or "").strip().lower()
            current_section = section_map.get(label, current_section)
            continue
        if "lineupRow" not in cls:
            continue
        link = first(tr.xpath('./td[1]/a/@href'))
        artist_id = ma_id_from_url(link)
        if artist_id is None:
            continue
        role = re.sub(r"\s+", " ", first(tr.xpath('./td[2]/text()')) or "").strip()
        # MA renders "Surname (R.I.P. YYYY)" — split off the parenthetical as credit_note.
        name_cell = re.sub(r"\s+", " ", first(tr.xpath('./td[1]/a/text()')) or "").strip()
        m = re.search(r"\((.+?)\)", first(tr.xpath('./td[1]//text()')) or "")
        credit_note = m.group(1).strip() if m else None
        key = (artist_id, role, current_section)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            ReleaseLineup(
                release_id=release_id,
                band_id=None,
                artist_id=artist_id,
                artist_name=name_cell,
                role=role,
                section=current_section,
                credit_note=credit_note,
            )
        )
    return rows


def get_other_versions(
    release_id: int, client: Optional[Client] = None
) -> List[Release]:
    """All other versions/editions/re-issues of this release."""
    c = client or default_client
    resp = c.get(URL_RELEASE_VERSIONS.format(release_id=release_id))
    tree = parse_html(resp.content)
    out: List[Release] = []
    for tr in tree.xpath("//tr"):
        link = first(tr.xpath("./td[1]/a/@href"))
        rid = ma_id_from_url(link)
        if rid is None:
            continue
        cells = [c.text_content().strip() for c in tr.xpath("./td")]
        if len(cells) < 4:
            continue
        date_raw, label_name, catalog, fmt_raw = cells[0], cells[1], cells[2], cells[3]
        notes = cells[4] if len(cells) > 4 else None
        try:
            fmt = ReleaseFormat(fmt_raw.split(",", 1)[0].strip())
        except ValueError:
            fmt = None
        out.append(
            Release(
                ma_id=rid,
                title=first(tr.xpath("./td[1]/a/text()")) or "",
                url=link,
                # The versions tab doesn't repeat type — reuse the parent's
                # type when known; default to FULL_LENGTH so the model validates.
                type=ReleaseType.FULL_LENGTH,
                release_date=re.sub(r"\s+", " ", date_raw).strip() or None,
                label_name=label_name or None,
                catalog_no=catalog or None,
                format=fmt,
                format_raw=fmt_raw or None,
                notes=notes or None,
            )
        )
    return out


def get_discography(
    band_id: int, client: Optional[Client] = None
) -> List[Release]:
    """All releases for a band — index rows only."""
    c = client or default_client
    resp = c.get(URL_BAND_TAB_DISCOGRAPHY.format(band_id=band_id))
    tree = parse_html(resp.content)

    out: List[Release] = []
    for tr in tree.xpath(XPATHS.disco_rows):
        link = first(tr.xpath(XPATHS.disco_title_link))
        title = first(tr.xpath(XPATHS.disco_title_text))
        if not link or not title:
            continue
        type_raw = first(tr.xpath(XPATHS.disco_type))
        year = first(tr.xpath(XPATHS.disco_year))
        reviews = first(tr.xpath('./td[4]//text()'))
        rcount, ravg = _parse_reviews(reviews)
        rid = ma_id_from_url(link)
        if rid is None:
            continue
        out.append(
            Release(
                ma_id=rid,
                title=title,
                url=link,
                type=_coerce_release_type(type_raw),
                release_date=year,
                reviews_count=rcount,
                reviews_avg_percent=ravg,
            )
        )
    return out
