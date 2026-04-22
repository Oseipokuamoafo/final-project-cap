"""
Spotify client using SpotAPI — no API keys, no result limits.

Extracts real track data: title, artist, album, artwork, Spotify link,
duration, and estimated audio features derived from genre.
"""

import logging
from typing import Dict, List

from spotapi import Public

logger = logging.getLogger(__name__)

_GENRE_ENERGY: Dict[str, float] = {
    "metal": 0.92, "punk": 0.88, "edm": 0.88, "electronic": 0.85,
    "hard rock": 0.85, "dance": 0.82, "synthwave": 0.78,
    "hip-hop": 0.75, "hip hop": 0.75, "rap": 0.75,
    "rock": 0.72, "pop": 0.70, "indie pop": 0.62,
    "indie": 0.58, "r&b": 0.58, "jazz": 0.50,
    "country": 0.52, "blues": 0.50, "folk": 0.42,
    "lofi": 0.32, "lo-fi": 0.32, "classical": 0.30, "ambient": 0.25,
}

_GENRE_ACOUSTIC: Dict[str, float] = {
    "classical": 0.85, "folk": 0.75, "jazz": 0.62, "blues": 0.52,
    "country": 0.55, "lofi": 0.55, "lo-fi": 0.55,
    "indie": 0.38, "r&b": 0.32, "indie pop": 0.28,
    "pop": 0.22, "rock": 0.18, "hip-hop": 0.10, "hip hop": 0.10,
    "dance": 0.08, "electronic": 0.06, "synthwave": 0.05,
    "metal": 0.04, "ambient": 0.42,
}

_GENRE_MOOD: Dict[str, str] = {
    "pop": "happy", "dance": "happy", "electronic": "happy",
    "rock": "intense", "metal": "intense", "punk": "intense",
    "lofi": "chill", "lo-fi": "chill", "ambient": "relaxed",
    "classical": "relaxed", "jazz": "relaxed", "folk": "relaxed",
    "blues": "moody", "indie": "moody", "r&b": "moody",
    "hip-hop": "focused", "hip hop": "focused", "synthwave": "focused",
    "indie pop": "moody",
}


def _ms_to_duration(ms: int) -> str:
    secs = ms // 1000
    return f"{secs // 60}:{secs % 60:02d}"


def _parse_track(item: Dict, genre: str, idx: int) -> Dict | None:
    try:
        track = item.get("item", {}).get("data", {})
        title = track.get("name", "").strip()
        if not title:
            return None

        # Artists
        artists = track.get("artists", {}).get("items", [])
        artist = ", ".join(a["profile"]["name"] for a in artists if a.get("profile"))

        # Album
        album_data = track.get("albumOfTrack", {})
        album_name = album_data.get("name", "")

        # Album artwork — prefer 300px, fall back to 640px
        artwork_url = ""
        sources = album_data.get("coverArt", {}).get("sources", [])
        for src in sources:
            if src.get("height") == 300:
                artwork_url = src["url"]
                break
        if not artwork_url and sources:
            artwork_url = sources[-1].get("url", "")

        # Spotify link
        track_id = track.get("id", "")
        spotify_url = f"https://open.spotify.com/track/{track_id}" if track_id else ""

        # Duration
        duration_ms = track.get("duration", {}).get("totalMilliseconds", 0)
        duration = _ms_to_duration(duration_ms) if duration_ms else ""

        # Estimated audio features from genre
        energy       = _GENRE_ENERGY.get(genre, 0.6)
        acousticness = _GENRE_ACOUSTIC.get(genre, 0.3)
        mood         = _GENRE_MOOD.get(genre, "chill")

        return {
            "id":           f"sp_{idx:03d}",
            "title":        title,
            "artist":       artist or "Unknown",
            "album":        album_name,
            "genre":        genre,
            "mood":         mood,
            "energy":       round(energy, 2),
            "acousticness": round(acousticness, 2),
            "artwork_url":  artwork_url,
            "spotify_url":  spotify_url,
            "duration":     duration,
        }
    except Exception:
        return None


def fetch_songs_by_genre(genre: str, limit: int = 20, **_kwargs) -> List[Dict]:
    songs: List[Dict] = []
    queries = [f"{genre} music", genre]

    for query in queries:
        if len(songs) >= limit:
            break
        try:
            for page in Public.song_search(query):
                for item in page:
                    if len(songs) >= limit:
                        break
                    song = _parse_track(item, genre, len(songs) + 1)
                    if song:
                        songs.append(song)
                if len(songs) >= limit:
                    break
        except Exception as exc:
            logger.warning("SpotAPI search failed for query=%r: %s", query, exc)

    logger.info("SpotAPI: %d songs fetched for genre=%s", len(songs), genre)
    return songs
