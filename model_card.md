# Model Card: Music Recommender Simulation

## 1. Model Name

**VibeFinder 1.0**

---

## 2. Intended Use

VibeFinder 1.0 is a content-based music recommender built for classroom exploration. It is designed to suggest songs from a small catalog that best match a user's stated taste preferences — specifically their favorite genre, preferred mood, target energy level, and whether they enjoy acoustic music.

The system assumes the user knows their own preferences and can describe them explicitly (e.g., "I like chill lofi at low energy"). It is not designed for real users on a streaming platform — it has no listening history, no implicit feedback, and no learning over time. Its purpose is to demonstrate how scoring and ranking logic work in a simplified, fully explainable recommender.

**Intended use:** Classroom simulation, algorithm education, CS coursework.
**Not intended for:** Production music streaming, real-user personalization, or commercial deployment.

---

## 3. How the Model Works

Imagine you hand the system a short description of your music taste: "I love chill lofi, low energy, and acoustic sounds." The system then goes through every song in its catalog and gives each one a score — like a judge at a competition — based on how well it matches your description.

Here is how the scoring works for each song:

- **Genre match** is worth the most (2 points). If the song's genre exactly matches your favorite, it gets a big boost. Genre is treated as the strongest signal of musical taste.
- **Mood match** is worth the second most (1.5 points). A song that matches your emotional vibe (happy, chill, intense, etc.) gets a solid bonus.
- **Energy proximity** contributes up to 1 point. Rather than rewarding songs for being "high" or "low" energy, this rule rewards songs for being *close* to your target. A song 0.02 away from your preference scores nearly 1.0; a song 0.5 away scores only 0.5. This means the system rewards closeness, not just direction.
- **Acoustic bonus** adds up to 0.5 points, but only if you said you like acoustic music. It scales with how acoustic the song actually is — so a fully acoustic track scores more than a slightly acoustic one.

After every song is scored, the system sorts them from highest to lowest and returns the top 5. The score is not hidden — every point is explained in plain language so you know exactly why a song was recommended.

---

## 4. Data

The catalog contains **18 songs** stored in `data/songs.csv`. Each song has the following attributes: `id`, `title`, `artist`, `genre`, `mood`, `energy` (0–1), `tempo_bpm`, `valence` (0–1), `danceability` (0–1), and `acousticness` (0–1).

**Genres represented:** pop, lofi, rock, ambient, jazz, synthwave, indie pop, folk, hip-hop, r&b, classical, electronic, metal
**Moods represented:** happy, chill, intense, relaxed, focused, moody

The dataset started with 10 songs and was expanded to 18 to add genre and mood diversity. The expansion specifically added underrepresented categories: folk, hip-hop, r&b, classical, electronic, and metal.

**Missing from the dataset:**
- No lyrics or lyrical sentiment data
- No spectral/timbral features (e.g., brightness, roughness)
- No user behavior data (plays, skips, saves)
- 18 songs is far too small for a realistic simulation — real platforms operate on catalogs of tens of millions of tracks

---

## 5. Strengths

The system works best for users whose preferences align clearly with a single genre and mood combination that is well-represented in the catalog. For example:

- The **Chill Lofi Listener** profile produces very intuitive results. Library Rain and Midnight Coding are correctly ranked #1 and #2, with the acoustic bonus cleanly separating them from other lofi tracks.
- The **High-Energy Pop Fan** profile correctly surfaces Sunrise City at #1 with a commanding score (4.47) because it matches on all three primary criteria: genre, mood, and energy.
- The energy proximity rule is effective — it prevents the system from recommending a "pop" song with mismatched energy simply because the genre label matched.
- Every recommendation comes with an explanation. A user can always see exactly why each song ranked where it did, which makes the system transparent and debuggable.

---

## 6. Limitations and Bias

**Genre dominance:** At 2.0 points, a genre match nearly guarantees a top-5 finish regardless of other features. For the Rock profile, Storm Runner (4.49) is so far ahead of #2 (2.49) that the ranking feels predetermined rather than nuanced. Reducing genre weight to 1.0 showed that mood + energy alone can outcompete a genre match — suggesting the current weight may be too aggressive.

**Catalog size bias:** With only 18 songs and some genres appearing only once (folk, classical, metal), users with niche preferences will always see the same song at #1 with no alternatives. A real system would diversify results to avoid this.

**Mood vocabulary mismatch:** Mood is matched as an exact string. "Chill" and "relaxed" are emotionally adjacent, but the system scores them as completely different — a "chill" user gets zero mood credit for "relaxed" songs, even though in practice those songs might feel very similar. A mood adjacency map (as designed in the Algorithm Recipe) would fix this.

**No acoustic penalty:** The acoustic bonus only activates when `likes_acoustic: True`. There is no penalty for highly acoustic songs when the user prefers electronic music. This means Coffee Shop Stories (acousticness 0.89) can sneak into recommendations for a synthwave user purely on energy proximity.

**Static profile:** The user profile never updates. If a user skips the top recommendation, that signal is ignored. Real systems would down-weight that song and adjust future scores accordingly.

---

## 7. Evaluation

Three user profiles were tested:

**Profile 1 — High-Energy Pop Fan** (`genre: pop, mood: happy, energy: 0.85`)
Results matched intuition well. Sunrise City correctly dominated. The most surprising result was Neon Cascade (electronic, moody) appearing at #5 with a score of 0.98 — zero genre or mood match, but energy 0.83 is close to the target 0.85. This exposed that energy proximity alone can still surface songs that feel completely wrong for the user.

**Profile 2 — Chill Lofi Listener** (`genre: lofi, mood: chill, energy: 0.38, likes_acoustic: True`)
This was the most successful profile. Library Rain and Midnight Coding were separated by just 0.09 points — a difference driven entirely by acousticness (0.86 vs 0.71). That micro-gap mirrors how real systems make fine-grained distinctions. Spacewalk Thoughts (ambient, not lofi) reached #4 purely through mood + energy, which felt like a reasonable cross-genre suggestion.

**Profile 3 — Deep Intense Rock Head** (`genre: rock, mood: intense, energy: 0.92`)
Storm Runner dominated at 4.49; the next four songs clustered tightly around 2.45–2.49. This showed that a single-song genre niche creates a cliff in the ranking — the #1 pick is obvious, but the remaining slots feel arbitrary.

**Weight Shift Experiment:** Halving genre from 2.0 to 1.0 caused Gym Hero (pop, intense) to overtake Storm Runner for the Rock profile — mood + energy beat the single-point genre bonus. This confirmed that genre is the decisive factor in the current weights, not a tiebreaker.

---

## 8. Future Work

1. **Gaussian energy scoring** — Replace the linear energy proximity formula (`1 - |Δ|`) with a Gaussian function (`e^(−Δ²/2σ²)`). This would reward very close matches much more aggressively and reduce the influence of songs that are "less wrong" rather than "genuinely right."

2. **Mood adjacency map** — Instead of binary exact/no-match for mood, define a graph of adjacent moods (chill ↔ relaxed ↔ focused, intense ↔ moody). This would allow cross-mood recommendations that still feel emotionally coherent.

3. **Valence and danceability integration** — The dataset includes valence and danceability but the current scoring ignores them. Adding these as weighted continuous features (similar to energy) would make the scoring richer and reduce over-reliance on genre.

4. **Diversity injection** — The top-k results could be filtered to ensure no two songs share the same genre, preventing the niche-genre cliff effect seen in the Rock profile.

---

## 9. Personal Reflection

Building VibeFinder showed me that a recommendation is not magic — it is just a weighted comparison repeated across a catalog. What surprised me most was how much the *weight design* matters. Changing genre from 2.0 to 1.0 completely changed which songs appeared in the top 5 for some profiles. That means the "algorithm" is really just the assumptions the designer baked in — which makes it a design problem as much as a math problem.

The transparent explanation system (printing "genre match: pop (+2.0)") was also more valuable than I expected. On real platforms like Spotify, you never see why a song was recommended — it just appears. Having to write the reasons made every weight decision feel more accountable.

The biggest gap between this simulation and a real system is the absence of implicit feedback. When a user skips a song, that signal is more valuable than any feature comparison. VibeFinder is essentially frozen — it makes the same recommendation forever regardless of what the user does with it. Real systems are dynamic; this one is static. That gap is where most of the real engineering in recommender systems actually lives.
