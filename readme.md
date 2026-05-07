# pymetal

A Python client for [Encyclopaedia Metallum](https://www.metal-archives.com/) (the Metal Archives) with a relational data model that captures what flat scrapers lose: splits, lineups changing over time, and tracks reused across releases.

Built on a pluggable HTTP layer (`curl_cffi` for TLS-fingerprint bypass, recommended) and `pydantic` for typed, validated data. Search methods return [`mediavocab`](https://github.com/OpenVoiceOS/mediavocab) `Release` and `Entity` objects for interoperability with other media clients.

## Why

Most scrapers model `Track = (id, title, band, album)`. That collapses three independent facts MA keeps separate:

- a track may have **multiple bands** (split releases, collaborations);
- a band's **lineup is time-sliced** — "the same band" on two tracks may mean different humans;
- a track may **appear on many releases** (compilations, re-issues, singles).

`pymetal` models each as a first-class entity (`TrackAppearance`, `LineupMember`, `ReleaseLineup`) keyed by metal-archives ids so re-scrapes are idempotent.

## Install

Recommended (with `curl_cffi` for browser-impersonated TLS — metal-archives.com is heavily defended):

```bash
pip install pymetal[stealth]
```

Minimal install (plain `requests`, will likely be blocked by metal-archives.com):

```bash
pip install pymetal
```

Requires Python 3.10+. Core deps: `lxml`, `mediavocab`, `pydantic>=2`, `random-user-agent`, `requests`. The `[stealth]` extra adds `curl_cffi`.

### HTTP transport

`pymetal` does not load `curl_cffi` automatically — it is opt-in to keep the
default install lightweight on platforms where `curl_cffi` is hard to build.
Selection rules for the default client:

* `PYMETAL_TRANSPORT=curl_cffi` **and** `curl_cffi` installed → curl_cffi-backed
  client (recommended; bypasses Cloudflare/TLS fingerprinting).
* Otherwise → plain `requests`-backed client + a `RuntimeWarning` noting that
  metal-archives.com may block these requests.

You can also inject your own session into `Client(session=...)` to bypass the
auto-selection entirely (useful for tests, custom retry logic, or proxies):

```python
from pymetal.http import Client
from pymetal import MetalArchives

# Bring-your-own session (anything with a requests-like .get() API).
my_session = ...
ma = MetalArchives(client=Client(session=my_session))
```

## Quick start

```python
from mediavocab import Release, Entity

from pymetal import MetalArchives

ma = MetalArchives()

# Search bands → mediavocab Entity objects
for entity in ma.search_bands(country="PT", genre="Heavy", year_from=1980, year_to=1989):
    print(entity.external_ids.get("ma_band_id"), entity.name, entity.extra.get("country"))

# Search albums → mediavocab Release objects
for release in ma.search_albums(band_name="Carcass", exact_band_match=True):
    artist = release.work.credits[0].entity.name if release.work.credits else ""
    print(release.work.title, artist, release.work.extra.get("release_type"))

# Search songs → mediavocab Release objects (lyrics_id preserved)
for release in ma.search_songs(song_title="Heartwork", band_name="Carcass"):
    lyrics_id = release.work.external_ids.get("ma_lyrics_id")
    print(release.work.title, lyrics_id)

# Pull a full release with all tracks (MA models — rich detail).
release, songs, appearances = ma.get_release(451600)  # Carcass — Heartwork
print(release.cover_url, release.total_length, release.label_name)
print(release.reviews_count, "reviews", release.reviews_avg_percent, "% avg")

# Lineup over time — Current / Past / Live / Last-known / Guest-Session.
for member in ma.get_lineup(14):
    print(member.status, member.artist_name, member.role, member.date_from, member.date_to)

# Lyrics by song id.
print(ma.get_lyrics_by_song_id(172090))
```

### Converting MA models to mediavocab

Detail methods (`get_band`, `get_release`, `get_artist`, `get_label`) return rich MA-specific Pydantic
models. Use the converter functions to get mediavocab objects:

```python
from pymetal import MetalArchives, band_to_entity, ma_release_to_release, artist_to_entity, label_to_entity

ma = MetalArchives()

band = ma.get_band(14)                      # Band (rich MA model)
entity = band_to_entity(band)               # mediavocab Entity
print(entity.name, entity.external_ids)     # {"ma_band_id": "14"}

release, songs, apps = ma.get_release(451600)
mv_release = ma_release_to_release(release)  # mediavocab Release
print(mv_release.work.title, mv_release.external_ids)

artist = ma.get_artist(490)
entity = artist_to_entity(artist)
```

### Return types at a glance

**`Entity`** — from `search_bands`:

```python
entity.name                              # band name
entity.kind                              # EntityKind.GROUP
entity.external_ids.get("ma_band_id")    # MA numeric id
entity.extra.get("artist_url")           # MA profile URL
entity.extra.get("genre")                # genre string
entity.extra.get("country")              # country code
```

**`Release`** — from `search_albums`:

```python
release.uri                              # MA album URL
release.work.title                       # album title
release.work.credits[0].entity.name      # band name (if available)
release.work.external_ids.get("ma_album_id")  # MA numeric id
release.work.extra.get("release_type")   # "Full-length", "EP", etc.
release.work.extra.get("release_date")   # date string
```

**`Release`** — from `search_songs`:

```python
release.work.title                             # song title
release.work.credits[0].entity.name            # band name (if available)
release.work.external_ids.get("ma_song_id")    # MA song id
release.work.external_ids.get("ma_lyrics_id")  # lyrics fetch id
release.work.extra.get("ma_release_title")     # album title
release.work.extra.get("release_type")         # release type
```

More examples in [`examples/`](examples/):
- [`metalarchives.py`](examples/metalarchives.py) — full API tour
- [`browse.py`](examples/browse.py) — catalog walks (country / genre / letter / labels / reviews / upcoming / RIP)
- [`genre_streams.py`](examples/genre_streams.py) — find YouTube / Bandcamp / SoundCloud URLs for bands in a genre
- [`portuguese_heavy_metal_pre2000.py`](examples/portuguese_heavy_metal_pre2000.py) — resumable lyrics-corpus crawl
- [`metallvm-rest.py`](examples/metallvm-rest.py) — FastAPI server exposing every endpoint over HTTP

## Endpoints

### Search (advanced-search forms)

| Function | What it returns |
|---|---|
| `search_bands(...)` | `Iterator[Entity]` — every advanced filter (country, status, year range, themes, location, label) |
| `search_albums(...)` | `Iterator[Release]` — release type, format, label, catalog/barcode, year+month range |
| `search_songs(...)` | `Iterator[Release]` — full-text lyrics search; `ma_lyrics_id` in `work.external_ids` |

### Detail pages

| Function | What it returns |
|---|---|
| `get_band(id)` | `Band` — name, country, genres, themes, labels, comment, photo, audit |
| `get_lineup(id)` | `List[LineupMember]` — partitioned by status with role-date ranges |
| `get_release(id)` | `(Release, List[Song], List[TrackAppearance])` — splits attribute per-band |
| `get_release_lineup(id)` | `List[ReleaseLineup]` — band / guest / staff credits |
| `get_other_versions(id)` | `List[Release]` — re-issues, re-masters, regional editions |
| `get_discography(id)` | `List[Release]` |
| `get_artist(id)` | `Artist` — real name, born, R.I.P., died of, place of birth |
| `get_label(id)` | `Label` — address, phone, styles, founding date, sub-labels, parent |
| `get_band_recommendations(id)` | `List[BandRecommendation]` — MA's "Similar artists" tab |
| `get_band_reviews(id)` | `Iterator[Review]` — every user review of every release by a band |
| `get_links(id, entity_type='band')` | `List[ExternalLink]` — Bandcamp/Spotify/merch grouped by section |
| `get_lyrics_by_song_id(id)` | `Optional[str]` |
| `get_lyrics(...)` | `Iterator[str]` — combined search + lyrics fetch |

### Catalog browse + discovery

| Function | What it returns |
|---|---|
| `browse_bands_by_country(code)` | `Iterator[BandSearchHit]` |
| `browse_bands_by_genre(slug)` | `Iterator[BandSearchHit]` |
| `browse_bands_by_letter(letter)` | `Iterator[BandSearchHit]` |
| `browse_labels_by_country(code)` | `Iterator[Label]` |
| `browse_labels_by_letter(letter)` | `Iterator[Label]` |
| `browse_reviews(year, month)` | `Iterator[Review]` |
| `get_upcoming_releases()` | `Iterator[UpcomingRelease]` |
| `get_rip_artists()` | `Iterator[RIPArtist]` |
| `list_countries()` | `dict[code, name]` |
| `list_genre_slugs()` | `list[str]` |

Detail methods return Pydantic v2 MA models — `.model_dump_json()` round-trip works on every type.
Use `band_to_entity()`, `ma_release_to_release()`, `artist_to_entity()`, `label_to_entity()` to convert to mediavocab.

## Documentation

- [Getting Started](docs/getting_started.md) — install + first commands
- [API Reference](docs/api_reference.md) — every public class + method
- [Advanced Usage](docs/advanced_usage.md) — splits, lineups over time, pagination, caching, lyrics download
- [Developer Guide](docs/developer_guide.md) — adding endpoints, capturing fixtures, running tests

## License

Apache 2.0
