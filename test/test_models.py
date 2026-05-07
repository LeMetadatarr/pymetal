"""Model-level tests — no network. Covers the three semantics that the
old flat (track, band, album) model could not represent.
"""
from __future__ import annotations

import pytest

from pymetal.models import (
    Band,
    LineupMember,
    LineupStatus,
    Release,
    ReleaseLineup,
    ReleaseType,
    Song,
    TrackAppearance,
)


def test_release_type_enum_round_trip():
    r = Release(ma_id=1, title="Heartwork", type=ReleaseType.FULL_LENGTH)
    j = r.model_dump_json()
    r2 = Release.model_validate_json(j)
    assert r2.type is ReleaseType.FULL_LENGTH


def test_track_on_multiple_releases_shares_song_id():
    """Compilation reuses a song_id from a studio album."""
    studio = Release(ma_id=10, title="Necroticism", type=ReleaseType.FULL_LENGTH)
    comp = Release(ma_id=11, title="Choice Cuts", type=ReleaseType.COMPILATION)
    song = Song(ma_id=999, title="Corporal Jigsore Quandary")
    apps = [
        TrackAppearance(release_id=studio.ma_id, song_id=song.ma_id, band_id=144, track_no=2),
        TrackAppearance(release_id=comp.ma_id, song_id=song.ma_id, band_id=144, track_no=5),
    ]
    by_song = [a for a in apps if a.song_id == song.ma_id]
    assert {a.release_id for a in by_song} == {10, 11}


def test_split_release_attributes_tracks_to_different_bands():
    """A Split release has TrackAppearance rows with two band_ids."""
    split = Release(ma_id=20, title="Napalm Death / S.O.B.", type=ReleaseType.SPLIT)
    apps = [
        TrackAppearance(release_id=split.ma_id, song_id=1, band_id=200, track_no=1),
        TrackAppearance(release_id=split.ma_id, song_id=2, band_id=201, track_no=2),
    ]
    bands_on_release = {a.band_id for a in apps if a.release_id == split.ma_id}
    assert bands_on_release == {200, 201}


def test_lineup_over_time_same_artist_two_stints():
    """One artist, two non-overlapping stints in the same band."""
    rows = [
        LineupMember(
            band_id=144, artist_id=42, role="Vocals",
            status=LineupStatus.PAST, date_from="1985", date_to="1990",
        ),
        LineupMember(
            band_id=144, artist_id=42, role="Vocals",
            status=LineupStatus.CURRENT, date_from="2007", date_to=None,
        ),
    ]
    stints = [r for r in rows if r.artist_id == 42 and r.band_id == 144]
    assert len(stints) == 2
    assert {r.status for r in stints} == {LineupStatus.PAST, LineupStatus.CURRENT}


def test_release_lineup_resolves_who_played_on_a_release():
    """ReleaseLineup is the authoritative answer to 'who recorded this'."""
    rl = ReleaseLineup(release_id=10, band_id=144, artist_id=42, role="Vocals")
    j = rl.model_dump_json()
    assert ReleaseLineup.model_validate_json(j) == rl


@pytest.mark.parametrize(
    "model, kwargs",
    [
        (Band, dict(ma_id=1, name="Carcass")),
        (Song, dict(ma_id=1, title="x")),
        (Release, dict(ma_id=1, title="x", type=ReleaseType.EP)),
        (TrackAppearance, dict(release_id=1, song_id=1, band_id=1, track_no=1)),
        (LineupMember, dict(band_id=1, artist_id=1, role="r", status=LineupStatus.CURRENT)),
        (ReleaseLineup, dict(release_id=1, band_id=1, artist_id=1, role="r")),
    ],
)
def test_round_trip(model, kwargs):
    obj = model(**kwargs)
    assert model.model_validate_json(obj.model_dump_json()) == obj
