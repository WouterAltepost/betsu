// betsu — suggested-bet catalog (World Cup 2026 slate).
// betsu's models surface value bets every morning. This is the catalog of
// suggestions; what the user *actually placed* (and for how much, in €) lives
// in the store (store.jsx, localStorage). Performance is computed only from
// placed + settled bets.
window.BETSU_DATA = (function () {
  let seed = 20260616;
  function rnd() {
    seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }

  const fixtures = [
    ['Argentina', 'Saudi Arabia'], ['Mexico', 'Poland'], ['France', 'Denmark'],
    ['Spain', 'Croatia'], ['Brazil', 'Serbia'], ['Germany', 'Japan'],
    ['Portugal', 'Uruguay'], ['Netherlands', 'Ecuador'], ['England', 'USA'],
    ['Belgium', 'Morocco'], ['Italy', 'Ghana'], ['Colombia', 'Senegal'],
    ['Croatia', 'Canada'], ['Switzerland', 'Cameroon'], ['Uruguay', 'South Korea'],
    ['Denmark', 'Tunisia'], ['Japan', 'Costa Rica'], ['Poland', 'Australia'],
    ['Morocco', 'Iran'], ['USA', 'Wales'], ['Senegal', 'Qatar'],
    ['Brazil', 'Switzerland'], ['Portugal', 'Ghana'], ['Spain', 'Germany'],
  ];
  const markets = [
    { m: '1X2', picks: ['Home', 'Away', 'Draw'] },
    { m: 'OU 2.5', picks: ['Over 2.5', 'Under 2.5'] },
    { m: 'BTTS', picks: ['BTTS Yes', 'BTTS No'] },
  ];
  function pick(arr) { return arr[Math.floor(rnd() * arr.length)]; }

  // historical suggestions (matches already played → a real outcome exists)
  const played = [];
  let day = new Date(2026, 4, 18); // May 18
  let fxi = 0;
  const N = 38;
  for (let i = 0; i < N; i++) {
    if (rnd() < 0.45) day = new Date(day.getTime() + 86400000);
    const [home, away] = fixtures[fxi % fixtures.length]; fxi++;
    const mk = pick(markets);
    let pickLabel = pick(mk.picks);
    if (mk.m === '1X2') {
      pickLabel = pickLabel === 'Home' ? `Home (${home})` : pickLabel === 'Away' ? `Away (${away})` : 'Draw';
    }
    const odds = +(1.4 + rnd() * 1.6).toFixed(2);
    const impliedMarket = 1 / odds;
    const edge = 0.05 + rnd() * 0.18;
    const model = Math.min(0.92, (impliedMarket * (1 + edge)));
    const truth = Math.max(0.05, Math.min(0.95, model * (0.78 + rnd() * 0.06)));
    const won = rnd() < truth;
    const mm = String(day.getMonth() + 1).padStart(2, '0');
    const dd = String(day.getDate()).padStart(2, '0');
    played.push({
      id: `b${i}`, date: `${mm}-${dd}`, played: true,
      home, away, market: mk.m, pick: pickLabel,
      odds, model: +model.toFixed(2), market_p: +impliedMarket.toFixed(2),
      edge: +(model * odds - 1).toFixed(3),
      kelly: +(Math.max(0.02, (model * odds - 1) / (odds - 1) * 0.25)).toFixed(2),
      outcome: won ? 'win' : 'loss',
    });
  }

  // today's fresh suggestions (matches not yet played → no outcome)
  const today = [
    { id: 't0', date: '06-16', played: false, home: 'Argentina', away: 'Mexico', market: '1X2', pick: 'Home (Argentina)', odds: 1.95, model: 0.62, market_p: 0.51, edge: 0.209, kelly: 0.05, outcome: null, note: 'Mexico likely to rotate — group already secured. Heat in Dallas favours the technical side.' },
    { id: 't1', date: '06-16', played: false, home: 'Croatia', away: 'Canada', market: 'OU 2.5', pick: 'Over 2.5', odds: 1.88, model: 0.58, market_p: 0.53, edge: 0.090, kelly: 0.04, outcome: null, note: null },
    { id: 't2', date: '06-16', played: false, home: 'Senegal', away: 'Iran', market: 'BTTS', pick: 'BTTS Yes', odds: 2.15, model: 0.52, market_p: 0.47, edge: 0.118, kelly: 0.04, outcome: null, note: null },
  ];

  const catalog = played.concat(today);
  return { catalog, played, today, bankroll: 1000, TODAY: '06-16' };
})();
