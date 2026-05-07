"""Pydantic v2 data model for metal-archives.com.

Designed to round-trip MA data faithfully. Keys are MA numeric ids
(`ma_id`) so re-scrapes are idempotent. Three relationship entities —
LineupMember, ReleaseLineup, TrackAppearance — encode facts a flat
(track, band, album) model loses (splits, lineup-over-time, track reuse).
"""
from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


# ---------------------------------------------------------------------------
# Enums mirror the exact vocabularies metal-archives renders.
# ---------------------------------------------------------------------------


class ReleaseType(str, Enum):
    FULL_LENGTH = "Full-length"
    EP = "EP"
    DEMO = "Demo"
    SINGLE = "Single"
    SPLIT = "Split"
    LIVE = "Live album"
    COMPILATION = "Compilation"
    VIDEO = "Video"
    BOXED_SET = "Boxed set"
    SPLIT_VIDEO = "Split video"
    COLLABORATION = "Collaboration"


class ReleaseFormat(str, Enum):
    CD = "CD"
    CASSETTE = "Cassette"
    VINYL = "Vinyl"
    VHS = "VHS"
    DVD = "DVD"
    DIGITAL = "Digital"
    BLU_RAY = "Blu-ray"
    OTHER = "Other"


class LineupStatus(str, Enum):
    CURRENT = "current"
    PAST = "past"
    LAST_KNOWN = "last_known"
    LIVE = "live"
    GUEST_SESSION = "guest_session"


class CreditSection(str, Enum):
    """Per-release credit category as MA renders it on a release lineup tab."""

    BAND = "band"            # 'Band members'
    GUEST = "guest"          # 'Guest/session musicians'
    STAFF = "staff"          # 'Miscellaneous staff' (producer, engineer, cover art)


class BandStatus(str, Enum):
    ACTIVE = "Active"
    SPLIT_UP = "Split-up"
    ON_HOLD = "On hold"
    UNKNOWN = "Unknown"
    CHANGED_NAME = "Changed name"
    DISPUTED = "Disputed"


# ---------------------------------------------------------------------------
# Audit metadata (MA renders this on every band/release/artist page).
# ---------------------------------------------------------------------------


class Audit(BaseModel):
    added_by: Optional[str] = None
    modified_by: Optional[str] = None
    added_on: Optional[str] = None
    last_modified_on: Optional[str] = None


# ---------------------------------------------------------------------------
# Core entities
# ---------------------------------------------------------------------------


class Label(BaseModel):
    ma_id: Optional[int] = None
    name: str
    url: Optional[HttpUrl] = None
    country: Optional[str] = None
    status: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[HttpUrl] = None
    styles: Optional[str] = None
    founding_date: Optional[str] = None
    sub_labels: List[str] = Field(default_factory=list)
    parent_label_id: Optional[int] = None
    parent_label_name: Optional[str] = None
    online_shopping: Optional[str] = None
    logo_url: Optional[HttpUrl] = None
    audit: Optional[Audit] = None


class UpcomingRelease(BaseModel):
    """A release in MA's upcoming-albums list."""

    band_id: Optional[int] = None
    band_name: str
    release_id: Optional[int] = None
    release_title: str
    type: Optional[ReleaseType] = None
    genre: Optional[str] = None
    release_date: Optional[str] = None  # human-readable, e.g. "April 29th, 2026"


class BandRecommendation(BaseModel):
    """A row from MA's 'Similar artists' tab."""

    band_id: int
    name: str
    url: Optional[HttpUrl] = None
    country: Optional[str] = None
    genre: Optional[str] = None
    match_score: Optional[int] = None  # how many users voted them as similar


class ExternalLink(BaseModel):
    """A single row from a band's or label's external-links tab."""

    name: str  # the service or merch shop label MA shows ('Bandcamp', 'Spotify')
    url: HttpUrl
    section: str = "Other"  # 'Official' / 'Official merchandise' / 'Tabulatures' / 'Other'


class Review(BaseModel):
    """A user review of a release."""

    review_id: Optional[int] = None
    review_url: Optional[HttpUrl] = None
    title: Optional[str] = None  # review's own title (separate from the release)
    band_id: Optional[int] = None
    band_name: str
    release_id: Optional[int] = None
    release_title: str
    score_percent: Optional[int] = None
    username: Optional[str] = None
    posted_on: Optional[str] = None  # 'YYYY-MM-DD HH:MM' once we combine day+time
    body: Optional[str] = None       # only populated by `get_review(review_id)`


class RIPArtist(BaseModel):
    """A row in MA's deceased-artists list (`/artist/rip`)."""

    artist_id: Optional[int] = None
    artist_name: str
    country: Optional[str] = None
    band_id: Optional[int] = None
    band_name: Optional[str] = None
    died_on: Optional[str] = None
    cause: Optional[str] = None


class Band(BaseModel):
    ma_id: Optional[int] = None
    name: str
    url: Optional[HttpUrl] = None
    country: Optional[str] = None
    location: Optional[str] = None
    status: Optional[BandStatus] = None
    formed_in: Optional[str] = None
    years_active: List[str] = Field(default_factory=list)
    genres: List[str] = Field(default_factory=list)
    themes: List[str] = Field(default_factory=list)
    current_label_id: Optional[int] = None
    current_label_name: Optional[str] = None
    last_label_id: Optional[int] = None
    last_label_name: Optional[str] = None
    comment: Optional[str] = None
    logo_url: Optional[HttpUrl] = None
    photo_url: Optional[HttpUrl] = None
    audit: Optional[Audit] = None


class Artist(BaseModel):
    ma_id: Optional[int] = None
    alias: Optional[str] = None
    real_name: Optional[str] = None
    url: Optional[HttpUrl] = None
    country: Optional[str] = None
    gender: Optional[str] = None
    born: Optional[str] = None
    died: Optional[str] = None  # the 'R.I.P.' date MA renders for deceased artists
    died_of: Optional[str] = None
    place_of_origin: Optional[str] = None
    photo_url: Optional[HttpUrl] = None
    biography: Optional[str] = None
    audit: Optional[Audit] = None


class Release(BaseModel):
    ma_id: Optional[int] = None
    title: str
    url: Optional[HttpUrl] = None
    type: ReleaseType
    release_date: Optional[str] = None
    label_id: Optional[int] = None
    label_name: Optional[str] = None
    catalog_no: Optional[str] = None
    format: Optional[ReleaseFormat] = None
    format_raw: Optional[str] = None  # MA sometimes adds qualifiers, e.g. "CD, limited edition"
    version_description: Optional[str] = None
    limitation: Optional[str] = None
    reviews_count: Optional[int] = None
    reviews_avg_percent: Optional[int] = None
    notes: Optional[str] = None
    band_ids: List[int] = Field(default_factory=list)  # populated for splits/collaborations
    cover_url: Optional[HttpUrl] = None
    total_length: Optional[str] = None  # MA renders the running time per release
    audit: Optional[Audit] = None


class Song(BaseModel):
    """Canonical song identity. Survives across releases."""

    ma_id: Optional[int] = None
    title: str
    length: Optional[str] = None  # MM:SS as MA renders it
    # The id used by /release/ajax-view-lyrics. Alphanumeric ('340', '589A').
    # Always pass `.lyrics_id` to `get_lyrics_by_song_id()`.
    lyrics_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Relationship entities
# ---------------------------------------------------------------------------


class LineupMember(BaseModel):
    """Time-sliced band membership.

    One artist can have several rows for the same band (left + rejoined,
    instrument switch). Don't derive `current` from `date_to is None` —
    metal-archives distinguishes 'last known' from 'current' for inactive
    bands.
    """

    band_id: int
    artist_id: int
    artist_name: Optional[str] = None
    role: str
    status: LineupStatus
    date_from: Optional[str] = None
    date_to: Optional[str] = None


class ReleaseLineup(BaseModel):
    """Who actually played on this specific release.

    `band_id` distinguishes attribution on splits/collaborations.
    `section` mirrors MA's three credit categories (band / guest / staff).
    """

    release_id: int
    band_id: Optional[int] = None  # None for staff credits not tied to a band
    artist_id: int
    artist_name: Optional[str] = None
    role: str
    section: CreditSection = CreditSection.BAND
    credit_note: Optional[str] = None


class TrackAppearance(BaseModel):
    """A song's appearance on a release.

    The join that makes a track reusable across releases AND attributable
    per-band on splits. `title_override` handles re-titled re-issues while
    `song_id` stays stable.
    """

    release_id: int
    song_id: int
    band_id: int
    track_no: int
    disc_no: int = 1
    title_override: Optional[str] = None
    length: Optional[str] = None
    is_bonus: bool = False
    is_instrumental: bool = False


# ---------------------------------------------------------------------------
# Search-result shapes — richer than Band/Song because the AJAX rows carry
# band_id, release_id and lyrics_id that we'd otherwise discard.
# ---------------------------------------------------------------------------


class BandSearchHit(BaseModel):
    ma_id: Optional[int]
    name: str
    url: Optional[HttpUrl] = None
    genre: Optional[str] = None
    country: Optional[str] = None


class AlbumSearchHit(BaseModel):
    ma_id: Optional[int]
    title: str
    url: Optional[HttpUrl] = None
    band_id: Optional[int] = None
    band_name: Optional[str] = None
    genre: Optional[str] = None
    type: Optional[ReleaseType] = None
    release_date: Optional[str] = None


class SongSearchHit(BaseModel):
    song_id: str  # alphanumeric MA song id
    title: str
    band_id: Optional[int] = None
    band_name: Optional[str] = None
    release_id: Optional[int] = None
    release_title: Optional[str] = None
    release_type: Optional[ReleaseType] = None
    lyrics_id: Optional[str] = None
