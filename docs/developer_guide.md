# Developer Guide

## Layout

```
pymetal/
  __init__.py            # public re-exports
  archives.py            # MetalArchives facade
  http.py                # Client (curl_cffi + cache) + Response
  locators.py            # URLs, regexes, CSS/XPath selectors, code tables
  models.py              # Pydantic v2 models + enums
  endpoints/
    _common.py           # parsing helpers (dl_pairs, audit, ma_id_from_url)
    bands.py             # get_band, get_lineup
    releases.py          # get_release, get_discography, get_release_lineup, get_other_versions
    artists.py           # get_artist
    search.py            # search_bands, search_albums, search_songs
    lyrics.py            # get_lyrics_by_song_id, get_lyrics
test/
  conftest.py            # FakeClient fixture used by parser tests
  fixtures/
    _capture.py          # re-capture script (network)
    html/                # captured MA HTML/JSON
  test_models.py         # round-trip + relationship semantics
  test_endpoints_unit.py # parser helpers, no I/O
  test_parsers_fixtures.py # end-to-end parsers against captured fixtures
  test_http.py           # Client cache behaviour
  test_archives.py       # facade-level
```

## Design rules

1. **Endpoint modules return models.** The parsing layer never returns
   dicts. Every function in `pymetal.endpoints` returns a typed Pydantic
   model or list/iterator thereof.
2. **`Client` only does HTTP + cache.** It knows nothing about parsing.
3. **Selectors are data.** Put new XPath / CSS / regex / URL templates in
   `pymetal/locators.py`. Don't hard-code them in parsers.
4. **Idempotent ids.** Every model uses MA's `ma_id` as the natural key
   so re-scrapes are safe to overwrite.
5. **No legacy shims.** This is a fresh release; if you change a shape,
   update every caller and the docs in the same commit.

## Adding a new endpoint

1. Add the URL template / selectors / any code tables to `locators.py`.
2. Add the Pydantic model to `models.py` (or extend an existing one).
3. Implement the parser in `endpoints/<area>.py`. Keep the function pure:
   take `(id, *, client=None)`, fetch, parse, return.
4. Re-export from `endpoints/__init__.py`.
5. Add a facade method to `MetalArchives` in `archives.py`.
6. Capture a real fixture (see below) and write a test in
   `test_parsers_fixtures.py`.

## Capturing fixtures

```bash
python test/fixtures/_capture.py
```

The script anchors on stable, well-known MA records (Carcass=14,
Heartwork=451600, Napalm Death/S.O.B. split=485040). Re-running
overwrites the existing files so parser tests are evaluated against
fresh HTML.

When adding a new fixture, append the target to `_capture.py` and pick a
stable record:

- Use a record that's existed for years (low risk of disappearing).
- Prefer records that exercise the edge case you're testing
  (split-up band, deceased artist, EP, etc.) over headline records.

## Test approach

- **Unit tests** in `test_endpoints_unit.py` and `test_models.py` —
  pure functions, no I/O. New helpers in `_common.py` belong here.
- **Parser tests** in `test_parsers_fixtures.py` use the `FakeClient`
  fixture from `conftest.py` to serve captured HTML. New endpoint =
  new fixture-backed test.
- **HTTP tests** in `test_http.py` swap `Client.session` for a
  recording stub; no fixtures needed.
- **Facade tests** in `test_archives.py` cover the wiring.

```bash
pytest test/ -q --ignore=test/license_tests.py
```

## Bug-fix workflow

When you find a parser bug:

1. Capture (or re-capture) a fixture exhibiting the failure.
2. Write a failing parser test against it.
3. Fix the parser.
4. The test should now pass; commit both together.

This is how the entire project was bootstrapped — see the existing
fixtures: each one anchors a real MA quirk (dt/dd label pairs, split
band attribution, lineup tab partitioning, audit-trail blocks).

## Releasing

Until 1.0, expect breaking changes. Bump `setup.py:version` and add a
`CHANGELOG.md` entry per release.
