"""Selectors and regexes for metal-archives.com — config-as-data.

Ported from pymetalapi. Kept as a module-level dataclass so endpoint
modules can `from pymetal.locators import L` without instantiating.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List


SITE_URL = "https://www.metal-archives.com/"

# AJAX endpoints
URL_SEARCH_SONGS = "search/ajax-advanced/searching/songs"
URL_SEARCH_BANDS = "search/ajax-advanced/searching/bands"
URL_SEARCH_ALBUMS = "search/ajax-advanced/searching/albums"

# Status select codes used by the bands form (status[]=...).
BAND_STATUS_CODES: Dict[str, int] = {
    "active": 1,
    "on hold": 2,
    "split-up": 3,
    "split_up": 3,
    "changed name": 4,
    "changed_name": 4,
    "unknown": 5,
    "disputed": 6,
}

# releaseType[] codes used by both album and song forms.
RELEASE_TYPE_CODES: Dict[str, int] = {
    "Full-length": 1,
    "Live album": 2,
    "Demo": 3,
    "Single": 4,
    "EP": 5,
    "Video": 6,
    "Boxed set": 7,
    "Split": 8,
    "Compilation": 10,
    "Split video": 12,
    "Collaboration": 13,
}

# releaseFormat[] codes for the album form.
RELEASE_FORMAT_CODES: Dict[str, int] = {
    "CD": 1,
    "Cassette": 2,
    "Vinyl": 3,
    "VHS": 4,
    "DVD": 5,
    "Digital": 6,
    "Blu-ray": 7,
    "Other": 8,
}
URL_LYRICS = "release/ajax-view-lyrics/id/"
URL_BAND_RANDOM = "band/random"
URL_BAND_TAB_DISCOGRAPHY = "band/discography/id/{band_id}/tab/all"
URL_BAND_RECOMMENDATIONS = "band/ajax-recommendations/id/{band_id}"
URL_LINKS = "link/ajax-list/type/{entity_type}/id/{entity_id}"
URL_RELEASE = "albums/_/_/{release_id}"
URL_BAND = "bands/_/{band_id}"
URL_ARTIST = "artists/_/{artist_id}"
URL_RELEASE_VERSIONS = "release/ajax-versions/current/{release_id}/parent/{release_id}"
URL_LABEL = "labels/_/{label_id}"

# Browse endpoints — alphabetical / country / genre listings (full, not paged search).
URL_BROWSE_COUNTRY = "browse/ajax-country/c/{country}/json/1"
URL_BROWSE_GENRE = "browse/ajax-genre/g/{genre}/json/1"
URL_BROWSE_LETTER = "browse/ajax-letter/l/{letter}/json/1"
URL_UPCOMING_RELEASES = "release/ajax-upcoming/json/1"
URL_RIP_ARTISTS = "artist/ajax-rip/"
URL_BROWSE_LABELS_COUNTRY = "label/ajax-list/c/{country}/json/1"
URL_BROWSE_LABELS_LETTER = "label/ajax-list/json/1/l/{letter}"
URL_COUNTRY_INDEX = "label/country"  # canonical list of MA country codes

# Reviews
URL_REVIEW_BROWSE = "review/ajax-list-browse/by/date/selection/{year_month}/json/1"
URL_BAND_REVIEWS = "review/ajax-list-band/id/{band_id}/json/1"

LYRICS_NOT_AVAILABLE = "(lyrics not available)"

# Regexes
RE_LYRIC_ID = re.compile(r"id=.+[a-z]+.(?P<id>\d+)")
RE_BAND_NAME = re.compile(r'title="(?P<name>.*)\"')
RE_TAGS = re.compile(r"<[^>]+>")
RE_TRAILING_ID = re.compile(r"/(?P<id>\d+)/?$")

# Genres normalised for fuzzy matching in random_band()
GENRES: List[str] = [
    "black", "death", "doom", "stoner", "sludge", "electronic",
    "industrial", "experimental", "avant-garde", "folk", "viking",
    "pagan", "gothic", "grindcore", "groove", "heavy", "metalcore",
    "deathcore", "power", "progressive", "speed", "symphonic", "thrash",
]


@dataclass(frozen=True)
class XPath:
    """XPath expressions for the band detail page (`/bands/<slug>/<id>`)."""

    name: str = '//*[@id="band_info"]/h1/a/text()'
    url: str = '//*[@id="band_info"]/h1/a/@href'
    country: str = ".//*[@id='band_stats']/dl[1]/dd[1]/a/text()"
    location: str = ".//*[@id='band_stats']/dl[1]/dd[2]/text()"
    status: str = ".//*[@id='band_stats']/dl[1]/dd[3]/text()"
    formed_in: str = ".//*[@id='band_stats']/dl[1]/dd[4]/text()"
    genre: str = ".//*[@id='band_stats']/dl[2]/dd[1]/text()"
    themes: str = ".//*[@id='band_stats']/dl[2]/dd[2]/text()"
    label: str = ".//*[@id='band_stats']/dl[2]/dd[3]/text()"
    years_active: str = ".//*[@id='band_stats']/dl[3]/dd/text()"

    # band/release stats use <dt>label</dt><dd>value</dd> pairs — extract by label
    stats_dl: str = '//*[@id="band_stats"]/dl'
    release_stats_dl: str = '//*[@id="album_info"]/dl'

    # lineup rows live inside per-status divs (band_tab_members_<status>)
    lineup_row: str = './/tr[contains(@class,"lineupRow")]'
    lineup_role: str = './td[2]/text()'
    lineup_artist_link: str = './td[1]/a/@href'

    # discography table — class="display discog"; rows are direct <tr> children
    disco_rows: str = '//table[contains(@class,"discog")]//tr'
    disco_title_link: str = './td[1]/a/@href'
    disco_title_text: str = './td[1]/a/text()'
    disco_type: str = './td[2]/text()'
    disco_year: str = './td[3]/text()'

    # release page
    release_title: str = '//h1[@class="album_name"]/a/text()'
    track_rows: str = '//table[contains(@class,"table_lyrics")]//tr[contains(@class,"even") or contains(@class,"odd") or contains(@class,"sideRow")]'
    track_no: str = './td[1]/text()'
    track_title: str = './td[2]//text()'
    track_length: str = './td[3]/text()'
    track_lyrics_link: str = './td[4]//a/@href'

XPATHS = XPath()


# Lineup section → status enum value
LINEUP_SECTION_STATUS: Dict[str, str] = {
    "band_tab_members_current": "current",
    "band_tab_members_past": "past",
    "band_tab_members_last": "last_known",
    "band_tab_members_live": "live",
    "band_tab_members_guest": "guest_session",
}
