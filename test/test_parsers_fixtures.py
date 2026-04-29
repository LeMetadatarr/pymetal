"""End-to-end parser tests against captured metal-archives fixtures.

The fixtures live in `test/fixtures/html/` and were captured from
metal-archives.com on 2026-04-29 with `pymetal.http.Client`. They are
real HTML/JSON, not synthesised — so parser regressions surface as
test failures with concrete diffs.

To re-capture (e.g. after MA changes its DOM), run:
    python test/fixtures/_capture.py
"""
from __future__ import annotations

from collections import Counter

from pymetal.endpoints.artists import get_artist
from pymetal.endpoints.bands import get_band, get_lineup
from pymetal.endpoints.releases import (
    get_discography,
    get_other_versions,
    get_release,
    get_release_lineup,
)
from pymetal.endpoints.search import search_albums, search_bands, search_songs
from pymetal.endpoints.lyrics import get_lyrics_by_song_id
from pymetal.models import BandStatus, CreditSection, LineupStatus, ReleaseType


# ---------------------------------------------------------------------------
# Band detail
# ---------------------------------------------------------------------------


def test_get_band_carcass(fake_client):
    c = fake_client({"bands/_/14": "band_carcass.html"})
    b = get_band(14, client=c)
    assert b.name == "Carcass"
    assert b.country == "United Kingdom"
    assert b.status is BandStatus.ACTIVE
    assert b.formed_in == "1986"
    assert b.location.startswith("Liverpool")
    assert "Death" in b.themes and "Gore" in b.themes
    assert b.genres  # at least one genre extracted
    assert b.years_active == ["1986-1996", "2007-present"]
    assert b.current_label_id is not None  # Nuclear Blast linked
    assert b.current_label_name and "Nuclear Blast" in b.current_label_name


def test_get_band_audit_metadata(fake_client):
    c = fake_client({"bands/_/14": "band_carcass.html"})
    b = get_band(14, client=c)
    assert b.audit is not None
    assert b.audit.added_by  # username
    assert b.audit.modified_by
    assert b.audit.added_on and b.audit.added_on.startswith("20")  # ISO-ish date
    assert b.audit.last_modified_on


# ---------------------------------------------------------------------------
# Lineup — covers the "same band, different humans over time" case
# ---------------------------------------------------------------------------


def test_get_lineup_carcass_partitions_by_status(fake_client):
    c = fake_client({"bands/_/14": "band_carcass.html"})
    rows = get_lineup(14, client=c)
    by_status = Counter(r.status for r in rows)
    # Carcass shows current + past + live members at minimum
    assert by_status[LineupStatus.CURRENT] > 0
    assert by_status[LineupStatus.PAST] > 0
    assert by_status[LineupStatus.LIVE] > 0
    # Roles are populated
    assert all(r.role for r in rows)
    assert all(r.artist_id > 0 for r in rows)


def test_get_lineup_mayhem_complex_history(fake_client):
    """Mayhem has a long lineup history (members died, replaced) — verifies
    the parser scales beyond Carcass's smaller membership and that every
    section MA renders is recognised."""
    c = fake_client({"bands/_/67": "band_mayhem.html"})
    rows = get_lineup(67, client=c)
    assert len(rows) > 10  # Mayhem has many members across decades
    # All artist_ids must be positive
    assert all(r.artist_id > 0 for r in rows)
    # At least one member with a closed (date_to is set) past stint
    closed = [r for r in rows if r.date_from and r.date_to]
    assert closed, "expected at least one member with a closed date range"


def test_get_lineup_extracts_role_dates(fake_client):
    """Jeff Walker (artist 563) — Bass/Vocals 1986-1996, 2007-present."""
    c = fake_client({"bands/_/14": "band_carcass.html"})
    rows = get_lineup(14, client=c)
    walker = [r for r in rows if r.artist_id == 563]
    assert walker, "Jeff Walker not in fixture"
    # Outer span is the first stint — date_from should be 1986
    assert walker[0].date_from == "1986"


# ---------------------------------------------------------------------------
# Release — Heartwork (Full-length, no splits)
# ---------------------------------------------------------------------------


def test_get_release_heartwork(fake_client):
    c = fake_client({"albums/_/_/451600": "release_heartwork.html"})
    rel, songs, apps = get_release(451600, client=c)
    assert rel.title == "Heartwork"
    assert rel.type is ReleaseType.FULL_LENGTH
    assert rel.release_date == "October 18th, 1993"
    assert rel.catalog_no == "MOSH 97CD"
    assert rel.label_name == "Earache Records"
    assert rel.format is not None and rel.format.value == "CD"
    assert rel.format_raw  # may include qualifiers
    assert rel.reviews_count is not None and rel.reviews_count > 0
    assert rel.reviews_avg_percent is not None and 0 < rel.reviews_avg_percent <= 100
    assert rel.notes and "Music video" in rel.notes
    assert rel.band_ids == [14]
    assert rel.audit is not None and rel.audit.added_on
    assert rel.cover_url is not None and "451600" in str(rel.cover_url)
    assert rel.total_length and ":" in rel.total_length
    assert len(songs) == len(apps) == 10
    assert songs[0].title == "Buried Dreams"
    assert apps[0].track_no == 1
    # No split — title_override should not be set
    assert all(a.title_override is None for a in apps)


# ---------------------------------------------------------------------------
# Split release — covers BOTH "multiple bands per release" AND
# the per-track band attribution case.
# ---------------------------------------------------------------------------


def test_get_release_split_attributes_tracks_per_band(fake_client):
    """Napalm Death / S.O.B. split (id 485040).

    MA renders track titles as 'BAND - Title' inside one cell, with both
    bands listed in the <h2 class="band_name">. Our parser strips the
    prefix and resolves it to the right band_id.
    """
    c = fake_client({"albums/_/_/485040": "release_split.html"})
    rel, songs, apps = get_release(485040, client=c)
    assert rel.type is ReleaseType.SPLIT
    # Both bands recorded on the release header
    assert set(rel.band_ids) == {219, 6214}
    band_ids = {a.band_id for a in apps}
    # Napalm Death = 219, S.O.B = 6214 — both must appear on appearances too
    assert 219 in band_ids and 6214 in band_ids
    # Every appearance carried a stripped title_override
    assert all(a.title_override for a in apps)
    # And the original title doesn't leak the "BAND - " prefix
    assert not any(s.title.startswith(("S.O.B - ", "Napalm Death - ")) for s in songs)


# ---------------------------------------------------------------------------
# Discography
# ---------------------------------------------------------------------------


def test_get_discography_carcass(fake_client):
    c = fake_client({"band/discography": "discography_carcass.html"})
    rows = get_discography(14, client=c)
    assert len(rows) > 30  # Carcass has a long history
    # First row from the captured fixture is "Flesh Ripping Sonic Torment" (Demo, 1987)
    assert rows[0].title == "Flesh Ripping Sonic Torment"
    assert rows[0].type is ReleaseType.DEMO
    assert rows[0].release_date == "1987"
    # All ma_ids are positive ints
    assert all(r.ma_id and r.ma_id > 0 for r in rows)
    # Heartwork (451600) is in there
    assert any(r.ma_id == 451600 and r.title == "Heartwork" for r in rows)
    # Reviews column populated for at least some rows
    reviewed = [r for r in rows if r.reviews_count is not None]
    assert reviewed, "no discography row carried review counts"
    assert all(0 <= (r.reviews_avg_percent or 0) <= 100 for r in reviewed)


# ---------------------------------------------------------------------------
# Search endpoints (AJAX JSON)
# ---------------------------------------------------------------------------


def test_search_bands_carcass(fake_client):
    c = fake_client({"search/ajax-advanced/searching/bands": "search_bands_carcass.json"})
    hits = list(search_bands(band_name="Carcass", client=c))
    assert hits
    first = hits[0]
    assert first.name == "Carcass"
    assert first.ma_id == 14
    assert first.country == "United Kingdom"


def test_search_songs_heartwork(fake_client):
    c = fake_client({"search/ajax-advanced/searching/songs": "search_songs_heartwork.json"})
    hits = list(search_songs(song_title="Heartwork", band_name="Carcass", client=c))
    assert hits
    titles = {h.title for h in hits}
    assert "Heartwork" in titles
    # SongSearchHit carries band_id, release_id, lyrics_id
    assert all(h.band_id for h in hits)
    assert all(h.release_id for h in hits)
    assert all(h.lyrics_id for h in hits)


def test_search_albums_carcass(fake_client):
    c = fake_client(
        {"search/ajax-advanced/searching/albums": "search_albums_carcass.json"}
    )
    hits = list(search_albums(band_name="Carcass", client=c))
    assert hits
    titles = {h.title for h in hits}
    assert "Heartwork" in titles
    sample = next(h for h in hits if h.title == "Heartwork")
    assert sample.band_id == 14
    assert sample.band_name == "Carcass"
    assert sample.ma_id == 451600


def test_search_albums_release_type_filter_param_coercion(fake_client):
    """Verify the function accepts ReleaseType enum values without error."""
    c = fake_client(
        {"search/ajax-advanced/searching/albums": "search_albums_carcass.json"}
    )
    hits = list(
        search_albums(
            band_name="Carcass",
            release_type=[ReleaseType.FULL_LENGTH, "Demo"],
            client=c,
        )
    )
    # Doesn't actually filter (FakeClient ignores params), but proves the
    # ReleaseType -> code coercion path doesn't blow up.
    assert hits


def test_search_songs_excluded_release_types(fake_client):
    c = fake_client({"search/ajax-advanced/searching/songs": "search_songs_heartwork.json"})
    full_only = list(
        search_songs(
            song_title="Heartwork",
            band_name="Carcass",
            excluded_release_types=["Compilation", "Live album"],
            client=c,
        )
    )
    assert full_only
    seen = {h.release_type for h in full_only if h.release_type}
    assert ReleaseType.COMPILATION not in seen
    assert ReleaseType.LIVE not in seen


# ---------------------------------------------------------------------------
# Lyrics endpoint
# ---------------------------------------------------------------------------


def test_get_artist_steer(fake_client):
    """Bill Steer (artist 490) — Carcass guitarist."""
    c = fake_client({"artists/_/490": "artist_steer.html"})
    a = get_artist(490, client=c)
    assert a.alias == "Bill Steer"
    assert a.real_name and "Steer" in a.real_name
    assert a.gender in {"Male", "Female", "Non-binary"} or a.gender is None
    # Born is parsed out of the "Age:" string
    assert a.born and "1969" in a.born
    assert a.audit is not None


def test_get_release_lineup_heartwork(fake_client):
    c = fake_client({"albums/_/_/451600": "release_heartwork.html"})
    rows = get_release_lineup(451600, client=c)
    assert rows
    sections = {r.section for r in rows}
    assert CreditSection.BAND in sections
    assert CreditSection.STAFF in sections
    # Bill Steer (490) appears as a band member
    band_members = [r for r in rows if r.section is CreditSection.BAND]
    assert any(r.artist_id == 490 for r in band_members)
    # All rows carry an artist_id and role
    assert all(r.artist_id and r.role for r in rows)


def test_get_other_versions_heartwork(fake_client):
    c = fake_client(
        {"release/ajax-versions": "release_versions_heartwork.html"}
    )
    versions = get_other_versions(451600, client=c)
    assert len(versions) > 5  # Heartwork has many re-issues
    # Original CD pressing is in there
    assert any(v.ma_id == 451600 for v in versions)
    # Multiple formats represented
    fmts = {v.format for v in versions if v.format is not None}
    assert len(fmts) > 1


def test_get_lyrics_strips_html_tags(fake_client):
    c = fake_client({"release/ajax-view-lyrics/id/5060": "lyrics_5060.html"})
    text = get_lyrics_by_song_id(5060, client=c)
    # Either we got real lyrics or MA reported "(lyrics not available)" → None
    if text is not None:
        assert "<" not in text and ">" not in text
        assert text.strip()


def test_get_lyrics_real_content(fake_client):
    """A song that actually has lyrics on MA — Carcass 'Heartwork' (172090)."""
    c = fake_client({"release/ajax-view-lyrics/id/172090": "lyrics_172090.html"})
    text = get_lyrics_by_song_id(172090, client=c)
    assert text is not None
    assert "<" not in text and ">" not in text
    # Reasonably long real lyrics (not a one-liner)
    assert len(text) > 100


# ---------------------------------------------------------------------------
# Edge-case bands: split-up status + last_known lineup
# ---------------------------------------------------------------------------


def test_get_band_split_up(fake_client):
    """Death (id 141) — band ended when Chuck Schuldiner died."""
    c = fake_client({"bands/_/141": "band_death.html"})
    b = get_band(141, client=c)
    assert b.name == "Death"
    assert b.status is BandStatus.SPLIT_UP
    # Split-up bands carry years_active with a closed range
    assert b.years_active
    assert any("-" in span for span in b.years_active)


def test_get_lineup_split_up_band_includes_last_known(fake_client):
    """Death band has a last_known section since it's no longer active."""
    c = fake_client({"bands/_/141": "band_death.html"})
    rows = get_lineup(141, client=c)
    statuses = {r.status for r in rows}
    # Past should be present at minimum; many split-up bands also have last_known
    assert LineupStatus.PAST in statuses or LineupStatus.LAST_KNOWN in statuses
    # Chuck Schuldiner (artist 3012) is on every Death lineup
    assert any(r.artist_id == 3012 for r in rows)


# ---------------------------------------------------------------------------
# Deceased artist
# ---------------------------------------------------------------------------


def test_get_artist_deceased(fake_client):
    """Chuck Schuldiner — exercises 'R.I.P.' and 'Died of' fields."""
    c = fake_client({"artists/_/3012": "artist_schuldiner.html"})
    a = get_artist(3012, client=c)
    assert a.alias == "Chuck Schuldiner"
    assert a.real_name and "Schuldiner" in a.real_name
    assert a.born and "1967" in a.born
    assert a.died and "2001" in a.died
    assert a.died_of  # 'Pneumonia'


# ---------------------------------------------------------------------------
# EP release type (covers _coerce_release_type for non-FULL_LENGTH)
# ---------------------------------------------------------------------------


def test_get_release_ep_type(fake_client):
    """Carcass 'The Heartwork E.P.' — release type EP."""
    c = fake_client({"albums/_/_/16885": "release_ep_heartwork.html"})
    rel, songs, apps = get_release(16885, client=c)
    assert rel.type is ReleaseType.EP
    assert len(songs) == len(apps)
    assert songs  # at least one track
    # Cover image always present on MA release pages
    assert rel.cover_url is not None


# ---------------------------------------------------------------------------
# Empty search result
# ---------------------------------------------------------------------------


def test_search_bands_empty_result(fake_client):
    c = fake_client(
        {"search/ajax-advanced/searching/bands": "search_bands_empty.json"}
    )
    hits = list(search_bands(band_name="qzxqzxqzxqzx", client=c))
    assert hits == []


def test_search_bands_paginate_stops_on_empty(fake_client):
    """`paginate=True` must terminate when MA returns zero rows."""
    c = fake_client(
        {"search/ajax-advanced/searching/bands": "search_bands_empty.json"}
    )
    hits = list(search_bands(band_name="qzxqzxqzxqzx", paginate=True, client=c))
    assert hits == []  # would loop forever if termination is broken


# ---------------------------------------------------------------------------
# Status / release-type filter coercion (no fixture call — sanity-only)
# ---------------------------------------------------------------------------


def test_search_bands_status_coercion_accepts_names_and_codes(fake_client):
    c = fake_client(
        {"search/ajax-advanced/searching/bands": "search_bands_carcass.json"}
    )
    # Mix of name + code shouldn't raise
    hits = list(
        search_bands(
            band_name="Carcass",
            status=["active", 3, "On hold"],
            client=c,
        )
    )
    assert hits  # the fake client ignores params, so the route still hits
