"""
Mood parser — uses the LLM to extract structured music preferences from:
  1. Natural language mood description  ("stressed and need to zone out")
  2. List of recently listened songs    ("Radiohead, Portishead, Bon Iver")

Returns a prefs dict compatible with the scoring engine:
  { genre, mood, energy, likes_acoustic, reasoning }
"""

import json
import logging
import os
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

_VALID_MOODS   = {"happy", "chill", "intense", "relaxed", "moody", "focused"}
_VALID_GENRES  = {
    "pop", "lofi", "rock", "ambient", "jazz", "synthwave",
    "indie pop", "hip-hop", "r&b", "classical", "metal", "electronic", "folk",
}

_SYSTEM = """\
You are a music preference analyzer. Given a user's mood description or their \
recent listening history, extract structured music preferences.

Valid moods  : happy, chill, intense, relaxed, moody, focused
Valid genres : pop, lofi, rock, ambient, jazz, synthwave, indie pop, hip-hop, \
r&b, classical, metal, electronic, folk
Energy       : 0.0 = very calm, 1.0 = very intense

Respond with ONLY a JSON object — no markdown, no explanation, no extra text:
{
  "mood": "<valid mood>",
  "genre": "<valid genre>",
  "energy": <float 0.0–1.0>,
  "likes_acoustic": <true | false>,
  "reasoning": "<one sentence>"
}"""

_MOOD_PROMPT = """\
The user says they are feeling: "{text}"

Infer the best music preferences to match this emotional state."""

_SONGS_PROMPT = """\
The user has been listening to these songs/artists recently:
{songs}

Based on the typical genre, energy level, and emotional character of this music, \
infer their current mood and what they would enjoy hearing next."""


# ── LLM call ─────────────────────────────────────────────────────────────────

def _call_llm(user_prompt: str) -> Optional[Dict]:
    text = None

    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        from groq import Groq
        completion = Groq(api_key=groq_key).chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=200,
            temperature=0.2,
        )
        text = completion.choices[0].message.content
    else:
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            import anthropic
            msg = anthropic.Anthropic(api_key=anthropic_key).messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=200,
                system=_SYSTEM,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = msg.content[0].text

    if not text:
        raise RuntimeError("No LLM key available for mood parsing.")

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"LLM returned non-JSON: {text}")

    data = json.loads(match.group())
    return _sanitise(data)


def _sanitise(data: Dict) -> Dict:
    mood  = data.get("mood", "chill").lower()
    genre = data.get("genre", "pop").lower()
    energy = float(data.get("energy", 0.5))

    if mood  not in _VALID_MOODS:   mood  = "chill"
    if genre not in _VALID_GENRES:  genre = "pop"
    energy = max(0.0, min(1.0, energy))

    return {
        "mood":          mood,
        "genre":         genre,
        "energy":        round(energy, 2),
        "likes_acoustic": bool(data.get("likes_acoustic", False)),
        "reasoning":     str(data.get("reasoning", "")),
    }


# ── Public API ────────────────────────────────────────────────────────────────

def from_text(text: str) -> Dict:
    """
    Parse a natural-language mood description into music preferences.
    Example: "anxious and need something calming" → mood=relaxed, energy=0.25
    """
    logger.info("Parsing mood from text: %r", text[:80])
    return _call_llm(_MOOD_PROMPT.format(text=text.strip()))


def from_songs(songs: List[str]) -> Dict:
    """
    Infer music preferences from a list of recently listened songs/artists.
    Example: ["Radiohead", "Portishead", "Bon Iver"] → mood=moody, energy=0.38
    """
    lines = "\n".join(f"- {s.strip()}" for s in songs if s.strip())
    logger.info("Parsing mood from %d songs", len(songs))
    return _call_llm(_SONGS_PROMPT.format(songs=lines))
