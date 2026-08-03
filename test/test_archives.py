"""Facade-level tests: `MetalArchives` delegates to the endpoint modules.

Uses the `fake_client` fixture from conftest.py to serve captured HTML.
"""
from __future__ import annotations

import json
import os
import unittest

from pymetal.archives import MetalArchives
from pymetal.models import BandStatus, ReleaseType


FIXTURES_PATH = os.path.join(os.path.dirname(__file__), "fixtures")
HTML_FIXTURES = os.path.join(FIXTURES_PATH, "html")


class _FakeResponse:
    def __init__(self, content: bytes) -> None:
        self.content = content
        self.text = content.decode("utf-8", errors="replace")
        self.url = ""
        self.from_cache = True


class _FakeClient:
    def __init__(self, routes):
        self.routes = routes

    def _read(self, path):
        for needle, fname in self.routes.items():
            if needle in path:
                with open(os.path.join(HTML_FIXTURES, fname), "rb") as f:
                    return f.read()
        raise AssertionError(f"no route for {path!r}")

    def get(self, path, params=None, use_cache=True):
        return _FakeResponse(self._read(path))

    def get_json(self, path, params=None):
        return json.loads(self._read(path).decode("utf-8"))


class TestMetalArchivesFacade(unittest.TestCase):
    def test_get_band_via_id(self):
        m = MetalArchives(client=_FakeClient({"bands/_/14": "band_carcass.html"}))
        b = m.get_band(14)
        self.assertEqual(b.name, "Carcass")
        self.assertEqual(b.country, "United Kingdom")
        self.assertIs(b.status, BandStatus.ACTIVE)

    def test_get_band_by_url(self):
        m = MetalArchives(client=_FakeClient({"bands/_/14": "band_carcass.html"}))
        b = m.get_band_by_url("https://www.metal-archives.com/bands/Carcass/14")
        self.assertEqual(b.ma_id, 14)

    def test_search_bands_iterator(self):
        m = MetalArchives(
            client=_FakeClient(
                {"search/ajax-advanced/searching/bands": "search_bands_carcass.json"}
            )
        )
        hits = list(m.search_bands(band_name="Carcass"))
        self.assertGreater(len(hits), 0)
        self.assertEqual(hits[0].name, "Carcass")

    def test_search_songs_returns_search_hit(self):
        m = MetalArchives(
            client=_FakeClient(
                {"search/ajax-advanced/searching/songs": "search_songs_heartwork.json"}
            )
        )
        hits = list(m.search_songs(song_title="Heartwork", band_name="Carcass"))
        self.assertGreater(len(hits), 0)
        self.assertTrue(all(h.title and h.lyrics_id for h in hits))

    def test_get_release_full_length(self):
        m = MetalArchives(
            client=_FakeClient({"albums/_/_/451600": "release_heartwork.html"})
        )
        rel, songs, apps = m.get_release(451600)
        self.assertIs(rel.type, ReleaseType.FULL_LENGTH)
        self.assertEqual(len(apps), 10)

    def test_get_lineup(self):
        m = MetalArchives(client=_FakeClient({"bands/_/14": "band_carcass.html"}))
        rows = m.get_lineup(14)
        self.assertGreater(len(rows), 0)


class _RandomBandFakeClient:
    """Serves a fixed `band/random` redirect (via `resp.url`) plus the
    matching band detail fixture, so `random_band()` can be exercised
    without hitting the network."""

    def __init__(self, band_id: int, band_fixture: str) -> None:
        self.band_id = band_id
        self.band_fixture = band_fixture
        self.calls = 0

    def get(self, path, params=None, use_cache=True):
        self.calls += 1
        if path == "band/random":
            url = f"https://www.metal-archives.com/bands/X/{self.band_id}"
            return _FakeResponse(b"")._with_url(url)
        with open(os.path.join(HTML_FIXTURES, self.band_fixture), "rb") as f:
            return _FakeResponse(f.read())

    def get_json(self, path, params=None):
        raise AssertionError("random_band should not need get_json")


def _with_url(self, url):
    self.url = url
    return self


_FakeResponse._with_url = _with_url


class TestRandomBand(unittest.TestCase):
    def test_random_band_matches_requested_genre(self):
        """Mayhem (id 67) is tagged 'Black Metal' — genre='black' must match."""
        m = MetalArchives(client=_RandomBandFakeClient(67, "band_mayhem.html"))
        b = m.random_band(genre="black", max_attempts=3, sleep_between=0)
        self.assertEqual(b.ma_id, 67)
        self.assertEqual(b.name, "Mayhem")

    def test_random_band_rerolls_when_genre_does_not_match(self):
        """Mayhem is Black Metal, not Death Metal — 'death' must exhaust
        attempts (re-rolling the same non-matching band each time) and
        fall back to the last band seen rather than hang."""
        m = MetalArchives(client=_RandomBandFakeClient(67, "band_mayhem.html"))
        b = m.random_band(genre="death", max_attempts=2, sleep_between=0)
        # No match found within max_attempts -> falls back to last_band.
        self.assertEqual(b.ma_id, 67)

    def test_random_band_unsupported_genre_raises(self):
        """Regression: previously an unrecognised/compound genre (e.g. a
        real MA compound tag like 'Melodic Death Metal') silently disabled
        the filter and matched *any* band instead of raising. Verified live
        against metal-archives.com on 2026-08-03: random bands routinely
        carry compound genre strings like 'Power/Melodic Death Metal' that
        `_normalise_genre` cannot reduce to a `GENRES` bucket."""
        m = MetalArchives(client=_RandomBandFakeClient(67, "band_mayhem.html"))
        with self.assertRaises(ValueError):
            m.random_band(genre="Melodic Death Metal", max_attempts=3, sleep_between=0)

    def test_random_band_no_genre_returns_first_hit(self):
        m = MetalArchives(client=_RandomBandFakeClient(67, "band_mayhem.html"))
        b = m.random_band(max_attempts=3, sleep_between=0)
        self.assertEqual(b.ma_id, 67)


class TestLegacyJSONFixtures(unittest.TestCase):
    """Sanity-check that the historical pre-parsed JSON fixtures still load."""

    def test_load_legacy_fixtures(self):
        for f in (
            "random_band",
            "band_burzum",
            "search_band_metallica",
            "search_song_bmik",
            "lyrics_1780488",
        ):
            with open(os.path.join(FIXTURES_PATH, f"{f}.json")) as fh:
                self.assertIsNotNone(json.load(fh))


if __name__ == "__main__":
    unittest.main()
