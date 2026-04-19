import pytest
from guardrails import ValidationError, validate_prefs


def test_valid_prefs_pass_through():
    prefs = {"genre": "pop", "mood": "happy", "energy": 0.8, "likes_acoustic": False}
    result = validate_prefs(prefs)
    assert result["energy"] == 0.8
    assert result["likes_acoustic"] is False


def test_energy_clamped_above_one(caplog):
    with caplog.at_level("WARNING"):
        result = validate_prefs({"genre": "pop", "mood": "happy", "energy": 1.5})
    assert result["energy"] == 1.0
    assert "clamping" in caplog.text.lower()


def test_energy_clamped_below_zero():
    result = validate_prefs({"genre": "pop", "mood": "happy", "energy": -0.2})
    assert result["energy"] == 0.0


def test_invalid_energy_type_raises():
    with pytest.raises(ValidationError, match="Energy must be a float"):
        validate_prefs({"genre": "pop", "mood": "happy", "energy": "loud"})


def test_non_dict_raises():
    with pytest.raises(ValidationError):
        validate_prefs("pop happy 0.8")


def test_unknown_genre_warns(caplog):
    with caplog.at_level("WARNING"):
        validate_prefs({"genre": "country", "mood": "happy", "energy": 0.5})
    assert "country" in caplog.text


def test_unknown_mood_warns(caplog):
    with caplog.at_level("WARNING"):
        validate_prefs({"genre": "pop", "mood": "electric", "energy": 0.5})
    assert "electric" in caplog.text


def test_likes_acoustic_coerced_to_bool():
    result = validate_prefs({"genre": "pop", "mood": "happy", "energy": 0.5, "likes_acoustic": 1})
    assert result["likes_acoustic"] is True


def test_missing_likes_acoustic_defaults_false():
    result = validate_prefs({"genre": "pop", "mood": "happy", "energy": 0.5})
    assert result["likes_acoustic"] is False
