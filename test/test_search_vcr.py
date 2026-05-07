"""Cassette-backed parser tests for the search endpoints.

Covers the three advanced-search AJAX endpoints (bands / albums / songs)
via the high-level ``MetalArchives`` facade, which converts raw search hits
into mediavocab ``Entity`` / ``Release`` objects.
"""
from __future__ import annotations

import itertools

import pytest
from mediavocab import Entity
from mediavocab import Release as MvRelease

from pymetal import MetalArchives
from pymetal.endpoints import search as _search


def _take(it, n=3):
    return list(itertools.islice(it, n))


def test_search_bands(cassette_client):
    hits = _take(MetalArchives(client=cassette_client).search_bands(band_name="Iron Maiden"))
    assert hits, "expected at least one band hit"
    assert all(isinstance(h, Entity) for h in hits)
    assert any("iron maiden" in (h.name or "").lower() for h in hits)


def test_search_albums(cassette_client):
    hits = _take(MetalArchives(client=cassette_client).search_albums(
        band_name="Metallica", release_title="Master of Puppets"
    ))
    assert hits, "expected at least one album hit"
    assert all(isinstance(h, MvRelease) for h in hits)
    assert any("master" in (h.work.title or "").lower() for h in hits)


def test_search_songs(cassette_client):
    hits = _take(MetalArchives(client=cassette_client).search_songs(
        band_name="Slayer", song_title="Raining Blood"
    ))
    assert hits, "expected at least one song hit"
    assert all(isinstance(h, MvRelease) for h in hits)
    assert any("raining blood" in (h.work.title or "").lower() for h in hits)


def test_search_bands_raw_hits(cassette_client):
    # exercise the lower-level generator directly (Pydantic BandSearchHit)
    from pymetal.models import BandSearchHit

    hits = _take(_search.search_bands(band_name="Slayer", client=cassette_client))
    assert hits
    assert all(isinstance(h, BandSearchHit) for h in hits)
    assert any("slayer" in h.name.lower() for h in hits)
