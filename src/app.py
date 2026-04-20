"""Streamlit UI for the Music Recommender with RAG + live Spotify data."""

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
def get_csv_songs():
    return load_songs(CSV_PATH)


@st.cache_data(ttl=300)
def get_spotify_songs(genre: str) -> list:
    """Fetch live Spotify tracks for *genre*. Cached for 5 minutes per genre."""
    from spotify_client import fetch_songs_by_genre
    return fetch_songs_by_genre(
        genre,
        os.getenv("SPOTIFY_CLIENT_ID", ""),
        os.getenv("SPOTIFY_CLIENT_SECRET", ""),
        limit=10,
    )


def _has_spotify() -> bool:
    return bool(os.getenv("SPOTIFY_CLIENT_ID") and os.getenv("SPOTIFY_CLIENT_SECRET"))


def _has_llm_key() -> bool:
    return bool(os.getenv("GROQ_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))


def _run_rag(prefs, songs, k):
    from rag_recommender import rag_recommend
    return rag_recommend(prefs, songs, k=k)


# ── Layout ────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="VibeFinder", page_icon="🎵", layout="centered")
st.title("🎵 VibeFinder — AI Music Recommender")

with st.sidebar:
    st.header("Your Taste Profile")
    genre = st.selectbox("Favorite Genre", sorted(VALID_GENRES))
    mood = st.selectbox("Favorite Mood", sorted(VALID_MOODS))
    energy = st.slider("Target Energy (0 = calm → 1 = intense)", 0.0, 1.0, 0.7, 0.01)
    likes_acoustic = st.checkbox("I like acoustic tracks")
    k = st.slider("Number of recommendations", 3, 10, 5)
    st.divider()
    if _has_spotify():
        st.success("🟢 Spotify connected — live songs")
    else:
        st.caption("Add SPOTIFY_CLIENT_ID + SPOTIFY_CLIENT_SECRET for live songs.")
    if _has_llm_key():
        backend = "Groq" if os.getenv("GROQ_API_KEY") else "Claude"
        st.success(f"🟢 {backend} connected — AI summaries on")
    else:
        st.caption("Add GROQ_API_KEY for free AI summaries.")
    run_btn = st.button("Get Recommendations", type="primary", use_container_width=True)

if run_btn:
    raw_prefs = {"genre": genre, "mood": mood, "energy": energy, "likes_acoustic": likes_acoustic}
    logger.info("User submitted prefs: %s", raw_prefs)

    try:
        prefs = validate_prefs(raw_prefs)
    except ValidationError as exc:
        st.error(f"Input error: {exc}")
        logger.error("Validation failed: %s", exc)
        st.stop()

    # ── Catalog: live Spotify or local CSV ───────────────────────────────────
    songs = get_csv_songs()
    data_source = "local catalog"

    if _has_spotify():
        with st.spinner(f"Fetching live {genre} tracks from Spotify..."):
            live = get_spotify_songs(genre)
        if live:
            songs = live
            data_source = f"Spotify ({len(live)} live tracks)"
            logger.info("Using live Spotify catalog: %d songs", len(live))
        else:
            st.warning("Spotify fetch failed — falling back to local catalog.")
            logger.warning("Spotify returned no songs for genre=%s", genre)

    st.caption(f"📂 Data source: {data_source}")

    retrieved = []

    # ── LLM summary (RAG) ────────────────────────────────────────────────────
    if _has_llm_key():
        with st.spinner("Scoring songs and generating AI summary..."):
            try:
                result = _run_rag(prefs, songs, k)
                backend_label = result.get("backend", "AI").capitalize()
                st.subheader(f"AI Recommendation Summary  ·  {backend_label}")
                st.info(result["response"])
                retrieved = result["retrieved"]
                logger.info("RAG complete — backend=%s usage=%s", result.get("backend"), result["usage"])
            except Exception as exc:
                logger.error("RAG pipeline failed: %s", exc, exc_info=True)
                st.warning("AI summary unavailable — showing scored results only.")
                retrieved = recommend_songs(prefs, songs, k=k)
    else:
        st.caption("ℹ️ No LLM key — scored-only mode. Set GROQ_API_KEY (free) to enable AI summaries.")
        retrieved = recommend_songs(prefs, songs, k=k)

    if not retrieved:
        st.error("No songs found. Try a different genre or check your Spotify credentials.")
        st.stop()

    # ── Confidence metric ─────────────────────────────────────────────────────
    top_score = retrieved[0][1]
    conf = confidence_score(top_score, prefs)
    st.metric(
        "Match Confidence", f"{conf:.0%}",
        help="Top song's score as a % of the theoretical maximum (all criteria perfectly matched).",
    )

    # ── Results ───────────────────────────────────────────────────────────────
    st.subheader(f"Top {k} Songs for You")
    for rank, (song, score, explanation) in enumerate(retrieved, 1):
        with st.expander(f"{rank}. **{song['title']}** — {song['artist']}  ·  score: {score:.2f}"):
            col1, col2 = st.columns(2)
            col1.metric("Genre", song["genre"])
            col1.metric("Mood", song["mood"])
            col2.metric("Energy", f"{song['energy']:.2f}")
            col2.metric("Acousticness", f"{song['acousticness']:.2f}")
            st.caption(f"Why: {explanation}")
