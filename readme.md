# pymetal

A Python client for [Encyclopaedia Metallum](https://www.metal-archives.com/) (the Metal Archives) with a relational data model that captures what flat scrapers lose: splits, lineups changing over time, and tracks reused across releases.

Built on `curl_cffi` for TLS-fingerprint bypass and `pydantic` for typed, validated data.

## Why

Most scrapers model `Track = (id, title, band, album)`. That collapses three independent facts MA keeps separate:

- a track may have **multiple bands** (split releases, collaborations);
- a band's **lineup is time-sliced** — "the same band" on two tracks may mean different humans;
- a track may **appear on many releases** (compilations, re-issues, singles).

`pymetal` models each as a first-class entity (`TrackAppearance`, `LineupMember`, `ReleaseLineup`) keyed by metal-archives ids so re-scrapes are idempotent.

## Install

```bash
pip install -e .
```

Requires Python 3.10+. Pulls `curl_cffi`, `lxml`, `pydantic>=2`, `random-user-agent`.

## Quick start

```python
from pymetal import MetalArchives

ma = MetalArchives()

# Search bands with the full advanced-search filter set.
for hit in ma.search_bands(country="PT", genre="Heavy", year_from=1980, year_to=1989):
    print(hit.ma_id, hit.name, hit.country)

# Pull a release with all its tracks (per-band attribution on splits).
release, songs, appearances = ma.get_release(451600)  # Carcass — Heartwork
print(release.cover_url, release.total_length, release.label_name)
print(release.reviews_count, "reviews", release.reviews_avg_percent, "% avg")

# Lineup over time — Current / Past / Live / Last-known / Guest-Session.
for member in ma.get_lineup(14):
    print(member.status, member.artist_name, member.role, member.date_from, member.date_to)

# Lyrics by song id.
print(ma.get_lyrics_by_song_id(172090))
```

More examples in [`examples/`](examples/):
- [`metalarchives.py`](examples/metalarchives.py) — full API tour
- [`browse.py`](examples/browse.py) — catalog walks (country / genre / letter / labels / reviews / upcoming / RIP)
- [`portuguese_heavy_metal_pre2000.py`](examples/portuguese_heavy_metal_pre2000.py) — resumable lyrics-corpus crawl
- [`metallvm-rest.py`](examples/metallvm-rest.py) — FastAPI server exposing every endpoint over HTTP

## Endpoints

### Search (advanced-search forms)

| Function | What it returns |
|---|---|
| `search_bands(...)` | `Iterator[BandSearchHit]` — every advanced filter (country, status, year range, themes, location, label) |
| `search_albums(...)` | `Iterator[AlbumSearchHit]` — release type, format, label, catalog/barcode, year+month range |
| `search_songs(...)` | `Iterator[SongSearchHit]` — full-text lyrics search; carries band_id / release_id / lyrics_id |

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
| `browse_bands_by_country(code)` | `Iterator[BandSearchHit]` — full country listing |
| `browse_bands_by_genre(slug)` | `Iterator[BandSearchHit]` — 23-bucket coarse taxonomy |
| `browse_bands_by_letter(letter)` | `Iterator[BandSearchHit]` — alphabetical (A–Z, NBR, ~) |
| `browse_labels_by_country(code)` | `Iterator[Label]` |
| `browse_labels_by_letter(letter)` | `Iterator[Label]` |
| `browse_reviews(year, month)` | `Iterator[Review]` — reviews posted in a given month |
| `get_upcoming_releases()` | `Iterator[UpcomingRelease]` — scheduled future releases |
| `get_rip_artists()` | `Iterator[RIPArtist]` — MA's deceased-artists list |
| `list_countries()` | `dict[code, name]` — all MA-known country codes |
| `list_genre_slugs()` | `list[str]` — the 23 genre browse slugs |

All return Pydantic v2 models — `.model_dump_json()` round-trip works on every type.

## Documentation

- [Getting Started](docs/getting_started.md) — install + first commands
- [API Reference](docs/api_reference.md) — every public class + method
- [Advanced Usage](docs/advanced_usage.md) — splits, lineups over time, pagination, caching, lyrics download
- [Developer Guide](docs/developer_guide.md) — adding endpoints, capturing fixtures, running tests

## License

Apache 2.0
