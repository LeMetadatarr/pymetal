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
