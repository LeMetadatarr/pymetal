"""Find playable stream URLs for bands in a given genre.

Walks MA's genre browse index, fetches the external-links tab for each band,
and prints any streaming-capable URLs (YouTube, Bandcamp, SoundCloud, Spotify, …).

Usage:
    python examples/genre_streams.py doom
    python examples/genre_streams.py black --limit 20
    python examples/genre_streams.py death --only youtube,bandcamp

Available genre slugs: black death doom stoner sludge electronic industrial
  experimental avant-garde folk viking pagan gothic grindcore groove heavy
  metalcore deathcore power progressive speed symphonic thrash
"""
import argparse
import time

from pymetal import MetalArchives, stream_links
from pymetal.locators import STREAM_DOMAINS


def parse_args():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("genre", help="MA genre slug (e.g. doom, black, death)")
    p.add_argument("--limit", type=int, default=10,
                   help="max number of bands to check (default: 10)")
    p.add_argument("--only", default="",
                   help="comma-separated service names to include (e.g. youtube,bandcamp,soundcloud)")
    p.add_argument("--sleep", type=float, default=0.5,
                   help="seconds to sleep between link requests (default: 0.5)")
    return p.parse_args()


def main():
    args = parse_args()
    only = {s.strip().lower() for s in args.only.split(",") if s.strip()}

    ma = MetalArchives()

    print(f"Browsing genre: {args.genre!r}  (limit={args.limit})\n")

    checked = 0
    for hit in ma.browse_bands_by_genre(args.genre):
        if checked >= args.limit:
            break

        band_id = hit.ma_id if hasattr(hit, "ma_id") else None
        if band_id is None:
            continue

        checked += 1
        streams = ma.get_stream_links(band_id)
        if not streams:
            print(f"  {hit.name} — no stream links found")
            time.sleep(args.sleep)
            continue

        # Apply --only filter
        if only:
            streams = [s for s in streams
                       if any(kw in s.name.lower() for kw in only)]

        if not streams:
            time.sleep(args.sleep)
            continue

        print(f"{hit.name} ({hit.country or '?'})")
        for s in streams:
            print(f"  {s.name:<30} {s.url}")

        time.sleep(args.sleep)

    print(f"\nDone. Checked {checked} bands.")


if __name__ == "__main__":
    main()
