# Getting Started

## Install

```bash
pip install -e .
```

Python 3.10+. Dependencies: `curl_cffi`, `lxml`, `pydantic>=2`, `random-user-agent`.

## The facade

`MetalArchives` wraps every endpoint and shares one `Client` (HTTP + cache):

```python
from pymetal import MetalArchives
ma = MetalArchives()
```

You can also import endpoint functions directly:

```python
from pymetal.endpoints import get_band, search_bands, get_release
```

Both forms accept a `client=` keyword for testing or running multiple isolated sessions.

## Five-minute tour

### 1. Search

`search_bands`, `search_albums`, `search_songs` mirror the metal-archives advanced-search forms:

```python
# Active Portuguese heavy metal bands formed 1980–1989
for b in ma.search_bands(
    country="PT",
    genre="Heavy",
    year_from=1980, year_to=1989,
    status=["active"],
):
    print(b.ma_id, b.name)

# Full-length and EP releases by Carcass
from pymetal import ReleaseType
for r in ma.search_albums(
    band_name="Carcass",
    release_type=[ReleaseType.FULL_LENGTH, ReleaseType.EP],
    paginate=True,
):
    print(r.ma_id, r.title, r.type)

# Songs whose lyrics contain a phrase
for s in ma.search_songs(lyrics="ace of spades"):
    print(s.band_name, "—", s.title, f"(lyrics_id={s.lyrics_id})")
```

`paginate=True` walks every page until `iTotalRecords` is exhausted.

### 2. Band + lineup

```python
band = ma.get_band(14)  # Carcass
print(band.country, band.formed_in, band.genres, band.current_label_name)
print(band.audit.added_on, band.audit.last_modified_on)

for m in ma.get_lineup(14):
    print(m.status, m.artist_name, m.role, m.date_from, "→", m.date_to)
```

### 3. Release with tracks

```python
release, songs, appearances = ma.get_release(451600)
print(release.title, release.type, release.cover_url, release.total_length)

# `appearances` is the join row carrying band_id (matters for splits) and track_no.
for app in appearances:
    print(app.track_no, app.song_id, app.band_id, app.length)
```

For a split release, `appearances` will have `band_id`s for *each* band on the release.

### 4. Per-release credits

```python
from pymetal import CreditSection
for c in ma.get_release_lineup(451600):
    if c.section is CreditSection.STAFF:
        print("staff:", c.artist_name, c.role)
```

### 5. Re-issues / other versions

```python
for v in ma.get_other_versions(451600):
    print(v.release_date, v.format, v.catalog_no, v.label_name)
```

### 6. Lyrics

```python
text = ma.get_lyrics_by_song_id(172090)
```

## Where next

- [API Reference](api_reference.md) — every model and function.
- [Advanced Usage](advanced_usage.md) — splits, lineup-at-time, caching, full-corpus crawls.
