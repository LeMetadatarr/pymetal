"""Band detail + lineup endpoints."""
from __future__ import annotations

import re
from typing import List, Optional, Tuple

from pymetal.endpoints._common import (
    collect_stats,
    extract_audit,
    first,
    ma_id_from_url,
    parse_html,
    split_csv,
)
from pymetal.http import Client
from pymetal.transport import default_client
from pymetal.locators import (
    LINEUP_SECTION_STATUS,
    URL_BAND,
    URL_BAND_RECOMMENDATIONS,
    URL_LINKS,
    XPATHS,
)
from pymetal.models import (
    Band,
    BandRecommendation,
    BandStatus,
    ExternalLink,
    LineupMember,
    LineupStatus,
)


def get_band(band_id: int, client: Optional[Client] = None) -> Band:
    """Fetch a band's metadata page and return a `Band`."""
    c = client or default_client()
    resp = c.get(URL_BAND.format(band_id=band_id))
    tree = parse_html(resp.content)

    name = first(tree.xpath(XPATHS.name)) or ""
    url = first(tree.xpath(XPATHS.url))
    stats = collect_stats(tree, XPATHS.stats_dl)

    status_raw = stats.get("Status")
    status: Optional[BandStatus] = None
    if status_raw:
        try:
            status = BandStatus(status_raw.strip())
        except ValueError:
            status = None

    current_href = stats.get("Current label :href")
    last_href = stats.get("Last label :href")
    comment = first(tree.xpath('//*[@id="band_comment"]//text()'))
    if comment:
        comment = re.sub(r"\s+", " ", comment).strip() or None
    logo = first(tree.xpath('//*[@id="logo"]/@href') + tree.xpath('//*[@id="logo"]//img/@src'))
    photo = first(tree.xpath('//*[@id="photo"]/@href') + tree.xpath('//*[@id="photo"]//img/@src'))
    return Band(
        ma_id=band_id,
        name=name,
        url=url,
        country=stats.get("Country of origin"),
        location=stats.get("Location"),
        status=status,
        formed_in=stats.get("Formed in"),
        years_active=split_csv(_normalise_ws(stats.get("Years active"))),
        genres=split_csv(stats.get("Genre")),
        themes=split_csv(stats.get("Themes")),
        current_label_id=ma_id_from_url(current_href),
        current_label_name=stats.get("Current label"),
        last_label_id=ma_id_from_url(last_href),
        last_label_name=stats.get("Last label"),
        comment=comment,
        logo_url=logo,
        photo_url=photo,
        audit=extract_audit(tree),
    )


def _normalise_ws(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    return re.sub(r"\s+", " ", s).strip()


def get_lineup(band_id: int, client: Optional[Client] = None) -> List[LineupMember]:
    """Parse the per-status lineup divs on a band page.

    metal-archives renders Current / Past / Last known / Live / Guest-Session
    as separate `band_tab_members_<status>` divs — one row per (artist, role).
    """
    c = client or default_client()
    resp = c.get(URL_BAND.format(band_id=band_id))
    tree = parse_html(resp.content)

    rows: List[LineupMember] = []
    for section_id, status_value in LINEUP_SECTION_STATUS.items():
        rel_path = XPATHS.lineup_row.lstrip(".")  # ".//tr..." -> "//tr..."
        for tr in tree.xpath(f'//div[@id="{section_id}"]{rel_path}'):
            link = first(tr.xpath(XPATHS.lineup_artist_link))
            artist_id = ma_id_from_url(link)
            if artist_id is None:
                continue
            role = _normalise_ws(first(tr.xpath(XPATHS.lineup_role))) or ""
            artist_name = _normalise_ws(first(tr.xpath('./td[1]/a/text()')))
            date_from, date_to = _parse_role_dates(role)
            rows.append(
                LineupMember(
                    band_id=band_id,
                    artist_id=artist_id,
                    artist_name=artist_name,
                    role=role,
                    status=LineupStatus(status_value),
                    date_from=date_from,
                    date_to=date_to,
                )
            )
    return rows


def get_band_recommendations(
    band_id: int, client: Optional[Client] = None
) -> List[BandRecommendation]:
    """Bands MA shows on the 'Similar artists' tab, sorted by match score."""
    c = client or default_client()
    resp = c.get(URL_BAND_RECOMMENDATIONS.format(band_id=band_id))
    tree = parse_html(resp.content)

    out: List[BandRecommendation] = []
    for tr in tree.xpath("//tr"):
        link = first(tr.xpath("./td[1]/a/@href"))
        bid = ma_id_from_url(link)
        if bid is None or bid == band_id:
            continue
        name = _normalise_ws(first(tr.xpath("./td[1]/a/text()"))) or ""
        country = _normalise_ws(first(tr.xpath("./td[2]/text()")))
        genre = _normalise_ws(first(tr.xpath("./td[3]/text()")))
        score_text = _normalise_ws(first(tr.xpath("./td[4]//text()")))
        score = int(score_text) if score_text and score_text.isdigit() else None
        out.append(
            BandRecommendation(
                band_id=bid,
                name=name,
                url=link or None,
                country=country,
                genre=genre,
                match_score=score,
            )
        )
    return out


def get_links(
    entity_id: int,
    entity_type: str = "band",
    client: Optional[Client] = None,
) -> List[ExternalLink]:
    """External links (Bandcamp, Spotify, official site, ...) for a band or label.

    `entity_type` is `'band'` or `'label'` — those are the two MA exposes.
    Section headers (Official / Official merchandise / Tabulatures / Other)
    drive `ExternalLink.section`.
    """
    c = client or default_client()
    resp = c.get(URL_LINKS.format(entity_type=entity_type, entity_id=entity_id))
    tree = parse_html(resp.content)

    out: List[ExternalLink] = []
    section = "Other"
    for tr in tree.xpath("//tr"):
        row_id = tr.get("id", "") or ""
        if row_id.startswith("header_"):
            # 'header_Official_merchandise' -> 'Official merchandise'
            section = row_id.removeprefix("header_").replace("_", " ").strip() or "Other"
            continue
        if not row_id.startswith("linkRow"):
            continue
        anchor = tr.xpath(".//a[@href]")
        if not anchor:
            continue
        href = anchor[0].get("href", "")
        name = _normalise_ws(anchor[0].text_content()) or ""
        if not href or not name:
            continue
        out.append(ExternalLink(name=name, url=href, section=section))
    return out


def _parse_role_dates(role: str) -> Tuple[Optional[str], Optional[str]]:
    """metal-archives roles look like 'Vocals (1991-1995, 2008-present)'.

    We return only the outer span — first start, first end — and leave
    finer parsing to callers who actually need each stint as a row.
    """
    m = re.search(r"\((\d{4})(?:[-–](\d{4}|present))?", role)
    if not m:
        return None, None
    start = m.group(1)
    end = m.group(2)
    if end == "present":
        end = None
    return start, end
