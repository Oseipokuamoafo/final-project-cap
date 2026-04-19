"""Tests for the RAG pipeline using a mocked Anthropic client."""

from unittest.mock import MagicMock

import pytest


MOCK_SONGS = [
    {
        "id": 1, "title": "Test Pop", "artist": "Artist A",
        "genre": "pop", "mood": "happy", "energy": 0.8,
        "tempo_bpm": 120, "valence": 0.9, "danceability": 0.8, "acousticness": 0.2,
    },
    {
        "id": 2, "title": "Chill Loop", "artist": "Artist B",
        "genre": "lofi", "mood": "chill", "energy": 0.4,
        "tempo_bpm": 80, "valence": 0.6, "danceability": 0.5, "acousticness": 0.9,
    },
]


def _make_mock_client(text: str = "Great picks!") -> MagicMock:
    mock_content = MagicMock()
    mock_content.text = text
    mock_message = MagicMock()
    mock_message.content = [mock_content]
    mock_message.usage.input_tokens = 50
    mock_message.usage.output_tokens = 20
    client = MagicMock()
    client.messages.create.return_value = mock_message
    return client


def test_rag_returns_required_keys():
    from rag_recommender import rag_recommend
    result = rag_recommend(
        user_prefs={"genre": "pop", "mood": "happy", "energy": 0.8},
        songs=MOCK_SONGS,
        k=2,
        client=_make_mock_client(),
    )
    assert {"retrieved", "context", "response", "usage"} <= result.keys()


def test_rag_response_comes_from_llm():
    from rag_recommender import rag_recommend
    result = rag_recommend(
        user_prefs={"genre": "pop", "mood": "happy", "energy": 0.8},
        songs=MOCK_SONGS,
        k=2,
        client=_make_mock_client("Awesome selections!"),
    )
    assert result["response"] == "Awesome selections!"


def test_rag_retrieves_correct_count():
    from rag_recommender import rag_recommend
    result = rag_recommend(
        user_prefs={"genre": "pop", "mood": "happy", "energy": 0.8},
        songs=MOCK_SONGS,
        k=2,
        client=_make_mock_client(),
    )
    assert len(result["retrieved"]) == 2


def test_rag_top_song_is_genre_match():
    from rag_recommender import rag_recommend
    result = rag_recommend(
        user_prefs={"genre": "pop", "mood": "happy", "energy": 0.8},
        songs=MOCK_SONGS,
        k=2,
        client=_make_mock_client(),
    )
    top_song, top_score, _ = result["retrieved"][0]
    assert top_song["genre"] == "pop"


def test_rag_context_contains_song_titles():
    from rag_recommender import rag_recommend
    result = rag_recommend(
        user_prefs={"genre": "pop", "mood": "happy", "energy": 0.8},
        songs=MOCK_SONGS,
        k=2,
        client=_make_mock_client(),
    )
    assert "Test Pop" in result["context"]
    assert "Chill Loop" in result["context"]


def test_rag_usage_keys_present():
    from rag_recommender import rag_recommend
    result = rag_recommend(
        user_prefs={"genre": "pop", "mood": "happy", "energy": 0.8},
        songs=MOCK_SONGS,
        k=2,
        client=_make_mock_client(),
    )
    assert result["usage"]["input_tokens"] == 50
    assert result["usage"]["output_tokens"] == 20
