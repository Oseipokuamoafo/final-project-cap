"""
Reliability tests for the Music Recommender.

Checks:
  - Each profile returns the expected top song (correctness)
  - Confidence scores are in [0.0, 1.0] (validity)
  - Repeated calls with identical input return identical output (determinism)
  - All returned scores are non-negative (score sanity)
  - At least one top-5 song has a genre OR mood match when one exists in the catalog (relevance)
  - Guardrail clamping does not break the scoring pipeline (resilience)
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from recommender import confidence_score, load_songs, max_possible_score, recommend_songs

CSV = os.path.join(os.path.dirname(__file__), "..", "data", "songs.csv")


@pytest.fixture(scope="module")
def songs():
    return load_songs(CSV)


# ── 1. Correctness — expected top song per profile ────────────────────────────

@pytest.mark.parametrize("prefs,expected_title", [
    ({"genre": "pop",  "mood": "happy",   "energy": 0.85}, "Sunrise City"),
    ({"genre": "lofi", "mood": "chill",   "energy": 0.38, "likes_acoustic": True}, "Library Rain"),
    ({"genre": "rock", "mood": "intense", "energy": 0.92}, "Storm Runner"),
])
def test_top_song_is_correct(prefs, expected_title, songs):
    results = recommend_songs(prefs, songs, k=5)
    assert results[0][0]["title"] == expected_title, (
        f"Expected '{expected_title}' at #1 for prefs={prefs}, "
        f"got '{results[0][0]['title']}'"
    )


# ── 2. Confidence validity ────────────────────────────────────────────────────

@pytest.mark.parametrize("prefs", [
    {"genre": "pop",  "mood": "happy",   "energy": 0.85},
    {"genre": "lofi", "mood": "chill",   "energy": 0.38, "likes_acoustic": True},
    {"genre": "rock", "mood": "intense", "energy": 0.92},
])
def test_confidence_in_valid_range(prefs, songs):
    results = recommend_songs(prefs, songs, k=5)
    top_score = results[0][1]
    conf = confidence_score(top_score, prefs)
    assert 0.0 <= conf <= 1.0, f"Confidence {conf} outside [0, 1] for prefs={prefs}"


# ── 3. Determinism — same input yields same output across multiple calls ───────

def test_results_are_deterministic(songs):
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.75}
    run_a = recommend_songs(prefs, songs, k=5)
    run_b = recommend_songs(prefs, songs, k=5)
    run_c = recommend_songs(prefs, songs, k=5)
    titles_a = [s["title"] for s, _, _ in run_a]
    titles_b = [s["title"] for s, _, _ in run_b]
    titles_c = [s["title"] for s, _, _ in run_c]
    assert titles_a == titles_b == titles_c, "Results changed across identical calls"


# ── 4. Score sanity — no negative scores ─────────────────────────────────────

def test_all_scores_non_negative(songs):
    prefs = {"genre": "ambient", "mood": "moody", "energy": 0.5}
    results = recommend_songs(prefs, songs, k=len(songs))
    negatives = [(s["title"], score) for s, score, _ in results if score < 0]
    assert not negatives, f"Negative scores found: {negatives}"


# ── 5. Relevance — at least one top-5 result has a genre or mood match ────────

@pytest.mark.parametrize("prefs", [
    {"genre": "pop",  "mood": "happy",   "energy": 0.8},
    {"genre": "lofi", "mood": "chill",   "energy": 0.4},
    {"genre": "rock", "mood": "intense", "energy": 0.9},
])
def test_top5_contains_genre_or_mood_match(prefs, songs):
    results = recommend_songs(prefs, songs, k=5)
    matched = [
        s for s, _, _ in results
        if s["genre"] == prefs["genre"] or s["mood"] == prefs["mood"]
    ]
    assert matched, (
        f"No genre or mood match in top-5 for prefs={prefs}. "
        f"Titles: {[s['title'] for s, _, _ in results]}"
    )


# ── 6. Resilience — clamped energy still produces valid output ────────────────

def test_clamped_energy_still_scores(songs):
    from guardrails import validate_prefs
    raw = {"genre": "pop", "mood": "happy", "energy": 1.9}
    prefs = validate_prefs(raw)          # clamps to 1.0
    results = recommend_songs(prefs, songs, k=5)
    assert len(results) == 5
    assert all(score >= 0 for _, score, _ in results)
