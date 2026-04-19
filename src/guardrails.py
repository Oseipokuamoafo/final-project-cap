"""Input validation guardrails for the Music Recommender."""

import logging
from typing import Dict

logger = logging.getLogger(__name__)

VALID_GENRES = {
    "pop", "lofi", "rock", "ambient", "jazz", "synthwave",
    "indie pop", "hip-hop", "r&b", "classical", "metal", "electronic", "folk",
}
VALID_MOODS = {"happy", "chill", "intense", "relaxed", "moody", "focused"}


class ValidationError(ValueError):
    pass


def validate_prefs(prefs: Dict) -> Dict:
    """
    Validate and sanitize a user preferences dict.
    Raises ValidationError for unrecoverable inputs; warns and corrects minor issues.
    Returns a sanitized copy of prefs.
    """
    if not isinstance(prefs, dict):
        raise ValidationError("Preferences must be a dictionary.")

    genre = prefs.get("genre", "")
    if genre not in VALID_GENRES:
        logger.warning("Unknown genre '%s' — no genre-match bonus will be applied.", genre)

    mood = prefs.get("mood", "")
    if mood not in VALID_MOODS:
        logger.warning("Unknown mood '%s' — no mood-match bonus will be applied.", mood)

    raw_energy = prefs.get("energy", 0.5)
    try:
        energy = float(raw_energy)
    except (TypeError, ValueError):
        raise ValidationError(
            f"Energy must be a float between 0.0 and 1.0, got: {raw_energy!r}"
        )

    if not (0.0 <= energy <= 1.0):
        clamped = max(0.0, min(1.0, energy))
        logger.warning("Energy %.2f outside [0, 1] — clamping to %.2f.", energy, clamped)
        prefs = {**prefs, "energy": clamped}

    prefs = {**prefs, "likes_acoustic": bool(prefs.get("likes_acoustic", False))}
    logger.debug("Validated prefs: %s", prefs)
    return prefs
