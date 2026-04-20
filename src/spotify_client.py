"""
Spotify API client using Client Credentials flow (no user login required).

Get free credentials at: https://developer.spotify.com/dashboard
  → Create App → copy Client ID + Client Secret into .env

Note: Spotify restricted the audio-features endpoint for apps created after
Nov 2024. This client tries it and falls back to genre-based estimates if
it gets a 403, so the scoring engine still works either way.
"""

import base64
import logging
import os
from typing import Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

_AUTH_URL = "https://accounts.spotify.com/api/token"
_BASE = "https://api.spotify.com/v1"

# Fallback energy estimates when audio-features endpoint is restricted
_GENRE_ENERGY = {
    "metal": 0.92, "punk": 0.88, "electronic": 0.85, "dance": 0.82,
    "synthwave": 0.78, "hip-hop": 0.75, "rock": 0.72, "pop": 0.70,
    "indie pop": 0.62, "indie": 0.58, "r&b": 0.58, "jazz": 0.50,
    "country": 0.52, "blues": 0.50, "folk": 0.42, "lofi": 0.32,
    "lo-fi": 0.32, "classical": 0.30, "ambient": 0.25,
}

_GENRE_ACOUSTIC = {
    "classical": 0.85, "folk": 0.75, "jazz": 0.62, "blues": 0.52,
    "country": 0.55, "lofi": 0.55, "lo-fi": 0.55, "indie": 0.38,
    "r&b": 0.32, "indie pop": 0.28, "pop": 0.22, "rock": 0.18,
    "hip-hop": 0.10, "dance": 0.08, "electronic": 0.06,
    "synthwave": 0.05, "metal": 0.04, "ambient": 0.42,
}

_GENRE_MOOD = {
    "pop": "happy", "dance": "happy", "electronic": "happy",
    "rock": "intense", "metal": "intense", "punk": "intense",
    "lofi": "chill", "lo-fi": "chill", "ambient": "relaxed",
    "classical": "relaxed", "jazz": "relaxed", "folk": "relaxed",
    "blues": "moody", "indie": "moody", "r&b": "moody",
    "hip-hop": "focused", "synthwave": "focused",
}


# ── Auth ──────────────────────────────────────────────────────────────────────

def _get_token(client_id: str, client_secret: str) -> str:
    creds = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    r = requests.post(
        _AUTH_URL,
        headers={"Authorization": f"Basic {creds}", "Content-Type": "application/x-www-form-urlencoded"},
        data={"grant_type": "client_credentials"},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["access_token"]


# ── Track search ──────────────────────────────────────────────────────────────

def _search_tracks(query: str, token: str, limit: int = 20) -> List[Dict]:
    r = requests.get(
        f"{_BASE}/search",
        headers={"Authorization": f"Bearer {token}"},
        params={"q": query, "type": "track", "limit": limit, "market": "US"},
        timeout=10,
    )
    if r.status_code == 400:
        return []          # invalid genre filter — caller will try plain-text fallback
    r.raise_for_status()
    return r.json().get("tracks", {}).get("items", []) or []


# ── Audio features ────────────────────────────────────────────────────────────

def _get_audio_features(track_ids: List[str], token: str) -> Dict[str, Dict]:
    """Returns a {track_id: features_dict} map, or {} if endpoint is restricted."""
    try:
        r = requests.get(
            f"{_BASE}/audio-features",
            headers={"Authorization": f"Bearer {token}"},
            params={"ids": ",".join(track_ids)},
            timeout=10,
        )
        if r.status_code == 403:
            logger.info("Spotify audio-features restricted for this app — using genre-based estimates")
            return {}
        r.raise_for_status()
        return {f["id"]: f for f in (r.json().get("audio_features") or []) if f}
    except Exception as exc:
        logger.warning("Audio-features fetch failed (%s) — using estimates", exc)
        return {}


# ── Song dict builder ─────────────────────────────────────────────────────────

def _mood_from_features(valence: float, energy: float, genre: str) -> str:
    if valence > 0.65 and energy > 0.60:
        return "happy"
    if energy > 0.80:
        return "intense"
    if valence < 0.35:
        return "moody"
    if energy < 0.40:
        return "relaxed"
    return _GENRE_MOOD.get(genre, "chill")


def _track_to_song(track: Dict, genre: str, features: Optional[Dict], idx: int) -> Dict:
    if features:
        energy       = features.get("energy", _GENRE_ENERGY.get(genre, 0.6))
        valence      = features.get("valence", 0.5)
        danceability = features.get("danceability", 0.6)
        acousticness = features.get("acousticness", _GENRE_ACOUSTIC.get(genre, 0.3))
        tempo        = int(features.get("tempo", 120))
        mood         = _mood_from_features(valence, energy, genre)
    else:
        energy       = _GENRE_ENERGY.get(genre, 0.6)
        acousticness = _GENRE_ACOUSTIC.get(genre, 0.3)
        mood         = _GENRE_MOOD.get(genre, "chill")
        valence      = round(energy * 0.85, 2)
        danceability = round(min(1.0, energy * 1.05), 2)
        tempo        = int(60 + energy * 100)

    artists = ", ".join(a["name"] for a in track.get("artists", []))
    return {
        "id": f"sp_{idx:03d}",
        "title": track.get("name", "Unknown"),
        "artist": artists,
        "genre": genre,
        "mood": mood,
        "energy": round(min(1.0, max(0.0, energy)), 2),
        "acousticness": round(min(1.0, max(0.0, acousticness)), 2),
        "valence": round(min(1.0, max(0.0, valence)), 2),
        "danceability": round(min(1.0, max(0.0, danceability)), 2),
        "tempo_bpm": tempo,
    }


# ── Public API ────────────────────────────────────────────────────────────────

def fetch_songs_by_genre(
    genre: str,
    client_id: str,
    client_secret: str,
    limit: int = 20,
) -> List[Dict]:
    """
    Search Spotify for real tracks in *genre* and return scoring-engine-compatible
    song dicts. Uses actual audio features when available, genre-based estimates
    when the audio-features endpoint is restricted.

    Returns [] and logs an error on any failure so callers can fall back gracefully.
    """
    try:
        token = _get_token(client_id, client_secret)

        # Try genre: filter; fall back to plain-text if Spotify returns 400 or nothing
        tracks = _search_tracks(f"genre:{genre}", token, limit=limit)
        if not tracks:
            tracks = _search_tracks(f"{genre} music", token, limit=limit)
        if not tracks:
            tracks = _search_tracks(genre, token, limit=limit)

        track_ids = [t["id"] for t in tracks if t.get("id")]
        features_map = _get_audio_features(track_ids, token) if track_ids else {}

        songs = [
            _track_to_song(t, genre, features_map.get(t.get("id")), i)
            for i, t in enumerate(tracks, 1)
        ]
        source = "audio features" if features_map else "estimated features"
        logger.info("Spotify: %d songs fetched for genre=%s (%s)", len(songs), genre, source)
        return songs

    except Exception as exc:
        logger.error("Spotify fetch failed (genre=%s): %s", genre, exc)
        return []
