# Loom Video Script — VibeFinder AI Music Recommender
# ~5–7 minutes | Record your screen at localhost:8501

---

## BEFORE YOU HIT RECORD

1. Run the Streamlit app:
   ```
   cd /Users/geraldamoafo/Downloads/final-project-cap
   streamlit run src/app.py
   ```
2. Open http://localhost:8501 in your browser — make it fullscreen
3. Open a second terminal tab for the CLI demo at the end
4. Make your browser font large (Cmd + on Mac)

---

## HIT RECORD — START TALKING

---

### INTRO  (30 seconds)
*Face camera or just speak over your screen*

SAY:
"Hey, I'm Gerald. This is VibeFinder — my Applied AI capstone project.
It's a music recommender that doesn't just let you pick a genre and
energy level. It actually listens to how you describe your mood, or
looks at what you've been listening to, and figures out what you need
to hear next. It pulls real songs from Spotify, scores them, and then
uses a free AI model to summarize why those songs fit you.
Let me show you how it works."

---

### SECTION 1 — Tell Me Your Mood  (90 seconds)
*App is open on Mode 1: "Tell me your mood"*

SAY:
"The first mode is the most natural one. You just tell the app
how you're feeling — in plain English, however you'd describe it
to a friend."

*Click the text area and type slowly so viewers can read:*
TYPE: "I've been stressed from school all week and I just want
something calm to help me decompress tonight"

SAY:
"I'm not picking a genre. I'm not setting an energy slider.
I'm just describing my state of mind."

*Click "Find my songs"*

SAY:
"The app sends that to Groq — which is a completely free AI model —
and it extracts structured music preferences from the description.
Watch what it comes back with."

*Point at the detected vibe banner*

SAY:
"Relaxed. Lofi. 20% energy. Acoustic. That's exactly right.
And underneath it explains its reasoning — it inferred I need
calming, low-energy music with acoustic texture.
Then it goes straight to Spotify and pulls real songs."

*Point at the song cards*

SAY:
"These are real Spotify tracks. Real artists. Real song titles.
Number one right here — look at the title and artist —
it matched lofi, relaxed mood, low energy. And the AI summary
above explains specifically why these songs fit the profile,
not just what the scores were."

---

### SECTION 2 — Guess from My Recent Songs  (90 seconds)
*Click Mode 2: "Guess from my recent songs"*

SAY:
"The second mode is the one I'm most proud of.
Instead of telling the app your mood, you tell it what
you've been listening to — and it figures out your mood
from that."

*Click the text area and type:*
```
Radiohead - Karma Police
Portishead - Glory Box
Bon Iver - Skinny Love
The National - Bloodbuzz Ohio
```

SAY:
"These are four songs I might have had on repeat.
I haven't said anything about how I feel.
The AI has to read the vibe from the music itself."

*Click "Guess my mood & find songs"*

SAY:
"It's analyzing the typical genre, energy level, and emotional
character of those artists. Radiohead and Portishead are
dark, cinematic, low-energy. Bon Iver is introspective acoustic.
The National is melancholy indie rock."

*Point at the detected vibe*

SAY:
"Moody. Indie pop. 40% energy. Acoustic preferred.
That's a genuinely accurate read of what those four artists
have in common emotionally. Now look at the recommendations —
these are real Spotify songs that match that inferred state."

---

### SECTION 3 — Manual Mode  (45 seconds)
*Click Mode 3: "Set manually"*

SAY:
"There's also a manual mode for when you know exactly what
you want. You pick a genre, mood, energy level — same as
a traditional music app. But even here, Groq generates an
AI summary explaining why the top picks fit your profile,
and the songs are still live from Spotify."

*Quickly set rock / intense / energy 0.9 and submit*

SAY:
"Rock, intense, high energy. Real songs from Spotify scored
by the engine and summarized by the AI."

---

### SECTION 4 — CLI and Reliability Report  (60 seconds)
*Switch to terminal*

SAY:
"Under the hood, the same engine powers a command-line interface.
Let me run the reliability report — this is a script that checks
every part of the system automatically."

TYPE:
```
python3 reliability_report.py
```

*Wait for output*

SAY:
"35 checks. Core reliability — 16 out of 16. RAG enhancement —
5 out of 5. Agentic workflow — 6 out of 6. Style specialization —
8 out of 8. 35 out of 35 total. No API key required to run these —
the LLM calls are mocked in the test suite.

Average confidence score across all profiles is 99%.
Every recommendation is traceable to a score,
every score is explainable, every behavior is tested."

---

### OUTRO  (30 seconds)

SAY:
"Everything I just showed you — the mood parsing, the Spotify
integration, the RAG pipeline, the guardrails, the agentic
workflow, the test suite — is all on GitHub at
github.com/Oseipokuamoafo/final-project-cap.

What this project taught me is that the AI part of an AI system
is maybe 20% of the work. The other 80% is building reliable
retrieval, honest confidence scores, real data sources,
and tests that prove it works. That's the engineering that
makes the AI actually useful. Thanks for watching."

*Stop recording*

---

## AFTER RECORDING

1. Upload to Loom at loom.com
2. Copy the share link (e.g. https://www.loom.com/share/abc123...)
3. Open README.md and replace the placeholder on line 5:
      [Add Loom link here after recording]
   with your actual Loom URL
4. Run:
      git add README.md
      git commit -m "Add Loom video walkthrough link"
      git push origin main
