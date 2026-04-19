"""
Agentic recommendation workflow using Claude tool_use.

The agent takes a free-text query (e.g., "I need chill study music, nothing too loud")
and works through a multi-step reasoning chain with observable tool calls:

  Step 1  parse_preferences   — extract structured prefs from the natural language query
  Step 2  retrieve_songs      — search the catalog and return scored results
  Step 3  evaluate_coverage   — assess result quality; flag if refinement is needed
  Step 4  retrieve_songs      — (optional) retry with adjusted params if coverage was poor
  Final   text response       — friendly, personalized recommendation summary

Every tool call and its result is logged and returned in the `steps` list so
intermediate reasoning is fully observable — not just the final answer.
"""

import json
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import anthropic

from guardrails import ValidationError, validate_prefs
from recommender import confidence_score, recommend_songs

logger = logging.getLogger(__name__)

# ── Tool schemas ──────────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "parse_preferences",
        "description": (
            "Extract structured music preferences from a natural-language query. "
            "Returns genre, mood, energy (0.0–1.0), and whether the user likes acoustic music. "
            "Use the closest matching values from the known vocabulary."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "genre": {
                    "type": "string",
                    "description": "Closest genre: pop, lofi, rock, ambient, jazz, synthwave, "
                                   "indie pop, hip-hop, r&b, classical, metal, electronic, folk",
                },
                "mood": {
                    "type": "string",
                    "description": "Closest mood: happy, chill, intense, relaxed, focused, moody",
                },
                "energy": {
                    "type": "number",
                    "description": "Energy level 0.0 (very calm) to 1.0 (very intense)",
                },
                "likes_acoustic": {
                    "type": "boolean",
                    "description": "True if the user prefers acoustic or unplugged sounds",
                },
            },
            "required": ["genre", "mood", "energy", "likes_acoustic"],
        },
    },
    {
        "name": "retrieve_songs",
        "description": "Search the music catalog and return the top-k songs scored against the given preferences.",
        "input_schema": {
            "type": "object",
            "properties": {
                "genre":          {"type": "string"},
                "mood":           {"type": "string"},
                "energy":         {"type": "number"},
                "likes_acoustic": {"type": "boolean"},
                "k":              {"type": "integer", "description": "Number of results (default 5)"},
            },
            "required": ["genre", "mood", "energy"],
        },
    },
    {
        "name": "evaluate_coverage",
        "description": (
            "Evaluate whether the retrieved songs adequately serve the user's request. "
            "Returns quality rating and whether a refined search is recommended."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "top_confidence": {
                    "type": "number",
                    "description": "Confidence score of the top result (0.0–1.0)",
                },
                "genre_matches": {
                    "type": "integer",
                    "description": "How many top-k results match the requested genre",
                },
                "mood_matches": {
                    "type": "integer",
                    "description": "How many top-k results match the requested mood",
                },
            },
            "required": ["top_confidence", "genre_matches", "mood_matches"],
        },
    },
]

_AGENT_SYSTEM = """\
You are a music recommendation agent. Work through these steps in order:
1. Call parse_preferences to extract structured taste preferences from the user's query.
2. Call retrieve_songs with those preferences.
3. Call evaluate_coverage to assess whether the results are good enough.
4. If coverage is poor (should_refine=true), call retrieve_songs again with adjusted
   parameters (e.g., widen energy range slightly or try an adjacent mood).
5. Write a concise, friendly recommendation summary (3–4 sentences).
Always complete all steps before writing your final response."""


# ── Tool execution ────────────────────────────────────────────────────────────

def _execute_tool(name: str, tool_input: dict, songs: list) -> str:
    logger.info("  Tool call: %s | input: %s", name, tool_input)

    if name == "parse_preferences":
        try:
            validated = validate_prefs(dict(tool_input))
            result = {"status": "ok", "preferences": validated}
        except ValidationError as exc:
            result = {"status": "error", "message": str(exc)}

    elif name == "retrieve_songs":
        inp = dict(tool_input)
        k = int(inp.pop("k", 5))
        try:
            prefs = validate_prefs(inp)
            retrieved = recommend_songs(prefs, songs, k=k)
            conf = confidence_score(retrieved[0][1], prefs) if retrieved else 0.0
            result = {
                "results": [
                    {
                        "title": s["title"],
                        "artist": s["artist"],
                        "genre": s["genre"],
                        "mood": s["mood"],
                        "energy": s["energy"],
                        "score": round(sc, 2),
                        "explanation": exp,
                    }
                    for s, sc, exp in retrieved
                ],
                "confidence": round(conf, 3),
                "genre_matches": sum(1 for s, _, _ in retrieved if s["genre"] == prefs.get("genre")),
                "mood_matches":  sum(1 for s, _, _ in retrieved if s["mood"]  == prefs.get("mood")),
            }
        except Exception as exc:
            result = {"status": "error", "message": str(exc)}

    elif name == "evaluate_coverage":
        conf = float(tool_input.get("top_confidence", 0.0))
        gm   = int(tool_input.get("genre_matches", 0))
        mm   = int(tool_input.get("mood_matches",  0))

        if conf >= 0.80 and gm + mm >= 2:
            quality, refine = "good",       False
            reason = "Strong match across multiple criteria — results should feel relevant."
        elif conf >= 0.50 or gm + mm >= 1:
            quality, refine = "acceptable", False
            reason = "Partial match — some cross-genre results may appear but top pick is solid."
        else:
            quality, refine = "poor",       True
            reason = "Weak match — catalog may underrepresent this taste. Consider broadening."

        result = {"quality": quality, "should_refine": refine, "reason": reason}

    else:
        result = {"status": "error", "message": f"Unknown tool: {name}"}

    logger.info("  Tool result: %s", result)
    return json.dumps(result)


# ── Agent loop ────────────────────────────────────────────────────────────────

def run_agent(
    query: str,
    songs: list,
    client: anthropic.Anthropic | None = None,
    max_turns: int = 8,
) -> dict:
    """
    Run the agentic recommendation loop for a natural-language query.

    Returns:
        steps        — list of observable intermediate steps
                       Each step: {step, tool, input, output}
        response     — final natural-language recommendation text
        preferences  — structured preferences Claude extracted (for inspection)
        tool_count   — total number of tool calls made
    """
    if client is None:
        client = anthropic.Anthropic()

    messages = [{"role": "user", "content": query}]
    steps: list[dict] = []
    preferences: dict = {}
    step_num = 0

    logger.info("Agent starting — query: %r", query)

    for turn in range(max_turns):
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=_AGENT_SYSTEM,
            tools=TOOLS,
            messages=messages,
        )
        logger.info("Agent turn %d — stop_reason=%s", turn + 1, response.stop_reason)

        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            final_text = next(
                (b.text for b in response.content if hasattr(b, "text")), ""
            )
            logger.info("Agent completed in %d tool calls across %d turns", step_num, turn + 1)
            return {
                "steps": steps,
                "response": final_text,
                "preferences": preferences,
                "tool_count": step_num,
            }

        if response.stop_reason != "tool_use":
            break

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue

            step_num += 1
            raw_output = _execute_tool(block.name, dict(block.input), songs)
            output_data = json.loads(raw_output)

            steps.append({
                "step": step_num,
                "tool": block.name,
                "input": dict(block.input),
                "output": output_data,
            })

            if block.name == "parse_preferences" and output_data.get("status") == "ok":
                preferences = output_data.get("preferences", {})

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": raw_output,
            })

        messages.append({"role": "user", "content": tool_results})

    return {
        "steps": steps,
        "response": "Agent did not produce a final response within the step limit.",
        "preferences": preferences,
        "tool_count": step_num,
    }
