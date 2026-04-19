"""
Last.fm API client — fetches real song data for the Music Recommender.

Free API, no OAuth needed. Get a key at: https://www.last.fm/api/account/create

Public functions:
  fetch_songs_by_genre  — top tracks for a genre tag
  fetch_similar_songs   — similar tracks based on a seed (artist, title)

Returns song dicts compatible with the scoring engine's format.
Energy, mood, and acousticness are estimated from the track's Last.fm tags.
"""

import logging
import os
from typing import Dict, List

import requests

logger = logging.getLogger(__name__)

_BASE = "https://ws.audioscrobbler.com/2.0/"

# Tag → energy estimate (0.0–1.0)
_TAG_ENERGY: Dict[str, float] = {
    "metal": 0.92, "punk": 0.90, "edm": 0.88, "energetic": 0.88,
    "electronic": 0.85, "hard rock": 0.85, "dance": 0.82, "upbeat": 0.80,
    "synthwave": 0.78, "hip-hop": 0.75, "hip hop": 0.75, "rap": 0.75,
    "pop": 0.72, "rock": 0.68, "indie": 0.60, "indie pop": 0.62,
    "r&b": 0.58, "country": 0.55, "blues": 0.52, "jazz": 0.50,
    "folk": 0.45, "mellow": 0.38, "acoustic": 0.38, "chill": 0.35,
    "classical": 0.35, "lofi": 0.32, "lo-fi": 0.32, "ambient": 0.25,
    "relaxing": 0.28, "meditation": 0.20, "sleep": 0.15,
}

# Tag → mood label
_TAG_MOOD: Dict[str, str] = {
    "happy": "happy", "upbeat": "happy", "cheerful": "happy",
    "chill": "chill", "lofi": "chill", "lo-fi": "chill",
    "relaxed": "relaxed", "mellow": "relaxed", "calm": "relaxed",
    "sleep": "relaxed", "ambient": "relaxed", "classical": "relaxed",
    "sad": "moody", "melancholy": "moody", "emotional": "moody", "dark": "moody",
    "aggressive": "intense", "metal": "intense", "intense": "intense", "heavy": "intense",
    "study": "focused", "focus": "focused", "concentration": "focused",
}

# Tag → acousticness estimate
_TAG_ACOUSTIC: Dict[str, float] = {
    "acoustic": 0.90, "classical": 0.85, "unplugged": 0.88, "folk": 0.75,
    "singer-songwriter": 0.72, "indie folk": 0.70, "jazz": 0.60, "blues": 0.50,
    "country": 0.55, "lofi": 0.55, "lo-fi": 0.55, "r&b": 0.30, "indie pop": 0.25,
    "pop": 0.20, "rock": 0.18, "hip-hop": 0.08, "hip hop": 0.08,
    "dance": 0.08, "metal": 0.05, "punk": 0.10, "electronic": 0.05,
    "edm": 0.02, "synthwave": 0.05,
}


def _estimate_features(tags: List[str]) -> Dict:
    """Estimate audio features from a list of Last.fm tag strings."""
    tl = [t.lower() for t in tags]

    energies = [_TAG_ENERGY[t] for t in tl if t in _TAG_ENERGY]
    energy = sum(energies) / len(energies) if energies else 0.5

    mood = "chill"
    for t in tl:
        if t in _TAG_MOOD:
            mood = _TAG_MOOD[t]
            break

    acoustics = [_TAG_ACOUSTIC[t] for t in tl if t in _TAG_ACOUSTIC]
    acousticness = sum(acoustics) / len(acoustics) if acoustics else 0.30

    genre = tl[0] if tl else "pop"

    return {
        "genre": genre,
        "mood": mood,
        "energy": round(min(1.0, max(0.0, energy)), 2),
        "acousticness": round(min(1.0, max(0.0, acousticness)), 2),
        "valence": round(min(1.0, energy * 0.85), 2),
        "danceability": round(min(1.0, energy * 1.05), 2),
        "tempo_bpm": int(60 + energy * 100),
    }


def _artist_name(raw) -> str:
    return raw.get("name", str(raw)) if isinstance(raw, dict) else str(raw)


def _get_track_tags(artist: str, title: str, api_key: str) -> List[str]:
    """Fetch the top tags for a specific track. Returns [] on any failure."""
    try:
        r = requests.get(
            _BASE,
            params={
                "method": "track.getTopTags",
                "artist": artist,
                "track": title,
                "api_key": api_key,
                "format": "json",
                "autocorrect": 1,
            },
            timeout=5,
        )
        r.raise_for_status()
        tags = r.json().get("toptags", {}).get("tag", [])
        return [t["name"].lower() for t in tags[:10] if t.get("name")]
    except Exception:
        return []


def _build_song(track: Dict, tags: List[str], song_id: str) -> Dict:
    features = _estimate_features(tags)
    return {
        "id": song_id,
        "title": track.get("name", "Unknown"),
        "artist": _artist_name(track.get("artist", "")),
        **features,
    }


def fetch_songs_by_genre(genre: str, api_key: str, limit: int = 20) -> List[Dict]:
    """
    Return up to *limit* top tracks tagged as *genre* from Last.fm.
    Each result is a song dict compatible with the scoring engine.
    Returns [] and logs an error if the request fails.
    """
    try:
        r = requests.get(
            _BASE,
            params={
                "method": "tag.getTopTracks",
                "tag": genre,
                "api_key": api_key,
                "format": "json",
                "limit": limit,
            },
            timeout=8,
        )
        r.raise_for_status()
        tracks = r.json().get("tracks", {}).get("track", [])
        songs = []
        for i, track in enumerate(tracks, 1):
            artist = _artist_name(track.get("artist", ""))
            title = track.get("name", "")
            tags = [genre] + _get_track_tags(artist, title, api_key)
            songs.append(_build_song(track, tags, f"lfm_{i:03d}"))
        logger.info("Last.fm: %d songs fetched for genre=%s", len(songs), genre)
        return songs
    except requests.RequestException as exc:
        logger.error("Last.fm fetch failed (genre=%s): %s", genre, exc)
        return []


def fetch_similar_songs(artist: str, title: str, api_key: str, limit: int = 5) -> List[Dict]:
    """
    Return up to *limit* tracks that Last.fm considers similar to (artist, title).
    Returns [] and logs an error if the request fails.
    """
    try:
        r = requests.get(
            _BASE,
            params={
                "method": "track.getSimilar",
                "artist": artist,
                "track": title,
                "api_key": api_key,
                "format": "json",
                "limit": limit,
                "autocorrect": 1,
            },
            timeout=8,
        )
        r.raise_for_status()
        tracks = r.json().get("similartracks", {}).get("track", [])
        songs = []
        for i, track in enumerate(tracks, 1):
            a = _artist_name(track.get("artist", ""))
            t = track.get("name", "")
            tags = _get_track_tags(a, t, api_key)
            songs.append(_build_song(track, tags, f"sim_{i:03d}"))
        logger.info("Last.fm: %d similar songs fetched for '%s'", len(songs), title)
        return songs
    except requests.RequestException as exc:
        logger.error("Last.fm similar-tracks failed ('%s'): %s", title, exc)
        return []
