"""Unit tests for endpoint helpers — no network."""
from lxml import html as lxml_html

from pymetal.endpoints._common import (
    collect_stats,
    dl_pairs,
    extract_audit,
    first,
    ma_id_from_url,
    parse_int,
    split_csv,
)
from pymetal.endpoints.bands import _parse_role_dates
from pymetal.endpoints.releases import (
    _coerce_release_type,
    _parse_reviews,
    _split_band_and_title,
    _sum_lengths,
)
from pymetal.models import ReleaseType


def test_ma_id_from_url():
    assert ma_id_from_url("https://www.metal-archives.com/bands/Carcass/144") == 144
    assert ma_id_from_url("https://www.metal-archives.com/albums/Carcass/Heartwork/536/") == 536
    assert ma_id_from_url(None) is None
    assert ma_id_from_url("no-id-here") is None


def test_split_csv_handles_multiple_separators():
    assert split_csv("Death Metal, Grindcore | Melodic Death Metal") == [
        "Death Metal",
        "Grindcore",
        "Melodic Death Metal",
    ]
    assert split_csv("") == []
    assert split_csv(None) == []


def test_first_skips_na_and_empty():
    assert first(["", "  ", "N/A", "ok"]) == "ok"
    assert first([]) is None


def test_parse_role_dates():
    # only the outer span — first start, first end of the leading stint
    assert _parse_role_dates("Vocals (1985-1990, 2007-present)") == ("1985", "1990")
    assert _parse_role_dates("Bass (1991-1995)") == ("1991", "1995")
    assert _parse_role_dates("Drums") == (None, None)


def test_coerce_release_type_exact_and_fuzzy():
    assert _coerce_release_type("Full-length") is ReleaseType.FULL_LENGTH
    assert _coerce_release_type("Split") is ReleaseType.SPLIT
    assert _coerce_release_type("Live album") is ReleaseType.LIVE
    assert _coerce_release_type("Split video") is ReleaseType.SPLIT_VIDEO
    assert _coerce_release_type("some unknown split thing") is ReleaseType.SPLIT  # fuzzy
    assert _coerce_release_type(None) is ReleaseType.FULL_LENGTH


def test_parse_reviews_release_page_format():
    # Release page renders "23 reviews (avg. 85%)"
    assert _parse_reviews("23 reviews (avg. 85%)") == (23, 85)
    # Discography column renders "2 (85%)"
    assert _parse_reviews("2 (85%)") == (2, 85)
    # No reviews
    assert _parse_reviews("") == (None, None)
    assert _parse_reviews(None) == (None, None)
    # Missing percent
    assert _parse_reviews("5 reviews") == (5, None)


def test_sum_lengths():
    assert _sum_lengths(["03:30", "04:00", "02:30"]) == "10:00"
    # Carry over to hours
    assert _sum_lengths(["45:00", "20:00"]) == "01:05:00"
    # Already-HH:MM:SS preserved
    assert _sum_lengths(["01:02:03", "00:01:00"]) == "01:03:03"
    # Empty / unparseable
    assert _sum_lengths([]) is None
    assert _sum_lengths([None, "", "n/a"]) is None
    # Mixed valid / invalid skips invalid
    assert _sum_lengths(["03:30", "garbage"]) == "03:30"


def test_split_band_and_title():
    """Split-release track titles like 'BAND - Song' should split cleanly."""
    assert _split_band_and_title("S.O.B - Repeat at Length") == ("S.O.B", "Repeat at Length")
    assert _split_band_and_title("Napalm Death - Multinational Corporations (Part 2)") == (
        "Napalm Death",
        "Multinational Corporations (Part 2)",
    )
    # Plain title with no prefix → (None, original)
    assert _split_band_and_title("Heartwork") == (None, "Heartwork")
    # MA's tab-laden whitespace from one <td> with newlines normalises out
    assert _split_band_and_title("S.O.B -\n\t\t\tDevice") == ("S.O.B", "Device")


def test_parse_int():
    assert parse_int("42") == 42
    assert parse_int("23 reviews") == 23
    assert parse_int(None) is None
    assert parse_int("no digits") is None


def test_dl_pairs_extracts_link_href():
    fragment = lxml_html.fromstring(
        '<dl><dt>Country:</dt><dd><a href="/c/PT">Portugal</a></dd>'
        '<dt>Genre:</dt><dd>Heavy</dd></dl>'
    )
    pairs = dl_pairs(fragment)
    assert pairs["Country"] == "Portugal"
    assert pairs["Country :href"] == "/c/PT"
    assert pairs["Genre"] == "Heavy"
    assert "Genre :href" not in pairs


def test_collect_stats_merges_multiple_dls():
    fragment = lxml_html.fromstring(
        '<div id="x">'
        '<dl><dt>A:</dt><dd>1</dd></dl>'
        '<dl><dt>B:</dt><dd>2</dd></dl>'
        "</div>"
    )
    assert collect_stats(fragment, '//*[@id="x"]/dl') == {"A": "1", "B": "2"}


def test_extract_audit_returns_none_when_absent():
    fragment = lxml_html.fromstring("<html><body>no audit here</body></html>")
    assert extract_audit(fragment) is None


def test_extract_audit_parses_known_labels():
    fragment = lxml_html.fromstring(
        '<table id="auditTrail"><tr>'
        "<td>Added by: alice</td>"
        "<td>Modified by: bob</td>"
        "<td>Added on: 2010-01-01 00:00:00</td>"
        "<td>Last modified on: 2026-04-29 12:00:00</td>"
        "</tr></table>"
    )
    a = extract_audit(fragment)
    assert a is not None
    assert a.added_by == "alice"
    assert a.modified_by == "bob"
    assert a.added_on == "2010-01-01 00:00:00"
    assert a.last_modified_on == "2026-04-29 12:00:00"


def test_normalise_genre_reduces_simple_coarse_genres():
    from pymetal.archives import _normalise_genre
    from pymetal.locators import GENRES

    assert _normalise_genre("Death Metal") == "death"
    assert _normalise_genre("Black Metal") == "black"
    assert _normalise_genre("Thrash Metal") == "thrash"
    assert _normalise_genre("Death Metal") in GENRES


def test_normalise_genre_does_not_reduce_compound_genres():
    """Real MA band pages carry compound genre strings ('Melodic Death
    Metal', 'Power/Melodic Death Metal') that `_normalise_genre` cannot
    reduce to a single `GENRES` bucket — callers must reject these rather
    than silently treating them as unfiltered (see `random_band`)."""
    from pymetal.archives import _normalise_genre
    from pymetal.locators import GENRES

    assert _normalise_genre("Melodic Death Metal") not in GENRES
    assert _normalise_genre("Power/Melodic Death Metal") not in GENRES
