"""Artist (musician) detail endpoint."""
from __future__ import annotations

import re
from typing import Optional

from pymetal.endpoints._common import (
    collect_stats,
    extract_audit,
    first,
    parse_html,
)
from pymetal.http import Client, default_client
from pymetal.locators import URL_ARTIST
from pymetal.models import Artist


_AGE_RE = re.compile(r"(\d+)\s*\(born\s+(.+?)\)", re.IGNORECASE)
_DIED_RE = re.compile(r"died\s+(.+)", re.IGNORECASE)


def get_artist(artist_id: int, client: Optional[Client] = None) -> Artist:
    """Fetch an artist page and return an `Artist`."""
    c = client or default_client
    resp = c.get(URL_ARTIST.format(artist_id=artist_id))
    tree = parse_html(resp.content)

    alias = first(tree.xpath("//h1/text()")) or ""
    stats = collect_stats(tree, '//*[@id="member_info"]//dl')
    photo = first(
        tree.xpath('//*[@id="member_img"]//img/@src')
        + tree.xpath('//*[@id="photo"]//img/@src')
    )
    bio_nodes = tree.xpath('//*[contains(@class,"member_biography")]')
    biography = None
    if bio_nodes:
        biography = re.sub(r"\s+\n", "\n", bio_nodes[0].text_content() or "").strip() or None

    age_text = stats.get("Age")
    born = None
    if age_text:
        m = _AGE_RE.search(age_text)
        if m:
            born = m.group(2).strip()

    return Artist(
        ma_id=artist_id,
        alias=alias.strip() or None,
        real_name=stats.get("Real/full name"),
        url=resp.url if resp.url and resp.url.startswith("http") else None,
        country=stats.get("Place of birth") or stats.get("Place of origin"),
        gender=stats.get("Gender"),
        born=born,
        died=stats.get("R.I.P.") or stats.get("Died on"),
        died_of=stats.get("Died of"),
        place_of_origin=stats.get("Place of birth") or stats.get("Place of origin"),
        photo_url=photo,
        biography=biography,
        audit=extract_audit(tree),
    )
