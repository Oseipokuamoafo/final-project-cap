# Loom Video Script — AI Music Recommender
# ~5–7 minutes | No API key required

---

## BEFORE YOU HIT RECORD

Open ONE terminal window and run:
```
cd /Users/geraldamoafo/Downloads/final-project-cap
```

Have this file open so you can read the lines while recording.
Make your terminal font big (Cmd + on Mac).

---

## HIT RECORD — START TALKING

---

### INTRO (30 seconds)

*Just look at the camera / screen*

SAY:
"Hi, I'm Gerald. This is my Applied AI capstone project —
an AI-powered music recommender that combines a scoring
engine with a RAG pipeline built on Claude. Let me show
you how it works end to end."

---

### SECTION 1 — End-to-End Demo, Profile 1 (1 min)

TYPE:
```
python3 demo.py
```

*Press Enter at the first pause*

SAY:
"The system takes a user's taste profile — genre, mood,
energy level, and whether they like acoustic music —
and scores every song in the catalog against it."

*Press Enter to run Demo 1*

SAY:
"Here's a high-energy pop fan. The top result is Sunrise City
with a score of 4.47. You can see exactly why — genre match
gives plus 2, mood match gives plus 1.5, and the energy
of 0.82 is almost identical to the target of 0.85.
Every recommendation is fully explainable."

*Point at the confidence number on screen*

SAY:
"The confidence score tells us the top song hit 99% of the
theoretical maximum — meaning the catalog had a strong
answer for this user."

---

### SECTION 2 — Profile 2, Acoustic (45 seconds)

*Press Enter for Demo 2*

SAY:
"Second profile — a chill lofi listener who likes acoustic
tracks. Library Rain comes in at 4.90. The interesting thing
here is that it beats the second result by only 0.09 points —
and that entire gap comes from the acoustic bonus.
Library Rain has an acousticness of 0.86 versus 0.71 for
Midnight Coding. That's a micro-decision the scoring engine
makes automatically."

---

### SECTION 3 — Guardrails (1 min)

*Press Enter for Demo 3*

SAY:
"Now let me show the guardrails. These run before any scoring
happens."

*Point at Test A output*

SAY:
"First — if someone passes in an energy of 1.9, which is out
of the valid range, the system clamps it to 1.0 and logs a
warning. It doesn't crash."

*Point at Test B*

SAY:
"Second — an unknown genre like 'country' isn't in the catalog.
The system warns that no genre-match bonus will apply but
keeps running. It still returns the best available match."

*Point at Test C*

SAY:
"Third — if someone passes the string 'loud' as the energy
value, the system raises a clear validation error and stops
before any scoring runs. The error message tells you exactly
what went wrong."

---

### SECTION 4 — RAG Pipeline (1 min)

*Press Enter for Demo 4*

SAY:
"This is the RAG enhancement. RAG stands for
Retrieval-Augmented Generation — the AI retrieves information
first, then generates a response based on what it found."

*Point at the 'without' section*

SAY:
"Without the knowledge base, Claude only sees the song scores.
It can say 'Library Rain scored 4.90' but nothing more."

*Point at the 'with' section*

SAY:
"With the knowledge base enabled, the system also retrieves
genre and mood descriptions from a second document. So Claude
now knows that lofi is defined by vinyl crackle, tape hiss,
and warm compressed sound — and that chill and relaxed are
emotionally adjacent moods. That context produces measurably
richer output. The LLM is writing about the music, not just
restating numbers."

---

### SECTION 5 — Agentic Workflow (1 min)

*Press Enter for Demo 5*

SAY:
"This is the agentic workflow. Instead of a fixed pipeline,
the agent takes a natural language query and figures out
what to do on its own using tool calls."

*Point at Step 1*

SAY:
"Step one — parse preferences. The agent calls a tool
that extracts structured preferences from the free-text query.
It figures out genre equals lofi, mood equals chill,
energy around 0.4."

*Point at Step 2*

SAY:
"Step two — retrieve songs. It calls the scoring engine
with those preferences and gets back the top results
with a confidence of 98%."

*Point at Step 3*

SAY:
"Step three — evaluate coverage. It checks whether the
results are good enough. In this case they are, so it
moves straight to the final response."

SAY:
"If coverage had been poor — say, for a genre not in the
catalog — the agent would have automatically retried
with adjusted parameters. That's what makes it agentic:
it checks its own work."

---

### SECTION 6 — Reliability Report (45 seconds)

*Press Enter for Demo 6*

SAY:
"Finally — the reliability report. This is a script that
runs 35 automated checks across every part of the system
and prints a pass-fail summary."

*Point at the numbers*

SAY:
"16 out of 16 core reliability checks pass — including
correctness for all three profiles, confidence in valid
range, determinism across three runs, and no negative scores.
5 out of 5 RAG enhancement checks. 6 out of 6 agentic
workflow checks. 8 out of 8 style specialization checks.
35 out of 35 total, no API key required."

---

### OUTRO (30 seconds)

SAY:
"The full code is on GitHub at
github.com/Oseipokuamoafo/final-project-cap.

What I built here is a system where every recommendation
is traceable, every failure is handled, and every claim
about the AI's behavior is backed by an automated check.
That's what I think applied AI engineering looks like.
Thanks for watching."

*Stop recording*

---

## AFTER RECORDING

1. Upload to Loom at loom.com
2. Copy the share link
3. Open README.md line 5 and replace:
   [Add Loom link here after recording]
   with your actual Loom URL
4. Commit and push to GitHub
