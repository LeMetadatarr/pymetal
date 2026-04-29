"""Download lyrics for every Portuguese metal song released before 2000.

Walks:
    /browse/country/c/PT (every band MA tracks for Portugal — 1800+ rows)
      -> filter to bands matching `--genre` substring on the free-text genre
      -> discography per band
        -> tracklist per pre-`--year` release (excluding demo / video / boxed-set)
          -> lyrics per track

Why /browse/country and not /search/bands?
    The advanced-search index is sparse (only 157 PT bands surface for
    'Heavy'). The browse endpoint returns the *full* country catalog
    (1835 PT bands) and gives us the free-text MA genre per band so we
    can match more loosely — "Heavy/Power Metal", "Doom/Heavy Metal",
    "Heavy Metal" all match `--genre Heavy`.

Why pre-2000?
    Older full-lengths and EPs are well-covered on MA (lyrics submitted
    over decades). Demos rarely have lyrics — we skip them by default.

Output:
    out/<band_slug>/<year>_<release_slug>/<NN>_<song_slug>.txt

`manifest.jsonl` records every (band, release, song) triple so a re-run
resumes cheaply — MA is rate-limited and we don't want to hammer it.

Run:
    python examples/portuguese_heavy_metal_pre2000.py
    python examples/portuguese_heavy_metal_pre2000.py --limit-bands 3   # smoke test
    python examples/portuguese_heavy_metal_pre2000.py --country US --genre thrash --year 1995
    python examples/portuguese_heavy_metal_pre2000.py --include-demos
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Iterable, Optional

from pymetal import MetalArchives
from pymetal.endpoints.browse import browse_bands_by_country
from pymetal.endpoints.lyrics import get_lyrics_by_song_id
from pymetal.endpoints.releases import get_discography, get_release
from pymetal.models import Release, ReleaseType


COUNTRY = "PT"
GENRE = "Heavy"  # substring matched against MA's free-text genre per band
DEFAULT_YEAR = 2000

# Demos almost never have lyrics on MA; skip by default. Video/boxed-set are
# never lyric-bearing.
SKIP_RELEASE_TYPES_DEFAULT = {
    ReleaseType.VIDEO,
    ReleaseType.BOXED_SET,
    ReleaseType.SPLIT_VIDEO,
    ReleaseType.DEMO,
}
SKIP_RELEASE_TYPES_INCLUDE_DEMOS = SKIP_RELEASE_TYPES_DEFAULT - {ReleaseType.DEMO}


def slugify(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE).strip().lower()
    return re.sub(r"[-\s]+", "_", s)[:80] or "untitled"


_YEAR_RE = re.compile(r"\b(\d{4})\b")


def release_year(rel: Release) -> Optional[int]:
    if not rel.release_date:
        return None
    m = _YEAR_RE.search(rel.release_date)
    return int(m.group(1)) if m else None


def iter_pre_year_releases(
    band_id: int,
    year_cutoff: int,
    ma: MetalArchives,
    skip_types: set,
) -> Iterable[Release]:
    for rel in get_discography(band_id, client=ma.client):
        if rel.type in skip_types:
            continue
        y = release_year(rel)
        if y is not None and y < year_cutoff:
            yield rel


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("out"), help="output directory")
    ap.add_argument("--year", type=int, default=DEFAULT_YEAR, help="release-year cutoff (exclusive)")
    ap.add_argument("--country", default=COUNTRY, help="MA country code (e.g. PT, NO, US)")
    ap.add_argument(
        "--genre",
        default=GENRE,
        help="substring matched against MA's free-text band genre (e.g. Heavy, Death, Doom)",
    )
    ap.add_argument("--limit-bands", type=int, default=0, help="stop after N bands (0 = no limit)")
    ap.add_argument("--sleep", type=float, default=0.5, help="pause between requests (be kind to MA)")
    ap.add_argument(
        "--include-demos",
        action="store_true",
        help="include demo releases (default skips them — they rarely have lyrics)",
    )
    args = ap.parse_args()
    skip_types = (
        SKIP_RELEASE_TYPES_INCLUDE_DEMOS if args.include_demos else SKIP_RELEASE_TYPES_DEFAULT
    )

    args.out.mkdir(parents=True, exist_ok=True)
    manifest_path = args.out / "manifest.jsonl"
    seen: set[tuple[int, str]] = set()  # (release_id, song_id) — song_id is MA's str id
    if manifest_path.exists():
        for line in manifest_path.read_text().splitlines():
            try:
                rec = json.loads(line)
                seen.add((rec["release_id"], str(rec["song_id"])))
            except (json.JSONDecodeError, KeyError):
                continue
        print(f"resume: {len(seen)} (release, song) pairs already done", file=sys.stderr)

    ma = MetalArchives()
    manifest = manifest_path.open("a", encoding="utf-8")

    n_bands = n_releases = n_tracks = n_lyrics = 0
    genre_needle = args.genre.lower()
    try:
        for band in browse_bands_by_country(args.country, client=ma.client):
            if not band.ma_id:
                continue
            # Match the substring against the free-text MA genre. Hits a much
            # broader set than search_bands(genre=...) which only matches MA's
            # 23-bucket coarse taxonomy.
            if genre_needle and genre_needle not in (band.genre or "").lower():
                continue
            n_bands += 1
            if args.limit_bands and n_bands > args.limit_bands:
                break

            band_slug = slugify(band.name)
            print(f"[{n_bands:3d}] {band.name}  ({band.genre})")

            for rel in iter_pre_year_releases(band.ma_id, args.year, ma, skip_types):
                n_releases += 1
                year = release_year(rel) or 0
                rel_slug = f"{year}_{slugify(rel.title)}"
                rel_dir = args.out / band_slug / rel_slug
                try:
                    _, songs, apps = get_release(rel.ma_id, client=ma.client)
                except Exception as e:  # noqa: BLE001
                    print(f"    ! release {rel.title!r}: {e!r}", file=sys.stderr)
                    continue
                time.sleep(args.sleep)

                for song, app in zip(songs, apps):
                    n_tracks += 1
                    if not song.lyrics_id:
                        continue
                    key = (rel.ma_id, song.lyrics_id)
                    if key in seen:
                        continue
                    text = get_lyrics_by_song_id(song.lyrics_id, client=ma.client)
                    time.sleep(args.sleep)
                    if not text:
                        continue
                    n_lyrics += 1
                    rel_dir.mkdir(parents=True, exist_ok=True)
                    fname = f"{app.track_no:02d}_{slugify(song.title)}.txt"
                    (rel_dir / fname).write_text(text, encoding="utf-8")
                    manifest.write(
                        json.dumps(
                            {
                                "band_id": band.ma_id,
                                "band_name": band.name,
                                "release_id": rel.ma_id,
                                "release_title": rel.title,
                                "release_year": year,
                                "release_type": rel.type.value,
                                "song_id": song.lyrics_id,
                                "song_title": song.title,
                                "track_no": app.track_no,
                                "path": str((rel_dir / fname).relative_to(args.out)),
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
                    manifest.flush()
                    seen.add(key)
    except KeyboardInterrupt:
        print("\ninterrupted — partial progress saved.", file=sys.stderr)
    finally:
        manifest.close()

    print(
        f"\ndone: bands={n_bands} releases={n_releases} tracks={n_tracks} "
        f"lyrics_saved={n_lyrics}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
