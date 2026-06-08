/* betsu mobile — bet store, backed by the server JSON API (Google Sheets is the
 * single source of truth; the prototype's localStorage + demo seed are gone).
 *
 * This ports the desktop dashboard's API plumbing (static/dashboard/store.jsx)
 * — fetch /api/bets, optimistic local patch, debounced stake write,
 * POST /api/bets/update, revert + toast on failure — and exposes it through the
 * INSTANCE-method surface the mobile screens call (store.rec / store.place /
 * store.computePerf / …). The screens are unchanged; underneath, every read is
 * the live catalog and every write goes to /api/bets/update.
 *
 * Note: eur/eurSigned/pct/fmtDate live in util.jsx (the single definition on
 * mobile) — they are NOT redefined here to avoid a redefinition clash.
 *
 * Two derivations (verbatim from the dashboard, same bin edges):
 *   computePerf(state)  — REAL MONEY (€) over the bets the user placed. Headline.
 *   computeModelPerf()  — the MODEL/paper track (units) over ALL suggestions. */

const BANKROLL = 1000;            // € bankroll for the ¼-Kelly stake suggestion
const STAKE_DEBOUNCE_MS = 600;    // coalesce stake keystrokes into one write

// suggested ¼-Kelly stake in € given the house bankroll (takes the bet object)
function suggestedStake(bet) {
  const s = Math.round((((bet && bet.kelly) || 0) * BANKROLL) / 5) * 5;
  return Math.max(10, s);
}

// ---- live state ----
// _catalog: the SPA-shaped bets from /api/bets (each carries placed/stake/result
// and its `key`). _state.bets: the per-id overlay the UI mutates optimistically.
let _catalog = [];
let _state = { bets: {} };
let _loaded = false;
let _error = null;
let _toast = null;

// today's ISO date 'YYYY-MM-DD', to match each bet's `date` (Sheets match_date).
function _todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

const _listeners = new Set();
function emit() { _state = { ..._state, bets: { ..._state.bets } }; _listeners.forEach(fn => fn()); }

function _overlayFrom(bet) {
  return { placed: !!bet.placed, stake: bet.stake || 0, result: bet.result || 'pending' };
}

function _applyCatalog(data) {
  _catalog = Array.isArray(data) ? data : [];
  const bets = {};
  for (const b of _catalog) bets[b.id] = _overlayFrom(b);
  _state = { bets };
  _loaded = true; _error = null;
  emit();
}

async function loadBets() {
  try {
    const res = await fetch('/api/bets', { headers: { Accept: 'application/json' } });
    const data = await res.json();
    if (data && data.error) { _error = data.error; _loaded = true; emit(); return; }
    _applyCatalog(data);
  } catch (e) {
    _error = String((e && e.message) || e);
    _loaded = true; emit();
  }
}

function _setToast(msg) {
  _toast = msg; emit();
  if (msg) setTimeout(() => { if (_toast === msg) { _toast = null; emit(); } }, 4200);
}

function _patchLocal(id, patch) {
  _state.bets[id] = { ...(_state.bets[id] || { placed: false, stake: 0, result: 'pending' }), ...patch };
  emit();
}

// Reconcile local state + catalog with the server's authoritative bet object
// (it returns effective_result, recomputed pnl, etc.).
function _syncFromServer(id, bet) {
  if (!bet || bet.error || !bet.id) return;
  _state.bets[id] = _overlayFrom(bet);
  const idx = _catalog.findIndex(b => b.id === id);
  if (idx >= 0) _catalog[idx] = bet;
  emit();
}

function _postUpdate(id, patch) {
  const bet = _catalog.find(b => b.id === id);
  if (!bet) return Promise.reject(new Error('unknown bet'));
  return fetch('/api/bets/update', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ key: bet.key, ...patch }),
  }).then(res => res.json().then(j => ({ ok: res.ok, j })));
}

// Send a write; on failure restore `prev` and toast. On success, reconcile.
function _write(id, patch, prev) {
  return _postUpdate(id, patch)
    .then(({ ok, j }) => {
      if (!ok) { _state.bets[id] = prev; _setToast((j && j.error) || 'Could not save — reverted.'); }
      else _syncFromServer(id, j);
    })
    .catch(() => { _state.bets[id] = prev; _setToast('Network error — reverted.'); emit(); });
}

const _timers = {};
function _writeDebounced(id, patch, prev) {
  clearTimeout(_timers[id]);
  _timers[id] = setTimeout(() => { _write(id, patch, prev); }, STAKE_DEBOUNCE_MS);
}

function rec(id) { return _state.bets[id] || { placed: false, stake: 0, result: 'pending' }; }

// ---- REAL MONEY (€): derive every headline number from PLACED bets ----
function computePerf(state) {
  const recOf = (id) => state.bets[id] || { placed: false, stake: 0, result: 'pending' };
  const placed = _catalog.filter(b => recOf(b.id).placed);
  const isSettled = (b) => { const r = recOf(b.id).result; return r === 'win' || r === 'loss'; };
  const settled = placed.filter(isSettled);
  const pnlOf = (b) => { const r = recOf(b.id); return r.result === 'win' ? r.stake * (b.odds - 1) : -r.stake; };

  let profit = 0, stakedSettled = 0;
  for (const b of settled) { profit += pnlOf(b); stakedSettled += recOf(b.id).stake; }
  const wins = settled.filter(b => recOf(b.id).result === 'win').length;
  const losses = settled.length - wins;
  const pending = placed.filter(b => !isSettled(b));
  const openExposure = pending.reduce((a, b) => a + recOf(b.id).stake, 0);
  const totalStaked = placed.reduce((a, b) => a + recOf(b.id).stake, 0);
  const avgEdge = placed.length ? placed.reduce((a, b) => a + b.edge, 0) / placed.length * 100 : 0;
  const best = settled.length ? Math.max(...settled.map(pnlOf)) : 0;

  // cumulative P&L curve (settled, chronological)
  const sorted = [...settled].sort((a, b) => (a.date === b.date ? (a.id < b.id ? -1 : 1) : (a.date < b.date ? -1 : 1)));
  let run = 0;
  const curve = sorted.map(b => { run += pnlOf(b); return { label: b.date, value: +run.toFixed(2) }; });

  // calibration bins from settled placed bets (dashboard's bin edges)
  const ranges = [[0.20, 0.35], [0.35, 0.45], [0.45, 0.55], [0.55, 0.65], [0.65, 0.78], [0.78, 0.95]];
  const bins = ranges.map(([lo, hi]) => {
    const inb = settled.filter(b => b.model >= lo && b.model < hi);
    const n = inb.length;
    if (!n) return null;
    const predicted = inb.reduce((a, b) => a + b.model, 0) / n;
    const actual = inb.filter(b => recOf(b.id).result === 'win').length / n;
    return { predicted: +predicted.toFixed(3), actual: +actual.toFixed(3), n };
  }).filter(Boolean);

  // per-market breakdown from settled placed bets
  const byMarket = ['1X2', 'OU 2.5', 'BTTS'].map(m => {
    const g = settled.filter(b => b.market === m);
    if (!g.length) return null;
    const w = g.filter(b => recOf(b.id).result === 'win').length;
    const p = g.reduce((a, b) => a + pnlOf(b), 0);
    const st = g.reduce((a, b) => a + recOf(b.id).stake, 0);
    return { market: m, n: g.length, wins: w, hit: Math.round(w / g.length * 100), pnl: +p.toFixed(2), staked: st, roi: st ? +(p / st * 100).toFixed(1) : 0 };
  }).filter(Boolean);

  return {
    summary: {
      profit: +profit.toFixed(2), roi: stakedSettled ? +(profit / stakedSettled * 100).toFixed(1) : 0,
      wins, losses, settled: settled.length, placedCount: placed.length,
      hit_rate: settled.length ? Math.round(wins / settled.length * 100) : 0,
      pending: pending.length, openExposure, totalStaked,
      avg_edge: +avgEdge.toFixed(1), best: +best.toFixed(2),
    },
    curve, bins, byMarket,
  };
}

// ---- MODEL / paper track (units): over ALL suggestions, placed or not ----
// The benchmark betsu is judged on (calibration + ROI vs the line), kept distinct
// from the user's real € P&L. Flat 1-unit paper stake per suggestion.
function computeModelPerf() {
  const settled = _catalog.filter(b => b.outcome === 'win' || b.outcome === 'loss');
  const wins = settled.filter(b => b.outcome === 'win').length;
  const losses = settled.length - wins;
  let pnl = 0;
  for (const b of settled) pnl += b.outcome === 'win' ? (b.odds - 1) : -1;
  const roi = settled.length ? pnl / settled.length * 100 : 0;
  const avgEdge = _catalog.length ? _catalog.reduce((a, b) => a + (b.edge || 0), 0) / _catalog.length * 100 : 0;

  const ranges = [[0.20, 0.35], [0.35, 0.45], [0.45, 0.55], [0.55, 0.65], [0.65, 0.78], [0.78, 0.95]];
  const bins = ranges.map(([lo, hi]) => {
    const inb = settled.filter(b => b.model >= lo && b.model < hi);
    const n = inb.length;
    if (!n) return null;
    const predicted = inb.reduce((a, b) => a + b.model, 0) / n;
    const actual = inb.filter(b => b.outcome === 'win').length / n;
    return { predicted: +predicted.toFixed(3), actual: +actual.toFixed(3), n };
  }).filter(Boolean);

  return {
    suggestions: _catalog.length, settled: settled.length, wins, losses,
    pnl_units: +pnl.toFixed(2),
    roi_units: +roi.toFixed(1),
    hit_rate: settled.length ? Math.round(wins / settled.length * 100) : 0,
    avg_edge: +avgEdge.toFixed(1),
    bins,
  };
}

// number of distinct fixtures among today's value bets (matches we have bets on
// today). We don't get the raw "matches scanned" count from /api/bets, so this is
// the closest honest number — distinct (date, home, away) tuples.
function _nMatchesToday() {
  const fixtures = new Set();
  for (const b of _catalog) {
    if (!b.played) fixtures.add(`${b.date}|${b.home}|${b.away}`);
  }
  return fixtures.size;
}

// The instance-style surface the mobile screens + shared.jsx call. Reads proxy
// to live module state via getters; writes go through the optimistic plumbing.
const store = {
  get catalog() { return _catalog; },
  get TODAY() { return _todayISO(); },
  get nMatchesToday() { return _nMatchesToday(); },

  // production states (ported from the dashboard, consumed by app.jsx)
  loaded: () => _loaded,
  error: () => _error,
  toast: () => _toast,
  dismissToast: () => _setToast(null),
  load: loadBets,
  reload: loadBets,

  rec,
  suggested(bet) { return suggestedStake(bet); },
  today() { return _catalog.filter(b => !b.played); },

  subscribe(fn) { _listeners.add(fn); return () => _listeners.delete(fn); },

  place(id, on) {
    const cur = rec(id);
    const bet = _catalog.find(b => b.id === id);
    const stake = on && (!cur.stake || cur.stake <= 0) ? suggestedStake(bet) : cur.stake;
    const prev = { ...cur };
    _patchLocal(id, { placed: on, stake });
    _write(id, { placed: on, stake }, prev);
  },
  setStake(id, amt) {
    const v = Math.max(0, +amt || 0);
    const prev = { ...rec(id) };
    _patchLocal(id, { stake: v, placed: true });
    _writeDebounced(id, { placed: true, stake: v }, prev);
  },
  settle(id, result) {
    const prev = { ...rec(id) };
    _patchLocal(id, { result, placed: true });
    _write(id, { placed: true, manual_result: result }, prev);
  },
  unsettle(id) {
    const prev = { ...rec(id) };
    // Clearing the manual override; the effective result falls back to the auto
    // grade, so the server response (synced) is the source of truth here.
    _patchLocal(id, { result: 'pending' });
    _write(id, { manual_result: '' }, prev);
  },

  computePerf: () => computePerf(_state),
  computeModelPerf,
};

// React hook — re-render a subscribing subtree whenever the store changes.
function useStore(store) {
  const [, force] = React.useState(0);
  React.useEffect(() => {
    const fn = () => force(x => x + 1);
    _listeners.add(fn);
    return () => _listeners.delete(fn);
  }, []);
  return store;
}

Object.assign(window, { store, useStore, computePerf, computeModelPerf, suggestedStake, BANKROLL });
