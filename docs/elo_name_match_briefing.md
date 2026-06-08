# Briefing: harden team-name matching in elo.py (prevent wrong-rating collisions)

**For:** Claude Code. **Author:** planning pass in Cowork.
**Goal:** Close the same fuzzy-match collision class you just fixed in
`results_fetch.py`, but in `tools/elo.py`, where it's more dangerous. Here a
misfire assigns a team the WRONG Elo rating, which silently corrupts that
match's Poisson lambdas, the blend, and any bet off it.

Read first: `tools/elo.py` (`lookup_rating`, `ALIASES`, `MATCH_THRESHOLD`,
`is_seeded`), and your own `tools/results_fetch.py` name-reconciliation code
(reuse that approach for consistency).

## Why the existing guard does NOT cover this

`run_daily.py` already drops Elo/Poisson when `is_seeded` is False (a MISSING
rating → no spurious edge). But a fuzzy MIS-match returns a real rating for the
WRONG seed, so `is_seeded` is True and nothing fires. The guard catches absent
ratings; it cannot catch a confident wrong match. This hardening is the only
thing protecting against cross-country swaps.

## The concrete risk

`token_sort_ratio` scores **Australia vs Austria at 87.5**, above the current
threshold of 85, and both are 2026 qualifiers both present in the seed. Iran/Iraq
and Slovakia/Slovenia are the same class. So a non-exact odds-API spelling of one
could resolve to the other. (Exact spellings are safe — exact match wins first —
but we must not rely on the feed always being exact.)

## Fix (mirror results_fetch.py)

In `lookup_rating`, before the fuzzy step:

1. **Accent-fold + normalize** the query and the keys/aliases (lowercase, strip
   accents so "Curaçao"=="Curacao", "Türkiye"=="Turkiye", collapse punctuation/
   whitespace). Try exact (normalized) match, then the alias map (normalized),
   then fuzzy.
2. **Expand `ALIASES`** so every 2026 qualifier whose likely odds-API spelling
   isn't an exact key resolves explicitly (e.g. Cabo Verde, Bosnia-Herzegovina /
   Bosnia & Herzegovina, Côte d'Ivoire, Korea Republic, Türkiye, IR Iran, DR
   Congo). These should match via alias, NOT via a borderline fuzzy score.
3. **Raise `MATCH_THRESHOLD` to 90.** With accents and aliases handled, genuine
   variants resolve before fuzzy is reached, so 90 separates Australia/Austria
   (87.5) and the other confusable pairs without losing real matches.
4. Optional but nice: if the top fuzzy candidate is within a few points of the
   second-best, treat it as ambiguous and fall back to default (let the guard
   drop the layer) rather than guess. Prevents future confusable pairs silently
   resolving wrong.

If it's clean to do, factor the normalize+alias+fuzzy resolver into one shared
helper used by both `elo.py` and `results_fetch.py` so they can't drift. If
that's too invasive, mirror the logic and leave a comment cross-referencing both.

## Acceptance criteria

- A regression test asserts: every 2026 qualifier resolves to its own seed from a
  curated list of plausible odds-API spellings (exact, accented, and common
  variants), AND the confusable pairs never cross-resolve — feeding "Austria"
  never returns Australia's rating, "Iran" never returns Iraq's, etc.
- `is_seeded` still returns False for genuinely unknown teams (club test sides),
  so the run_daily guard behaves as before.
- `get_rating` for an exact seed name is unchanged.
- No regression in the existing alias resolutions (USA, Cabo Verde, Korea
  Republic, Türkiye, etc. still resolve).

## Out of scope

Changing the ensemble/guard logic, the seed values themselves, or results_fetch
(already hardened — only consolidate if sharing a helper).
