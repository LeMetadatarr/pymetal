# API Reference

Every public symbol is re-exported from the `pymetal` top-level package.

## Models

All models are Pydantic v2; round-trip with `.model_dump_json()` /
`Model.model_validate_json()`.

### Core entities

#### `Band`

| Field | Type | Notes |
|---|---|---|
| `ma_id` | `int` | metal-archives numeric id |
| `name` | `str` | |
| `url` | `HttpUrl` | |
| `country` | `str` | |
| `location` | `str` | |
| `status` | `BandStatus` | `Active` / `Split-up` / `On hold` / `Unknown` / `Changed name` / `Disputed` |
| `formed_in` | `str` | year |
| `years_active` | `List[str]` | e.g. `['1986-1996', '2007-present']` |
| `genres` | `List[str]` | |
| `themes` | `List[str]` | |
| `current_label_id` / `current_label_name` | `int` / `str` | |
| `last_label_id` / `last_label_name` | `int` / `str` | |
| `comment` | `str` | free text |
| `logo_url` / `photo_url` | `HttpUrl` | |
| `audit` | `Audit` | added_by / modified_by / added_on / last_modified_on |

#### `Release`

| Field | Type | Notes |
|---|---|---|
| `ma_id` | `int` | |
| `title` | `str` | |
| `url` | `HttpUrl` | |
| `type` | `ReleaseType` | `Full-length` / `EP` / `Demo` / `Single` / `Split` / `Live album` / `Compilation` / `Video` / `Boxed set` / `Split video` / `Collaboration` |
| `release_date` | `str` | as MA renders it ("October 18th, 1993") |
| `label_id` / `label_name` | `int` / `str` | |
| `catalog_no` | `str` | |
| `format` | `ReleaseFormat` | `CD` / `Cassette` / `Vinyl` / `VHS` / `DVD` / `Digital` / `Blu-ray` / `Other` |
| `format_raw` | `str` | unparsed (e.g. `"CD, limited edition"`) |
| `version_description` | `str` | |
| `limitation` | `str` | |
| `reviews_count` / `reviews_avg_percent` | `int` | |
| `notes` | `str` | full text |
| `band_ids` | `List[int]` | populated for splits/collaborations |
| `cover_url` | `HttpUrl` | |
| `total_length` | `str` | summed track lengths |
| `audit` | `Audit` | |

#### `Song`

`ma_id`, `title`, `length`, `lyrics_id`. Canonical song identity — survives
across releases.

#### `Artist`

`ma_id`, `alias`, `real_name`, `country`, `gender`, `born`, `died`,
`died_of`, `place_of_origin`, `photo_url`, `biography`, `audit`.

#### `Label`

`ma_id`, `name`, `url`, `country`, `status`.

### Relationship entities

#### `LineupMember`

| Field | Type | Notes |
|---|---|---|
| `band_id` | `int` | |
| `artist_id` | `int` | |
| `artist_name` | `str` | |
| `role` | `str` | as MA renders it (e.g. `"Bass, Vocals (1986-1996, 2007-present)"`) |
| `status` | `LineupStatus` | `current` / `past` / `last_known` / `live` / `guest_session` |
| `date_from` / `date_to` | `str` | outer span; `None` end == "present" |

A single artist may have several rows for the same band (multiple stints).
Don't derive `current` from `date_to is None` — MA distinguishes
`last_known` for inactive bands.

#### `ReleaseLineup`

`release_id`, `band_id` (Optional — None for staff), `artist_id`,
`artist_name`, `role`, `section: CreditSection` (`band` / `guest` /
`staff`), `credit_note`.

#### `TrackAppearance`

`release_id`, `song_id`, `band_id`, `track_no`, `disc_no`,
`title_override`, `length`, `is_bonus`, `is_instrumental`.

The join row that makes a song reusable across releases AND attributable
per-band on splits.

### Search-result models

`BandSearchHit`, `AlbumSearchHit`, `SongSearchHit`. Carry the ids that
the AJAX result rows expose (band_id, release_id, lyrics_id) — richer
than the full detail models would be when only minimal data is needed.

### Enums

`BandStatus`, `LineupStatus`, `CreditSection`, `ReleaseType`,
`ReleaseFormat`. Values mirror the exact strings metal-archives renders.

---

## Functions

All functions accept `client: Optional[Client]` as a keyword argument.
The default is a process-wide `default_client` with TLS-fingerprint
bypass and a 5-minute response cache.

### Bands

`get_band(band_id) -> Band`
Fetch a band's detail page.

`get_lineup(band_id) -> List[LineupMember]`
Returns one row per (artist, role) per status section.

### Releases

`get_release(release_id) -> Tuple[Release, List[Song], List[TrackAppearance]]`
The release record plus its tracklist with band attribution. For splits,
`appearances[i].band_id` resolves to the per-track band.

`get_discography(band_id) -> List[Release]`
All releases for a band (no tracks).

`get_release_lineup(release_id) -> List[ReleaseLineup]`
Per-release credits, partitioned by `CreditSection`.

`get_other_versions(release_id) -> List[Release]`
Re-issues, re-masters, regional editions of a release.

### Artists

`get_artist(artist_id) -> Artist`

### Lyrics

`get_lyrics_by_song_id(song_id) -> Optional[str]`
Returns `None` when MA reports `(lyrics not available)`.

`get_lyrics(song_title="", band_name="", release_type=None) -> Iterator[str]`
High-level helper — searches songs, then yields their lyrics.

### Search

```python
search_bands(
    band_name="", *,
    exact_band_match=False,
    genre="",
    country="",                    # str or list of MA codes
    year_from=None, year_to=None,
    status=None,                   # list of names ('active') or codes (1..6)
    themes="",
    location="",
    label="",
    indie_label=False,
    band_notes="",
    index=0, page_size=200, paginate=False,
) -> Iterator[BandSearchHit]
```

```python
search_albums(
    band_name="", release_title="", *,
    exact_band_match=False, exact_release_match=False,
    year_from=None, year_to=None,
    month_from=None, month_to=None,
    country="",                    # or list
    location="",
    label="", indie_label=False,
    catalog_number="",
    identifiers="",                # barcode / ISRC / matrix
    recording_info="",
    description="",
    notes="",
    genre="",
    release_type=None,             # list of names, codes, or ReleaseType members
    release_format=None,           # list of names or codes
    index=0, page_size=200, paginate=False,
) -> Iterator[AlbumSearchHit]
```

```python
search_songs(
    song_title="", *,
    exact_song_match=False,
    band_name="", exact_band_match=False,
    release_title="", exact_release_match=False,
    lyrics="",                     # full-text within lyrics
    genre="",
    country="",                    # or list
    release_type=None,
    excluded_release_types=None,
    index=0, page_size=200, paginate=False,
) -> Iterator[SongSearchHit]
```

---

## `MetalArchives`

A facade holding a shared `Client`. Methods delegate to the endpoint
functions, threading `self.client` through.

```python
ma = MetalArchives()                              # uses default_client
ma = MetalArchives(client=Client(cache_ttl=60))   # custom client
```

| Method | Returns |
|---|---|
| `get_band(id)` / `get_band_by_url(url)` | `Band` |
| `get_lineup(id)` | `List[LineupMember]` |
| `get_release(id)` | `(Release, List[Song], List[TrackAppearance])` |
| `get_discography(id)` | `List[Release]` |
| `get_release_lineup(id)` | `List[ReleaseLineup]` |
| `get_other_versions(id)` | `List[Release]` |
| `get_artist(id)` | `Artist` |
| `search_bands(**kw)` / `search_albums(**kw)` / `search_songs(**kw)` | iterators |
| `get_lyrics_by_song_id(id)` | `Optional[str]` |
| `get_lyrics(song_title, band_name, release_type)` | `Iterator[str]` |
| `random_band(genre=None)` | `Band` |

---

## `Client`

`from pymetal import Client`

```python
Client(
    base_url="https://www.metal-archives.com/",
    impersonate="chrome123",
    cache_ttl=300.0,                # seconds; 0 disables expiry
    cache_size=512,                 # entries
)
```

`get(path, params=None, use_cache=True) -> Response` and
`get_json(path, params=None) -> Any`. The cache is in-process, keyed on
(method, url, sorted-params).
