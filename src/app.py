"""VibeFinder — AI Music Recommender with Spotify-style UI."""

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

# ── Spotify-style CSS ─────────────────────────────────────────────────────────

SPOTIFY_CSS = """
<style>
  /* ── Base ── */
  html, body, [data-testid="stAppViewContainer"] {
    background-color: #121212 !important;
    color: #FFFFFF !important;
    font-family: 'Circular', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  }
  [data-testid="stHeader"] { background: transparent !important; }
  [data-testid="stSidebar"] { display: none; }
  section[data-testid="stMain"] > div { padding-top: 0 !important; }

  /* ── Hide Streamlit branding ── */
  #MainMenu, footer, header { visibility: hidden; }

  /* ── Scrollbar ── */
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: #121212; }
  ::-webkit-scrollbar-thumb { background: #535353; border-radius: 3px; }

  /* ── Top nav bar ── */
  .vf-navbar {
    background: linear-gradient(180deg,#2a2a2a 0%,#121212 100%);
    padding: 28px 40px 20px;
    margin-bottom: 0;
  }
  .vf-logo {
    font-size: 2rem; font-weight: 800; letter-spacing: -1px;
    color: #1DB954;
  }
  .vf-logo span { color: #FFFFFF; }
  .vf-tagline { color: #B3B3B3; font-size: 0.85rem; margin-top: 2px; }

  /* ── Status pills ── */
  .vf-status-bar {
    display: flex; gap: 10px; padding: 0 40px 16px; flex-wrap: wrap;
  }
  .vf-pill {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 5px 14px; border-radius: 20px; font-size: 0.78rem;
    font-weight: 600; letter-spacing: 0.02em;
  }
  .vf-pill-green { background: #1a3a23; color: #1DB954; border: 1px solid #1DB954; }
  .vf-pill-yellow { background: #3a320a; color: #f8c700; border: 1px solid #f8c700; }
  .vf-pill-dot { font-size: 0.6rem; }

  /* ── Section container ── */
  .vf-section {
    padding: 0 40px 40px;
  }

  /* ── Mode tabs ── */
  .vf-tabs {
    display: flex; gap: 6px; margin-bottom: 28px; flex-wrap: wrap;
  }
  .vf-tab {
    padding: 8px 20px; border-radius: 20px; font-size: 0.85rem; font-weight: 600;
    cursor: pointer; border: none; transition: all 0.2s ease;
    background: #282828; color: #B3B3B3;
  }
  .vf-tab:hover { background: #333; color: #fff; }
  .vf-tab.active { background: #1DB954; color: #000; }

  /* ── Section heading ── */
  .vf-heading {
    font-size: 1.6rem; font-weight: 800; color: #FFFFFF;
    margin-bottom: 4px; letter-spacing: -0.5px;
  }
  .vf-subtext { color: #B3B3B3; font-size: 0.88rem; margin-bottom: 20px; }

  /* ── Inputs ── */
  textarea, input[type="text"] {
    background: #2a2a2a !important;
    color: #FFFFFF !important;
    border: 1px solid #3e3e3e !important;
    border-radius: 6px !important;
    font-size: 0.92rem !important;
    transition: border-color 0.2s !important;
  }
  textarea:focus, input[type="text"]:focus {
    border-color: #1DB954 !important;
    box-shadow: 0 0 0 2px rgba(29,185,84,0.15) !important;
  }
  label, .st-emotion-cache-1gulkj5 { color: #B3B3B3 !important; }

  /* ── Primary button ── */
  [data-testid="baseButton-primary"] button,
  button[kind="primary"] {
    background: #1DB954 !important;
    color: #000 !important;
    border: none !important;
    border-radius: 500px !important;
    font-weight: 700 !important;
    font-size: 0.9rem !important;
    letter-spacing: 0.05em !important;
    padding: 12px 32px !important;
    transition: all 0.2s ease !important;
    text-transform: uppercase !important;
  }
  [data-testid="baseButton-primary"] button:hover { background: #1ed760 !important; transform: scale(1.02); }

  /* ── Secondary button ── */
  button[kind="secondary"] {
    background: transparent !important;
    color: #FFFFFF !important;
    border: 1px solid #535353 !important;
    border-radius: 500px !important;
    font-weight: 600 !important;
  }
  button[kind="secondary"]:hover { border-color: #fff !important; }

  /* ── Slider ── */
  [data-testid="stSlider"] > div > div > div > div {
    background: #1DB954 !important;
  }
  .stSlider [data-baseweb="slider"] [role="slider"] {
    background: #1DB954 !important;
    border-color: #1DB954 !important;
  }

  /* ── Selectbox ── */
  [data-testid="stSelectbox"] > div > div {
    background: #2a2a2a !important;
    border-color: #3e3e3e !important;
    color: #fff !important;
    border-radius: 6px !important;
  }

  /* ── Divider ── */
  hr { border-color: #282828 !important; margin: 20px 0 !important; }

  /* ── Vibe detected banner ── */
  .vf-vibe-banner {
    background: linear-gradient(135deg,#1a3a23,#0d2a18);
    border: 1px solid #1DB954;
    border-radius: 12px;
    padding: 16px 22px;
    margin: 16px 0;
    display: flex; align-items: center; gap: 16px;
  }
  .vf-vibe-icon { font-size: 2rem; }
  .vf-vibe-label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.1em; color: #1DB954; font-weight: 700; }
  .vf-vibe-value { font-size: 1.1rem; font-weight: 700; color: #FFFFFF; }
  .vf-vibe-reasoning { font-size: 0.82rem; color: #B3B3B3; margin-top: 4px; }

  /* ── AI summary box ── */
  .vf-ai-box {
    background: #1a1a2e;
    border-left: 3px solid #1DB954;
    border-radius: 0 10px 10px 0;
    padding: 16px 20px;
    margin: 16px 0;
    font-size: 0.9rem;
    line-height: 1.6;
    color: #e0e0e0;
  }
  .vf-ai-label {
    font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.1em;
    color: #1DB954; font-weight: 700; margin-bottom: 6px;
  }

  /* ── Confidence metric ── */
  .vf-confidence {
    display: inline-flex; align-items: center; gap: 10px;
    background: #181818; border: 1px solid #282828;
    border-radius: 10px; padding: 12px 20px; margin: 12px 0;
  }
  .vf-conf-label { font-size: 0.75rem; color: #B3B3B3; text-transform: uppercase; letter-spacing: 0.08em; }
  .vf-conf-value { font-size: 1.6rem; font-weight: 800; color: #1DB954; }

  /* ── Song card ── */
  .vf-card {
    background: #181818;
    border-radius: 12px;
    padding: 18px 22px;
    margin-bottom: 10px;
    border: 1px solid #282828;
    transition: background 0.2s ease, border-color 0.2s ease;
    display: flex; align-items: center; gap: 18px;
  }
  .vf-card:hover { background: #242424; border-color: #404040; }

  .vf-card-rank {
    font-size: 1.8rem; font-weight: 800;
    color: #1DB954; min-width: 36px; text-align: center;
    line-height: 1;
  }
  .vf-card-rank.top { font-size: 2.2rem; }

  .vf-card-art {
    width: 52px; height: 52px; border-radius: 6px;
    background: linear-gradient(135deg,#1DB954,#191414);
    display: flex; align-items: center; justify-content: center;
    font-size: 1.4rem; flex-shrink: 0;
  }

  .vf-card-info { flex: 1; min-width: 0; }
  .vf-card-title {
    font-size: 1rem; font-weight: 700; color: #FFFFFF;
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  }
  .vf-card-artist { font-size: 0.85rem; color: #B3B3B3; margin-top: 2px; }
  .vf-card-explanation { font-size: 0.78rem; color: #727272; margin-top: 6px; }

  .vf-card-badges { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
  .vf-badge {
    background: #282828; color: #B3B3B3;
    border-radius: 4px; padding: 3px 10px;
    font-size: 0.72rem; font-weight: 600;
    text-transform: uppercase; letter-spacing: 0.06em;
  }
  .vf-badge-green { background: #1a3a23; color: #1DB954; }

  .vf-card-score {
    text-align: right; flex-shrink: 0;
  }
  .vf-score-val { font-size: 1.1rem; font-weight: 700; color: #FFFFFF; }
  .vf-score-label { font-size: 0.68rem; color: #727272; text-transform: uppercase; letter-spacing: 0.06em; }
  .vf-energy-bar-wrap { margin-top: 6px; }
  .vf-energy-bar {
    height: 3px; border-radius: 2px;
    background: linear-gradient(90deg,#1DB954,#1ed760);
    min-width: 4px;
  }
  .vf-energy-bg { height: 3px; border-radius: 2px; background: #333; width: 80px; }

  /* ── Section title ── */
  .vf-section-title {
    font-size: 1.3rem; font-weight: 800; color: #FFFFFF;
    margin: 24px 0 14px; letter-spacing: -0.3px;
  }
  .vf-source-tag {
    display: inline-flex; align-items: center; gap: 5px;
    background: #282828; border-radius: 4px;
    padding: 3px 10px; font-size: 0.72rem; color: #B3B3B3;
    margin-bottom: 14px; font-weight: 600;
  }

  /* ── No results ── */
  .vf-empty {
    text-align: center; padding: 48px 24px; color: #535353;
    font-size: 0.95rem;
  }
  .vf-empty-icon { font-size: 3rem; margin-bottom: 12px; }
</style>
"""

# ── Genre emoji map ────────────────────────────────────────────────────────────

GENRE_EMOJI = {
    "pop": "🎤", "lofi": "☕", "rock": "🎸", "ambient": "🌊",
    "jazz": "🎷", "synthwave": "🌆", "indie pop": "🌿", "hip-hop": "🎤",
    "r&b": "🎵", "classical": "🎻", "metal": "⚡", "electronic": "🎛️",
    "folk": "🪕",
}

MOOD_EMOJI = {
    "happy": "😊", "chill": "😌", "intense": "🔥",
    "relaxed": "🌙", "moody": "🌧️", "focused": "🎯",
}


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
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("GROQ_API_KEY"))


def _llm_name() -> str:
    if os.getenv("ANTHROPIC_API_KEY"):
        return "Claude"
    if os.getenv("GOOGLE_API_KEY"):
        return "Gemini"
    return "Groq"


def _load_songs_for_genre(genre: str) -> tuple[list, str]:
    with st.spinner(f"Fetching live {genre} tracks from Spotify…"):
        live = get_spotify_songs(genre)
    if live:
        return live, f"Spotify · {len(live)} live tracks"
    st.warning("Spotify unavailable — using local catalog.")
    return get_csv_songs(), "local catalog"


def _run_rag(prefs, songs, k):
    from rag_recommender import rag_recommend
    return rag_recommend(prefs, songs, k=k)


def _render_vibe_banner(parsed: dict) -> None:
    genre = parsed.get("genre", "")
    mood  = parsed.get("mood", "")
    icon  = GENRE_EMOJI.get(genre, "🎵")
    tags  = f"{mood.capitalize()}  ·  {genre.title()}  ·  {parsed['energy']:.0%} energy"
    if parsed.get("likes_acoustic"):
        tags += "  ·  Acoustic"
    reasoning = parsed.get("reasoning", "")
    st.markdown(f"""
    <div class="vf-vibe-banner">
      <div class="vf-vibe-icon">{icon}</div>
      <div>
        <div class="vf-vibe-label">Vibe detected</div>
        <div class="vf-vibe-value">{tags}</div>
        {"<div class='vf-vibe-reasoning'>💡 " + reasoning + "</div>" if reasoning else ""}
      </div>
    </div>""", unsafe_allow_html=True)


def _render_card(rank: int, song: dict, score: float, explanation: str) -> None:
    genre   = song.get("genre", "")
    mood    = song.get("mood", "")
    energy  = song.get("energy", 0.5)
    icon    = GENRE_EMOJI.get(genre, "🎵")
    rank_cls = "top" if rank == 1 else ""
    energy_w = max(4, int(energy * 80))

    st.markdown(f"""
    <div class="vf-card">
      <div class="vf-card-rank {rank_cls}">{rank}</div>
      <div class="vf-card-art">{icon}</div>
      <div class="vf-card-info">
        <div class="vf-card-title">{song['title']}</div>
        <div class="vf-card-artist">{song['artist']}</div>
        <div class="vf-card-badges">
          <span class="vf-badge vf-badge-green">{genre.title()}</span>
          <span class="vf-badge">{mood.capitalize()}</span>
          {"<span class='vf-badge'>🎸 Acoustic</span>" if song.get('acoustic') else ""}
        </div>
        <div class="vf-card-explanation">{explanation}</div>
      </div>
      <div class="vf-card-score">
        <div class="vf-score-val">{score:.2f}</div>
        <div class="vf-score-label">Score</div>
        <div class="vf-energy-bar-wrap">
          <div class="vf-energy-bg">
            <div class="vf-energy-bar" style="width:{energy_w}px"></div>
          </div>
        </div>
        <div class="vf-score-label" style="margin-top:3px">{energy:.0%} energy</div>
      </div>
    </div>""", unsafe_allow_html=True)


def _show_results(prefs: dict, songs: list, k: int) -> None:
    retrieved = []

    if _has_llm():
        with st.spinner(f"Generating AI summary via {_llm_name()}…"):
            try:
                result = _run_rag(prefs, songs, k)
                backend = result.get("backend", "AI").capitalize()
                st.markdown(f"""
                <div class="vf-ai-box">
                  <div class="vf-ai-label">✨ AI Summary · {backend}</div>
                  {result["response"]}
                </div>""", unsafe_allow_html=True)
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
        st.markdown("""
        <div class="vf-empty">
          <div class="vf-empty-icon">🔍</div>
          No songs found for these preferences.
        </div>""", unsafe_allow_html=True)
        return

    top_score = retrieved[0][1]
    conf = confidence_score(top_score, prefs)

    st.markdown(f"""
    <div class="vf-confidence">
      <div>
        <div class="vf-conf-label">Match Confidence</div>
        <div class="vf-conf-value">{conf:.0%}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    st.markdown(f'<div class="vf-section-title">🎶 Top {k} picks for you</div>',
                unsafe_allow_html=True)

    for rank, (song, score, explanation) in enumerate(retrieved, 1):
        _render_card(rank, song, score, explanation)


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="VibeFinder", page_icon="🎵", layout="wide")
st.markdown(SPOTIFY_CSS, unsafe_allow_html=True)

# ── Nav bar ───────────────────────────────────────────────────────────────────

st.markdown("""
<div class="vf-navbar">
  <div class="vf-logo">Vibe<span>Finder</span></div>
  <div class="vf-tagline">AI-powered music that matches your mood</div>
</div>""", unsafe_allow_html=True)

# Status pills
llm_pill = (f'<span class="vf-pill vf-pill-green"><span class="vf-pill-dot">●</span>{_llm_name()} · AI summaries on</span>'
            if _has_llm() else
            '<span class="vf-pill vf-pill-yellow"><span class="vf-pill-dot">●</span>No LLM key · scored mode only</span>')
st.markdown(f"""
<div class="vf-status-bar">
  <span class="vf-pill vf-pill-green"><span class="vf-pill-dot">●</span>Spotify · live songs</span>
  {llm_pill}
</div>""", unsafe_allow_html=True)

# ── Mode selector ─────────────────────────────────────────────────────────────

st.markdown('<div class="vf-section">', unsafe_allow_html=True)

mode = st.radio(
    "mode",
    ["💬  Tell me your mood", "🎵  Guess from my recent songs", "⚙️  Set manually"],
    horizontal=True,
    label_visibility="collapsed",
)

k = st.slider("Recommendations", 3, 20, 5, label_visibility="collapsed")
st.caption(f"Showing top **{k}** songs")

st.markdown("<hr>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# Mode 1 — Natural language mood
# ══════════════════════════════════════════════════════════════════════════════

if mode == "💬  Tell me your mood":
    st.markdown('<div class="vf-heading">How are you feeling right now?</div>', unsafe_allow_html=True)
    st.markdown('<div class="vf-subtext">Describe your mood in plain English — no sliders, no dropdowns.</div>', unsafe_allow_html=True)

    mood_text = st.text_area(
        "mood_input",
        placeholder=(
            "e.g.  'stressed from school all week and need something calm'\n"
            "       'hyped up before a workout'\n"
            "       'cozy Sunday morning with coffee'"
        ),
        height=110,
        label_visibility="collapsed",
    )

    if st.button("Find my songs  →", type="primary", use_container_width=False):
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

        _render_vibe_banner(parsed)
        logger.info("Mood parsed: %s", parsed)

        try:
            prefs = validate_prefs(parsed)
        except ValidationError as exc:
            st.error(str(exc)); st.stop()

        songs, src = _load_songs_for_genre(prefs["genre"])
        st.markdown(f'<div class="vf-source-tag">📂 {src}</div>', unsafe_allow_html=True)
        _show_results(prefs, songs, k)


# ══════════════════════════════════════════════════════════════════════════════
# Mode 2 — Guess from recent songs
# ══════════════════════════════════════════════════════════════════════════════

elif mode == "🎵  Guess from my recent songs":
    st.markdown('<div class="vf-heading">What have you been listening to?</div>', unsafe_allow_html=True)
    st.markdown('<div class="vf-subtext">Paste songs or artists — one per line. VibeFinder reads your mood from them.</div>', unsafe_allow_html=True)

    recent_text = st.text_area(
        "recent_input",
        placeholder=(
            "Radiohead - Karma Police\n"
            "Portishead - Glory Box\n"
            "Bon Iver - Skinny Love\n"
            "The National - Bloodbuzz Ohio"
        ),
        height=150,
        label_visibility="collapsed",
    )

    if st.button("Guess my mood & find songs  →", type="primary", use_container_width=False):
        lines = [l.strip() for l in recent_text.splitlines() if l.strip()]
        if not lines:
            st.warning("Add at least one song or artist.")
            st.stop()
        if not _has_llm():
            st.error("Mood inference requires a GROQ_API_KEY or ANTHROPIC_API_KEY.")
            st.stop()

        with st.spinner(f"Analyzing {len(lines)} tracks to read your mood…"):
            try:
                from mood_parser import from_songs
                parsed = from_songs(lines)
            except Exception as exc:
                st.error(f"Could not infer mood: {exc}")
                logger.error("Song mood parse failed: %s", exc)
                st.stop()

        _render_vibe_banner(parsed)
        logger.info("Mood inferred from songs: %s", parsed)

        try:
            prefs = validate_prefs(parsed)
        except ValidationError as exc:
            st.error(str(exc)); st.stop()

        songs, src = _load_songs_for_genre(prefs["genre"])
        st.markdown(f'<div class="vf-source-tag">📂 {src}</div>', unsafe_allow_html=True)
        _show_results(prefs, songs, k)


# ══════════════════════════════════════════════════════════════════════════════
# Mode 3 — Manual
# ══════════════════════════════════════════════════════════════════════════════

else:
    st.markdown('<div class="vf-heading">Set your preferences</div>', unsafe_allow_html=True)
    st.markdown('<div class="vf-subtext">Fine-tune every parameter yourself.</div>', unsafe_allow_html=True)

    with st.form("manual_form"):
        c1, c2 = st.columns(2)
        genre          = c1.selectbox("Genre", sorted(VALID_GENRES))
        mood           = c2.selectbox("Mood",  sorted(VALID_MOODS))
        energy         = st.slider("Energy  (0 = calm → 1 = intense)", 0.0, 1.0, 0.7, 0.01)
        likes_acoustic = st.checkbox("Acoustic tracks preferred")
        submitted      = st.form_submit_button("Get Recommendations  →", type="primary",
                                               use_container_width=False)

    if submitted:
        raw = {"genre": genre, "mood": mood, "energy": energy, "likes_acoustic": likes_acoustic}
        logger.info("Manual prefs submitted: %s", raw)
        try:
            prefs = validate_prefs(raw)
        except ValidationError as exc:
            st.error(str(exc)); st.stop()

        songs, src = _load_songs_for_genre(prefs["genre"])
        st.markdown(f'<div class="vf-source-tag">📂 {src}</div>', unsafe_allow_html=True)
        _show_results(prefs, songs, k)

st.markdown('</div>', unsafe_allow_html=True)
