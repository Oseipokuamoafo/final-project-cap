"""
RAG (Retrieval-Augmented Generation) pipeline for the Music Recommender.

Three-stage pipeline:
  1. Retrieve  — score the full catalog AND retrieve relevant knowledge snippets
  2. Augment   — format both sources as structured context for the LLM
  3. Generate  — call the LLM to produce a natural-language recommendation summary

LLM backends (auto-detected by env var, in priority order):
  1. Groq  — free tier, fast inference (set GROQ_API_KEY)
             Sign up: https://console.groq.com  — no credit card required
  2. Anthropic — Claude Haiku (set ANTHROPIC_API_KEY)
             Sign up: https://console.anthropic.com

RAG Enhancement (stretch feature):
  A second data source — data/music_knowledge.md — is retrieved alongside the song
  catalog. Relevant genre and mood sections are extracted and injected into the context,
  giving the LLM genre-specific vocabulary and mood-adjacency awareness it would not
  have from song scores alone.
"""

import logging
import os
import re
from typing import Dict, List, Optional, Tuple

from recommender import confidence_score, recommend_songs

logger = logging.getLogger(__name__)

_KNOWLEDGE_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "music_knowledge.md"
)

_SYSTEM_PROMPT = """\
You are a knowledgeable music recommendation assistant.
You receive a user's taste profile, a ranked list of retrieved songs, and relevant
genre/mood knowledge context.
Write a concise, friendly recommendation summary (3–5 sentences total) that:
- Names the top pick and explains specifically why it fits the user's profile.
- References genre or mood characteristics from the knowledge context where relevant.
- Notes any interesting pattern across the full results.
- Mentions one "sleeper pick" if a lower-ranked song deserves special attention.
Do not repeat every score verbatim — weave the reasoning into natural prose."""


# ── LLM backend helpers ───────────────────────────────────────────────────────

def _detect_backend(client) -> Tuple[str, object]:
    """
    Return (backend_name, client) by inspecting *client* or env vars.

    Priority when client is None:
      1. GROQ_API_KEY  → Groq  (free, no credit card)
      2. ANTHROPIC_API_KEY → Anthropic

    When client is provided, duck-typing determines the backend:
      - .messages attribute  → Anthropic (also matches mocks in tests)
      - .chat attribute      → Groq
    """
    if client is not None:
        if hasattr(client, "messages"):
            return "anthropic", client
        if hasattr(client, "chat"):
            return "groq", client
        return "anthropic", client  # safe fallback for unknown mocks

    groq_key = os.getenv("GROQ_API_KEY")
    if groq_key:
        from groq import Groq
        logger.info("LLM backend: Groq (free tier)")
        return "groq", Groq(api_key=groq_key)

    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        import anthropic as _anthropic
        logger.info("LLM backend: Anthropic Claude")
        return "anthropic", _anthropic.Anthropic(api_key=anthropic_key)

    raise RuntimeError(
        "No LLM API key found.\n"
        "  • Free option: set GROQ_API_KEY  (get one at https://console.groq.com)\n"
        "  • Paid option: set ANTHROPIC_API_KEY (https://console.anthropic.com)"
    )


def _call_llm(backend: str, client, user_message: str) -> Tuple[str, Dict]:
    """Dispatch to the appropriate LLM backend and return (response_text, usage)."""
    if backend == "groq":
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            max_tokens=512,
        )
        text = completion.choices[0].message.content
        usage = {
            "input_tokens": completion.usage.prompt_tokens,
            "output_tokens": completion.usage.completion_tokens,
        }
        return text, usage

    # Anthropic (default / test mock path)
    import anthropic as _anthropic
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=[{"type": "text", "text": _SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_message}],
    )
    text = message.content[0].text
    usage = {
        "input_tokens": message.usage.input_tokens,
        "output_tokens": message.usage.output_tokens,
    }
    return text, usage


# ── Knowledge retrieval ───────────────────────────────────────────────────────

def _load_knowledge(path: str = _KNOWLEDGE_PATH) -> str:
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.warning("music_knowledge.md not found at %s — skipping.", path)
        return ""


def _extract_knowledge_snippets(knowledge: str, user_prefs: Dict) -> str:
    if not knowledge:
        return ""

    genre = (user_prefs.get("genre") or "").lower()
    mood  = (user_prefs.get("mood")  or "").lower()

    snippets = []
    sections = re.split(r"\n(?=###\s)", knowledge)
    for section in sections:
        heading = section.split("\n")[0].lower()
        if genre in heading or mood in heading:
            snippets.append(section.strip())

    for anchor in ["## Mood Definitions", "## Energy Level Guide", "## Scoring Context"]:
        match = re.search(rf"{re.escape(anchor)}.*?(?=\n## |\Z)", knowledge, re.DOTALL)
        if match:
            snippets.append(match.group().strip())

    if not snippets:
        return ""
    return "Knowledge context:\n" + "\n\n".join(snippets)


# ── Context building ──────────────────────────────────────────────────────────

def _build_song_context(retrieved: List[Tuple[Dict, float, str]]) -> str:
    lines = ["Retrieved songs (best → lowest match):"]
    for i, (song, score, explanation) in enumerate(retrieved, 1):
        lines.append(
            f"  {i}. \"{song['title']}\" by {song['artist']}"
            f" | genre={song['genre']}, mood={song['mood']}, energy={song['energy']:.2f}"
            f" | score={score:.2f} | {explanation}"
        )
    return "\n".join(lines)


# ── Main pipeline ─────────────────────────────────────────────────────────────

def rag_recommend(
    user_prefs: Dict,
    songs: List[Dict],
    k: int = 5,
    client=None,
    use_knowledge: bool = True,
) -> Dict:
    """
    Full RAG pipeline: retrieve → augment → generate.

    The LLM backend is selected automatically:
      - GROQ_API_KEY set  → Groq (free, recommended)
      - ANTHROPIC_API_KEY set → Claude Haiku
      - client passed in  → use that client directly (used by tests)

    Args:
        use_knowledge: inject genre/mood snippets from music_knowledge.md (default True).
                       Set False to run the baseline (songs only) for comparison.

    Returns a dict with keys:
        retrieved       — list of (song_dict, score, explanation) tuples
        context         — the augmented context sent to the LLM
        knowledge_used  — knowledge snippet injected (empty string if disabled)
        response        — LLM's natural-language recommendation text
        usage           — dict with input_tokens / output_tokens
        confidence      — float 0.0–1.0
        backend         — "groq" or "anthropic"
    """
    # 1. Retrieve — songs
    logger.info("RAG 1/3 — retrieving top %d songs for prefs: %s", k, user_prefs)
    retrieved = recommend_songs(user_prefs, songs, k=k)
    top_score = retrieved[0][1] if retrieved else 0.0
    conf = confidence_score(top_score, user_prefs)
    logger.info("Retrieved %d songs; top score=%.2f, confidence=%.3f", len(retrieved), top_score, conf)

    # 1b. Retrieve — knowledge base
    knowledge_snippet = ""
    if use_knowledge:
        raw_knowledge = _load_knowledge()
        knowledge_snippet = _extract_knowledge_snippets(raw_knowledge, user_prefs)
        if knowledge_snippet:
            logger.info("Knowledge: injecting %d chars of genre/mood context", len(knowledge_snippet))

    # 2. Augment
    song_context = _build_song_context(retrieved)
    parts = [
        f"My preferences: genre={user_prefs.get('genre')}, "
        f"mood={user_prefs.get('mood')}, "
        f"energy={float(user_prefs.get('energy', 0.5)):.2f}, "
        f"likes_acoustic={user_prefs.get('likes_acoustic', False)}",
        "",
        song_context,
    ]
    if knowledge_snippet:
        parts += ["", knowledge_snippet]
    user_message = "\n".join(parts)

    # 3. Generate
    backend, actual_client = _detect_backend(client)
    logger.info("RAG 3/3 — calling %s (knowledge=%s)", backend, use_knowledge)
    response_text, usage = _call_llm(backend, actual_client, user_message)
    logger.info("Generation done — input=%d tokens, output=%d tokens",
                usage["input_tokens"], usage["output_tokens"])

    return {
        "retrieved": retrieved,
        "context": user_message,
        "knowledge_used": knowledge_snippet,
        "response": response_text,
        "usage": usage,
        "confidence": conf,
        "backend": backend,
    }
