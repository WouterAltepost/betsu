"""
llm_context.py — the LLM news/context nudge (the fourth ensemble layer).

This is an ADJUSTMENT, not a base model. It asks Claude to research a single
fixture with the Anthropic server-side **web search** tool and return a small,
bounded nudge to the blended 1X2 probabilities for real-world context the stats
can't see: confirmed key-player injuries/suspensions, dead-rubber situations,
extreme heat / kickoff-time / venue factors, and unusual rest or travel.

Non-negotiables (see docs/llm_context_briefing.md):
  - Ground every acted-on factor in a recent, cited source (web search). A nudge
    built on stale training-data "injuries" is worse than no nudge.
  - Trust the model's *findings*, never its *magnitudes*: each nudge component is
    clamped in code to [-MAX_LLM_NUDGE, +MAX_LLM_NUDGE] and scaled by confidence.
  - Fail safe: any exception, timeout, malformed JSON, or empty/unsourced result
    yields an all-zero nudge. This layer must never break or block a run.

Public:
    get_adjustment(home, away, commence_time) -> {
        "nudge": {"1": float, "X": float, "2": float},  # additive, clamped
        "factors": [{type, detail, source, favors}, ...],
        "summary": str,
        "confidence": "low|medium|high",
    }

CLI:
    python tools/llm_context.py "Brazil" "Spain" 2026-06-20T18:00:00Z
"""

import json
import os
import re
import sys

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (LLM_CACHE_HOURS, LLM_MAX_WEB_SEARCHES, LLM_MODEL,
                    LLM_TIMEOUT_SECONDS, LLM_WEB_SEARCH_TOOL, MAX_LLM_NUDGE)

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

OUTCOMES = ("1", "X", "2")
ZERO_NUDGE = {o: 0.0 for o in OUTCOMES}
# Lower-confidence findings move the number less; high confidence isn't trusted
# beyond MAX_LLM_NUDGE either (clamp still applies after scaling).
CONFIDENCE_SCALE = {"low": 0.4, "medium": 0.7, "high": 1.0}


def _zero_result(summary="No sourced context; zero nudge.", confidence="low"):
    return {"nudge": dict(ZERO_NUDGE), "factors": [],
            "summary": summary, "confidence": confidence}


# --- Prompt -----------------------------------------------------------------

def _build_prompt(home, away, commence_time):
    when = commence_time or "the upcoming fixture date"
    return f"""You are a football match-context researcher. Use the web search tool to find \
CURRENT, SOURCED information about this specific fixture, then return a small \
probability nudge. This is an adjustment to a statistical model — be conservative.

Fixture: {home} (home/first-listed) vs {away} (away/second-listed)
Kickoff (UTC): {when}

Search the web and consider ONLY these factor types, and ONLY when confirmed by a \
credible source published within roughly the last 7 days before kickoff:
  - confirmed key-player injuries or suspensions (a genuine starter/star, not a squad player)
  - dead-rubber / qualification-already-decided situations (a team with nothing to play for)
  - extreme heat, unusual kickoff time, or a notable venue/altitude factor
  - unusual rest or travel disadvantage versus the opponent

Rules:
  - Every factor you ACT ON must have a real source URL you found via web search. \
No source → do not let it move the number.
  - If you find nothing credible and recent, return an all-zero nudge. A zero nudge \
is the correct, expected answer for a quiet fixture. Do not invent factors.
  - "favors" is which side the factor helps: "home", "away", "draw", or "none".
  - The nudge is additive to probabilities that sum to 1, with keys "1" (home win), \
"X" (draw), "2" (away win). Keep each component small (roughly within ±0.08) and \
have them roughly offset (sum near zero). The system clamps your magnitudes anyway.

Respond with ONLY a single JSON object, no prose before or after:
{{
  "factors": [
    {{"type": "injury|suspension|dead_rubber|heat|venue|rest_travel",
      "detail": "<one line>", "source": "https://...",
      "favors": "home|away|draw|none"}}
  ],
  "nudge": {{"1": 0.0, "X": 0.0, "2": 0.0}},
  "confidence": "low|medium|high",
  "summary": "<=120 chars, one-line rationale"
}}"""


# --- LLM call (web-search grounded) -----------------------------------------

def _extract_json(text):
    """Pull the JSON object out of the model's final text. Returns dict or None."""
    if not text:
        return None
    text = text.strip()
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        pass
    # Fall back to the largest {...} span (model may wrap it in prose/fences).
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except (ValueError, TypeError):
        return None


def _final_text(message):
    """Concatenate the text blocks of a (possibly tool-using) response."""
    parts = []
    for block in message.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "\n".join(parts)


def _research(home, away, commence_time):
    """Run the web-search-grounded Claude call. Returns the parsed JSON dict or
    None. Raises on hard API/timeout errors (the caller turns that into zero)."""
    import anthropic

    client = anthropic.Anthropic().with_options(timeout=LLM_TIMEOUT_SECONDS)
    tools = [{"type": LLM_WEB_SEARCH_TOOL, "name": "web_search",
              "max_uses": LLM_MAX_WEB_SEARCHES}]
    messages = [{"role": "user",
                 "content": _build_prompt(home, away, commence_time)}]

    # Server-side tool loop: the search runs on Anthropic's side; we only need to
    # resume on pause_turn (iteration limit) until the model gives its answer.
    message = None
    for _ in range(LLM_MAX_WEB_SEARCHES + 2):
        message = client.messages.create(
            model=LLM_MODEL, max_tokens=2048, tools=tools, messages=messages)
        if message.stop_reason != "pause_turn":
            break
        messages.append({"role": "assistant", "content": message.content})

    return _extract_json(_final_text(message)) if message else None


# --- Normalisation: clamp + scale, never trust the model's magnitudes --------

def _clamp_nudge(raw_nudge, confidence):
    scale = CONFIDENCE_SCALE.get(str(confidence).lower(), 0.4)
    out = {}
    for o in OUTCOMES:
        try:
            v = float((raw_nudge or {}).get(o, 0.0))
        except (TypeError, ValueError):
            v = 0.0
        v *= scale
        out[o] = round(max(-MAX_LLM_NUDGE, min(MAX_LLM_NUDGE, v)), 4)
    return out


def _normalise_result(data):
    """Turn a parsed model dict into a safe, clamped result. Unsourced or empty
    findings collapse to a zero nudge."""
    if not isinstance(data, dict):
        return _zero_result("Malformed model output; zero nudge.")

    raw_factors = data.get("factors") or []
    factors = [f for f in raw_factors
               if isinstance(f, dict) and str(f.get("source", "")).strip().startswith("http")]
    confidence = str(data.get("confidence", "low")).lower()
    if confidence not in CONFIDENCE_SCALE:
        confidence = "low"
    summary = str(data.get("summary") or "").strip()[:200]

    # No acted-on factor carries a source → the number must not move.
    if not factors:
        return _zero_result(summary or "No sourced factors; zero nudge.", confidence)

    nudge = _clamp_nudge(data.get("nudge"), confidence)
    if all(v == 0.0 for v in nudge.values()):
        return _zero_result(summary or "Sourced context, but no net lean.", confidence)

    return {"nudge": nudge, "factors": factors,
            "summary": summary or "Context nudge applied.", "confidence": confidence}


# --- Cache (storage-agnostic behind these two helpers) -----------------------

def _now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


def _cache_load(key):
    """Return a cached result dict if present and fresh (< LLM_CACHE_HOURS), else
    None. Any storage error is swallowed — the cache is an optimisation, not a
    dependency."""
    try:
        from datetime import datetime, timezone
        from tools import tracker
        row = tracker.fetch_context(key)
        if not row:
            return None
        fetched = row.get("fetched_at") or ""
        try:
            ts = datetime.strptime(fetched, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            return None
        if (_now() - ts).total_seconds() > LLM_CACHE_HOURS * 3600:
            return None
        nudge = row.get("nudge") or {}
        nudge = {o: float(nudge.get(o, 0.0) or 0.0) for o in OUTCOMES}
        return {"nudge": nudge, "factors": [],
                "summary": row.get("summary") or "",
                "confidence": row.get("confidence") or "low",
                "source": row.get("source") or "", "cached": True}
    except Exception:
        return None


def _cache_store(key, result):
    """Persist a result to the cache. Best-effort; never raises."""
    try:
        from tools import tracker
        source = ""
        if result.get("factors"):
            source = result["factors"][0].get("source", "")
        tracker.upsert_context(
            key, result["nudge"], result.get("summary", ""), source,
            result.get("confidence", "low"),
            _now().strftime("%Y-%m-%d %H:%M:%S"))
    except Exception:
        pass


# --- Public -----------------------------------------------------------------

def get_adjustment(home, away, commence_time, use_cache=True):
    """Return the bounded context nudge for one fixture. Always returns a valid
    result dict; on any failure it returns an all-zero nudge so a run never
    breaks. `commence_time` should be the kickoff ISO string (used for the
    cache key date and the research prompt)."""
    match_date = (commence_time or "")[:10]
    try:
        from tools import tracker
        key = tracker.context_key(match_date, home, away)
    except Exception:
        key = f"{match_date}|{home}|{away}"

    if use_cache:
        cached = _cache_load(key)
        if cached is not None:
            return cached

    try:
        data = _research(home, away, commence_time)
        result = _normalise_result(data)
    except Exception as e:
        print(f"  [llm_context: skipped — {type(e).__name__}: {e}]")
        return _zero_result("LLM context lookup failed; zero nudge.")

    if use_cache:
        _cache_store(key, result)
    return result


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        print('usage: python tools/llm_context.py "<home>" "<away>" [commence_time_iso]')
        sys.exit(1)
    home, away = args[0], args[1]
    commence = args[2] if len(args) > 2 else ""
    res = get_adjustment(home, away, commence, use_cache="--no-cache" not in sys.argv)
    print(json.dumps(res, indent=2))
