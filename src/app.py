"""Streamlit UI for the Music Recommender with RAG support."""

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


@st.cache_data
def get_songs():
    return load_songs(CSV_PATH)


def _has_api_key() -> bool:
    return bool(os.getenv("GROQ_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))


def _run_rag(prefs, songs, k):
    from rag_recommender import rag_recommend
    return rag_recommend(prefs, songs, k=k)


# ── Layout ────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Music Recommender", page_icon="🎵", layout="centered")
st.title("🎵 AI Music Recommender")
st.caption(
    "Content-based filtering + RAG-powered summaries. "
    "Set `GROQ_API_KEY` (free) or `ANTHROPIC_API_KEY` to enable AI summaries."
)

songs = get_songs()

with st.sidebar:
    st.header("Your Taste Profile")
    genre = st.selectbox("Favorite Genre", sorted(VALID_GENRES))
    mood = st.selectbox("Favorite Mood", sorted(VALID_MOODS))
    energy = st.slider("Target Energy (0 = calm → 1 = intense)", 0.0, 1.0, 0.7, 0.01)
    likes_acoustic = st.checkbox("I like acoustic tracks")
    k = st.slider("Number of recommendations", 3, 10, 5)
    run_btn = st.button("Get Recommendations", type="primary", use_container_width=True)

if run_btn:
    raw_prefs = {
        "genre": genre,
        "mood": mood,
        "energy": energy,
        "likes_acoustic": likes_acoustic,
    }
    logger.info("User submitted prefs: %s", raw_prefs)

    try:
        prefs = validate_prefs(raw_prefs)
    except ValidationError as exc:
        st.error(f"Input error: {exc}")
        logger.error("Validation failed: %s", exc)
        st.stop()

    retrieved = []

    if _has_api_key():
        with st.spinner("Retrieving songs and generating AI summary..."):
            try:
                result = _run_rag(prefs, songs, k)
                st.subheader("AI Recommendation Summary")
                st.info(result["response"])
                retrieved = result["retrieved"]
                logger.info("RAG complete — usage: %s", result["usage"])
            except Exception as exc:
                logger.error("RAG pipeline failed: %s", exc, exc_info=True)
                st.warning("AI generation unavailable — showing scored results only.")
                retrieved = recommend_songs(prefs, songs, k=k)
    else:
        st.caption(
            "ℹ️ No API key found — running in scored-only mode. "
            "Set GROQ_API_KEY (free at console.groq.com) to enable AI summaries."
        )
        retrieved = recommend_songs(prefs, songs, k=k)

    top_score = retrieved[0][1] if retrieved else 0.0
    conf = confidence_score(top_score, prefs)
    st.metric("Match Confidence", f"{conf:.0%}",
              help="Top song's score as a % of the theoretical maximum (genre + mood + energy + acoustic all perfect).")

    st.subheader(f"Top {k} Songs for You")
    for rank, (song, score, explanation) in enumerate(retrieved, 1):
        with st.expander(
            f"{rank}. **{song['title']}** — {song['artist']}  ·  score: {score:.2f}"
        ):
            col1, col2 = st.columns(2)
            col1.metric("Genre", song["genre"])
            col1.metric("Mood", song["mood"])
            col2.metric("Energy", f"{song['energy']:.2f}")
            col2.metric("Acousticness", f"{song['acousticness']:.2f}")
            st.caption(f"Why: {explanation}")
