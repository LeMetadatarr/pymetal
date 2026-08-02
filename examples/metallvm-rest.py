"""metallvm-rest — a FastAPI server exposing every pymetal endpoint over HTTP.

A drop-in metadata REST API in front of metal-archives.com: search,
detail pages, catalog browse, lyrics, recommendations, reviews. Every
route returns Pydantic models from `pymetal.models` so the OpenAPI
schema MA's data is self-documenting (visit `/docs`).

Run:
    pip install fastapi uvicorn
    uvicorn examples.metallvm-rest:app --reload --port 8000

Try:
    curl http://localhost:8000/bands/14
    curl http://localhost:8000/bands/14/lineup
    curl http://localhost:8000/bands/14/recommendations
    curl 'http://localhost:8000/search/bands?country=PT&genre=Heavy&year_from=1980&year_to=1989'
    curl http://localhost:8000/browse/bands/genre/black?limit=10
    curl http://localhost:8000/lyrics/172090
    curl http://localhost:8000/meta/countries
    curl http://localhost:8000/meta/genres
    open http://localhost:8000/docs

Notes:
- Iterator-returning endpoints take optional `?limit=N` and `?offset=N`
  query params so HTTP clients can page without exhausting MA's catalog.
- Errors from upstream (rate-limit, 404, schema drift) bubble up as
  502 responses with the underlying message.
"""
from __future__ import annotations

from itertools import islice
from typing import Annotated, List, Optional, Sequence

try:
    from fastapi import FastAPI, HTTPException, Query
except ImportError as e:  # pragma: no cover
    raise SystemExit(
        "fastapi is required for this example. Install with:\n"
        "    pip install fastapi uvicorn"
    ) from e

from pymetal import (
    AlbumSearchHit,
    Artist,
    Band,
    BandRecommendation,
    BandSearchHit,
    ExternalLink,
    Label,
    LineupMember,
    MetalArchives,
    Release,
    ReleaseLineup,
    ReleaseType,
    Review,
    RIPArtist,
    Song,
    SongSearchHit,
    TrackAppearance,
    UpcomingRelease,
    __version__,
)


app = FastAPI(
    title="metallvm-rest",
    summary="REST front for metal-archives.com (powered by pymetal).",
    version=__version__,
    description=(
        "Every route is a thin wrapper around a `pymetal.endpoints` "
        "function. See https://github.com/LeMetadatarr/pymetal."
    ),
)
ma = MetalArchives()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _take(it, limit: Optional[int], offset: int) -> list:
    """Apply offset/limit to an iterator without materialising the rest."""
    if offset:
        it = islice(it, offset, None)
    if limit is not None:
        it = islice(it, limit)
    return list(it)


def _safe(call):
    """Run an endpoint call and re-raise upstream errors as 502."""
    try:
        return call()
    except RuntimeError as e:
        # Rate-limit / non-JSON / parser fail
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# Meta
# ---------------------------------------------------------------------------


@app.get("/", summary="Service banner")
def root() -> dict:
    return {
        "service": "metallvm-rest",
        "pymetal_version": __version__,
        "docs": "/docs",
        "openapi": "/openapi.json",
    }


@app.get("/meta/countries", response_model=dict[str, str])
def meta_countries() -> dict:
    """All MA-known country codes — `{code: name}` (134+ entries)."""
    return _safe(ma.list_countries)


@app.get("/meta/genres", response_model=List[str])
def meta_genres() -> list:
    """The 23 coarse genre slugs accepted by `/browse/bands/genre/{slug}`."""
    return ma.list_genre_slugs()


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


@app.get("/search/bands", response_model=List[BandSearchHit])
def search_bands(
    name: str = "",
    exact: bool = False,
    genre: str = "",
    country: str = "",
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    status: Annotated[Optional[List[str]], Query()] = None,
    themes: str = "",
    location: str = "",
    label: str = "",
    indie_label: bool = False,
    limit: int = 200,
    offset: int = 0,
) -> list:
    return _take(
        _safe(
            lambda: ma.search_bands(
                band_name=name,
                exact_band_match=exact,
                genre=genre,
                country=country,
                year_from=year_from,
                year_to=year_to,
                status=status,
                themes=themes,
                location=location,
                label=label,
                indie_label=indie_label,
                paginate=True,
            )
        ),
        limit,
        offset,
    )


@app.get("/search/albums", response_model=List[AlbumSearchHit])
def search_albums(
    band_name: str = "",
    exact_band_match: bool = False,
    release_title: str = "",
    exact_release_match: bool = False,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    country: str = "",
    label: str = "",
    catalog_number: str = "",
    identifiers: str = "",
    genre: str = "",
    release_type: Annotated[Optional[List[str]], Query()] = None,
    release_format: Annotated[Optional[List[str]], Query()] = None,
    limit: int = 200,
    offset: int = 0,
) -> list:
    return _take(
        _safe(
            lambda: ma.search_albums(
                band_name=band_name,
                exact_band_match=exact_band_match,
                release_title=release_title,
                exact_release_match=exact_release_match,
                year_from=year_from,
                year_to=year_to,
                country=country,
                label=label,
                catalog_number=catalog_number,
                identifiers=identifiers,
                genre=genre,
                release_type=release_type,
                release_format=release_format,
                paginate=True,
            )
        ),
        limit,
        offset,
    )


@app.get("/search/songs", response_model=List[SongSearchHit])
def search_songs(
    title: str = "",
    band_name: str = "",
    release_title: str = "",
    lyrics: str = "",
    genre: str = "",
    country: str = "",
    release_type: Annotated[Optional[List[str]], Query()] = None,
    limit: int = 200,
    offset: int = 0,
) -> list:
    return _take(
        _safe(
            lambda: ma.search_songs(
                song_title=title,
                band_name=band_name,
                release_title=release_title,
                lyrics=lyrics,
                genre=genre,
                country=country,
                release_type=release_type,
                paginate=True,
            )
        ),
        limit,
        offset,
    )


# ---------------------------------------------------------------------------
# Bands
# ---------------------------------------------------------------------------


@app.get("/bands/random", response_model=Band)
def bands_random(genre: Optional[str] = None) -> Band:
    """Random band; optionally re-rolls until `genre` (a coarse slug) matches."""
    return _safe(lambda: ma.random_band(genre=genre))


@app.get("/bands/{band_id}", response_model=Band)
def bands_get(band_id: int) -> Band:
    return _safe(lambda: ma.get_band(band_id))


@app.get("/bands/{band_id}/lineup", response_model=List[LineupMember])
def bands_lineup(band_id: int) -> list:
    return _safe(lambda: ma.get_lineup(band_id))


@app.get("/bands/{band_id}/discography", response_model=List[Release])
def bands_discography(band_id: int) -> list:
    return _safe(lambda: ma.get_discography(band_id))


@app.get("/bands/{band_id}/recommendations", response_model=List[BandRecommendation])
def bands_recommendations(band_id: int) -> list:
    return _safe(lambda: ma.get_band_recommendations(band_id))


@app.get("/bands/{band_id}/links", response_model=List[ExternalLink])
def bands_links(band_id: int) -> list:
    return _safe(lambda: ma.get_links(band_id, entity_type="band"))


@app.get("/bands/{band_id}/reviews", response_model=List[Review])
def bands_reviews(band_id: int, limit: int = 200, offset: int = 0) -> list:
    return _take(_safe(lambda: ma.get_band_reviews(band_id)), limit, offset)


# ---------------------------------------------------------------------------
# Releases
# ---------------------------------------------------------------------------


class ReleasePayload(Release.__pydantic_model__ if False else Release):  # type: ignore[misc]
    """Release plus tracklist (used only as the response model below)."""


@app.get("/releases/{release_id}")
def releases_get(release_id: int) -> dict:
    """Release record + tracklist + per-track band attribution.

    Returns `{release, songs, appearances}` so callers can join the
    three lists themselves (matters for splits where appearances carry
    different `band_id`s).
    """
    release, songs, apps = _safe(lambda: ma.get_release(release_id))
    return {
        "release": release.model_dump(mode="json"),
        "songs": [s.model_dump(mode="json") for s in songs],
        "appearances": [a.model_dump(mode="json") for a in apps],
    }


@app.get("/releases/{release_id}/lineup", response_model=List[ReleaseLineup])
def releases_lineup(release_id: int) -> list:
    return _safe(lambda: ma.get_release_lineup(release_id))


@app.get("/releases/{release_id}/versions", response_model=List[Release])
def releases_versions(release_id: int) -> list:
    return _safe(lambda: ma.get_other_versions(release_id))


# ---------------------------------------------------------------------------
# Artists
# ---------------------------------------------------------------------------


@app.get("/artists/{artist_id}", response_model=Artist)
def artists_get(artist_id: int) -> Artist:
    return _safe(lambda: ma.get_artist(artist_id))


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------


@app.get("/labels/{label_id}", response_model=Label)
def labels_get(label_id: int) -> Label:
    return _safe(lambda: ma.get_label(label_id))


@app.get("/labels/{label_id}/links", response_model=List[ExternalLink])
def labels_links(label_id: int) -> list:
    return _safe(lambda: ma.get_links(label_id, entity_type="label"))


# ---------------------------------------------------------------------------
# Lyrics
# ---------------------------------------------------------------------------


@app.get("/lyrics/{song_id}")
def lyrics_get(song_id: int) -> dict:
    text = _safe(lambda: ma.get_lyrics_by_song_id(song_id))
    if text is None:
        raise HTTPException(status_code=404, detail="(lyrics not available)")
    return {"song_id": song_id, "text": text}


# ---------------------------------------------------------------------------
# Browse
# ---------------------------------------------------------------------------


@app.get("/browse/bands/country/{country_code}", response_model=List[BandSearchHit])
def browse_country(country_code: str, limit: int = 200, offset: int = 0) -> list:
    return _take(_safe(lambda: ma.browse_bands_by_country(country_code)), limit, offset)


@app.get("/browse/bands/genre/{genre_slug}", response_model=List[BandSearchHit])
def browse_genre(genre_slug: str, limit: int = 200, offset: int = 0) -> list:
    return _take(_safe(lambda: ma.browse_bands_by_genre(genre_slug)), limit, offset)


@app.get("/browse/bands/letter/{letter}", response_model=List[BandSearchHit])
def browse_letter(letter: str, limit: int = 200, offset: int = 0) -> list:
    return _take(_safe(lambda: ma.browse_bands_by_letter(letter)), limit, offset)


@app.get("/browse/labels/country/{country_code}", response_model=List[Label])
def browse_labels_country(country_code: str, limit: int = 200, offset: int = 0) -> list:
    return _take(_safe(lambda: ma.browse_labels_by_country(country_code)), limit, offset)


@app.get("/browse/labels/letter/{letter}", response_model=List[Label])
def browse_labels_letter(letter: str, limit: int = 200, offset: int = 0) -> list:
    return _take(_safe(lambda: ma.browse_labels_by_letter(letter)), limit, offset)


@app.get("/browse/reviews", response_model=List[Review])
def browse_reviews(
    year: Optional[int] = None,
    month: Optional[int] = None,
    limit: int = 200,
    offset: int = 0,
) -> list:
    return _take(_safe(lambda: ma.browse_reviews(year=year, month=month)), limit, offset)


@app.get("/browse/upcoming", response_model=List[UpcomingRelease])
def browse_upcoming(limit: int = 200, offset: int = 0) -> list:
    return _take(_safe(ma.get_upcoming_releases), limit, offset)


@app.get("/browse/rip", response_model=List[RIPArtist])
def browse_rip(limit: int = 200, offset: int = 0) -> list:
    return _take(_safe(ma.get_rip_artists), limit, offset)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
