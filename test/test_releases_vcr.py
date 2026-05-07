"""Cassette-backed parser tests for the release endpoints."""
from __future__ import annotations

import pytest

from pymetal import MetalArchives
from pymetal.models import (
    Release,
    ReleaseLineup,
    Song,
    TrackAppearance,
)


# Stable release ids on metal-archives.com:
#   74   -> Iron Maiden, "Killers"
#   547  -> Metallica, "Master of Puppets"
KILLERS = 74
MASTER_OF_PUPPETS = 547
IRON_MAIDEN_BAND = 25


def test_get_release(cassette_client):
    release, songs, appearances = MetalArchives(client=cassette_client).get_release(KILLERS)
    assert isinstance(release, Release)
    assert release.ma_id == KILLERS
    assert release.title
    assert songs, "expected song list"
    assert all(isinstance(s, Song) for s in songs)
    assert appearances, "expected track appearances"
    assert all(isinstance(t, TrackAppearance) for t in appearances)
    assert all(t.release_id == KILLERS for t in appearances)


def test_get_discography(cassette_client):
    discog = MetalArchives(client=cassette_client).get_discography(IRON_MAIDEN_BAND)
    assert isinstance(discog, list)
    assert discog, "expected non-empty discography"
    assert all(isinstance(r, Release) for r in discog)
    assert any(r.title for r in discog)


def test_get_release_lineup(cassette_client):
    lineup = MetalArchives(client=cassette_client).get_release_lineup(KILLERS)
    assert isinstance(lineup, list)
    assert lineup, "expected at least one lineup credit"
    assert all(isinstance(m, ReleaseLineup) for m in lineup)
    assert all(m.release_id == KILLERS for m in lineup)


def test_get_other_versions(cassette_client):
    versions = MetalArchives(client=cassette_client).get_other_versions(MASTER_OF_PUPPETS)
    assert isinstance(versions, list)
    # Master of Puppets has many reissues; tolerate empty but enforce typing.
    assert all(isinstance(r, Release) for r in versions)
