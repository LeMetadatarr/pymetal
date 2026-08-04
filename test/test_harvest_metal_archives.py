"""Row-schema equivalence tests for the metal_archives bulk harvester.

These lock the exact flat-row shape emitted by MetalArchivesSource against a
realistic upstream sample — moved verbatim (schema unchanged) from
metadatarr's test_scrapers_batch2.py when the scraper was ported onto the
shared harvestkit engine.
"""
from __future__ import annotations

from pymetal.harvest.bands import MetalArchivesSource


def test_metal_archives_map_row_schema():
    src = MetalArchivesSource()
    row_data = ['<a href="https://www.metal-archives.com/bands/Metallica/125">Metallica</a>',
                "United States", "Thrash Metal", "Active"]
    row = src.map_row(row_data)
    assert row["ma_id"] == "125"
    assert row["name"] == "Metallica"
    assert row["country"] == "United States"
    assert set(row) == {"ma_id", "name", "url", "country", "genre", "status"}


def test_metal_archives_fetch_stops_at_total():
    src = MetalArchivesSource()
    src.get_json = lambda url, params: {
        "iTotalRecords": 1,
        "aaData": [['<a href="/bands/X/1">X</a>', "US", "Rock", "Active"]],
    }
    rows, cursor = src.fetch(0)
    assert len(rows) == 1
    assert cursor is None
