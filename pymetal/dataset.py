"""Flat, tabular rows from metal-archives data for Hugging Face datasets.

Four join-able streams keyed on metal-archives numeric ids (``ma_id``):

- :func:`band_rows`    — one row per :class:`~pymetal.models.Band` (headline table)
- :func:`release_rows` — one row per :class:`~pymetal.models.Release`, carrying ``band_id``
- :func:`song_rows`    — one row per track, carrying ``release_id`` and ``band_id``
- :func:`label_rows`   — one row per :class:`~pymetal.models.Label`

The streams join: ``release.band_id`` → ``band.band_id``, ``song.release_id`` →
``release.release_id``, ``release.label_id`` → ``label.label_id``.

:func:`build_dataset` lazily enumerates the whole catalogue
(``browse_bands_by_letter`` over ``A``..``Z`` + ``NBR`` + ``~``) and, with
``detail=True``, fetches each band page for the per-band genre/status/label and
its discography. :func:`write_jsonl` streams the rows to a JSONL file.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Iterable, Iterator, List, Optional

from pymetal.archives import MetalArchives
from pymetal.models import Band, Label, Release, Song

# A..Z plus the two extra metal-archives band-index buckets.
LETTERS: List[str] = [chr(c) for c in range(ord("A"), ord("Z") + 1)] + ["NBR", "~"]


# ---------------------------------------------------------------------------
# Hugging Face feature dictionary (one entry per config / stream).
# ---------------------------------------------------------------------------

HF_FEATURES: Dict[str, Dict[str, str]] = {
    "bands": {
        "band_id": "int64",
        "name": "string",
        "url": "string",
        "country": "string",
        "location": "string",
        "status": "string",
        "formed_in": "string",
        "years_active": "list<string>",
        "genres": "list<string>",
        "themes": "list<string>",
        "current_label_id": "int64",
        "current_label_name": "string",
        "comment": "string",
    },
    "releases": {
        "release_id": "int64",
        "band_id": "int64",
        "title": "string",
        "type": "string",
        "release_date": "string",
        "label_id": "int64",
        "label_name": "string",
        "reviews_count": "int64",
        "reviews_avg_percent": "int64",
        "n_songs": "int64",
        "url": "string",
    },
    "songs": {
        "song_id": "int64",
        "release_id": "int64",
        "band_id": "int64",
        "title": "string",
        "track_no": "int64",
        "disc_no": "int64",
        "length": "string",
        "is_instrumental": "bool",
        "lyrics_id": "string",
    },
    "labels": {
        "label_id": "int64",
        "name": "string",
        "url": "string",
        "country": "string",
        "status": "string",
        "styles": "string",
        "founding_date": "string",
        "parent_label_id": "int64",
        "parent_label_name": "string",
        "website": "string",
    },
}

CONFIGS = list(HF_FEATURES)


def _s(v: Any) -> Optional[str]:
    """Stringify a pydantic ``HttpUrl`` / enum / scalar, or pass ``None``."""
    if v is None:
        return None
    if hasattr(v, "value"):  # Enum -> its string value
        return v.value
    return str(v)


# ---------------------------------------------------------------------------
# Row flatteners
# ---------------------------------------------------------------------------


def band_rows(bands: Iterable[Band]) -> Iterator[Dict[str, Any]]:
    """Yield one flat row per :class:`Band`."""
    for b in bands:
        yield {
            "band_id": b.ma_id,
            "name": b.name,
            "url": _s(b.url),
            "country": b.country,
            "location": b.location,
            "status": _s(b.status),
            "formed_in": b.formed_in,
            "years_active": list(b.years_active),
            "genres": list(b.genres),
            "themes": list(b.themes),
            "current_label_id": b.current_label_id,
            "current_label_name": b.current_label_name,
            "comment": b.comment,
        }


def release_rows(
    releases: Iterable[Release],
    *,
    band_id: Optional[int] = None,
    n_songs: Optional[int] = None,
) -> Iterator[Dict[str, Any]]:
    """Yield one row per :class:`Release`.

    ``band_id`` stamps the owning band (discography rows don't carry it);
    ``n_songs`` is filled when a detail fetch counted the tracklist.
    """
    for r in releases:
        yield {
            "release_id": r.ma_id,
            "band_id": band_id if band_id is not None else (r.band_ids[0] if r.band_ids else None),
            "title": r.title,
            "type": _s(r.type),
            "release_date": r.release_date,
            "label_id": r.label_id,
            "label_name": r.label_name,
            "reviews_count": r.reviews_count,
            "reviews_avg_percent": r.reviews_avg_percent,
            "n_songs": n_songs,
            "url": _s(r.url),
        }


def song_rows(
    songs: Iterable[Song],
    *,
    release_id: int,
    band_id: Optional[int] = None,
    appearances: Optional[Iterable[Any]] = None,
) -> Iterator[Dict[str, Any]]:
    """Yield one row per :class:`Song` on a release.

    ``appearances`` (the parallel list :func:`pymetal.endpoints.releases.get_release`
    returns) supplies track number / disc / instrumental flags when present.
    """
    appr = list(appearances) if appearances is not None else []
    for i, s in enumerate(songs):
        a = appr[i] if i < len(appr) else None
        yield {
            "song_id": s.ma_id,
            "release_id": release_id,
            "band_id": (a.band_id or band_id) if a is not None else band_id,
            "title": s.title,
            "track_no": getattr(a, "track_no", None),
            "disc_no": getattr(a, "disc_no", None),
            "length": s.length,
            "is_instrumental": getattr(a, "is_instrumental", None),
            "lyrics_id": s.lyrics_id,
        }


def label_rows(labels: Iterable[Label]) -> Iterator[Dict[str, Any]]:
    """Yield one flat row per :class:`Label`."""
    for lb in labels:
        yield {
            "label_id": lb.ma_id,
            "name": lb.name,
            "url": _s(lb.url),
            "country": lb.country,
            "status": lb.status,
            "styles": lb.styles,
            "founding_date": lb.founding_date,
            "parent_label_id": lb.parent_label_id,
            "parent_label_name": lb.parent_label_name,
            "website": _s(lb.website),
        }


# ---------------------------------------------------------------------------
# Streaming dataset builder
# ---------------------------------------------------------------------------


def build_dataset(
    config: str = "bands",
    *,
    letters: Optional[Iterable[str]] = None,
    detail: bool = False,
    archives: Optional[MetalArchives] = None,
    delay: float = 0.0,
) -> Iterator[Dict[str, Any]]:
    """Stream rows for one *config* across the band index (or a letter subset).

    - ``bands``    — band-index rows; ``detail=True`` fetches each band page
      for genres/status/label (one request per band).
    - ``releases`` — every release of every band (always needs the discography
      fetch). ``detail=True`` additionally fetches each release for ``n_songs``.
    - ``songs``    — every track of every release (forces per-release fetches).
    - ``labels``   — every label across the label index (one fetch per label
      when ``detail=True``, else the lightweight browse rows).

    ``delay`` sleeps between detail HTTP requests. Everything is lazy — at most
    one band's worth of releases/songs is held in memory at a time.
    """
    import time

    ma = archives or MetalArchives()
    pick = list(letters) if letters else LETTERS

    if config == "labels":
        for letter in pick:
            for lb in ma.browse_labels_by_letter(letter):
                if detail and lb.ma_id is not None:
                    if delay:
                        time.sleep(delay)
                    try:
                        lb = ma.get_label(lb.ma_id)
                    except Exception:
                        pass
                yield from label_rows([lb])
        return

    # bands / releases / songs all enumerate the band index first.
    for letter in pick:
        for hit in ma.browse_bands_by_letter(letter):
            band_id = hit.ma_id
            if band_id is None:
                continue

            if config == "bands":
                if detail:
                    if delay:
                        time.sleep(delay)
                    try:
                        band = ma.get_band(band_id)
                    except Exception:
                        continue
                    yield from band_rows([band])
                else:
                    # Synthesize a Band from the browse hit (no extra request).
                    yield {
                        "band_id": band_id,
                        "name": hit.name,
                        "url": _s(hit.url),
                        "country": hit.country,
                        "location": None,
                        "status": None,
                        "formed_in": None,
                        "years_active": [],
                        "genres": [hit.genre] if hit.genre else [],
                        "themes": [],
                        "current_label_id": None,
                        "current_label_name": None,
                        "comment": None,
                    }
                continue

            # releases / songs need the discography.
            if delay:
                time.sleep(delay)
            try:
                discog = ma.get_discography(band_id)
            except Exception:
                continue

            if config == "releases":
                for rel in discog:
                    n_songs = None
                    if detail and rel.ma_id is not None:
                        if delay:
                            time.sleep(delay)
                        try:
                            _, songs, _ = ma.get_release(rel.ma_id)
                            n_songs = len(songs)
                        except Exception:
                            pass
                    yield from release_rows([rel], band_id=band_id, n_songs=n_songs)

            elif config == "songs":
                for rel in discog:
                    if rel.ma_id is None:
                        continue
                    if delay:
                        time.sleep(delay)
                    try:
                        _, songs, appr = ma.get_release(rel.ma_id)
                    except Exception:
                        continue
                    yield from song_rows(
                        songs, release_id=rel.ma_id, band_id=band_id, appearances=appr
                    )


def write_jsonl(path: str, rows: Iterable[Dict[str, Any]], *, mode: str = "w") -> int:
    """Stream *rows* to *path* as JSON Lines; return the count written.

    Writes and flushes one line at a time so an interrupted run leaves a valid
    prefix. ``mode='a'`` appends (for resume).
    """
    n = 0
    with open(path, mode, encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()
            n += 1
    return n
