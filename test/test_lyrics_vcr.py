"""Cassette-backed parser tests for the lyrics endpoint."""
from __future__ import annotations

import itertools

import pytest

from pymetal import MetalArchives


def test_get_lyrics_by_song_id(cassette_client):
    # 4471 -> Iron Maiden "Hallowed Be Thy Name" (off Number of the Beast).
    # MA's lyrics ids are alphanumeric strings; this one has been stable for
    # well over a decade.
    lyrics = MetalArchives(client=cassette_client).get_lyrics_by_song_id(4471)
    assert isinstance(lyrics, str)
    assert lyrics.strip(), "expected non-empty lyrics"


def test_get_lyrics_by_search():
    """Regression test for the get_lyrics() bug.

    ``MetalArchives.search_songs()`` yields mediavocab ``Release`` objects, so
    ``get_lyrics()`` must read the MA lyrics id from
    ``external_ids['ma_lyrics_id']`` rather than a non-existent ``lyrics_id``
    attribute. Uses offline fixtures rather than VCR cassettes so the test
    stays self-contained even when the search cassette has no matching
    lyrics cassettes.
    """
    import json
    from pathlib import Path

    HTML = Path(__file__).parent / "fixtures" / "html"

    class _Resp:
        def __init__(self, b):
            self.content = b
            self.text = b.decode("utf-8", errors="replace")
            self.url = ""
            self.from_cache = True

    class _Client:
        def get(self, path, params=None, use_cache=True):
            if "release/ajax-view-lyrics" in path:
                return _Resp((HTML / "lyrics_172090.html").read_bytes())
            raise AssertionError(path)

        def get_json(self, path, params=None):
            if "search/ajax-advanced/searching/songs" in path:
                return json.loads((HTML / "search_songs_heartwork.json").read_text())
            raise AssertionError(path)

    ma = MetalArchives(client=_Client())
    texts = list(itertools.islice(
        ma.get_lyrics(song_title="Heartwork", band_name="Carcass"), 1
    ))
    assert texts, "expected at least one matching lyric"
    assert texts[0].strip()
