"""Converters from pymetal MA models to mediavocab typed objects.

``stream_links(links)`` filters an ``ExternalLink`` list to services that can
provide a direct stream or embed (YouTube, Bandcamp, SoundCloud, Spotify, …).
Pass the result to ``band_to_entity(band, links=...)`` and the stream URLs will
appear in ``entity.extra["stream_urls"]`` as a ``{service: url}`` dict.

These allow a pymetal-enriched ``Band``, ``Artist``, ``Release``, or ``Song``
to be handed off to code that expects the common mediavocab vocabulary.

Search-result shapes (``BandSearchHit``, ``AlbumSearchHit``, ``SongSearchHit``)
are also covered — those are the objects returned by ``MetalArchives.search_*``.
"""
from __future__ import annotations

from typing import List, Optional

from mediavocab import (
    Credit,
    CreditSection as MvCreditSection,
    Entity,
    EntityKind,
    EntityRef,
    MediaType,
    RelationRole,
    Release as MvRelease,
    StreamMode,
    Work,
)

from pymetal.locators import STREAM_DOMAINS
from pymetal.models import (
    AlbumSearchHit,
    Artist,
    Band,
    BandSearchHit,
    ExternalLink,
    Label,
    Release as MARelease,
    Song,
    SongSearchHit,
)


def stream_links(links: List[ExternalLink]) -> List[ExternalLink]:
    """Filter an ``ExternalLink`` list to services that provide audio/video streams.

    Matches against :data:`pymetal.locators.STREAM_DOMAINS` by substring in the
    URL.  Preserves the original order.

    Example::

        links = ma.get_links(14)
        streams = stream_links(links)
        for s in streams:
            print(s.name, s.url)   # "YouTube  https://youtube.com/user/Carcass"
    """
    result = []
    for link in links:
        url_str = str(link.url).lower()
        if any(domain in url_str for domain in STREAM_DOMAINS):
            result.append(link)
    return result


def band_to_entity(band: Band,
                   links: Optional[List[ExternalLink]] = None) -> Entity:
    """Convert a full ``Band`` model to a mediavocab ``Entity``.

    Pass ``links=ma.get_links(band_id)`` (or the already-filtered result of
    :func:`stream_links`) to populate ``entity.extra["stream_urls"]`` with a
    ``{service_name: url}`` dict for streaming-capable services (YouTube,
    Bandcamp, SoundCloud, Spotify, …).
    """
    external_ids: dict = {}
    if band.ma_id is not None:
        external_ids["ma_band_id"] = str(band.ma_id)
    extra: dict = {}
    if band.url:
        extra["artist_url"] = str(band.url)
    if band.photo_url:
        extra["image"] = str(band.photo_url)
    if band.country:
        extra["country"] = band.country
    if band.location:
        extra["location"] = band.location
    if band.genres:
        extra["genres"] = band.genres
    if band.status:
        extra["status"] = band.status.value
    if links is not None:
        streams = stream_links(links)
        if streams:
            extra["stream_urls"] = {s.name: str(s.url) for s in streams}
    return Entity(name=band.name, kind=EntityKind.GROUP,
                  external_ids=external_ids, extra=extra)


def artist_to_entity(artist: Artist) -> Entity:
    """Convert a full ``Artist`` model to a mediavocab ``Entity``."""
    external_ids: dict = {}
    if artist.ma_id is not None:
        external_ids["ma_artist_id"] = str(artist.ma_id)
    extra: dict = {}
    if artist.url:
        extra["artist_url"] = str(artist.url)
    if artist.photo_url:
        extra["image"] = str(artist.photo_url)
    if artist.real_name:
        extra["real_name"] = artist.real_name
    if artist.country:
        extra["country"] = artist.country
    if artist.born:
        extra["born"] = artist.born
    name = artist.alias or artist.real_name or ""
    return Entity(name=name, kind=EntityKind.PERSON,
                  external_ids=external_ids, extra=extra)


def label_to_entity(label: Label) -> Entity:
    """Convert a full ``Label`` model to a mediavocab ``Entity``."""
    external_ids: dict = {}
    if label.ma_id is not None:
        external_ids["ma_label_id"] = str(label.ma_id)
    extra: dict = {}
    if label.url:
        extra["artist_url"] = str(label.url)
    if label.country:
        extra["country"] = label.country
    if label.logo_url:
        extra["image"] = str(label.logo_url)
    return Entity(name=label.name, kind=EntityKind.ORGANISATION,
                  external_ids=external_ids, extra=extra)


def ma_release_to_release(ma_release: MARelease,
                           band_name: Optional[str] = None) -> MvRelease:
    """Convert a full MA ``Release`` model to a mediavocab ``Release``."""
    external_ids: dict = {}
    if ma_release.ma_id is not None:
        external_ids["ma_album_id"] = str(ma_release.ma_id)
    extra: dict = {}
    if ma_release.type:
        extra["release_type"] = ma_release.type.value
    if ma_release.release_date:
        extra["release_date"] = ma_release.release_date
    if ma_release.label_name:
        extra["label_name"] = ma_release.label_name
    if ma_release.catalog_no:
        extra["catalog_no"] = ma_release.catalog_no
    credits: list = []
    if band_name:
        artist_ref = EntityRef(name=band_name, kind=EntityKind.GROUP)
        credits.append(Credit(entity=artist_ref, role="artist",
                               relation_role=RelationRole.CREATOR,
                               section=MvCreditSection.PRINCIPAL))
    work = Work(title=ma_release.title, media_type=MediaType.MUSIC,
                credits=credits, external_ids=external_ids, extra=extra)
    return MvRelease(work=work, uri=str(ma_release.url) if ma_release.url else "",
                     image=str(ma_release.cover_url) if ma_release.cover_url else "",
                     stream_mode=StreamMode.ON_DEMAND, external_ids=external_ids)


def song_to_release(song: Song, band_name: Optional[str] = None,
                    band_id: Optional[int] = None,
                    release_title: Optional[str] = None) -> MvRelease:
    """Convert a ``Song`` model to a mediavocab ``Release``."""
    external_ids: dict = {}
    if song.ma_id is not None:
        external_ids["ma_song_id"] = str(song.ma_id)
    if song.lyrics_id:
        external_ids["ma_lyrics_id"] = song.lyrics_id
    extra: dict = {}
    if band_id is not None:
        extra["ma_band_id"] = str(band_id)
    if release_title:
        extra["ma_release_title"] = release_title
    credits: list = []
    if band_name:
        artist_ref = EntityRef(name=band_name, kind=EntityKind.GROUP)
        credits.append(Credit(entity=artist_ref, role="artist",
                               relation_role=RelationRole.PERFORMER,
                               section=MvCreditSection.PRINCIPAL))
    work = Work(title=song.title, media_type=MediaType.MUSIC,
                credits=credits, external_ids=external_ids, extra=extra)
    return MvRelease(work=work, uri="", image="",
                     stream_mode=StreamMode.ON_DEMAND, external_ids=external_ids)


# ---------------------------------------------------------------------------
# Search-hit converters (used by MetalArchives.search_* methods)
# ---------------------------------------------------------------------------

def band_search_hit_to_entity(hit: BandSearchHit) -> Entity:
    """Convert a ``BandSearchHit`` (search result) to a mediavocab ``Entity``."""
    external_ids: dict = {}
    if hit.ma_id is not None:
        external_ids["ma_band_id"] = str(hit.ma_id)
    extra: dict = {}
    if hit.url:
        extra["artist_url"] = str(hit.url)
    if hit.genre:
        extra["genre"] = hit.genre
    if hit.country:
        extra["country"] = hit.country
    return Entity(name=hit.name, kind=EntityKind.GROUP,
                  external_ids=external_ids, extra=extra)


def album_search_hit_to_release(hit: AlbumSearchHit) -> MvRelease:
    """Convert an ``AlbumSearchHit`` (search result) to a mediavocab ``Release``."""
    external_ids: dict = {}
    if hit.ma_id is not None:
        external_ids["ma_album_id"] = str(hit.ma_id)
    extra: dict = {}
    if hit.band_id is not None:
        extra["ma_band_id"] = str(hit.band_id)
    if hit.genre:
        extra["genre"] = hit.genre
    if hit.type:
        extra["release_type"] = hit.type.value
    if hit.release_date:
        extra["release_date"] = hit.release_date
    credits: list = []
    if hit.band_name:
        artist_ref = EntityRef(name=hit.band_name, kind=EntityKind.GROUP)
        credits.append(Credit(entity=artist_ref, role="artist",
                               relation_role=RelationRole.CREATOR,
                               section=MvCreditSection.PRINCIPAL))
    work = Work(title=hit.title, media_type=MediaType.MUSIC,
                credits=credits, external_ids=external_ids, extra=extra)
    return MvRelease(work=work, uri=str(hit.url) if hit.url else "",
                     image="", stream_mode=StreamMode.ON_DEMAND,
                     external_ids=external_ids)


def song_search_hit_to_release(hit: SongSearchHit) -> MvRelease:
    """Convert a ``SongSearchHit`` (search result) to a mediavocab ``Release``."""
    external_ids: dict = {}
    if hit.song_id:
        external_ids["ma_song_id"] = str(hit.song_id)
    if hit.lyrics_id:
        external_ids["ma_lyrics_id"] = hit.lyrics_id
    extra: dict = {}
    if hit.band_id is not None:
        extra["ma_band_id"] = str(hit.band_id)
    if hit.release_id is not None:
        extra["ma_release_id"] = str(hit.release_id)
    if hit.release_title:
        extra["ma_release_title"] = hit.release_title
    if hit.release_type:
        extra["release_type"] = hit.release_type.value
    credits: list = []
    if hit.band_name:
        artist_ref = EntityRef(name=hit.band_name, kind=EntityKind.GROUP)
        credits.append(Credit(entity=artist_ref, role="artist",
                               relation_role=RelationRole.PERFORMER,
                               section=MvCreditSection.PRINCIPAL))
    work = Work(title=hit.title, media_type=MediaType.MUSIC,
                credits=credits, external_ids=external_ids, extra=extra)
    return MvRelease(work=work, uri="", image="",
                     stream_mode=StreamMode.ON_DEMAND, external_ids=external_ids)
