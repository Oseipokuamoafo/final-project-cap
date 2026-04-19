"""
Few-shot style specialization for the Music Recommender.

Demonstrates that output measurably differs across three recommendation personas:
  - DJ        energetic, hype, club-ready language
  - Study     calm, focused, productivity-oriented language
  - Wellness  empathetic, emotional, self-care framing

Each persona is defined by a system prompt + 2 few-shot examples that lock in
vocabulary and tone. A baseline (no examples) is also available for comparison.

Measurable difference is verified by checking for persona-specific marker words
in the generated output (see STYLE_MARKERS below).
"""

import logging
from typing import Dict, List, Optional, Tuple

import anthropic

from recommender import confidence_score, recommend_songs

logger = logging.getLogger(__name__)

# ── Marker words used by the test harness to confirm style adherence ──────────
STYLE_MARKERS = {
    "dj":       ["drop", "floor", "crowd", "bpm", "mix", "beat", "energy", "hype", "track", "vibe"],
    "study":    ["focus", "study", "concentration", "productive", "distraction", "workflow",
                 "steady", "background", "calm", "session"],
    "wellness": ["feel", "mood", "emotional", "breathe", "space", "restor", "comfort",
                 "nurtur", "gentle", "mindful"],
    "baseline": [],
}

# ── Persona definitions ───────────────────────────────────────────────────────

_BASE_INSTRUCTION = (
    "You receive a user's music preferences and a ranked list of retrieved songs. "
    "Write a 3–4 sentence recommendation summary."
)

PERSONAS: Dict[str, Dict] = {

    "baseline": {
        "system": _BASE_INSTRUCTION,
        "examples": [],
    },

    "dj": {
        "system": (
            "You are an enthusiastic DJ giving track recommendations. "
            "Use high-energy, club-oriented language. Reference BPM, danceability, "
            "drops, and crowd energy. Keep it hype but informative."
        ),
        "examples": [
            {
                "prefs": "genre=electronic, mood=moody, energy=0.83",
                "songs": '1. "Neon Cascade" | score=3.90 | genre match: electronic (+2.0); energy similarity (+0.98)',
                "response": (
                    "Yo, Neon Cascade is the one — that 0.83 energy is going to move the floor "
                    "without blowing anyone out at the start of the night. The electronic production "
                    "is clean and the moody vibe makes it perfect for that pre-drop tension. "
                    "Throw this in your opening set and watch the crowd lock in."
                ),
            },
            {
                "prefs": "genre=pop, mood=happy, energy=0.85",
                "songs": '1. "Sunrise City" | score=4.47 | genre match: pop (+2.0); mood match: happy (+1.5); energy similarity (+0.97)',
                "response": (
                    "Sunrise City is a certified banger for this slot — pop, happy, and hitting 0.82 "
                    "energy means the BPM is in that sweet spot for peak-hour crowd control. "
                    "This track will keep the floor locked and smiling. "
                    "Queue it between your mid-energy builds and watch the room light up."
                ),
            },
        ],
    },

    "study": {
        "system": (
            "You are a productivity coach recommending background music for focused work. "
            "Emphasize how each track supports concentration, avoids distraction, and "
            "maintains a steady workflow. Keep the tone calm and practical."
        ),
        "examples": [
            {
                "prefs": "genre=lofi, mood=chill, energy=0.38, likes_acoustic=True",
                "songs": '1. "Library Rain" | score=4.90 | genre match: lofi (+2.0); mood match: chill (+1.5); energy similarity (+0.97); acoustic bonus (+0.43)',
                "response": (
                    "Library Rain is an excellent choice for a focused study session — its low energy "
                    "and chill lofi texture create a steady, non-distracting background that supports "
                    "sustained concentration without pulling your attention away from the work. "
                    "The acoustic warmth reduces mental fatigue over longer sessions. "
                    "This is exactly the kind of track to put on when you need to stay in flow for two hours."
                ),
            },
            {
                "prefs": "genre=classical, mood=focused, energy=0.22",
                "songs": '1. "Cathedral Echo" | score=3.97 | genre match: classical (+2.0); mood match: focused (+1.5); energy similarity (+0.98)',
                "response": (
                    "Cathedral Echo is built for deep concentration — classical, very low energy, "
                    "and a focused mood means it provides structure without stimulation. "
                    "The acoustic texture keeps the soundscape organic and prevents the digital fatigue "
                    "that electronic tracks can introduce over long work sessions. "
                    "Add this to your study playlist for tasks that require careful, sustained thinking."
                ),
            },
        ],
    },

    "wellness": {
        "system": (
            "You are a wellness guide recommending music for emotional wellbeing and self-care. "
            "Emphasize how each track makes the listener feel, its emotional qualities, and "
            "when in their day or mood it would be most restorative. Use warm, empathetic language."
        ),
        "examples": [
            {
                "prefs": "genre=r&b, mood=relaxed, energy=0.44",
                "songs": '1. "Sunday Slow Dance" | score=3.94 | genre match: r&b (+2.0); mood match: relaxed (+1.5); energy similarity (+0.44)',
                "response": (
                    "Sunday Slow Dance feels like a gentle exhale — the r&b warmth and relaxed mood "
                    "create a space where you can let go of the tension you've been carrying. "
                    "This is the kind of track to put on when you need to remind yourself to slow down "
                    "and just be present for a few minutes. "
                    "Let it carry you into the evening without any pressure."
                ),
            },
            {
                "prefs": "genre=folk, mood=relaxed, energy=0.31, likes_acoustic=True",
                "songs": '1. "Golden Hour" | score=3.96 | genre match: folk (+2.0); mood match: relaxed (+1.5); energy similarity (+0.81); acoustic bonus (+0.48)',
                "response": (
                    "Golden Hour offers something genuinely restorative — the acoustic folk warmth "
                    "and very low energy make it feel like sitting in soft afternoon light with nowhere "
                    "to be. It's the kind of music that gently reminds you to breathe. "
                    "If you've been going hard all day, this track is your permission slip to rest."
                ),
            },
        ],
    },
}


# ── Style generation ──────────────────────────────────────────────────────────

def _build_few_shot_messages(
    persona_key: str,
    user_prefs: Dict,
    retrieved: List[Tuple[Dict, float, str]],
) -> list:
    persona = PERSONAS[persona_key]
    messages = []

    for ex in persona["examples"]:
        messages.append({
            "role": "user",
            "content": f"Preferences: {ex['prefs']}\n\nRetrieved songs:\n{ex['songs']}",
        })
        messages.append({"role": "assistant", "content": ex["response"]})

    song_lines = "\n".join(
        f"{i}. \"{s['title']}\" by {s['artist']} | genre={s['genre']}, mood={s['mood']}, "
        f"energy={s['energy']:.2f} | score={sc:.2f} | {exp}"
        for i, (s, sc, exp) in enumerate(retrieved, 1)
    )
    prefs_str = (
        f"genre={user_prefs.get('genre')}, mood={user_prefs.get('mood')}, "
        f"energy={float(user_prefs.get('energy', 0.5)):.2f}, "
        f"likes_acoustic={user_prefs.get('likes_acoustic', False)}"
    )
    messages.append({
        "role": "user",
        "content": f"Preferences: {prefs_str}\n\nRetrieved songs:\n{song_lines}",
    })
    return messages


def styled_recommend(
    user_prefs: Dict,
    songs: List[Dict],
    persona: str = "baseline",
    k: int = 5,
    client: Optional[anthropic.Anthropic] = None,
) -> Dict:
    """
    Generate a recommendation summary using the specified few-shot persona.

    Args:
        persona: one of "baseline", "dj", "study", "wellness"

    Returns:
        retrieved    — top-k (song, score, explanation) tuples
        response     — styled recommendation text
        persona      — the persona used
        confidence   — float 0.0–1.0
        usage        — token counts
    """
    if persona not in PERSONAS:
        raise ValueError(f"Unknown persona '{persona}'. Choose from: {list(PERSONAS)}")

    if client is None:
        client = anthropic.Anthropic()

    retrieved = recommend_songs(user_prefs, songs, k=k)
    top_score = retrieved[0][1] if retrieved else 0.0
    conf = confidence_score(top_score, user_prefs)

    logger.info("Styled recommend — persona=%s, confidence=%.3f", persona, conf)

    messages = _build_few_shot_messages(persona, user_prefs, retrieved)

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=400,
        system=[{
            "type": "text",
            "text": PERSONAS[persona]["system"],
            "cache_control": {"type": "ephemeral"},
        }],
        messages=messages,
    )

    response_text = message.content[0].text
    logger.info("Style generation complete — persona=%s, output=%d tokens",
                persona, message.usage.output_tokens)

    return {
        "retrieved": retrieved,
        "response": response_text,
        "persona": persona,
        "confidence": conf,
        "usage": {
            "input_tokens": message.usage.input_tokens,
            "output_tokens": message.usage.output_tokens,
        },
    }


def measure_style_adherence(response: str, persona: str) -> Dict:
    """
    Count how many persona marker words appear in the response.
    Returns hit_count, total_markers, and adherence ratio (0.0–1.0).
    """
    markers = STYLE_MARKERS.get(persona, [])
    if not markers:
        return {"hit_count": 0, "total_markers": 0, "adherence": 0.0}
    lower = response.lower()
    hits = [m for m in markers if m in lower]
    return {
        "hit_count": len(hits),
        "total_markers": len(markers),
        "adherence": round(len(hits) / len(markers), 3),
        "matched": hits,
    }
