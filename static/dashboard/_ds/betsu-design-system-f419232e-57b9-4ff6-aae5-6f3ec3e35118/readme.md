# betsu — Design System

**betsu** is an AI-integrated football (soccer) **value-bet predictor**. Each
morning it scans the day's fixtures, blends several models into one probability
per match, finds **value bets** against bookmaker odds, sends a bet card to
**Telegram**, and logs everything to a **performance dashboard** for calibration
and ROI tracking.

It is honest by design: the goal is not raw hit-rate (favourites win a lot and
still lose money) but **calibration + positive ROI** versus the closing line.
Bets are **paper-traded by default**; real money only when the user decides a bet
makes sense.

> "No public model reliably beats the closing line. Judge betsu on calibration
> and ROI over the tournament, not on any single day."

---

## The product, in one breath

A morning run produces a ranked list of value bets — each with a model
probability, the market's implied probability, the resulting **edge**, the odds,
and a quarter-Kelly sizing guide. That card goes to Telegram. As results land,
bets are graded win/loss, P&L accrues in units, and the dashboard shows the
running record, hit rate, P&L curve, ROI, and pending count.

**The ensemble (the "predictor"), one blended probability per match:**
- **market** — de-vigged bookmaker odds. Strongest single signal; also the benchmark.
- **elo** — World Football Elo, neutral-venue, self-updating after results.
- **poisson** — Dixon-Coles goal model (unlocks Over/Under 2.5 + BTTS markets).
- **llm** — Claude news/context nudge (injuries, dead rubbers, heat) — an adjustment, not a base model.

**Value rule:** `edge = model_prob × decimal_odds − 1`. Suggest selections with
`edge ≥ MIN_EDGE` (default 5%), capped per day, ranked by edge. Flat 1-unit paper
stake; a quarter-Kelly figure shown as a real-money sizing guide.

---

## Surfaces (what this system designs for)

1. **Performance dashboard** (web) — the home view. Stat tiles (record, hit
   rate, P&L units, ROI, pending), a cumulative P&L curve, and a bets table
   (date · match · market · pick · odds · model% · edge · result · P&L).
2. **Telegram bet card** (messaging) — the daily ranked card and the results
   recap, as they appear in a Telegram chat bubble.

---

## Sources (for whoever extends this)

This system was reverse-engineered from the product's own code. You don't need
access to build with the system, but if you have it, go deeper:

- **GitHub — app & logic:** <https://github.com/WouterAltepost/betsu>
  - `CLAUDE.md` — product overview & the WAT (Workflows/Agents/Tools) framework.
  - `app.py` — the Flask service + the dashboard HTML/CSS template (the original
    surface this kit re-skins from dark → light).
  - `tools/message.py` — the exact Telegram bet-card & results-recap strings.
  - `tools/value.py` — value-bet shape (`edge`, `selection_label`, `kelly_units`, …).
  - `branding/` — the logo (`betsu-logo.svg` / `.png`).
  - `docs/` — deploy briefings (Railway + Google Sheets + n8n scheduling).
  - Related: `WouterAltepost/bet_tracker` (the earlier tipster-aggregator predecessor).

Explore the repo to recreate or extend product views more faithfully than any
screenshot allows.

---

## CONTENT FUNDAMENTALS — how betsu writes

The voice is **honest, plain-spoken, and quietly confident** — an analyst who
respects the maths and refuses to oversell. It never hypes a bet.

- **Brand name is always lowercase: `betsu`.** Even at the start of a sentence
  and in titles. (The wordmark, the dashboard `<h1>`, the Telegram header — all lowercase.)
- **Voice & person:** mostly impersonal/declarative ("4 matches scanned",
  "Sitting out"); addresses the user as **you** when it matters ("Paper unless
  **you** choose to back it"). Avoids "I". No marketing "we" chest-thumping.
- **Tone:** measured, numerate, faintly wry. Comfortable saying it has **no
  edge today** and sitting out. Honesty over bravado — it grades itself in public.
- **Casing:** sentence case for everything except UPPERCASE micro-labels on
  stat tiles ("HIT RATE", "ROI", "PENDING"). No Title Case headlines.
- **Numbers are the content.** Odds to 2 decimals (`1.95`), probabilities as
  whole percents (`62%`), edge always **signed** (`+20.9%`), P&L in **units**
  with a sign (`+1.8u`), ROI signed (`+18.0%`). Signs carry meaning — keep them.
- **Vocabulary:** value bet · edge · model probability · implied / market
  probability · de-vig · closing line · unit (u) · quarter-Kelly · calibration ·
  ROI · pick · selection · 1X2 · Over/Under 2.5 · BTTS · paper / real.
- **Responsible-gambling footer is non-negotiable** on any bet output:
  *"Paper unless you choose to back it. Bet responsibly."*
- **Emoji:** used **sparingly and only in Telegram**, as section markers, never
  decoration: ⚽ (card header), 📊 (running record), 📋 (results recap). The web
  dashboard is emoji-light. Do **not** sprinkle emoji through the UI.

**Copy examples (verbatim from the product):**
- Card header: `⚽ betsu — 2026-06-11` · `4 match(es) scanned · 2 value bet(s)`
- A pick line: `Pick: Home (Argentina) @ 1.95` / `Model 62% vs market 51% → edge +20.9%` / `Stake: 1u (¼-Kelly guide 0.05)`
- No-bet day: `No value bets clear the edge threshold today. Sitting out.`
- Running line: `📊 Running: 6-4 (60%) · +1.8u · ROI +18.0%`
- Dashboard subtitle: `Paper-traded unless flagged real. Source: Google Sheets`
- Empty state: `No bets recorded yet. Run a morning card first.`

---

## VISUAL FOUNDATIONS

The original dashboard shipped **dark**; this system moves betsu to a **warm,
light-primary** look that lets the gold/orange brand mark lead — calmer and more
"editorial analyst", less "neon sportsbook".

**Colour.** Warm off-white canvas (`--warm-50 #FBF9F6`) with white cards. Ink is
a warm near-black (`--warm-900 #1A1611`), not pure black. The brand is the logo's
**gold→orange gradient** — `--gold-300 #FFD970 → --gold-500 #F7941E`, with
`--orange-400 #FF914D` (the two dots) as a secondary accent. Results use a
slightly **warm green** (`--win #1F9D63`) and a **clearly-red red** (`--loss
#D93F2D`, kept distinct from the orange so loss never reads as accent); pending
uses a muted amber (`--pending #D98A1A`). Accent is used with intent: gold drives
brand moments and primary CTAs, green/red are reserved for win/loss and P&L.

**Brand mark.** A gold-gradient disc with an abstract **node-graph** (a white
"lollipop" node linked to two orange dots) — reads as connected data points / AI
analysis, also faintly a ball. Rounded, friendly, confident. Use it on the
gradient disc or knocked-out on solid backgrounds.

**Type.** Display = **Bricolage Grotesque** (warm, slightly characterful
grotesque — humble but with personality), used bold/extra-bold for the wordmark,
big numbers, and screen titles with tight tracking (`-0.02em`). Body/UI =
**Inter**, 400–700. **No separate mono** — numbers use Inter with
**tabular figures** (`font-variant-numeric: tabular-nums`) so odds and edges
align in columns. Uppercase micro-labels carry `+0.04em` tracking.

**Backgrounds.** Mostly flat warm surfaces — **no full-bleed photography, no
textures, no busy patterns.** The one signature flourish is the **brand
gradient**, used deliberately on the logo disc, hero/header accents, and the
"top pick" highlight — never as a page-wide wash. Charts sit on white cards.

**Corner radii.** Generously rounded, echoing the disc mark: tiles/cards
`--radius-lg 16px` to `--radius-2xl 28px`, buttons/inputs `--radius-md 12px`,
pills/badges `--radius-full`. Avoid hard 0px corners.

**Cards.** White fill, **1px warm hairline border** (`--border #E3DBCF`), soft
radius, and a soft warm-tinted shadow (`--shadow-sm`/`--shadow-md`, ink at
4–10% alpha — never harsh black). Elevation is gentle. A highlighted card
(e.g. top pick) may add a thin gold border and `--shadow-gold` glow.

**Borders & dividers.** Hairline warm neutrals; table rows separated by
`--border-subtle`. Strong borders (`--border-strong`) only for emphasis.

**Shadows.** Two systems: soft **drop shadows** for elevation (warm, diffuse,
low-alpha) and the **gold glow** (`--shadow-gold`) reserved for the primary CTA
and brand-highlighted surfaces. No inner shadows except subtle pressed states.

**Buttons & states.** Primary = solid **gold (`--gold-500`) with dark ink**
(`--accent-fg #1A1611`) — the signature betsu button; hover darkens to
`--gold-600`, press to `--gold-700`. Secondary = white with warm border; ghost =
transparent, fills `--bg-hover` on hover. **Hover** = darken accent / fill a
subtle warm tint; **press** = darken one more step plus a 1px nudge or 0.98
scale; **focus** = 2px gold outline, 2px offset (`--focus-ring`). No colour
inversions.

**Motion.** Quiet and confident — short fades and small slides (120–320ms) on
`--ease-out`. **No bounces, no springy overshoot, no infinite decorative loops.**
The P&L curve may draw in once; stat tiles may fade/rise on load.

**Transparency & blur.** Used rarely — a faint backdrop blur on sticky headers /
the Telegram chrome, and low-alpha tints for badge fills (`--win-bg`, `--loss-bg`,
`--pending-bg`). Otherwise opaque.

**Layout.** Centred single column, ~1000px max for the dashboard, generous
vertical rhythm on the 4px spacing scale. Sticky table header. Stat tiles in a
responsive auto-fit grid. Imagery is essentially absent — the data **is** the
imagery.

**Imagery vibe.** Warm, bright, optimistic — driven entirely by the gold/orange
palette. No grain, no duotone photography, no stock imagery.

---

## ICONOGRAPHY

betsu's own codebase ships **no icon set** — the original dashboard uses only the
⚽ emoji and coloured text pills. This system therefore standardises on
**[Lucide](https://lucide.dev)** (loaded from CDN) as the icon language:
thin, rounded, 1.5–2px stroke, geometric — a clean match for the rounded,
friendly brand mark. Use Lucide for all UI affordances (nav, table controls,
stat-tile glyphs, status, send).

**Rules**
- **Stroke icons only**, `stroke-width: 1.75`, sized 16/18/20/24px, `currentColor`.
- Icons are **functional, not decorative** — every icon earns a meaning.
- **Emoji** appear **only in the Telegram surface**, as section markers (⚽ 📊 📋),
  mirroring the real product. Keep them out of the web UI.
- The **logo mark** (`assets/betsu-logo.svg`) is not an icon — never substitute it
  for a UI glyph, and never recolour it.
- *Substitution flag:* Lucide is a chosen, CDN-loaded substitute since the repo
  has no native icon set. If betsu later adopts an official set, swap the CDN link.

Suggested mappings: `trophy`/`target` (record, edge), `trending-up` (ROI, P&L
curve), `clock` (pending), `send` (Telegram), `circle-check` / `circle-x` (win /
loss), `chevron-down` (sort), `dot` / `goal` (matches).

---

## Assets

- `assets/betsu-logo.svg` — primary mark, gold→orange gradient (vector, scalable).
- `assets/betsu-logo.png` — raster fallback (2011×2011).

The mark is gradient-on-transparent; place it on light/white or on the gradient
disc. Do not recolour, outline, or place on a busy background.

---

## Index — what's in this system

See the **Design System** tab for every live card. Files:

- `styles.css` — global entry point (link this one file). `@import`s everything below.
- `tokens/` — `fonts.css` · `colors.css` · `typography.css` · `spacing.css` · `base.css`
- `guidelines/` — foundation specimen cards: `colors-brand` · `colors-neutrals` ·
  `colors-semantic` · `type-display` · `type-body` · `type-numbers` · `type-scale` ·
  `spacing-scale` · `spacing-radii` · `spacing-shadows` · `brand-logo`
- `components/`
  - `core/` — **Button**, **Badge**, **Card**, **Logo**
  - `data/` — **StatTile**, **BetCard** (the signature value-bet card)
  - each has `<Name>.jsx`, `<Name>.d.ts`, `<Name>.prompt.md`; one preview card per dir
- `ui_kits/dashboard/` — `{index.html, Dashboard.jsx, data.js}` — performance dashboard (light theme, tabs: Performance / Today's card)
- `ui_kits/telegram/` — `{index.html, Telegram.jsx}` — daily bet card + results recap as chat messages, with a working `/today` composer
- `SKILL.md` — packaging so this system works as a downloadable Claude Skill
- `assets/` — `betsu-logo.svg`, `betsu-logo.png`

**Namespace for cards/kits:** components are exposed on
`window.BetsuDesignSystem_f41923`. In any `.html`, link `styles.css`, load
`_ds_bundle.js` (the auto-compiled bundle), then
`const { Button, BetCard, … } = window.BetsuDesignSystem_f41923`.

### Starting points
- **Performance dashboard** (screen) · **Telegram bet card** (screen)
- **Button**, **Badge**, **StatTile**, **BetCard** (components)
