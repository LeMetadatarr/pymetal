# Advanced Usage

## Splits: per-track band attribution

A split release lists multiple bands. metal-archives renders track titles
as `"BAND - Song"` inside one cell. `pymetal` parses the prefix, strips
it into `TrackAppearance.title_override`, and resolves the band id from
the `<h2 class="band_name">` link list at the top of the release page.

```python
release, songs, apps = ma.get_release(485040)  # Napalm Death / S.O.B.
assert release.type.value == "Split"
assert set(release.band_ids) == {219, 6214}

for app in apps:
    print(app.band_id, app.track_no, app.title_override)
# 6214 1 Repeat at Length
# 6214 2 Humanity of Stupidity
# 219  5 Multinational Corporations (Part 2)
# ...
```

## Lineups over time

`get_lineup` returns one row per (artist, role) per status section MA renders
(`band_tab_members_current` / `_past` / `_last` / `_live` / `_guest`).
A single artist with multiple stints in the same band produces one row
per stint.

```python
from pymetal import LineupStatus

rows = ma.get_lineup(14)
walker = [r for r in rows if r.artist_id == 563]  # Jeff Walker
# Bass/Vocals 1986-1996 (past) + 2007-present (current)
```

To answer "who played guitar on song S as released on R":

```python
release, _, apps = ma.get_release(R)
band_id = next(a.band_id for a in apps if a.song_id == S)
for credit in ma.get_release_lineup(R):
    if credit.band_id is None and credit.section.value == "band":
        continue
    if "Guitar" in credit.role:
        print(credit.artist_name, credit.role)
```

`ReleaseLineup` is the source of truth for who recorded a release. You
cannot derive it from `LineupMember`, because session musicians and
guests are not in the band's main lineup.

## Tracks reused across releases

Compilations and re-issues reuse song ids:

```python
hits = list(ma.search_songs(song_title="Heartwork", band_name="Carcass"))
by_song = {}
for h in hits:
    by_song.setdefault(h.lyrics_id, []).append(h.release_title)

for sid, releases in by_song.items():
    if len(releases) > 1:
        print(sid, "appears on:", releases)
```

## Pagination

Search functions take `paginate=True` to walk every page until
`iTotalRecords` is exhausted. Without it you get only `page_size` (200)
hits.

```python
hits = list(ma.search_bands(country="PT", genre="Heavy", paginate=True))
```

`page_size` is also tunable. For large crawls keep it at 200 (MA's
default) and rely on `paginate=True`.

## Caching

The default `Client` keeps a small in-process cache: a 5-minute TTL and
a 512-entry capacity, keyed on (method, url, sorted-params).

```python
from pymetal import Client, MetalArchives

# Disable caching for a one-shot scrape:
ma = MetalArchives(client=Client(cache_ttl=0))

# Or per-call:
resp = ma.client.get("bands/_/14", use_cache=False)
```

The cache stores response bodies, not parsed models, so re-parsing the
same response is cheap on the parser side too.

## Filtering with enums and codes

`status`, `release_type`, and `release_format` filters accept either MA's
exact strings, lowercase aliases, or numeric codes:

```python
from pymetal import ReleaseType

# All three are equivalent:
ma.search_albums(band_name="Carcass", release_type=[ReleaseType.FULL_LENGTH])
ma.search_albums(band_name="Carcass", release_type=["Full-length"])
ma.search_albums(band_name="Carcass", release_type=[1])  # MA's internal code

ma.search_bands(country="PT", status=["active", "on hold"])
ma.search_bands(country="PT", status=[1, 2])
```

Multi-valued filters (`country`, `status`, `release_type`,
`release_format`) accept a single string or a list. They are sent as
repeated `key[]=...` query params.

## Full-text lyrics search

```python
for hit in ma.search_songs(lyrics="ace of spades", paginate=True):
    print(hit.band_name, "-", hit.title)
    text = ma.get_lyrics_by_song_id(hit.lyrics_id)
```

## Building a corpus: resumable crawls

This is the pattern from
[`examples/portuguese_heavy_metal_pre2000.py`](../examples/portuguese_heavy_metal_pre2000.py).

1. Paginate-walk an advanced search.
2. Call `get_discography` per band.
3. Filter releases by `release_year < cutoff`.
4. Call `get_release` to enumerate tracks.
5. Call `get_lyrics_by_song_id` for each track.
6. Append a `(band_id, release_id, song_id)` line to a `manifest.jsonl`
   so a re-run can skip work already done.

Throttle with a small `time.sleep(0.5)` between requests. MA is
small-team infrastructure, and it rate-limits aggressive scrapers.

## Custom session

```python
from curl_cffi import requests
from pymetal import Client, MetalArchives

c = Client()
c.session = requests.Session(impersonate="chrome120", proxies={"https": "http://localhost:8080"})
ma = MetalArchives(client=c)
```

---
[← API Reference](api_reference.md) · [Home](../readme.md) · [Developer Guide →](developer_guide.md)
