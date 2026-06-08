// betsu — bet store, backed by the server JSON API (Sheets is the single source
// of truth; the prototype's localStorage is gone). On load it fetches
// GET /api/bets into the catalog and derives today/played. place / setStake /
// settle / unsettle update local state optimistically (so the UI stays instant),
// then POST /api/bets/update; a failed write reverts and raises a toast. The
// stake input is debounced so typing doesn't fire a Sheets write per keystroke.
//
// Two derivations live here:
//   computePerf(state)  — REAL MONEY (€) over the bets the user placed. Headline.
//   computeModelPerf()  — the model track (units) over ALL suggestions,
//                         placed or not — what betsu is judged on (calibration).

const BANKROLL = 1000;            // € bankroll for the ¼-Kelly stake suggestion
const STAKE_DEBOUNCE_MS = 600;    // coalesce stake keystrokes into one write

// ---- EUR formatters (whole-platform currency) ----
function eur(n) { return '€' + Math.round(Math.abs(n)).toLocaleString('en-IE'); }
function eurSigned(n) { const r = Math.round(n); return (r >= 0 ? '+' : '−') + '€' + Math.abs(r).toLocaleString('en-IE'); }
function pct(n, signed = false, dp = 1) { const v = (signed && n >= 0 ? '+' : n < 0 ? '−' : '') + Math.abs(n).toFixed(dp); return v + '%'; }

// suggested ¼-Kelly stake in € given the house bankroll
function suggestedStake(bet) {
  const s = Math.round(((bet.kelly || 0) * BANKROLL) / 5) * 5;
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

// A placeholder so modules that read window.BETSU_DATA.* don't throw before the
// first fetch resolves (the app shows a loading shell until _loaded anyway).
window.BETSU_DATA = window.BETSU_DATA || { catalog: [], today: [], played: [], bankroll: BANKROLL, TODAY: '' };

function _todayStr() {
  const d = new Date();
  return `${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

const _listeners = new Set();
function emit() { _state = { ..._state, bets: { ..._state.bets } }; _listeners.forEach(fn => fn()); }

function _overlayFrom(bet) {
  return { placed: !!bet.placed, stake: bet.stake || 0, result: bet.result || 'pending' };
}

// Rebuild window.BETSU_DATA (catalog/today/played) from _catalog. `today` =
// fixtures not yet kicked off (still bettable); `played` = has a real outcome.
function _rebuildDerived() {
  window.BETSU_DATA = {
    catalog: _catalog,
    today: _catalog.filter(b => !b.played),
    played: _catalog.filter(b => b.outcome === 'win' || b.outcome === 'loss'),
    bankroll: BANKROLL,
    TODAY: _todayStr(),
  };
}

function _applyCatalog(data) {
  _catalog = Array.isArray(data) ? data : [];
  const bets = {};
  for (const b of _catalog) bets[b.id] = _overlayFrom(b);
  _state = { bets };
  _rebuildDerived();
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
  _rebuildDerived();
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

const Store = {
  get: () => _state,
  rec,
  loaded: () => _loaded,
  error: () => _error,
  toast: () => _toast,
  dismissToast: () => _setToast(null),
  load: loadBets,
  reload: loadBets,
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
};

// React hook — re-renders subscribers on any store change
function useBets() {
  const [, force] = React.useState(0);
  React.useEffect(() => {
    const fn = () => force(x => x + 1);
    _listeners.add(fn);
    return () => _listeners.delete(fn);
  }, []);
  return Store;
}

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

  // calibration bins from settled placed bets
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

// ---- MODEL track (units): over ALL suggestions, placed or not ----
// This is the benchmark betsu is judged on (calibration + ROI vs the line), kept
// distinct from the user's real € P&L. Flat 1-unit model stake per suggestion.
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

Object.assign(window, { useBets, Store, computePerf, computeModelPerf, eur, eurSigned, pct, suggestedStake, BANKROLL });
