# Telegram Message Redesign Briefing

## Problem
The current daily bet card is dense and hard to scan at a glance. Each bet repeats match info and context, resulting in 8-10 lines per pick. Users can't quickly see what's being suggested.

## Target Format (Version A)
```
⚽ betsu — 2026-06-11 | 5 value bets

🇰🇷 SOUTH KOREA vs CZECH REPUBLIC
  Home (SK) @ 2.82 | 39% → +11.1% edge | €15
  Over 2.5 @ 2.30 | 48% → +10.8% edge | €20

🇲🇽 MEXICO vs SOUTH AFRICA
  Home (MEX) @ 1.47 | 75% → +10.2% edge | €55
  Over 2.5 @ 2.25 | 48% → +8.4% edge | €15
  BTTS No @ 1.60 | 66% → +5.1% edge | €20

SK: Altitude acclimatization (link)
MEX: Altitude + RSA lineup gaps (link)

Bet responsibly
```

## Changes to `tools/message.py`

### 1. Refactor `build_daily_card()`
- Group bets by match (match key = `f"{home_team}|{away_team}"`)
- Build match sections first (match name + all picks for that match)
- Then build context section (match key: context snippet with link)
- Replace sequential numbering with grouped layout

### 2. New helper function `_fmt_match_group()`
Take a match dict with:
```python
{
  "name": "SOUTH KOREA vs CZECH REPUBLIC",  # all-caps
  "bets": [list of bet dicts]
}
```
Return formatted string like:
```
🇰🇷 SOUTH KOREA vs CZECH REPUBLIC
  Home (SK) @ 2.82 | 39% → +11.1% edge | €15
  Over 2.5 @ 2.30 | 48% → +10.8% edge | €20
```

Each bet line format:
```
  {selection_label} @ {odds:.2f} | {model_prob:.0%} → {edge:+.1%} edge | €{stake}
```

### 3. New helper function `_fmt_context_line()`
Take a match key and list of bets for that match, extract unique context, return:
```
SK: Altitude acclimatization (https://...)
```
If a match has multiple picks with the same context (common), de-dup and show once.

### 4. Update summary line
Change from `2 match(es) scanned · 5 value bet(s)` to `| 5 value bets` (inline after date).

### 5. Grouping logic in `build_daily_card()`
```python
def build_daily_card(run_date, bets, n_matches, record=None):
    # Group bets by (home_team, away_team)
    matches_dict = {}
    for bet in bets:
        key = (bet['home_team'], bet['away_team'])
        if key not in matches_dict:
            matches_dict[key] = {
                'name': f"{bet['home_team'].upper()} vs {bet['away_team'].upper()}",
                'bets': []
            }
        matches_dict[key]['bets'].append(bet)
    
    # Build sections
    lines = [header]
    for (home, away), match_data in matches_dict.items():
        lines.append(_fmt_match_group(match_data))
    
    # Context section
    context_lines = [_fmt_context_line(home, away, matches_dict[(home, away)]['bets']) 
                     for (home, away) in matches_dict.keys()]
    lines.append('\n'.join(c for c in context_lines if c))
    
    # Running record, disclaimer
    ...
```

## Key Design Notes
- **Country emojis** (🇰🇷, 🇲🇽, etc.): optional for now; if including, pass country codes from `bets` or hardcode for World Cup 2026 (32 teams fixed)
- **Compact inline format:** model % → edge % → stake fit on one line per pick
- **Context de-duplication:** if two picks in the same match have identical context, show once
- **Link preservation:** context line includes the URL from `context_note` or a new `context_url` field if needed
- **No numbering:** matches group naturally by position, picks within a match are not numbered

## Testing
Run with the example bets (SK vs CZ, MEX vs SA) from the live message and verify:
- Compactness: whole card should fit in ~15-18 lines (vs current ~30+)
- Scannability: all picks for one match grouped visually
- Accuracy: edge%, stakes, context preserved
- HTML: tags still work (`<b>`, `<i>`)

## Backward Compat
- `build_results_recap()` unchanged
- `_real_record_line()` unchanged
- Tests in `__main__` should pass (update expected output)
