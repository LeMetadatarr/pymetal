from pymetal.endpoints.artists import get_artist
from pymetal.endpoints.bands import get_band, get_lineup
from pymetal.endpoints.lyrics import get_lyrics, get_lyrics_by_song_id
from pymetal.endpoints.releases import (
    get_discography,
    get_other_versions,
    get_release,
    get_release_lineup,
)
from pymetal.endpoints.search import (
    search_albums,
    search_bands,
    search_songs,
)

__all__ = [
    "get_artist",
    "get_band",
    "get_discography",
    "get_lineup",
    "get_lyrics",
    "get_lyrics_by_song_id",
    "get_other_versions",
    "get_release",
    "get_release_lineup",
    "search_albums",
    "search_bands",
    "search_songs",
]
