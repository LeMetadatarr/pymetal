"""Unit tests for ``pymetal.converters`` — exercises every conversion path."""
from __future__ import annotations

from pymetal.converters import (
    album_search_hit_to_release,
    artist_to_entity,
    band_search_hit_to_entity,
    band_to_entity,
    label_to_entity,
    ma_release_to_release,
    song_search_hit_to_release,
    song_to_release,
    stream_links,
)
from pymetal.models import (
    AlbumSearchHit,
    Artist,
    Band,
    BandSearchHit,
    BandStatus,
    ExternalLink,
    Label,
    Release as MARelease,
    ReleaseType,
    Song,
    SongSearchHit,
)


def test_stream_links_filters_known_services():
    links = [
        ExternalLink(name="YouTube", url="https://www.youtube.com/user/Carcass"),
        ExternalLink(name="Bandcamp", url="https://carcass.bandcamp.com/"),
        ExternalLink(name="Random", url="https://example.com/blah"),
    ]
    streams = stream_links(links)
    assert {s.name for s in streams} == {"YouTube", "Bandcamp"}


def test_stream_links_empty():
    assert stream_links([]) == []


def test_band_to_entity_full():
    band = Band(
        ma_id=14,
        name="Carcass",
        url="https://www.metal-archives.com/bands/Carcass/14",
        country="United Kingdom",
        location="Liverpool",
        genres=["Death Metal"],
        status=BandStatus.ACTIVE,
        photo_url="https://example.com/p.jpg",
    )
    links = [ExternalLink(name="YouTube", url="https://www.youtube.com/u/x")]
    e = band_to_entity(band, links=links)
    assert e.name == "Carcass"
    assert e.external_ids["ma_band_id"] == "14"
    assert e.extra["country"] == "United Kingdom"
    assert e.extra["location"] == "Liverpool"
    assert e.extra["genres"] == ["Death Metal"]
    assert e.extra["status"] == "Active"
    assert "stream_urls" in e.extra
    assert e.extra["image"] == "https://example.com/p.jpg"
    assert e.extra["artist_url"].startswith("https://")


def test_band_to_entity_minimal():
    e = band_to_entity(Band(name="X"))
    assert e.name == "X"
    assert e.external_ids == {}
    assert "stream_urls" not in e.extra


def test_band_to_entity_no_streamable_links():
    band = Band(ma_id=1, name="X")
    links = [ExternalLink(name="Foo", url="https://example.com/x")]
    e = band_to_entity(band, links=links)
    assert "stream_urls" not in e.extra


def test_artist_to_entity_full():
    a = Artist(
        ma_id=42,
        alias="Mr Death",
        real_name="Bob",
        url="https://example.com/a",
        country="US",
        born="1970",
        photo_url="https://example.com/a.jpg",
    )
    e = artist_to_entity(a)
    assert e.name == "Mr Death"
    assert e.external_ids["ma_artist_id"] == "42"
    assert e.extra["real_name"] == "Bob"
    assert e.extra["born"] == "1970"
    assert e.extra["country"] == "US"


def test_artist_to_entity_uses_real_name_fallback():
    e = artist_to_entity(Artist(real_name="Alice"))
    assert e.name == "Alice"


def test_artist_to_entity_empty():
    e = artist_to_entity(Artist())
    assert e.name == ""


def test_label_to_entity_full():
    lbl = Label(
        ma_id=99,
        name="Earache",
        url="https://example.com/l",
        country="UK",
        logo_url="https://example.com/logo.png",
    )
    e = label_to_entity(lbl)
    assert e.name == "Earache"
    assert e.external_ids["ma_label_id"] == "99"
    assert e.extra["country"] == "UK"
    assert e.extra["image"] == "https://example.com/logo.png"


def test_label_to_entity_minimal():
    e = label_to_entity(Label(name="No Label"))
    assert e.external_ids == {}


def test_ma_release_to_release_full():
    rel = MARelease(
        ma_id=451600,
        title="Heartwork",
        url="https://example.com/r",
        type=ReleaseType.FULL_LENGTH,
        release_date="1993",
        label_name="Earache",
        catalog_no="MOSH123",
        cover_url="https://example.com/c.jpg",
    )
    out = ma_release_to_release(rel, band_name="Carcass")
    assert out.work.title == "Heartwork"
    assert out.external_ids["ma_album_id"] == "451600"
    assert out.work.extra["release_type"] == "Full-length"
    assert out.work.extra["release_date"] == "1993"
    assert out.work.extra["label_name"] == "Earache"
    assert out.work.extra["catalog_no"] == "MOSH123"
    assert out.uri.startswith("https://")
    assert out.image.startswith("https://")
    assert out.work.credits[0].entity.name == "Carcass"


def test_ma_release_to_release_minimal_no_band():
    rel = MARelease(title="x", type=ReleaseType.DEMO)
    out = ma_release_to_release(rel)
    assert out.work.credits == []
    assert out.uri == ""
    assert out.image == ""


def test_song_to_release_full():
    s = Song(ma_id=1234, title="Heartwork", lyrics_id="LX1")
    rel = song_to_release(s, band_name="Carcass", band_id=14, release_title="Heartwork")
    assert rel.work.title == "Heartwork"
    assert rel.external_ids["ma_song_id"] == "1234"
    assert rel.external_ids["ma_lyrics_id"] == "LX1"
    assert rel.work.extra["ma_band_id"] == "14"
    assert rel.work.extra["ma_release_title"] == "Heartwork"
    assert rel.work.credits[0].entity.name == "Carcass"


def test_song_to_release_minimal():
    rel = song_to_release(Song(title="x"))
    assert rel.work.credits == []
    assert rel.external_ids == {}


def test_band_search_hit_to_entity_full():
    h = BandSearchHit(ma_id=14, name="Carcass", url="https://example.com/x",
                     genre="Death", country="UK")
    e = band_search_hit_to_entity(h)
    assert e.external_ids["ma_band_id"] == "14"
    assert e.extra["genre"] == "Death"
    assert e.extra["country"] == "UK"


def test_band_search_hit_to_entity_minimal():
    e = band_search_hit_to_entity(BandSearchHit(ma_id=None, name="x"))
    assert e.external_ids == {}


def test_album_search_hit_to_release_full():
    h = AlbumSearchHit(
        ma_id=1, title="x", url="https://example.com/x",
        band_id=2, band_name="B", genre="Death",
        type=ReleaseType.EP, release_date="2020",
    )
    r = album_search_hit_to_release(h)
    assert r.external_ids["ma_album_id"] == "1"
    assert r.work.extra["ma_band_id"] == "2"
    assert r.work.extra["release_type"] == "EP"
    assert r.work.extra["release_date"] == "2020"
    assert r.work.extra["genre"] == "Death"
    assert r.work.credits[0].entity.name == "B"


def test_album_search_hit_to_release_minimal():
    r = album_search_hit_to_release(AlbumSearchHit(ma_id=None, title="x"))
    assert r.work.credits == []
    assert r.uri == ""


def test_song_search_hit_to_release_full():
    h = SongSearchHit(
        song_id="42", title="t",
        band_id=1, band_name="B",
        release_id=2, release_title="R", release_type=ReleaseType.LIVE,
        lyrics_id="LX",
    )
    r = song_search_hit_to_release(h)
    assert r.external_ids["ma_song_id"] == "42"
    assert r.external_ids["ma_lyrics_id"] == "LX"
    assert r.work.extra["ma_band_id"] == "1"
    assert r.work.extra["ma_release_id"] == "2"
    assert r.work.extra["ma_release_title"] == "R"
    assert r.work.extra["release_type"] == "Live album"
    assert r.work.credits[0].entity.name == "B"


def test_song_search_hit_to_release_minimal():
    r = song_search_hit_to_release(SongSearchHit(song_id="1", title="x"))
    assert r.work.credits == []
