"""Cassette-backed parser tests for the browse / discovery endpoints."""
from __future__ import annotations

import itertools

import pytest

from pymetal import MetalArchives
from pymetal.models import (
    BandSearchHit,
    Label,
    Review,
    RIPArtist,
    UpcomingRelease,
)


def _take(it, n=5):
    return list(itertools.islice(it, n))


def test_browse_bands_by_country(cassette_client):
    # 'US' has thousands of MA bands, so first page is always populated.
    hits = _take(MetalArchives(client=cassette_client).browse_bands_by_country("US"))
    assert hits, "expected at least one band"
    assert all(isinstance(h, BandSearchHit) for h in hits)


def test_browse_bands_by_genre(cassette_client):
    hits = _take(MetalArchives(client=cassette_client).browse_bands_by_genre("black"))
    assert hits
    assert all(isinstance(h, BandSearchHit) for h in hits)


def test_browse_bands_by_letter(cassette_client):
    hits = _take(MetalArchives(client=cassette_client).browse_bands_by_letter("M"))
    assert hits
    assert all(isinstance(h, BandSearchHit) for h in hits)


def test_browse_labels_by_country(cassette_client):
    hits = _take(MetalArchives(client=cassette_client).browse_labels_by_country("DE"))
    assert hits
    assert all(isinstance(h, Label) for h in hits)


def test_browse_labels_by_letter(cassette_client):
    hits = _take(MetalArchives(client=cassette_client).browse_labels_by_letter("N"))
    assert hits
    assert all(isinstance(h, Label) for h in hits)


def test_get_upcoming_releases(cassette_client):
    hits = _take(MetalArchives(client=cassette_client).get_upcoming_releases())
    assert all(isinstance(h, UpcomingRelease) for h in hits)
    # MA may have an empty upcoming list at the boundary of a month;
    # only enforce typing.


def test_get_rip_artists(cassette_client):
    hits = _take(MetalArchives(client=cassette_client).get_rip_artists())
    assert hits, "expected at least one RIP entry"
    assert all(isinstance(h, RIPArtist) for h in hits)


def test_list_countries(cassette_client):
    countries = MetalArchives(client=cassette_client).list_countries()
    assert isinstance(countries, dict)
    assert countries, "expected populated country index"
    assert "US" in countries


def test_browse_reviews(cassette_client):
    hits = _take(MetalArchives(client=cassette_client).browse_reviews(year=2024, month=1))
    assert hits, "expected at least one review for Jan 2024"
    assert all(isinstance(h, Review) for h in hits)


def test_get_band_reviews(cassette_client):
    # Iron Maiden has hundreds of release reviews — never empty.
    hits = _take(MetalArchives(client=cassette_client).get_band_reviews(25))
    assert hits, "expected at least one review for Iron Maiden"
    assert all(isinstance(h, Review) for h in hits)
