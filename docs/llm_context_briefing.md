# Briefing: build tools/llm_context.py (the news/context nudge layer)

**For:** Claude Code. **Author:** planning pass in Cowork.
**Goal:** Add the fourth ensemble layer described in `CLAUDE.md`: a Claude-driven
adjustment that nudges the blended 1X2 probabilities for real-world context the
stats can't see (key injuries/suspensions, dead rubbers, extreme heat, rest and
travel). It is an ADJUSTMENT, not a base model.

Read first: `tools/ensemble.py`, `run_daily.py`, `config.py`, `tools/elo.py`.
Note that `ensemble.blend(predictions, llm_adjust=...)` already accepts an
additive, bounded, renormalised nudge dict, so the plumbing exists. This task
produces that nudge.

## Non-negotiable: ground it, never hallucinate

A nudge based on stale training-data "injuries" is worse than no nudge. So the
module MUST use Claude's **web search tool** (via the Anthropic SDK, already a
dependency) to find current information, and must only act on **sourced, recent**
findings (roughly the last 7 days before kickoff). If it finds nothing credible,
it returns a **zero nudge**. The prompt must say this explicitly and require a
source URL for every factor it acts on.

## The module

`tools/llm_context.py` with a primary function:

```
get_adjustment(home, away, commence_time) -> {
    "nudge": {"1": float, "X": float, "2": float},  # additive, already clamped
    "factors": [ {type, detail, source, favors}, ... ],
    "summary": "one-line rationale",
    "confidence": "low|medium|high",
}
```

Implementation:

- Call Claude (`config.LLM_MODEL`) with the web search tool enabled. Prompt it to
  research, for this specific fixture and date, only: confirmed key-player
  injuries/suspensions, dead-rubber/qualification-decided situations, extreme
  heat or kickoff-time/venue factors, and unusual rest/travel. Require it to
  return a single JSON object:
  ```
  {
    "factors": [{"type": "...", "detail": "...", "source": "https://...",
                 "favors": "home|away|draw|none"}],
    "nudge": {"1": <float>, "X": <float>, "2": <float>},
    "confidence": "low|medium|high",
    "summary": "<=120 chars"
  }
  ```
- **Clamp in code**, do not trust the model's magnitudes: each nudge component to
  `[-MAX_LLM_NUDGE, +MAX_LLM_NUDGE]` (config, default 0.08). Optionally scale by
  confidence (low x0.4, medium x0.7, high x1.0). If `factors` is empty or has no
  sources, force the nudge to all zeros.
- **Fail-safe:** any exception, timeout, malformed JSON, or empty result returns
  a zero nudge. This layer must never break or block a run.

## Integration into the run

In `run_daily.py`, only after the stats blend, and only when both teams are
seeded (reuse `elo.is_seeded`, same gate as Elo/Poisson) and `LLM_ENABLED=1`:

- Call `llm_context.get_adjustment(home, away, commence_time)`.
- Pass its `nudge` into the existing `ensemble.blend(preds, llm_adjust=nudge)`.
- Keep the `summary` + top `source` so the Telegram card can show one short
  context line under affected matches (e.g. "Context: starter X ruled out,
  slight lean away"). Add a `context_note` field on the bet dict and render it in
  `tools/message.py` if present. Optional but recommended.

Scope the nudge to **1X2 only** for v1 (that is what `ensemble.blend` adjusts).
Goal-market (O/U, BTTS) nudges are a future extension; do not build them now.

## Caching (cost control)

A web-search call per match per run is the expensive part, and context changes
slowly. Cache an adjustment per `(match_date, home, away)`:

- If the data layer is already Sheets-backed (see the deploy briefing), add a
  small **Context** tab: key, nudge, summary, source, confidence, fetched_at.
  Reuse a cached row if `fetched_at` is within `LLM_CACHE_HOURS` (default 12);
  otherwise refresh. This means at most ~one lookup per match per half-day.
- If still on SQLite when this is built, a simple local cache table or a
  `.tmp/llm_cache.json` is fine. Keep it storage-agnostic behind one helper.

## Config + env

Add to `config.py` / `.env.example`:

- `LLM_ENABLED` (env, default off) so runs without it are unaffected.
- `MAX_LLM_NUDGE = 0.08`
- `LLM_CACHE_HOURS = 12`
- `LLM_MODEL` already exists.
- `ANTHROPIC_API_KEY` already in `.env`.

## Cost note

With two runs/day and a handful of seeded matches, expect a small number of
web-search-backed Claude calls per day, mostly served from cache on the second
run. Acceptable. The odds-API budget is unaffected (this calls Anthropic, not
the odds API).

## Acceptance criteria

- With `LLM_ENABLED=0`, runs are byte-for-byte unchanged from today.
- With it on, a fixture with a real recent injury produces a non-zero, clamped
  nudge with a cited source; a quiet fixture produces an all-zero nudge.
- Every acted-on factor carries a source URL; unsourced claims never move the
  number.
- A forced API failure yields a zero nudge and the run completes and still sends
  the card.
- No nudge component ever exceeds `MAX_LLM_NUDGE` in absolute value.
- Second run within `LLM_CACHE_HOURS` reuses the cache (no duplicate web calls).

## Out of scope

Goal-market nudges, multi-model ensembling of the LLM output, and any change to
the Elo/Poisson/market layers.
