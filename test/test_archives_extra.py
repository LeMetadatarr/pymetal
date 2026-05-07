"""Additional facade tests covering random_band, get_lyrics regression,
genre normalisation, util helpers, and url-error paths."""
from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from pymetal.archives import MetalArchives, _normalise_genre
from pymetal.util import merge_dict, get_random_user_agent


HTML_FIXTURES = Path(__file__).parent / "fixtures" / "html"


class _Resp:
    def __init__(self, content: bytes, url: str = "") -> None:
        self.content = content
        self.text = content.decode("utf-8", errors="replace")
        self.url = url
        self.from_cache = True


class _RoutedClient:
    """Fake client that returns fixtures based on path substring routes."""

    def __init__(self, routes, random_urls=None) -> None:
        self.routes = routes
        self.random_urls = list(random_urls or [])
        self.calls = []

    def _read(self, path):
        for needle, fname in self.routes.items():
            if needle in path:
                return (HTML_FIXTURES / fname).read_bytes()
        raise AssertionError(f"no route for {path!r}")

    def get(self, path, params=None, use_cache=True):
        self.calls.append(path)
        if "band/random" in path:
            url = self.random_urls.pop(0) if self.random_urls else ""
            return _Resp(b"", url=url)
        return _Resp(self._read(path))

    def get_json(self, path, params=None):
        return json.loads(self._read(path).decode("utf-8"))


# ---------------------------------------------------------------------------
# util.py
# ---------------------------------------------------------------------------


def test_merge_dict_recursive():
    base = {"a": 1, "b": {"c": 2, "d": 3}}
    delta = {"b": {"c": 9, "e": 4}, "f": 5}
    out = merge_dict(base, delta)
    assert out == {"a": 1, "b": {"c": 9, "d": 3, "e": 4}, "f": 5}


def test_merge_dict_overwrites_non_dict():
    assert merge_dict({"a": [1]}, {"a": [2]}) == {"a": [2]}


def test_get_random_user_agent_returns_chrome_string():
    ua = get_random_user_agent()
    assert "Chrome" in ua


# ---------------------------------------------------------------------------
# _normalise_genre
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("inp,expected", [
    ("Death Metal", "death"),
    ("Trash Metal", "thrash"),
    ("Death core", "deathcore"),
    ("Black", "black"),
])
def test_normalise_genre(inp, expected):
    assert _normalise_genre(inp) == expected


# ---------------------------------------------------------------------------
# get_band_by_url error path
# ---------------------------------------------------------------------------


def test_get_band_by_url_invalid_raises():
    m = MetalArchives(client=_RoutedClient({}))
    with pytest.raises(ValueError, match="could not extract MA band id"):
        m.get_band_by_url("https://example.com/no-id-here")


# ---------------------------------------------------------------------------
# random_band — mock the client to drive every branch
# ---------------------------------------------------------------------------


def test_random_band_returns_first_hit():
    client = _RoutedClient(
        {"bands/_/14": "band_carcass.html"},
        random_urls=["https://www.metal-archives.com/bands/Carcass/14"],
    )
    m = MetalArchives(client=client)
    band = m.random_band(sleep_between=0)
    assert band.name == "Carcass"


def test_random_band_skips_when_id_unparseable_then_succeeds():
    client = _RoutedClient(
        {"bands/_/14": "band_carcass.html"},
        random_urls=[
            "https://www.metal-archives.com/garbage",
            "https://www.metal-archives.com/bands/Carcass/14",
        ],
    )
    m = MetalArchives(client=client)
    band = m.random_band(sleep_between=0)
    assert band.name == "Carcass"


def test_random_band_unsupported_genre_falls_through_to_first_hit():
    client = _RoutedClient(
        {"bands/_/14": "band_carcass.html"},
        random_urls=["https://www.metal-archives.com/bands/Carcass/14"],
    )
    m = MetalArchives(client=client)
    band = m.random_band(genre="not-a-real-genre", sleep_between=0)
    assert band.name == "Carcass"


def test_random_band_genre_match():
    client = _RoutedClient(
        {"bands/_/14": "band_carcass.html"},
        random_urls=["https://www.metal-archives.com/bands/Carcass/14"],
    )
    m = MetalArchives(client=client)
    # Carcass listed as Death/Grind on MA — match coarse "death".
    band = m.random_band(genre="death", sleep_between=0)
    assert band.name == "Carcass"


def test_random_band_exhausts_attempts_and_raises():
    client = _RoutedClient(
        {},
        random_urls=["https://example.com/no-id"] * 5,
    )
    m = MetalArchives(client=client)
    with pytest.raises(RuntimeError, match="rate-limiting"):
        m.random_band(max_attempts=5, sleep_between=0)


def test_random_band_returns_last_when_genre_never_matches():
    # Coarse genre 'black' won't match Carcass — exhaust and return last_band.
    client = _RoutedClient(
        {"bands/_/14": "band_carcass.html"},
        random_urls=["https://www.metal-archives.com/bands/Carcass/14"] * 3,
    )
    m = MetalArchives(client=client)
    band = m.random_band(genre="black", max_attempts=3, sleep_between=0)
    assert band.name == "Carcass"


# ---------------------------------------------------------------------------
# get_lyrics regression — uses external_ids['ma_lyrics_id'] now
# ---------------------------------------------------------------------------


def test_get_lyrics_uses_external_id():
    routes = {
        "search/ajax-advanced/searching/songs": "search_songs_heartwork.json",
        # Any lyric id from the search fixture maps to the same html blob.
        "release/ajax-view-lyrics": "lyrics_172090.html",
    }
    m = MetalArchives(client=_RoutedClient(routes))
    texts = list(m.get_lyrics(song_title="Heartwork", band_name="Carcass"))
    assert texts, "expected at least one lyric returned"
    assert all(isinstance(t, str) and t.strip() for t in texts)


def test_get_lyrics_skips_when_no_lyrics_id():
    """Verify the no-id branch is exercised with a hand-rolled hit list."""
    from pymetal import archives as arch
    # Fake mediavocab Release with empty external_ids.
    class _FakeRelease:
        external_ids = {}
    m = MetalArchives(client=_RoutedClient({}))
    with patch.object(m, "search_songs", return_value=iter([_FakeRelease()])):
        assert list(m.get_lyrics(song_title="x")) == []
