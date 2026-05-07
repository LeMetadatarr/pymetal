"""Cassette-backed parser tests for artist and label detail pages."""
from __future__ import annotations

import pytest

from pymetal import MetalArchives
from pymetal.models import Artist, Label


# Stable ids on metal-archives.com:
#   170   -> James Hetfield (Metallica vocalist)  — artist page
#   2     -> Nuclear Blast Records                — label page
JAMES_HETFIELD = 170
NUCLEAR_BLAST = 2


def test_get_artist(cassette_client):
    artist = MetalArchives(client=cassette_client).get_artist(JAMES_HETFIELD)
    assert isinstance(artist, Artist)
    assert artist.ma_id == JAMES_HETFIELD
    assert artist.alias or artist.real_name


def test_get_label(cassette_client):
    label = MetalArchives(client=cassette_client).get_label(NUCLEAR_BLAST)
    assert isinstance(label, Label)
    assert label.ma_id == NUCLEAR_BLAST
    assert label.name
