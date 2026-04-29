from pymetal.endpoints.artists import get_artist
from pymetal.endpoints.bands import get_band, get_lineup
from pymetal.endpoints.browse import (
    browse_bands_by_country,
    browse_bands_by_genre,
    browse_bands_by_letter,
    browse_labels_by_country,
    browse_labels_by_letter,
    get_rip_artists,
    get_upcoming_releases,
    list_countries,
    list_genre_slugs,
)
from pymetal.endpoints.labels import get_label
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
    "browse_bands_by_country",
    "browse_bands_by_genre",
    "browse_bands_by_letter",
    "browse_labels_by_country",
    "browse_labels_by_letter",
    "list_countries",
    "list_genre_slugs",
    "get_artist",
    "get_band",
    "get_discography",
    "get_label",
    "get_lineup",
    "get_lyrics",
    "get_lyrics_by_song_id",
    "get_other_versions",
    "get_release",
    "get_release_lineup",
    "get_rip_artists",
    "get_upcoming_releases",
    "search_albums",
    "search_bands",
    "search_songs",
]
