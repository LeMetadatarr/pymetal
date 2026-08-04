# pymetal

A Python client for [Encyclopaedia Metallum](https://www.metal-archives.com/) (the Metal Archives). It uses a relational data model that keeps facts flat scrapers usually lose: splits, lineups that change over time, and tracks reused across releases.

Built on `curl_cffi` for TLS-fingerprint bypass and `pydantic` for typed, validated data.

## Why

Most scrapers model `Track = (id, title, band, album)`. That model collapses three facts that MA keeps separate.

- A track can have **multiple bands** (split releases, collaborations).
- A band's **lineup is time-sliced**. The same band on two tracks can mean different people.
- A track can **appear on many releases** (compilations, re-issues, singles).

`pymetal` models each fact as a separate entity (`TrackAppearance`, `LineupMember`, `ReleaseLineup`), keyed by metal-archives ids. This keeps re-scrapes idempotent.

## Install

```bash
pip install -e .
```

Requires Python 3.10+. Pulls in `curl_cffi`, `lxml`, `pydantic>=2`, and `random-user-agent`.

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

More examples are in [`examples/`](examples/):
- [`metalarchives.py`](examples/metalarchives.py): a full API tour
- [`browse.py`](examples/browse.py): catalog walks (country, genre, letter, labels, reviews, upcoming, RIP)
- [`portuguese_heavy_metal_pre2000.py`](examples/portuguese_heavy_metal_pre2000.py): a resumable lyrics-corpus crawl
- [`metallvm-rest.py`](examples/metallvm-rest.py): a FastAPI server that exposes every endpoint over HTTP

## Endpoints

### Search (advanced-search forms)

| Function | What it returns |
|---|---|
| `search_bands(...)` | `Iterator[BandSearchHit]`. Covers every advanced filter: country, status, year range, themes, location, label. |
| `search_albums(...)` | `Iterator[AlbumSearchHit]`. Covers release type, format, label, catalog/barcode, year and month range. |
| `search_songs(...)` | `Iterator[SongSearchHit]`. Full-text lyrics search, carries band_id, release_id, and lyrics_id. |

### Detail pages

| Function | What it returns |
|---|---|
| `get_band(id)` | `Band`: name, country, genres, themes, labels, comment, photo, audit. |
| `get_lineup(id)` | `List[LineupMember]`, partitioned by status with role-date ranges. |
| `get_release(id)` | `(Release, List[Song], List[TrackAppearance])`. Splits attribute tracks per band. |
| `get_release_lineup(id)` | `List[ReleaseLineup]`: band, guest, and staff credits. |
| `get_other_versions(id)` | `List[Release]`: re-issues, re-masters, regional editions. |
| `get_discography(id)` | `List[Release]` |
| `get_artist(id)` | `Artist`: real name, born, R.I.P., died of, place of birth. |
| `get_label(id)` | `Label`: address, phone, styles, founding date, sub-labels, parent. |
| `get_band_recommendations(id)` | `List[BandRecommendation]`, MA's "Similar artists" tab. |
| `get_band_reviews(id)` | `Iterator[Review]`, every user review of every release by a band. |
| `get_links(id, entity_type='band')` | `List[ExternalLink]`: Bandcamp, Spotify, and merch links grouped by section. |
| `get_lyrics_by_song_id(id)` | `Optional[str]` |
| `get_lyrics(...)` | `Iterator[str]`, a combined search and lyrics fetch. |

### Catalog browse and discovery

| Function | What it returns |
|---|---|
| `browse_bands_by_country(code)` | `Iterator[BandSearchHit]`, the full country listing. |
| `browse_bands_by_genre(slug)` | `Iterator[BandSearchHit]`, from a 23-bucket coarse taxonomy. |
| `browse_bands_by_letter(letter)` | `Iterator[BandSearchHit]`, alphabetical (A-Z, NBR, ~). |
| `browse_labels_by_country(code)` | `Iterator[Label]` |
| `browse_labels_by_letter(letter)` | `Iterator[Label]` |
| `browse_reviews(year, month)` | `Iterator[Review]`, reviews posted in a given month. |
| `get_upcoming_releases()` | `Iterator[UpcomingRelease]`, scheduled future releases. |
| `get_rip_artists()` | `Iterator[RIPArtist]`, MA's deceased-artists list. |
| `list_countries()` | `dict[code, name]`, all MA-known country codes. |
| `list_genre_slugs()` | `list[str]`, the 23 genre browse slugs. |

All functions return Pydantic v2 models. `.model_dump_json()` round-trips on every type.

## Documentation

- [Getting Started](docs/getting_started.md): install and first commands.
- [API Reference](docs/api_reference.md): every public class and method.
- [Advanced Usage](docs/advanced_usage.md): splits, lineups over time, pagination, caching, lyrics download.
- [Developer Guide](docs/developer_guide.md): adding endpoints, capturing fixtures, running tests.

## Bulk harvesting (optional)

`pymetal` itself is a query client — it fetches one band, one release, one page at
a time. For a full catalogue dump (every band Metal Archives lists), install the
`harvest` extra, which adds a resumable bulk scraper built on
[harvestkit](https://github.com/LeMetadatarr/harvestkit):

```bash
pip install pymetal[harvest]
pymetal-harvest                 # or: python -m harvestkit metal_archives
```

This walks the public browse-bands endpoint end to end and writes a JSONL band
dataset (`ma_id`, `name`, `url`, `country`, `genre`, `status`) with resume-on-restart
checkpointing. It is not part of the base install.

## Related projects

- [metadatarr](https://github.com/LeMetadatarr/metadatarr): metadata aggregation across the `pymetal` family of clients.
- [pymusicbrainz](https://github.com/LeMetadatarr/pymusicbrainz): a Python client for the MusicBrainz database.
- [pydiscogs](https://github.com/LeMetadatarr/pydiscogs): a Python client for Discogs.
- [pyrateyourmusic](https://github.com/LeMetadatarr/pyrateyourmusic): a Python client for Rate Your Music.

## License

Apache 2.0
