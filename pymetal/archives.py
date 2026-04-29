"""High-level facade over the endpoint modules.

Holds a shared `pymetal.http.Client` so all calls reuse the cache.
"""
from __future__ import annotations

from typing import Iterable, Iterator, List, Optional, Sequence, Tuple, Union

from pymetal.endpoints import bands as _bands
from pymetal.endpoints import lyrics as _lyrics
from pymetal.endpoints import releases as _releases
from pymetal.endpoints import search as _search
from pymetal.endpoints._common import ma_id_from_url
from pymetal.http import Client, default_client
from pymetal.locators import GENRES, URL_BAND_RANDOM
from pymetal.models import (
    AlbumSearchHit,
    Band,
    BandSearchHit,
    LineupMember,
    Release,
    ReleaseType,
    Song,
    SongSearchHit,
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

    def random_band(self, genre: Optional[str] = None) -> Band:
        resp = self.client.get(URL_BAND_RANDOM, use_cache=False)
        bid = ma_id_from_url(resp.url)
        if bid is None:
            raise RuntimeError(f"could not extract band id from random redirect {resp.url!r}")
        band = _bands.get_band(bid, client=self.client)
        if genre is None:
            return band
        target = _normalise_genre(genre)
        if target not in GENRES:
            return band
        for _ in range(50):
            band_genre = _normalise_genre(" ".join(band.genres))
            if target in {g.strip() for g in band_genre.split("/")}:
                return band
            resp = self.client.get(URL_BAND_RANDOM, use_cache=False)
            bid = ma_id_from_url(resp.url)
            if bid is not None:
                band = _bands.get_band(bid, client=self.client)
        return band

    # -- search -------------------------------------------------------------

    def search_bands(self, *args, **kwargs) -> Iterator[BandSearchHit]:
        kwargs.setdefault("client", self.client)
        return _search.search_bands(*args, **kwargs)

    def search_albums(self, *args, **kwargs) -> Iterator[AlbumSearchHit]:
        kwargs.setdefault("client", self.client)
        return _search.search_albums(*args, **kwargs)

    def search_songs(self, *args, **kwargs) -> Iterator[SongSearchHit]:
        kwargs.setdefault("client", self.client)
        return _search.search_songs(*args, **kwargs)

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
            if hit.lyrics_id is None:
                continue
            text = self.get_lyrics_by_song_id(hit.lyrics_id)
            if text:
                yield text


if __name__ == "__main__":
    m = MetalArchives()
    for hit in m.search_bands(band_name="Carcass"):
        print(hit)
