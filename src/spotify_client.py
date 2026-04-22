"""
Spotify client using SpotAPI — no API keys, no result limits.

Fetches real Spotify songs for a genre PLUS related genres and similar
artists, so results are musically cohesive rather than just keyword matches.
"""

import logging
from typing import Dict, List

from spotapi import Public

logger = logging.getLogger(__name__)

# ── Genre audio-feature estimates ─────────────────────────────────────────────

_GENRE_ENERGY: Dict[str, float] = {
    "metal": 0.92, "punk": 0.88, "edm": 0.88, "electronic": 0.85,
    "hard rock": 0.85, "dance": 0.82, "synthwave": 0.78,
    "hip-hop": 0.75, "hip hop": 0.75, "rap": 0.75,
    "rock": 0.72, "pop": 0.70, "afrobeats": 0.78, "afropop": 0.72,
    "afroswing": 0.68, "afro fusion": 0.70, "amapiano": 0.72,
    "highlife": 0.65, "afrosoul": 0.55,
    "indie pop": 0.62, "indie": 0.58, "r&b": 0.58, "jazz": 0.50,
    "country": 0.52, "blues": 0.50, "folk": 0.42,
    "lofi": 0.32, "lo-fi": 0.32, "classical": 0.30, "ambient": 0.25,
}

_GENRE_ACOUSTIC: Dict[str, float] = {
    "classical": 0.85, "folk": 0.75, "jazz": 0.62, "blues": 0.52,
    "country": 0.55, "lofi": 0.55, "lo-fi": 0.55,
    "afrosoul": 0.52, "highlife": 0.48, "afro fusion": 0.38,
    "indie": 0.38, "r&b": 0.32, "indie pop": 0.28, "afropop": 0.25,
    "afrobeats": 0.18, "afroswing": 0.15, "amapiano": 0.12,
    "pop": 0.22, "rock": 0.18, "hip-hop": 0.10, "hip hop": 0.10,
    "dance": 0.08, "electronic": 0.06, "synthwave": 0.05, "metal": 0.04,
    "ambient": 0.42,
}

_GENRE_MOOD: Dict[str, str] = {
    "pop": "happy", "dance": "happy", "electronic": "happy",
    "afrobeats": "happy", "afropop": "happy", "amapiano": "happy",
    "afroswing": "chill", "afro fusion": "chill", "highlife": "happy",
    "afrosoul": "moody",
    "rock": "intense", "metal": "intense", "punk": "intense",
    "lofi": "chill", "lo-fi": "chill", "ambient": "relaxed",
    "classical": "relaxed", "jazz": "relaxed", "folk": "relaxed",
    "blues": "moody", "indie": "moody", "r&b": "moody",
    "hip-hop": "focused", "hip hop": "focused", "synthwave": "focused",
    "indie pop": "moody",
}

# ── Related genres — fetching these alongside the primary broadens results ─────

_RELATED_GENRES: Dict[str, List[str]] = {
    # African / Afro
    "afrobeats":   ["afropop", "afroswing", "amapiano", "afrosoul"],
    "afrosoul":    ["afrobeats", "afropop", "afro fusion", "r&b"],
    "afropop":     ["afrobeats", "afrosoul", "highlife", "pop"],
    "afroswing":   ["afrobeats", "afropop", "r&b"],
    "amapiano":    ["afrobeats", "afropop", "electronic"],
    "highlife":    ["afrobeats", "afropop", "afrosoul"],
    "afro fusion": ["afrobeats", "afrosoul", "jazz", "r&b"],
    # Western
    "pop":         ["indie pop", "dance", "r&b"],
    "rock":        ["indie", "alternative", "hard rock"],
    "hip-hop":     ["r&b", "rap", "trap"],
    "r&b":         ["soul", "hip-hop", "afrosoul"],
    "lofi":        ["chillhop", "ambient", "jazz"],
    "jazz":        ["soul", "blues", "bossa nova"],
    "electronic":  ["synthwave", "dance", "ambient"],
    "indie pop":   ["indie", "pop", "folk"],
    "folk":        ["indie", "country", "acoustic"],
    "classical":   ["ambient", "instrumental"],
    "metal":       ["hard rock", "rock"],
    "ambient":     ["lofi", "classical", "electronic"],
    "synthwave":   ["electronic", "retro pop"],
}

# ── Artist search queries for popular genres ──────────────────────────────────

_GENRE_ARTISTS: Dict[str, List[str]] = {
    "afrobeats":   ["Burna Boy", "Wizkid", "Davido", "Rema", "Tems"],
    "afrosoul":    ["Tems", "Adekunle Gold", "Simi", "Fireboy DML"],
    "afropop":     ["Wizkid", "Davido", "CKay", "Omah Lay", "BNXN"],
    "afroswing":   ["Afro B", "Kojo Funds", "Not3s", "Fredo"],
    "amapiano":    ["Kabza De Small", "DJ Maphorisa", "Focalistic", "Ami Faku"],
    "highlife":    ["Fela Kuti", "King Sunny Ade", "Ebo Taylor"],
    "afro fusion": ["Burna Boy", "Tems", "Adekunle Gold", "Yemi Alade"],
    "lofi":        ["Joji", "potsu", "tomppabeats"],
    "jazz":        ["Miles Davis", "John Coltrane", "Norah Jones"],
    "r&b":         ["Frank Ocean", "SZA", "Daniel Caesar", "Bryson Tiller"],
    "hip-hop":     ["Kendrick Lamar", "J. Cole", "Drake"],
    "pop":         ["The Weeknd", "Dua Lipa", "Harry Styles"],
    "rock":        ["Arctic Monkeys", "The Strokes", "Tame Impala"],
    "electronic":  ["Disclosure", "Kaytranada", "Four Tet"],
    "indie pop":   ["Clairo", "Beabadoobee", "Dominic Fike"],
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

        artists = track.get("artists", {}).get("items", [])
        artist = ", ".join(a["profile"]["name"] for a in artists if a.get("profile"))

        album_data  = track.get("albumOfTrack", {})
        album_name  = album_data.get("name", "")

        artwork_url = ""
        sources = album_data.get("coverArt", {}).get("sources", [])
        for src in sources:
            if src.get("height") == 300:
                artwork_url = src["url"]
                break
        if not artwork_url and sources:
            artwork_url = sources[-1].get("url", "")

        track_id    = track.get("id", "")
        spotify_url = f"https://open.spotify.com/track/{track_id}" if track_id else ""
        duration_ms = track.get("duration", {}).get("totalMilliseconds", 0)
        duration    = _ms_to_duration(duration_ms) if duration_ms else ""

        # Use the canonical genre passed in for scoring, not the search term
        canonical = genre
        energy       = _GENRE_ENERGY.get(canonical, 0.6)
        acousticness = _GENRE_ACOUSTIC.get(canonical, 0.3)
        mood         = _GENRE_MOOD.get(canonical, "chill")

        return {
            "id":           f"sp_{idx:03d}",
            "title":        title,
            "artist":       artist or "Unknown",
            "album":        album_name,
            "genre":        canonical,
            "mood":         mood,
            "energy":       round(energy, 2),
            "acousticness": round(acousticness, 2),
            "artwork_url":  artwork_url,
            "spotify_url":  spotify_url,
            "duration":     duration,
        }
    except Exception:
        return None


def _search(query: str, genre: str, songs: list, limit: int) -> None:
    """Run one SpotAPI search query and append results to *songs* up to *limit*."""
    try:
        for page in Public.song_search(query):
            for item in page:
                if len(songs) >= limit:
                    return
                song = _parse_track(item, genre, len(songs) + 1)
                if song and not any(s["title"] == song["title"] and s["artist"] == song["artist"]
                                    for s in songs):
                    songs.append(song)
            if len(songs) >= limit:
                return
    except Exception as exc:
        logger.warning("SpotAPI search failed for %r: %s", query, exc)


def fetch_songs_by_genre(genre: str, limit: int = 30, **_kwargs) -> List[Dict]:
    """
    Fetch real Spotify songs for *genre* plus related genres and key artists.

    Search order:
      1. Primary genre queries  (up to 40% of limit)
      2. Related genre queries  (up to 40% of limit)
      3. Key artist queries     (remaining slots)
    """
    songs: List[Dict] = []
    primary_cap = max(8, int(limit * 0.40))
    related_cap = max(8, int(limit * 0.40))

    # 1. Primary genre
    for q in [f"{genre} music", genre, f"best {genre}"]:
        if len(songs) >= primary_cap:
            break
        _search(q, genre, songs, primary_cap)

    # 2. Related genres (map each to canonical genre for consistent scoring)
    for related in _RELATED_GENRES.get(genre, []):
        if len(songs) >= primary_cap + related_cap:
            break
        _search(f"{related} music", genre, songs, primary_cap + related_cap)

    # 3. Key artists for this genre
    for artist in _GENRE_ARTISTS.get(genre, []):
        if len(songs) >= limit:
            break
        _search(artist, genre, songs, limit)

    logger.info("SpotAPI: %d songs fetched for genre=%s (incl. related genres & artists)",
                len(songs), genre)
    return songs
