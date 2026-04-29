"""Download lyrics for every Heavy Metal song from Portugal released before 2000.

Walks:
    advanced band search (country=PT, genre=Heavy)
        -> discography per band
            -> tracklist per pre-2000 release
                -> lyrics per track

Lyrics are written to:
    out/<band_slug>/<year>_<release_slug>/<NN>_<song_slug>.txt

A small `manifest.jsonl` records every (band, release, song) triple so a
re-run can resume cheaply — metal-archives is rate-limited and we don't
want to hammer it.

Run:
    python examples/portuguese_heavy_metal_pre2000.py
    python examples/portuguese_heavy_metal_pre2000.py --limit-bands 3   # smoke test
    python examples/portuguese_heavy_metal_pre2000.py --year 2010       # different cutoff
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
from pymetal.endpoints.bands import get_band
from pymetal.endpoints.lyrics import get_lyrics_by_song_id
from pymetal.endpoints.releases import get_discography, get_release
from pymetal.endpoints.search import search_bands
from pymetal.models import Release, ReleaseType


COUNTRY = "PT"
GENRE = "Heavy"
DEFAULT_YEAR = 2000

# Releases without lyrics worth scraping — skip outright.
SKIP_RELEASE_TYPES = {ReleaseType.VIDEO, ReleaseType.BOXED_SET, ReleaseType.SPLIT_VIDEO}


def slugify(s: str) -> str:
    s = re.sub(r"[^\w\s-]", "", s, flags=re.UNICODE).strip().lower()
    return re.sub(r"[-\s]+", "_", s)[:80] or "untitled"


_YEAR_RE = re.compile(r"\b(\d{4})\b")


def release_year(rel: Release) -> Optional[int]:
    if not rel.release_date:
        return None
    m = _YEAR_RE.search(rel.release_date)
    return int(m.group(1)) if m else None


def iter_pre_year_releases(band_id: int, year_cutoff: int, ma: MetalArchives) -> Iterable[Release]:
    for rel in get_discography(band_id, client=ma.client):
        if rel.type in SKIP_RELEASE_TYPES:
            continue
        y = release_year(rel)
        if y is not None and y < year_cutoff:
            yield rel


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=Path("out"), help="output directory")
    ap.add_argument("--year", type=int, default=DEFAULT_YEAR, help="release-year cutoff (exclusive)")
    ap.add_argument("--country", default=COUNTRY, help="MA country code (e.g. PT, NO, US)")
    ap.add_argument("--genre", default=GENRE, help="MA genre keyword (e.g. Heavy, Death, Doom)")
    ap.add_argument("--limit-bands", type=int, default=0, help="stop after N bands (0 = no limit)")
    ap.add_argument("--sleep", type=float, default=0.5, help="pause between requests (be kind to MA)")
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    manifest_path = args.out / "manifest.jsonl"
    seen: set[tuple[int, int]] = set()  # (release_id, song_id)
    if manifest_path.exists():
        for line in manifest_path.read_text().splitlines():
            try:
                rec = json.loads(line)
                seen.add((rec["release_id"], rec["song_id"]))
            except (json.JSONDecodeError, KeyError):
                continue
        print(f"resume: {len(seen)} (release, song) pairs already done", file=sys.stderr)

    ma = MetalArchives()
    manifest = manifest_path.open("a", encoding="utf-8")

    n_bands = n_releases = n_tracks = n_lyrics = 0
    try:
        for band in search_bands(
            country=args.country, genre=args.genre, paginate=True, client=ma.client
        ):
            if not band.ma_id:
                continue
            n_bands += 1
            if args.limit_bands and n_bands > args.limit_bands:
                break

            # Need full band record (location, formed_in) for the manifest.
            try:
                full = get_band(band.ma_id, client=ma.client)
            except Exception as e:  # noqa: BLE001
                print(f"  ! band {band.name!r}: {e!r}", file=sys.stderr)
                continue

            band_slug = slugify(full.name)
            print(f"[{n_bands:3d}] {full.name} ({full.location or full.country})")

            for rel in iter_pre_year_releases(full.ma_id, args.year, ma):
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
                    key = (rel.ma_id, song.ma_id)
                    if key in seen:
                        continue
                    text = get_lyrics_by_song_id(song.ma_id, client=ma.client)
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
                                "band_id": full.ma_id,
                                "band_name": full.name,
                                "release_id": rel.ma_id,
                                "release_title": rel.title,
                                "release_year": year,
                                "release_type": rel.type.value,
                                "song_id": song.ma_id,
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
