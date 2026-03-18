"""
Command line runner for the Music Recommender Simulation.

Runs three distinct user profiles to compare recommendations.
"""

import os
from recommender import load_songs, recommend_songs


# Three diverse user profiles for evaluation
PROFILES = [
    {
        "name": "High-Energy Pop Fan",
        "prefs": {"genre": "pop", "mood": "happy", "energy": 0.85, "likes_acoustic": False},
    },
    {
        "name": "Chill Lofi Listener",
        "prefs": {"genre": "lofi", "mood": "chill", "energy": 0.38, "likes_acoustic": True},
    },
    {
        "name": "Deep Intense Rock Head",
        "prefs": {"genre": "rock", "mood": "intense", "energy": 0.92, "likes_acoustic": False},
    },
]


def main() -> None:
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "songs.csv")
    songs = load_songs(csv_path)
    print(f"Loaded songs: {len(songs)}\n")

    for profile in PROFILES:
        print("=" * 55)
        print(f"Profile: {profile['name']}")
        print(f"Prefs:   {profile['prefs']}")
        print("-" * 55)

        recommendations = recommend_songs(profile["prefs"], songs, k=5)
        for i, (song, score, explanation) in enumerate(recommendations, 1):
            print(f"  {i}. {song['title']} by {song['artist']}")
            print(f"     Score: {score:.2f}")
            print(f"     Because: {explanation}")
        print()


if __name__ == "__main__":
    main()
