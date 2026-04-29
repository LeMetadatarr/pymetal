"""Re-capture HTML/JSON fixtures from metal-archives.

Run from repo root: `python test/fixtures/_capture.py`. Requires network.

Fixtures are anchored on stable, well-known MA records:
  - Carcass band id 14 (formed 1986, multiple lineup eras)
  - Heartwork album id 451600 (full-length)
  - Napalm Death / S.O.B. split id 485040 (two bands on one release)
"""
from __future__ import annotations

from pathlib import Path

from pymetal.http import Client
from pymetal.locators import (
    URL_ARTIST,
    URL_BAND,
    URL_BAND_TAB_DISCOGRAPHY,
    URL_BROWSE_COUNTRY,
    URL_BROWSE_GENRE,
    URL_BROWSE_LETTER,
    URL_LABEL,
    URL_LYRICS,
    URL_RELEASE,
    URL_RELEASE_VERSIONS,
    URL_RIP_ARTISTS,
    URL_SEARCH_ALBUMS,
    URL_SEARCH_BANDS,
    URL_SEARCH_SONGS,
    URL_UPCOMING_RELEASES,
)


OUT = Path(__file__).parent / "html"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    c = Client()
    targets = [
        ("band_carcass.html", URL_BAND.format(band_id=14), None),
        ("release_heartwork.html", URL_RELEASE.format(release_id=451600), None),
        ("release_split.html", URL_RELEASE.format(release_id=485040), None),
        ("discography_carcass.html", URL_BAND_TAB_DISCOGRAPHY.format(band_id=14), None),
        ("search_bands_carcass.json", URL_SEARCH_BANDS, {"bandName": "Carcass"}),
        (
            "search_songs_heartwork.json",
            URL_SEARCH_SONGS,
            {"bandName": "Carcass", "songTitle": "Heartwork"},
        ),
        ("search_albums_carcass.json", URL_SEARCH_ALBUMS, {"bandName": "Carcass"}),
        ("artist_steer.html", URL_ARTIST.format(artist_id=490), None),
        # Deceased artist (Chuck Schuldiner) — exercises R.I.P. / Died of fields.
        ("artist_schuldiner.html", URL_ARTIST.format(artist_id=3012), None),
        # Split-up band (Death) — exercises Status: Split-up + last_known lineup.
        ("band_death.html", URL_BAND.format(band_id=141), None),
        # EP release type — different from Full-length / Split.
        ("release_ep_heartwork.html", URL_RELEASE.format(release_id=16885), None),
        # Real lyrics with newlines — for the lyrics tag-stripping path.
        ("lyrics_172090.html", URL_LYRICS + "172090", None),
        # Empty-result band search — verifies pagination/empty handling.
        ("search_bands_empty.json", URL_SEARCH_BANDS, {"bandName": "qzxqzxqzxqzx"}),
        (
            "release_versions_heartwork.html",
            URL_RELEASE_VERSIONS.format(release_id=451600),
            None,
        ),
        # Browse + label + meta endpoints
        ("browse_country_pt.json", URL_BROWSE_COUNTRY.format(country="PT"), None),
        ("browse_genre_black.json", URL_BROWSE_GENRE.format(genre="black"), None),
        ("browse_letter_a.json", URL_BROWSE_LETTER.format(letter="A"), None),
        ("label_nuclear_blast.html", URL_LABEL.format(label_id=2), None),
        ("upcoming_releases.json", URL_UPCOMING_RELEASES, None),
        # Slim RIP fixture (full list is ~3MB; 20 rows is enough for tests).
        ("rip_artists.json", URL_RIP_ARTISTS, {"iDisplayStart": 0, "iDisplayLength": 20}),
        ("lyrics_5060.html", URL_LYRICS + "5060", None),
    ]
    for fname, path, params in targets:
        r = c.get(path, params=params, use_cache=False)
        (OUT / fname).write_bytes(r.content)
        print(f"  {fname:34s} {len(r.content):>7d} bytes  {r.url}")


if __name__ == "__main__":
    main()
