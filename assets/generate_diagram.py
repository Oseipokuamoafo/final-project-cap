"""
Generates assets/system_diagram.png — run from the project root:
    python3 assets/generate_diagram.py
"""

import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = os.path.join(os.path.dirname(__file__), "system_diagram.png")

# ── colour palette ────────────────────────────────────────────────────────────
C_INPUT   = "#4A90D9"   # blue   – human / input
C_GUARD   = "#E8A838"   # amber  – guardrails
C_CORE    = "#5BAD6F"   # green  – retriever / augmenter
C_LLM     = "#9B59B6"   # purple – LLM
C_OUTPUT  = "#2ECC71"   # teal   – output
C_DATA    = "#95A5A6"   # grey   – data store
C_TEST    = "#E74C3C"   # red    – test suite
C_LOG     = "#7F8C8D"   # dark grey – logger
C_ARROW   = "#2C3E50"
BG        = "#F8F9FA"

fig, ax = plt.subplots(figsize=(13, 9))
ax.set_xlim(0, 13)
ax.set_ylim(0, 9)
ax.axis("off")
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)


def box(ax, x, y, w, h, label, sublabel=None, color="#4A90D9", fontsize=9.5):
    rect = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.08",
        facecolor=color, edgecolor="white", linewidth=1.5, zorder=3,
    )
    ax.add_patch(rect)
    cy = y + h / 2 + (0.12 if sublabel else 0)
    ax.text(x + w / 2, cy, label, ha="center", va="center",
            color="white", fontsize=fontsize, fontweight="bold", zorder=4)
    if sublabel:
        ax.text(x + w / 2, y + h / 2 - 0.22, sublabel, ha="center", va="center",
                color="white", fontsize=7.5, alpha=0.9, zorder=4)


def arrow(ax, x1, y1, x2, y2, label="", color=C_ARROW):
    ax.annotate(
        "", xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(arrowstyle="-|>", color=color, lw=1.6),
        zorder=2,
    )
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(mx + 0.08, my, label, fontsize=7.5, color=color,
                ha="left", va="center", zorder=5)


def hbar(ax, x, y, w, h, label, color="#7F8C8D"):
    rect = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.06",
        facecolor=color, edgecolor="white", linewidth=1.2, zorder=3, alpha=0.88,
    )
    ax.add_patch(rect)
    ax.text(x + w / 2, y + h / 2, label, ha="center", va="center",
            color="white", fontsize=8.5, fontweight="bold", zorder=4)


# ── title ─────────────────────────────────────────────────────────────────────
ax.text(6.5, 8.6, "AI Music Recommender — System Architecture",
        ha="center", va="center", fontsize=13, fontweight="bold", color="#2C3E50")

# ── Row 1: input pipeline ─────────────────────────────────────────────────────
# Human Input
box(ax, 0.3,  6.5, 2.0, 0.85, "Human Input",    "genre · mood · energy", C_INPUT)
# Guardrails
box(ax, 3.0,  6.5, 2.0, 0.85, "Guardrails",     "validate & clamp",      C_GUARD)
# Retriever
box(ax, 5.7,  6.5, 2.0, 0.85, "Retriever",      "score_song × catalog",  C_CORE)
# Data store
box(ax, 8.7,  6.5, 2.2, 0.85, "songs.csv",      "18-song catalog",       C_DATA)

arrow(ax, 2.3,  6.93, 3.0,  6.93)           # Input → Guardrails
arrow(ax, 5.0,  6.93, 5.7,  6.93)           # Guardrails → Retriever
arrow(ax, 8.7,  6.93, 7.7,  6.93, "loads")  # songs.csv → Retriever (reverse)

# ── Row 2: dual paths out of retriever ───────────────────────────────────────
# Augmenter (RAG path)
box(ax, 3.8,  4.85, 2.2, 0.85, "Augmenter",     "format context",        C_CORE)
# Scored results (no-key path)
box(ax, 7.5,  4.85, 2.5, 0.85, "Scored Results","no API key",            C_OUTPUT)

# Retriever → Augmenter
arrow(ax, 6.2,  6.5,  4.9,  5.7,  "top-k songs")
# Retriever → Scored Results
arrow(ax, 7.3,  6.5,  8.35, 5.7,  "top-k songs")

# RAG path label
ax.text(3.5, 5.9, "RAG path\n(API key present)",
        fontsize=7.5, color=C_LLM, ha="center", style="italic")
ax.text(9.3, 5.9, "fallback\n(no key)",
        fontsize=7.5, color=C_OUTPUT, ha="center", style="italic")

# ── Row 3: LLM ───────────────────────────────────────────────────────────────
box(ax, 3.8,  3.2, 2.2, 0.85, "Claude Haiku",   "claude-haiku-4-5",      C_LLM)
arrow(ax, 4.9,  4.85, 4.9,  4.05)   # Augmenter → Claude

# ── Row 4: output ─────────────────────────────────────────────────────────────
box(ax, 4.0,  1.7, 5.0, 0.85, "Output to User",
    "AI summary  +  ranked song list", C_OUTPUT, fontsize=10)

arrow(ax, 4.9,  3.2,  5.5,  2.55)   # Claude → Output
arrow(ax, 8.35, 4.85, 7.5,  2.55)   # Scored → Output

# ── Logger (horizontal bar) ──────────────────────────────────────────────────
hbar(ax, 0.3, 0.85, 12.4, 0.55,
     "Logger  —  all steps recorded to console + logs/app.log  (logger_setup.py)",
     C_LOG)

# ── Test suite (horizontal bar) ──────────────────────────────────────────────
hbar(ax, 0.3, 0.18, 12.4, 0.55,
     "Test Suite (pytest)  —  test_recommender  |  test_guardrails  |  test_rag (mocked Anthropic client)",
     C_TEST)

# ── Legend ────────────────────────────────────────────────────────────────────
legend_items = [
    mpatches.Patch(color=C_INPUT,  label="Human / Input"),
    mpatches.Patch(color=C_GUARD,  label="Guardrails"),
    mpatches.Patch(color=C_CORE,   label="Retriever / Augmenter"),
    mpatches.Patch(color=C_LLM,    label="LLM (Claude Haiku)"),
    mpatches.Patch(color=C_OUTPUT, label="Output"),
    mpatches.Patch(color=C_DATA,   label="Data Store"),
    mpatches.Patch(color=C_TEST,   label="Test Suite"),
    mpatches.Patch(color=C_LOG,    label="Logger"),
]
ax.legend(handles=legend_items, loc="upper left", fontsize=7.5,
          framealpha=0.85, bbox_to_anchor=(0.01, 0.97),
          ncol=2, handlelength=1.2, handleheight=0.9)

plt.tight_layout(pad=0.3)
plt.savefig(OUT, dpi=160, bbox_inches="tight", facecolor=BG)
print(f"Saved → {OUT}")
