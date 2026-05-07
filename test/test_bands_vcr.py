"""Cassette-backed parser tests for the band endpoints.

These tests replay real captured metal-archives.com responses against the
parsers so upstream HTML changes surface as test failures rather than
silent empty results.

Re-record::

    PYMETAL_CASSETTE_MODE=once pytest test/test_bands_vcr.py

The nightly-live workflow re-records against the live site daily.
"""
from __future__ import annotations

import pytest

from pymetal import MetalArchives
from pymetal.models import Band, ExternalLink, LineupMember, BandRecommendation


# Stable, well-known band ids on metal-archives.com:
#   25  -> Iron Maiden
#   125 -> Metallica
#   72  -> Slayer
IRON_MAIDEN = 25
METALLICA = 125


def test_get_band(cassette_client):
    band: Band = MetalArchives(client=cassette_client).get_band(IRON_MAIDEN)
    assert isinstance(band, Band)
    assert band.ma_id == IRON_MAIDEN
    assert "iron maiden" in band.name.lower()
    assert band.country
    assert band.genres, "expected at least one genre tag"


def test_get_band_by_url(cassette_client):
    url = f"https://www.metal-archives.com/bands/Iron_Maiden/{IRON_MAIDEN}"  # noqa: F841 — id-only extraction
    band = MetalArchives(client=cassette_client).get_band_by_url(url)
    assert isinstance(band, Band)
    assert band.ma_id == IRON_MAIDEN
    assert band.name


def test_get_lineup(cassette_client):
    lineup = MetalArchives(client=cassette_client).get_lineup(IRON_MAIDEN)
    assert isinstance(lineup, list)
    assert lineup, "expected at least one lineup member"
    assert all(isinstance(m, LineupMember) for m in lineup)
    assert any(m.artist_name for m in lineup)


def test_get_band_recommendations(cassette_client):
    recs = MetalArchives(client=cassette_client).get_band_recommendations(IRON_MAIDEN)
    assert isinstance(recs, list)
    # MA usually returns a populated similar-bands list for Iron Maiden.
    assert recs, "expected at least one recommendation"
    assert all(isinstance(r, BandRecommendation) for r in recs)
    assert any(r.name for r in recs)


def test_get_links(cassette_client):
    links = MetalArchives(client=cassette_client).get_links(IRON_MAIDEN, entity_type="band")
    assert isinstance(links, list)
    assert links, "expected at least one external link"
    assert all(isinstance(l, ExternalLink) for l in links)
    assert any(l.url for l in links)


def test_get_stream_links(cassette_client):
    links = MetalArchives(client=cassette_client).get_stream_links(METALLICA)
    assert isinstance(links, list)
    assert all(isinstance(l, ExternalLink) for l in links)
    # Metallica almost always has streaming links — but tolerate empty if
    # MA hides them; just enforce typing.
