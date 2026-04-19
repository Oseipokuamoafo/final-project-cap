"""
Music Recommender core logic.

Implements:
- Song and UserProfile data classes
- Recommender class (OOP interface used by tests)
- load_songs: reads data/songs.csv into a list of dicts
- score_song: computes a relevance score and explanation for one song
- recommend_songs: ranks all songs and returns the top k
"""

import csv
from typing import List, Dict, Tuple
from dataclasses import dataclass


@dataclass
class Song:
    """Represents a song and its audio attributes."""
    id: int
    title: str
    artist: str
    genre: str
    mood: str
    energy: float
    tempo_bpm: float
    valence: float
    danceability: float
    acousticness: float


@dataclass
class UserProfile:
    """Represents a user's listening taste preferences."""
    favorite_genre: str
    favorite_mood: str
    target_energy: float
    likes_acoustic: bool


class Recommender:
    """OOP wrapper around the scoring logic. Used by tests."""

    def __init__(self, songs: List[Song]):
        """Initialize with a list of Song objects."""
        self.songs = songs

    def recommend(self, user: UserProfile, k: int = 5) -> List[Song]:
        """Return the top k songs ranked by relevance to the user's profile."""
        def song_score(song: Song) -> float:
            score = 0.0
            if song.genre == user.favorite_genre:
                score += 2.0
            if song.mood == user.favorite_mood:
                score += 1.5
            score += 1.0 - abs(song.energy - user.target_energy)
            if user.likes_acoustic:
                score += song.acousticness * 0.5
            return score

        return sorted(self.songs, key=song_score, reverse=True)[:k]

    def explain_recommendation(self, user: UserProfile, song: Song) -> str:
        """Return a plain-language explanation of why a song was recommended."""
        reasons = []
        if song.genre == user.favorite_genre:
            reasons.append(f"genre match: {song.genre} (+2.0)")
        if song.mood == user.favorite_mood:
            reasons.append(f"mood match: {song.mood} (+1.5)")
        energy_score = round(1.0 - abs(song.energy - user.target_energy), 2)
        reasons.append(f"energy similarity (+{energy_score:.2f})")
        if user.likes_acoustic:
            acoustic_bonus = round(song.acousticness * 0.5, 2)
            reasons.append(f"acoustic bonus (+{acoustic_bonus:.2f})")
        return "; ".join(reasons) if reasons else "general match"


def load_songs(csv_path: str) -> List[Dict]:
    """Load songs from a CSV file and return a list of dicts with numeric fields converted."""
    songs = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            songs.append({
                "id":           int(row["id"]),
                "title":        row["title"],
                "artist":       row["artist"],
                "genre":        row["genre"],
                "mood":         row["mood"],
                "energy":       float(row["energy"]),
                "tempo_bpm":    float(row["tempo_bpm"]),
                "valence":      float(row["valence"]),
                "danceability": float(row["danceability"]),
                "acousticness": float(row["acousticness"]),
            })
    return songs


def score_song(user_prefs: Dict, song: Dict) -> Tuple[float, str]:
    """
    Compute a relevance score and explanation string for a single song.

    Scoring rules:
      +2.0  genre match
      +1.5  mood match
      +1.0 * (1 - |user_energy - song_energy|)  energy proximity (0.0 – 1.0)
      +0.5 * song_acousticness  if user likes_acoustic is True

    Returns (score, explanation_string).
    """
    score = 0.0
    reasons = []

    if song["genre"] == user_prefs.get("genre"):
        score += 2.0
        reasons.append(f"genre match: {song['genre']} (+2.0)")

    if song["mood"] == user_prefs.get("mood"):
        score += 1.5
        reasons.append(f"mood match: {song['mood']} (+1.5)")

    target_energy = user_prefs.get("energy", 0.5)
    energy_proximity = round(1.0 - abs(song["energy"] - target_energy), 2)
    score += energy_proximity
    reasons.append(f"energy similarity (+{energy_proximity:.2f})")

    if user_prefs.get("likes_acoustic", False):
        acoustic_bonus = round(song["acousticness"] * 0.5, 2)
        score += acoustic_bonus
        reasons.append(f"acoustic bonus (+{acoustic_bonus:.2f})")

    explanation = "; ".join(reasons) if reasons else "low match"
    return round(score, 2), explanation


def max_possible_score(user_prefs: Dict) -> float:
    """Theoretical maximum score any song could earn for these preferences."""
    base = 2.0 + 1.5 + 1.0  # genre + mood + perfect energy proximity
    if user_prefs.get("likes_acoustic", False):
        base += 0.5
    return base


def confidence_score(top_score: float, user_prefs: Dict) -> float:
    """
    Ratio of the top song's score to the theoretical maximum (0.0–1.0).
    A score of 1.0 means the best available song matched every criterion perfectly.
    """
    maximum = max_possible_score(user_prefs)
    return round(min(top_score / maximum, 1.0), 3) if maximum > 0 else 0.0


def recommend_songs(user_prefs: Dict, songs: List[Dict], k: int = 5) -> List[Tuple[Dict, float, str]]:
    """
    Score every song against user preferences and return the top k results.

    Uses sorted() (non-destructive) so the original song list is unchanged.
    Returns a list of (song_dict, score, explanation) tuples, highest score first.
    """
    scored = []
    for song in songs:
        score, explanation = score_song(user_prefs, song)
        scored.append((song, score, explanation))

    return sorted(scored, key=lambda x: x[1], reverse=True)[:k]
