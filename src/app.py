"""VibeFinder — AI Music Recommender with mood-aware suggestions."""

import logging
import os
import sys

from dotenv import load_dotenv
import streamlit as st

load_dotenv()
sys.path.insert(0, os.path.dirname(__file__))

from guardrails import VALID_GENRES, VALID_MOODS, ValidationError, validate_prefs
from logger_setup import setup_logging
from recommender import confidence_score, load_songs, recommend_songs

setup_logging(level=os.getenv("LOG_LEVEL", "INFO"), log_file="logs/app.log")
logger = logging.getLogger(__name__)

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "songs.csv")


# ── Cached data loaders ───────────────────────────────────────────────────────

@st.cache_data
def get_csv_songs():
    return load_songs(CSV_PATH)


@st.cache_data(ttl=300)
def get_spotify_songs(genre: str) -> list:
    from spotify_client import fetch_songs_by_genre
    return fetch_songs_by_genre(genre, limit=20)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _has_llm() -> bool:
    return bool(os.getenv("GROQ_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))


def _llm_name() -> str:
    return "Groq" if os.getenv("GROQ_API_KEY") else "Claude"


def _load_songs_for_genre(genre: str) -> tuple[list, str]:
    """Return (songs, source_label) — Spotify live or CSV fallback."""
    with st.spinner(f"Fetching live {genre} tracks from Spotify…"):
        live = get_spotify_songs(genre)
    if live:
        return live, f"Spotify · {len(live)} live tracks"
    st.warning("Spotify unavailable — using local catalog.")
    return get_csv_songs(), "local catalog"


def _run_rag(prefs, songs, k):
    from rag_recommender import rag_recommend
    return rag_recommend(prefs, songs, k=k)


def _show_results(prefs: dict, songs: list, k: int) -> None:
    """Score songs, optionally generate AI summary, and render results."""
    retrieved = []

    if _has_llm():
        with st.spinner(f"Scoring songs and generating AI summary via {_llm_name()}…"):
            try:
                result = _run_rag(prefs, songs, k)
                backend = result.get("backend", "AI").capitalize()
                st.subheader(f"AI Recommendation Summary  ·  {backend}")
                st.info(result["response"])
                retrieved = result["retrieved"]
                logger.info("RAG complete — backend=%s usage=%s",
                            result.get("backend"), result["usage"])
            except Exception as exc:
                logger.error("RAG failed: %s", exc, exc_info=True)
                st.warning("AI summary unavailable — showing scored results.")
                retrieved = recommend_songs(prefs, songs, k=k)
    else:
        st.caption("Set GROQ_API_KEY (free) to enable AI summaries.")
        retrieved = recommend_songs(prefs, songs, k=k)

    if not retrieved:
        st.error("No songs found for these preferences.")
        return

    top_score = retrieved[0][1]
    conf = confidence_score(top_score, prefs)
    st.metric("Match Confidence", f"{conf:.0%}",
              help="Top song's score as % of the theoretical maximum.")

    st.subheader(f"🎶 Top {k} Songs for You")
    for rank, (song, score, explanation) in enumerate(retrieved, 1):
        with st.container(border=True):
            # Rank badge + title + artist always visible
            col_rank, col_info = st.columns([1, 11])
            col_rank.markdown(
                f"<div style='font-size:1.6rem;font-weight:700;color:#1DB954;"
                f"text-align:center;padding-top:4px'>{rank}</div>",
                unsafe_allow_html=True,
            )
            with col_info:
                st.markdown(f"### {song['title']}")
                st.markdown(
                    f"**{song['artist']}**",
                )

            # Details row
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Genre",        song["genre"].title())
            c2.metric("Mood",         song["mood"].capitalize())
            c3.metric("Energy",       f"{song['energy']:.0%}")
            c4.metric("Match Score",  f"{score:.2f}")
            st.caption(f"💡 {explanation}")


# ── Page ──────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="VibeFinder", page_icon="🎵", layout="centered")
st.title("🎵 VibeFinder — AI Music Recommender")

# Status strip
col_a, col_b = st.columns(2)
col_a.success("🟢 Spotify — live songs")
if _has_llm():
    col_b.success(f"🟢 {_llm_name()} — AI summaries on")
else:
    col_b.warning("⚠️ No LLM key — scored mode only")

st.divider()

# ── Mode selector ─────────────────────────────────────────────────────────────

mode = st.radio(
    "How do you want to find music?",
    ["💬  Tell me your mood", "🎵  Guess from my recent songs", "⚙️  Set manually"],
    horizontal=True,
    label_visibility="collapsed",
)

k = st.slider("Number of recommendations", 3, 20, 5)

# ══════════════════════════════════════════════════════════════════════════════
# Mode 1 — Natural language mood
# ══════════════════════════════════════════════════════════════════════════════

if mode == "💬  Tell me your mood":
    st.subheader("💬 How are you feeling right now?")
    mood_text = st.text_area(
        "Describe your mood — as specific or vague as you like",
        placeholder=(
            "e.g. 'stressed from work and need something calming'\n"
            "      'hyped up before a workout'\n"
            "      'cozy Sunday morning with coffee'"
        ),
        height=120,
    )

    if st.button("Find my songs", type="primary", use_container_width=True):
        if not mood_text.strip():
            st.warning("Type something about how you feel first.")
            st.stop()
        if not _has_llm():
            st.error("Mood parsing requires a GROQ_API_KEY or ANTHROPIC_API_KEY.")
            st.stop()

        with st.spinner("Reading your vibe…"):
            try:
                from mood_parser import from_text
                parsed = from_text(mood_text)
            except Exception as exc:
                st.error(f"Could not parse mood: {exc}")
                logger.error("Mood parse failed: %s", exc)
                st.stop()

        st.success(
            f"**Vibe detected:** {parsed['mood'].capitalize()} · "
            f"{parsed['genre'].title()} · energy {parsed['energy']:.0%}"
        )
        if parsed.get("reasoning"):
            st.caption(f"💡 {parsed['reasoning']}")

        logger.info("Mood parsed: %s", parsed)

        try:
            prefs = validate_prefs(parsed)
        except ValidationError as exc:
            st.error(str(exc)); st.stop()

        songs, src = _load_songs_for_genre(prefs["genre"])
        st.caption(f"📂 Data source: {src}")
        _show_results(prefs, songs, k)


# ══════════════════════════════════════════════════════════════════════════════
# Mode 2 — Guess from recent songs
# ══════════════════════════════════════════════════════════════════════════════

elif mode == "🎵  Guess from my recent songs":
    st.subheader("🎵 What have you been listening to lately?")
    st.caption("Enter songs or artists — one per line. The AI will read your current vibe from them.")
    recent_text = st.text_area(
        "Recent songs / artists",
        placeholder=(
            "Radiohead - Karma Police\n"
            "Portishead - Glory Box\n"
            "Bon Iver - Skinny Love\n"
            "Nick Drake"
        ),
        height=160,
    )

    if st.button("Guess my mood & find songs", type="primary", use_container_width=True):
        lines = [l.strip() for l in recent_text.splitlines() if l.strip()]
        if not lines:
            st.warning("Add at least one song or artist.")
            st.stop()
        if not _has_llm():
            st.error("Mood inference requires a GROQ_API_KEY or ANTHROPIC_API_KEY.")
            st.stop()

        with st.spinner(f"Analyzing {len(lines)} songs to read your mood…"):
            try:
                from mood_parser import from_songs
                parsed = from_songs(lines)
            except Exception as exc:
                st.error(f"Could not infer mood: {exc}")
                logger.error("Song mood parse failed: %s", exc)
                st.stop()

        st.success(
            f"**Detected vibe:** {parsed['mood'].capitalize()} · "
            f"{parsed['genre'].title()} · energy {parsed['energy']:.0%}"
        )
        if parsed.get("reasoning"):
            st.caption(f"💡 {parsed['reasoning']}")

        logger.info("Mood inferred from songs: %s", parsed)

        try:
            prefs = validate_prefs(parsed)
        except ValidationError as exc:
            st.error(str(exc)); st.stop()

        songs, src = _load_songs_for_genre(prefs["genre"])
        st.caption(f"📂 Data source: {src}")
        _show_results(prefs, songs, k)


# ══════════════════════════════════════════════════════════════════════════════
# Mode 3 — Manual (existing sidebar approach)
# ══════════════════════════════════════════════════════════════════════════════

else:
    st.subheader("⚙️ Set your preferences manually")
    with st.form("manual_form"):
        c1, c2 = st.columns(2)
        genre        = c1.selectbox("Genre", sorted(VALID_GENRES))
        mood         = c2.selectbox("Mood",  sorted(VALID_MOODS))
        energy       = st.slider("Energy (0 = calm → 1 = intense)", 0.0, 1.0, 0.7, 0.01)
        likes_acoustic = st.checkbox("I like acoustic tracks")
        submitted    = st.form_submit_button("Get Recommendations", type="primary",
                                             use_container_width=True)

    if submitted:
        raw = {"genre": genre, "mood": mood, "energy": energy,
               "likes_acoustic": likes_acoustic}
        logger.info("Manual prefs submitted: %s", raw)
        try:
            prefs = validate_prefs(raw)
        except ValidationError as exc:
            st.error(str(exc)); st.stop()

        songs, src = _load_songs_for_genre(prefs["genre"])
        st.caption(f"📂 Data source: {src}")
        _show_results(prefs, songs, k)
