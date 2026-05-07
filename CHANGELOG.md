# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Relational data model in `pymetal.models`: `Band`, `Artist`, `Release`,
  `Song`, `Label` plus three relationship entities — `LineupMember`,
  `ReleaseLineup`, `TrackAppearance` — that capture splits, lineup
  changes over time, and tracks reused across releases.
- `ReleaseType`, `LineupStatus`, `BandStatus` enums mirroring metal-archives
  vocabularies.
- `pymetal.endpoints` package (`bands`, `releases`, `search`, `lyrics`)
  returning the new models. CSS/XPath selectors live in
  `pymetal.locators`.
- `pymetal.http.Client` — curl_cffi session with a small in-process
  response cache.
- `MetalArchives.get_release`, `get_discography`, `get_lineup`.

### Changed

- `pymetal.Track` is retained as a deprecated flat shape returned by
  `search_song` only. New code should use `Song` + `TrackAppearance`.
- `setup.py` switched to setuptools and updated to declare `curl_cffi`,
  `pydantic>=2`, `lxml`, `random-user-agent`. Bumped to 0.6.0.

## [0.4.1]  - 2019-12-12

### Changed

- Transfered ownership to [OpenJarbas](https://github.com/OpenJarbas)
- Made a changelog


[unreleased]: https://github.com/OpenJarbas/little_questions/tree/dev
[0.4.1]: https://github.com/OpenJarbas/little_questions/tree/0.4.1
