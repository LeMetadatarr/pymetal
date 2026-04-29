"""Lyrics endpoint."""
from __future__ import annotations

from typing import Iterator, Optional, Sequence, Union

from pymetal.endpoints.search import search_songs
from pymetal.http import Client, default_client
from pymetal.locators import LYRICS_NOT_AVAILABLE, RE_TAGS, URL_LYRICS
from pymetal.models import ReleaseType


def get_lyrics_by_song_id(song_id: Union[int, str], client: Optional[Client] = None) -> Optional[str]:
    """Return cleaned lyrics text or None if MA reports them unavailable."""
    c = client or default_client
    resp = c.get(URL_LYRICS + str(song_id))
    text = RE_TAGS.sub("", resp.text.strip())
    if not text or text == LYRICS_NOT_AVAILABLE:
        return None
    return text


def get_lyrics(
    song_title: str = "",
    band_name: str = "",
    release_type: Optional[Sequence[Union[str, int, ReleaseType]]] = None,
    client: Optional[Client] = None,
) -> Iterator[str]:
    for hit in search_songs(
        song_title=song_title,
        band_name=band_name,
        release_type=release_type,
        client=client,
    ):
        if hit.lyrics_id is None:
            continue
        text = get_lyrics_by_song_id(hit.lyrics_id, client=client)
        if text:
            yield text
