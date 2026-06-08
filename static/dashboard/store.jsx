// betsu — bet store. Single source of truth for which suggestions the user
// actually placed, the € stake, and the settled result. Persists to
// localStorage so the prototype survives reloads. All performance numbers are
// DERIVED from this via computePerf().
const _CAT = window.BETSU_DATA.catalog;
const BANKROLL = window.BETSU_DATA.bankroll;
const STORE_KEY = 'betsu.store.v3';

// ---- EUR formatters (whole-platform currency) ----
function eur(n) { return '€' + Math.round(Math.abs(n)).toLocaleString('en-IE'); }
function eurSigned(n) { const r = Math.round(n); return (r >= 0 ? '+' : '−') + '€' + Math.abs(r).toLocaleString('en-IE'); }
function pct(n, signed = false, dp = 1) { const v = (signed && n >= 0 ? '+' : n < 0 ? '−' : '') + Math.abs(n).toFixed(dp); return v + '%'; }

// suggested ¼-Kelly stake in € given the house bankroll
function suggestedStake(bet) {
  const s = Math.round((bet.kelly * BANKROLL) / 5) * 5;
  return Math.max(10, s);
}

function hash(s) { let h = 0; for (let i = 0; i < s.length; i++) h = (Math.imul(h, 31) + s.charCodeAt(i)) | 0; return Math.abs(h); }

// ---- seed: a believable history of placed + settled bets ----
function seedState() {
  const bets = {};
  for (const b of _CAT) bets[b.id] = { placed: false, stake: 0, result: 'pending' };
  // place ~66% of already-played suggestions, settled to their real outcome
  const placedPlayed = [];
  for (const b of _CAT) {
    if (!b.played) continue;
    if (hash(b.id + 'p') % 100 < 66) {
      // decorrelated human-ish stake around €40 (independent of odds)
      const v = 0.75 + (hash(b.id + 's') % 50) / 100; // 0.75–1.25×
      bets[b.id] = {
        placed: true,
        stake: Math.max(10, Math.round((40 * v) / 5) * 5),
        result: b.outcome,
      };
      placedPlayed.push(b);
    }
  }
  // leave the 3 most-recent placed bets awaiting a result (so the user can settle them)
  placedPlayed.sort((a, b) => (a.date < b.date ? 1 : -1));
  placedPlayed.slice(0, 3).forEach(b => { bets[b.id].result = 'pending'; });
  return { bets, bankroll: BANKROLL };
}

function loadState() {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    // backfill any catalog ids missing from a stale save
    for (const b of _CAT) if (!parsed.bets[b.id]) parsed.bets[b.id] = { placed: false, stake: 0, result: 'pending' };
    return parsed;
  } catch (e) { return null; }
}

let _state = loadState() || seedState();
function persist() { try { localStorage.setItem(STORE_KEY, JSON.stringify(_state)); } catch (e) {} }
persist();

const _listeners = new Set();
function emit() { _state = { ..._state, bets: { ..._state.bets } }; _listeners.forEach(fn => fn()); }

function patchBet(id, patch) {
  _state.bets[id] = { ..._state.bets[id], ...patch };
  persist(); emit();
}
const Store = {
  get: () => _state,
  rec: (id) => _state.bets[id] || { placed: false, stake: 0, result: 'pending' },
  place(id, on) {
    const cur = Store.rec(id);
    const bet = _CAT.find(b => b.id === id);
    const stake = on && (!cur.stake || cur.stake <= 0) ? suggestedStake(bet) : cur.stake;
    patchBet(id, { placed: on, stake });
  },
  setStake(id, amt) { patchBet(id, { stake: Math.max(0, +amt || 0), placed: true }); },
  settle(id, result) { patchBet(id, { result, placed: true }); },
  unsettle(id) { patchBet(id, { result: 'pending' }); },
  reset() { _state = seedState(); persist(); emit(); },
  clearAll() {
    const bets = {}; for (const b of _CAT) bets[b.id] = { placed: false, stake: 0, result: 'pending' };
    _state = { bets, bankroll: BANKROLL }; persist(); emit();
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

// ---- derive every performance number from placed bets ----
function computePerf(state) {
  const rec = (id) => state.bets[id] || { placed: false, stake: 0, result: 'pending' };
  const placed = _CAT.filter(b => rec(b.id).placed);
  const isSettled = (b) => { const r = rec(b.id).result; return r === 'win' || r === 'loss'; };
  const settled = placed.filter(isSettled);
  const pnlOf = (b) => { const r = rec(b.id); return r.result === 'win' ? r.stake * (b.odds - 1) : -r.stake; };

  let profit = 0, stakedSettled = 0;
  for (const b of settled) { profit += pnlOf(b); stakedSettled += rec(b.id).stake; }
  const wins = settled.filter(b => rec(b.id).result === 'win').length;
  const losses = settled.length - wins;
  const pending = placed.filter(b => !isSettled(b));
  const openExposure = pending.reduce((a, b) => a + rec(b.id).stake, 0);
  const totalStaked = placed.reduce((a, b) => a + rec(b.id).stake, 0);
  const avgEdge = placed.length ? placed.reduce((a, b) => a + b.edge, 0) / placed.length * 100 : 0;
  const best = settled.length ? Math.max(...settled.map(pnlOf)) : 0;

  // cumulative P&L curve (settled, chronological)
  const sorted = [...settled].sort((a, b) => (a.date === b.date ? (a.id < b.id ? -1 : 1) : (a.date < b.date ? -1 : 1)));
  let run = 0;
  const curve = sorted.map(b => { run += pnlOf(b); return { label: b.date, value: +run.toFixed(2) }; });

  // calibration bins from settled
  const ranges = [[0.20, 0.35], [0.35, 0.45], [0.45, 0.55], [0.55, 0.65], [0.65, 0.78], [0.78, 0.95]];
  const bins = ranges.map(([lo, hi]) => {
    const inb = settled.filter(b => b.model >= lo && b.model < hi);
    const n = inb.length;
    if (!n) return null;
    const predicted = inb.reduce((a, b) => a + b.model, 0) / n;
    const actual = inb.filter(b => rec(b.id).result === 'win').length / n;
    return { predicted: +predicted.toFixed(3), actual: +actual.toFixed(3), n };
  }).filter(Boolean);

  // per-market breakdown from settled
  const byMarket = ['1X2', 'OU 2.5', 'BTTS'].map(m => {
    const g = settled.filter(b => b.market === m);
    if (!g.length) return null;
    const w = g.filter(b => rec(b.id).result === 'win').length;
    const p = g.reduce((a, b) => a + pnlOf(b), 0);
    const st = g.reduce((a, b) => a + rec(b.id).stake, 0);
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

Object.assign(window, { useBets, Store, computePerf, eur, eurSigned, pct, suggestedStake, BANKROLL });
