"""
CLI runner for the Music Recommender Simulation.

Runs three user profiles. Pass --rag to enable AI-generated summaries
(requires ANTHROPIC_API_KEY in the environment).
"""

import logging
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from guardrails import ValidationError, validate_prefs
from logger_setup import setup_logging
from recommender import confidence_score, load_songs, recommend_songs

setup_logging(level=os.getenv("LOG_LEVEL", "INFO"), log_file="logs/cli.log")
logger = logging.getLogger(__name__)

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


def run_profile(profile: dict, songs: list, use_rag: bool = False) -> None:
    name = profile["name"]
    logger.info("Running profile: %s", name)

    try:
        prefs = validate_prefs(profile["prefs"])
    except ValidationError as exc:
        logger.error("Invalid prefs for '%s': %s — skipping.", name, exc)
        return

    print("=" * 55)
    print(f"Profile: {name}")
    print(f"Prefs:   {prefs}")
    print("-" * 55)

    if use_rag and os.getenv("ANTHROPIC_API_KEY"):
        from rag_recommender import rag_recommend
        try:
            result = rag_recommend(prefs, songs, k=5)
            print("\nAI Summary:")
            print(result["response"])
            print(f"\nConfidence: {result['confidence']:.0%}")
            print()
            retrieved = result["retrieved"]
        except Exception as exc:
            logger.error("RAG failed for '%s': %s — falling back.", name, exc)
            retrieved = recommend_songs(prefs, songs, k=5)
    else:
        retrieved = recommend_songs(prefs, songs, k=5)

    top_score = retrieved[0][1] if retrieved else 0.0
    conf = confidence_score(top_score, prefs)
    print(f"Confidence: {conf:.0%}  (top score {top_score:.2f} / max possible {top_score/conf:.2f})" if conf > 0 else "")

    for i, (song, score, explanation) in enumerate(retrieved, 1):
        print(f"  {i}. {song['title']} by {song['artist']}")
        print(f"     Score: {score:.2f} | {explanation}")
    print()


def main() -> None:
    use_rag = "--rag" in sys.argv
    csv_path = os.path.join(os.path.dirname(__file__), "..", "data", "songs.csv")

    logger.info("Loading catalog from %s", csv_path)
    songs = load_songs(csv_path)
    logger.info("Loaded %d songs", len(songs))
    print(f"Loaded {len(songs)} songs\n")

    for profile in PROFILES:
        run_profile(profile, songs, use_rag=use_rag)


if __name__ == "__main__":
    main()
