"""High-level facade over the endpoint modules.

Holds a shared `pymetal.http.Client` so all calls reuse the cache.
"""
from __future__ import annotations

from typing import Iterable, Iterator, List, Optional, Sequence, Tuple, Union

from mediavocab import Entity
from mediavocab import Release as MvRelease

from pymetal.converters import (
    album_search_hit_to_release,
    band_search_hit_to_entity,
    song_search_hit_to_release,
    stream_links,
)
from pymetal.endpoints import bands as _bands
from pymetal.endpoints import lyrics as _lyrics
from pymetal.endpoints import releases as _releases
from pymetal.endpoints import search as _search
from pymetal.endpoints._common import ma_id_from_url
from pymetal.http import Client, default_client
from pymetal.locators import GENRES, URL_BAND_RANDOM
from pymetal.models import (
    Band,
    LineupMember,
    Release,
    ReleaseType,
    Song,
    TrackAppearance,
)


def _normalise_genre(g: str) -> str:
    return (
        g.lower()
        .replace("death core", "deathcore")
        .replace("metal core", "metalcore")
        .replace("metal", "")
        .replace("trash", "thrash")
        .strip()
    )


class MetalArchives:
    def __init__(self, client: Optional[Client] = None) -> None:
        self.client = client or default_client

    # -- band ---------------------------------------------------------------

    def get_band(self, band_id: int) -> Band:
        return _bands.get_band(band_id, client=self.client)

    def get_band_by_url(self, url: str) -> Band:
        bid = ma_id_from_url(url)
        if bid is None:
            raise ValueError(f"could not extract MA band id from {url!r}")
        return _bands.get_band(bid, client=self.client)

    def get_lineup(self, band_id: int) -> List[LineupMember]:
        return _bands.get_lineup(band_id, client=self.client)

    def get_band_recommendations(self, band_id: int):
        return _bands.get_band_recommendations(band_id, client=self.client)

    def get_links(self, entity_id: int, entity_type: str = "band"):
        return _bands.get_links(entity_id, entity_type=entity_type, client=self.client)

    def get_stream_links(self, band_id: int):
        """External links that provide audio/video streams (YouTube, Bandcamp, SoundCloud, …).

        Fetches the full links tab and filters to streaming-capable services.
        Returns a list of ``ExternalLink`` objects — pass to ``band_to_entity(band, links=...)``
        to get ``entity.extra["stream_urls"]``.
        """
        return stream_links(self.get_links(band_id, entity_type="band"))

    def random_band(
        self,
        genre: Optional[str] = None,
        *,
        max_attempts: int = 20,
        sleep_between: float = 0.3,
    ) -> Band:
        """Roll a random band; if `genre` is given, re-roll until a match.

        Re-rolls also trigger when the parser returns an empty `Band`
        (typical when MA rate-limits and serves a stripped error page).
        Sleeps `sleep_between` seconds between attempts so we don't
        hammer MA.
        """
        import time

        target = _normalise_genre(genre) if genre else None
        if target and target not in GENRES:
            target = None  # caller asked for an unsupported coarse genre

        last_band: Optional[Band] = None
        for attempt in range(max_attempts):
            resp = self.client.get(URL_BAND_RANDOM, use_cache=False)
            bid = ma_id_from_url(resp.url)
            if bid is None:
                if sleep_between:
                    time.sleep(sleep_between)
                continue
            band = _bands.get_band(bid, client=self.client)
            if not band.name:
                # MA likely rate-limited us — back off and retry.
                if sleep_between:
                    time.sleep(sleep_between)
                continue
            last_band = band
            if target is None:
                return band
            band_genre = _normalise_genre(" ".join(band.genres))
            if target in {g.strip() for g in band_genre.split("/") if g.strip()}:
                return band
            if sleep_between:
                time.sleep(sleep_between)
        if last_band is not None:
            return last_band
        raise RuntimeError(
            f"could not get a random band after {max_attempts} attempts "
            "(metal-archives may be rate-limiting)"
        )

    # -- search -------------------------------------------------------------

    def search_bands(self, *args, **kwargs) -> Iterator[Entity]:
        kwargs.setdefault("client", self.client)
        for hit in _search.search_bands(*args, **kwargs):
            yield band_search_hit_to_entity(hit)

    def search_albums(self, *args, **kwargs) -> Iterator[MvRelease]:
        kwargs.setdefault("client", self.client)
        for hit in _search.search_albums(*args, **kwargs):
            yield album_search_hit_to_release(hit)

    def search_songs(self, *args, **kwargs) -> Iterator[MvRelease]:
        kwargs.setdefault("client", self.client)
        for hit in _search.search_songs(*args, **kwargs):
            yield song_search_hit_to_release(hit)

    # -- release ------------------------------------------------------------

    def get_release(self, release_id: int) -> Tuple[Release, List[Song], List[TrackAppearance]]:
        return _releases.get_release(release_id, client=self.client)

    def get_discography(self, band_id: int) -> List[Release]:
        return _releases.get_discography(band_id, client=self.client)

    def get_release_lineup(self, release_id: int):
        return _releases.get_release_lineup(release_id, client=self.client)

    def get_other_versions(self, release_id: int) -> List[Release]:
        return _releases.get_other_versions(release_id, client=self.client)

    # -- artist -------------------------------------------------------------

    def get_artist(self, artist_id: int):
        from pymetal.endpoints.artists import get_artist
        return get_artist(artist_id, client=self.client)

    # -- label --------------------------------------------------------------

    def get_label(self, label_id: int):
        from pymetal.endpoints.labels import get_label
        return get_label(label_id, client=self.client)

    # -- browse -------------------------------------------------------------

    def browse_bands_by_country(self, country_code: str, **kw):
        from pymetal.endpoints.browse import browse_bands_by_country
        kw.setdefault("client", self.client)
        return browse_bands_by_country(country_code, **kw)

    def browse_bands_by_genre(self, genre_slug: str, **kw):
        from pymetal.endpoints.browse import browse_bands_by_genre
        kw.setdefault("client", self.client)
        return browse_bands_by_genre(genre_slug, **kw)

    def browse_bands_by_letter(self, letter: str, **kw):
        from pymetal.endpoints.browse import browse_bands_by_letter
        kw.setdefault("client", self.client)
        return browse_bands_by_letter(letter, **kw)

    def get_upcoming_releases(self, **kw):
        from pymetal.endpoints.browse import get_upcoming_releases
        kw.setdefault("client", self.client)
        return get_upcoming_releases(**kw)

    def get_rip_artists(self, **kw):
        from pymetal.endpoints.browse import get_rip_artists
        kw.setdefault("client", self.client)
        return get_rip_artists(**kw)

    def browse_labels_by_country(self, country_code: str, **kw):
        from pymetal.endpoints.browse import browse_labels_by_country
        kw.setdefault("client", self.client)
        return browse_labels_by_country(country_code, **kw)

    def browse_labels_by_letter(self, letter: str, **kw):
        from pymetal.endpoints.browse import browse_labels_by_letter
        kw.setdefault("client", self.client)
        return browse_labels_by_letter(letter, **kw)

    def list_countries(self):
        from pymetal.endpoints.browse import list_countries
        return list_countries(client=self.client)

    @staticmethod
    def list_genre_slugs():
        from pymetal.endpoints.browse import list_genre_slugs
        return list_genre_slugs()

    def browse_reviews(self, year=None, month=None, **kw):
        from pymetal.endpoints.browse import browse_reviews
        kw.setdefault("client", self.client)
        return browse_reviews(year=year, month=month, **kw)

    def get_band_reviews(self, band_id: int, **kw):
        from pymetal.endpoints.browse import get_band_reviews
        kw.setdefault("client", self.client)
        return get_band_reviews(band_id, **kw)

    # -- lyrics -------------------------------------------------------------

    def get_lyrics_by_song_id(self, song_id: Union[int, str]) -> Optional[str]:
        return _lyrics.get_lyrics_by_song_id(song_id, client=self.client)

    def get_lyrics(
        self,
        song_title: str = "",
        band_name: str = "",
        release_type: Optional[Sequence[Union[str, int, ReleaseType]]] = None,
        client: Optional[Client] = None,
    ) -> Iterator[str]:
        for hit in self.search_songs(
            song_title=song_title,
            band_name=band_name,
            release_type=release_type,
        ):
            # ``search_songs`` yields mediavocab ``Release`` objects; the MA
            # lyrics id is stashed under ``external_ids['ma_lyrics_id']``.
            lyrics_id = hit.external_ids.get("ma_lyrics_id") if hit.external_ids else None
            if not lyrics_id:
                continue
            text = self.get_lyrics_by_song_id(lyrics_id)
            if text:
                yield text


if __name__ == "__main__":
    m = MetalArchives()
    for hit in m.search_bands(band_name="Carcass"):
        print(hit)
