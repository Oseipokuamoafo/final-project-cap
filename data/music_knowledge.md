# Music Knowledge Base

This document is retrieved by the RAG pipeline to give the LLM genre and mood context
beyond what is available in the song scores alone.

---

## Genre Profiles

### Pop
Pop music prioritizes accessible hooks, clean production, and high danceability. Energy
tends to be moderate to high (0.6–0.9). Listeners drawn to pop typically want something
immediately engaging rather than challenging. Top production features: bright synths,
punchy drums, layered vocals.

### Lofi Hip-Hop
Lofi (low-fidelity) hip-hop is defined by deliberate imperfection — vinyl crackle, tape
hiss, slightly off-key samples, and a warm, compressed sound. Tempos sit between 60–90
BPM. The genre is closely associated with studying and sustained focus. Energy is
consistently low (0.3–0.5) and acousticness is high. Adjacent genres: ambient, jazz.

### Rock
Rock spans a wide energy range but is defined by guitar-driven arrangements and rhythmic
drive. Intense rock subgenres (metal, hard rock) push energy above 0.85 and tempo above
140 BPM. The genre rewards listeners who want physicality and emotional release.

### Ambient
Ambient music foregrounds texture and atmosphere over melody or rhythm. Tempo is very
slow or absent. Energy is low (0.1–0.4). The genre is ideal for background listening,
meditation, or transitional moments between tasks. Adjacent genres: classical, lofi.

### Jazz
Jazz is built on improvisation, syncopation, and harmonic sophistication. Tempos range
widely (60–180 BPM). Acousticness is typically high. Emotional range covers relaxed
listening and intense concentration. Adjacent genres: r&b, lofi.

### Synthwave
Synthwave evokes 1980s electronic aesthetics — pulsing arpeggios, gated reverb, and
cinematic textures. Energy is moderate to high (0.6–0.85). Mood tends toward moody or
nostalgic rather than happy or intense. Adjacent genre: electronic.

### Electronic
Electronic music covers a broad spectrum but typically features synthesized timbres, high
danceability, and produced (non-acoustic) textures. Energy can span the full range
depending on subgenre. Adjacent genres: synthwave, pop.

### Classical
Classical music is acoustic by definition (acousticness near 1.0) and covers an enormous
emotional range. For this catalog, classical tracks tend toward low energy and a focused
mood — suitable for deep concentration. Adjacent genres: ambient, jazz.

### Hip-Hop
Hip-hop is characterized by rhythmic flow, sample-based production, and high danceability.
Energy tends to be moderate to high (0.7–0.95). Mood can be intense, moody, or relaxed
depending on subgenre. Adjacent genres: r&b, pop.

### R&B
R&B (rhythm and blues) blends soul, funk, and electronic production. It tends toward
mid-range energy (0.4–0.7) and emotionally nuanced moods — moody, relaxed, or expressive.
Acousticness varies. Adjacent genres: hip-hop, jazz.

### Folk
Folk is defined by acoustic instrumentation, storytelling lyricism, and organic production.
Acousticness is very high. Energy is low to moderate (0.2–0.5). Mood tends toward relaxed
or reflective. Adjacent genres: classical, indie pop.

### Metal
Metal is the most extreme rock subgenre — very high energy (0.9–1.0), very fast tempo
(160–200 BPM), and low acousticness. The mood is typically intense. Not suited for
relaxed or focused listening contexts.

### Indie Pop
Indie pop blends pop's accessibility with an independent, often lo-fi aesthetic. Energy is
moderate (0.6–0.8). Mood is often happy or wistful. Acousticness is higher than mainstream
pop. Adjacent genres: pop, folk.

---

## Mood Definitions and Adjacency

| Mood     | Description                                                      | Adjacent moods         |
|----------|------------------------------------------------------------------|------------------------|
| Happy    | Uplifting, positive, energetic emotional quality                 | Relaxed                |
| Chill    | Effortless calm — music that doesn't demand attention            | Relaxed, Focused       |
| Relaxed  | Intentional unwinding — warmer and slightly more acoustic        | Chill, Moody           |
| Intense  | High arousal, driven, emotionally charged                        | Moody                  |
| Focused  | Steady, neutral — supports sustained cognitive work              | Chill, Relaxed         |
| Moody    | Emotionally complex, introspective, atmospheric                  | Relaxed, Intense       |

**Adjacency rule:** if a user's requested mood has no exact match in the catalog, the
system should note that adjacent moods may serve the same emotional function.

---

## Energy Level Guide

| Range     | Label         | Best for                                 |
|-----------|---------------|------------------------------------------|
| 0.0–0.3   | Very calm     | Deep focus, sleep, meditation            |
| 0.3–0.5   | Calm          | Study, quiet work, background listening  |
| 0.5–0.7   | Moderate      | Casual listening, commuting, socializing |
| 0.7–0.85  | High          | Exercise, upbeat social settings         |
| 0.85–1.0  | Very high     | Intense workouts, hype moments           |

---

## Scoring Context

The recommendation engine uses four weighted criteria:
- **Genre match (+2.0):** strongest signal of musical taste
- **Mood match (+1.5):** second-strongest signal
- **Energy proximity (+0.0–1.0):** rewards closeness to target energy
- **Acoustic bonus (+0.0–0.5):** applied only if the user prefers acoustic tracks

A confidence score (top song score / theoretical maximum) above 0.80 indicates a strong
catalog match. Below 0.50 suggests the catalog underrepresents this listener's taste.
