# pymetal — agent guide

Python client for Encyclopaedia Metallum (metal-archives.com) with a typed, relational
data model (pydantic v2). Scrapes HTML/AJAX endpoints, converts results into `mediavocab`
typed objects (`Entity`, `Release`). It is a plain library, not an OVOS/OPM plugin.

## Setup

```bash
pip install -e .[test]          # plain requests transport (likely blocked by Cloudflare)
pip install -e .[stealth,test]  # adds curl_cffi TLS-fingerprint bypass (recommended)
export PYMETAL_TRANSPORT=curl_cffi
```

Python 3.10+. Core deps: `lxml`, `mediavocab>=0.1.0`, `pydantic>=2`, `random-user-agent`,
`requests`. `[stealth]` adds `curl_cffi`.

## Test

```bash
pytest test/
```

Tests are VCR cassette-backed (`test/cassettes/`) plus offline fixtures (`test/fixtures/`)
and unit tests — they run without network. To re-record against live endpoints:

```bash
PYMETAL_CASSETTE_MODE=all pytest -q test/ -k "_vcr"
```

## Lint/Typecheck

Ruff via the shared lint workflow (`.github/workflows/lint.yml`). No local ruff config or
pre-commit hook committed; `pre_commit: false`. No typecheck step configured.

## Layout

- `pymetal/archives.py` — `MetalArchives` facade; the public entry surface.
- `pymetal/endpoints/` — one module per area: `bands`, `search`, `releases`,
  `artists`, `labels`, `browse`, `lyrics`, shared helpers in `_common.py`. Each parses
  HTML/AJAX into models.
- `pymetal/models.py` — pydantic v2 models (`Band`, `Artist`, `Label`, `Release`, `Song`,
  `LineupMember`, `TrackAppearance`, search-hit and discovery types).
- `pymetal/converters.py` — MA models → `mediavocab` `Entity`/`Release`; sets `external_ids`
  keys like `ma_band_id`, `ma_album_id`, `ma_song_id`, `ma_lyrics_id`.
- `pymetal/http.py` — `Client` (caching session wrapper, `cache_ttl`, `cache_size`).
- `pymetal/transport.py` — `default_client`; selects curl_cffi vs requests from
  `PYMETAL_TRANSPORT`.
- `pymetal/locators.py` — URL builders / `STREAM_DOMAINS`. `pymetal/util.py` — helpers.
- `docs/` reference pages, `examples/` numbered zero-to-hero scripts.

No entry-point group is declared — this ships as an importable client, not a plugin.

## Conventions (org hard rules)

- Branches: `dev` (work) and `master` (stable). NEVER `main`.
- Never edit `pymetal/version.py`; gh-automations bumps semver from conventional-commit
  prefixes (`feat:`, `fix:`, `feat!:`).
- New repos private by default.
- Commit identity: JarbasAi <jarbasai@mailfence.com>.
- Reference `OpenVoiceOS/gh-automations` reusable workflows at `@dev`.
- No Neon / `neon-*` references.
- No meta-commentary in docs/commits/PRs/code (no history, dates, or "before times").
- CI is provided by OpenVoiceOS/gh-automations.

## Gotchas

- metal-archives.com is Cloudflare-protected; plain `requests` is usually blocked and emits
  a `RuntimeWarning`. Use `[stealth]` + `PYMETAL_TRANSPORT=curl_cffi`, or inject a session
  via `Client(session=...)`.
- `search_bands` returns `mediavocab.Entity`; `search_albums`/`search_songs` return
  `mediavocab.Release` — search methods already hand back mediavocab objects, while
  `get_band`/`get_release` return native MA models that you convert via `converters`.
- `get_release(id)` returns a 3-tuple `(Release, List[Song], List[TrackAppearance])`.
- Parsing depends on upstream HTML; the `nightly-live` workflow re-runs `_vcr` tests against
  live endpoints (detect-only, cassettes not committed back) to surface HTML drift.
