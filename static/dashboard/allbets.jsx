// betsu — "All bets" tab. The master ledger: tick what you actually placed,
// set the € stake, and settle the result. Everything persists via the store.
const { useState: _aus } = React;

function Check({ on, onClick }) {
  return (
    <button onClick={onClick} aria-pressed={on} style={{
      width: 22, height: 22, flex: 'none', cursor: 'pointer', borderRadius: 6,
      border: on ? '1.5px solid var(--gold-500)' : '1.5px solid var(--border-strong)',
      background: on ? 'var(--gold-500)' : 'var(--bg-surface)',
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      transition: 'all var(--dur-fast) var(--ease-out)', padding: 0,
    }}>
      {on ? <Icon name="check" size={14} color="var(--accent-fg)" strokeWidth={3} /> : null}
    </button>
  );
}

function SettleControl({ bet }) {
  const store = useBets();
  const r = store.rec(bet.id);
  if (!r.placed) return <span style={{ color: 'var(--text-muted)' }}>—</span>;
  if (!bet.played) return <Badge variant="pending" dot>pending</Badge>;
  if (r.result === 'pending') {
    const btn = (label, color, bg, on) => (
      <button onClick={on} style={{
        border: `1px solid ${color}`, background: 'var(--bg-surface)', color, cursor: 'pointer',
        fontFamily: 'var(--font-sans)', fontWeight: 700, fontSize: 11.5, padding: '4px 9px',
        borderRadius: 'var(--radius-full)', transition: 'all var(--dur-fast) var(--ease-out)',
      }}
        onMouseEnter={e => { e.currentTarget.style.background = bg; }}
        onMouseLeave={e => { e.currentTarget.style.background = 'var(--bg-surface)'; }}>{label}</button>
    );
    return (
      <div style={{ display: 'inline-flex', gap: 5, alignItems: 'center' }}>
        <span style={{ fontSize: 11, color: 'var(--text-muted)', fontWeight: 600, marginRight: 2 }}>settle</span>
        {btn('Win', 'var(--win)', 'var(--win-bg)', () => store.settle(bet.id, 'win'))}
        {btn('Loss', 'var(--loss)', 'var(--loss-bg)', () => store.settle(bet.id, 'loss'))}
      </div>
    );
  }
  return (
    <button onClick={() => store.unsettle(bet.id)} title="Click to change" style={{ border: 'none', background: 'transparent', cursor: 'pointer', padding: 0 }}>
      <ResultPill result={r.result} />
    </button>
  );
}

function AllBets() {
  const store = useBets();
  const tw = useTw();
  const cat = window.BETSU_DATA.catalog;
  const TODAY = window.BETSU_DATA.TODAY;
  const [filter, setFilter] = _aus('all');
  const [market, setMarket] = _aus('all');
  const [sort, setSort] = _aus('newest');
  const rec = (id) => store.rec(id);
  const perf = computePerf(store.get());
  const s = perf.summary;

  const isSettled = (b) => { const x = rec(b.id).result; return x === 'win' || x === 'loss'; };
  let rows = cat.filter(b => {
    if (market !== 'all' && b.market !== market) return false;
    if (filter === 'today') return b.date === TODAY;
    if (filter === 'placed') return rec(b.id).placed;
    if (filter === 'pending') return rec(b.id).placed && !isSettled(b);
    if (filter === 'win') return rec(b.id).result === 'win';
    if (filter === 'loss') return rec(b.id).result === 'loss';
    return true;
  });
  rows = [...rows].sort((a, b) => sort === 'edge'
    ? b.edge - a.edge
    : (a.date === b.date ? (a.id < b.id ? 1 : -1) : (a.date < b.date ? 1 : -1)));

  const pnlOf = (b) => { const r = rec(b.id); if (r.result === 'win') return r.stake * (b.odds - 1); if (r.result === 'loss') return -r.stake; return null; };
  const cellY = dens(tw, '10px', '7px');

  const filters = [['all', 'All'], ['today', 'Today'], ['placed', 'Placed'], ['pending', 'Pending'], ['win', 'Wins'], ['loss', 'Losses']];
  const markets = [['all', 'All markets'], ['1X2', '1X2'], ['OU 2.5', 'Over/Under'], ['BTTS', 'BTTS']];

  const pill = (active) => ({
    border: '1px solid', borderColor: active ? 'var(--gold-400)' : 'var(--border)',
    background: active ? 'var(--gold-100)' : 'var(--bg-surface)',
    color: active ? 'var(--gold-700)' : 'var(--text-secondary)',
    fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 12.5, padding: '5px 12px',
    borderRadius: 'var(--radius-full)', cursor: 'pointer', transition: 'all var(--dur-fast) var(--ease-out)',
  });

  return (
    <div style={{ maxWidth: CONTENT_MAX, margin: '0 auto', padding: '26px 20px 80px' }}>
      {/* heading */}
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap', marginBottom: 18 }}>
        <div>
          <h1 style={{ fontSize: 34, fontFamily: 'var(--font-display)', fontWeight: 800, letterSpacing: '-0.02em' }}>all bets</h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: 14, marginTop: 4, maxWidth: 560 }}>
            Tick the bets you actually placed, set your stake in €, and settle the result. Your P&amp;L is computed from these.
          </p>
        </div>
      </div>

      {/* summary chips */}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16 }}>
        <SummaryChip icon="layers" label="Placed" value={`${s.placedCount} bets`} />
        <SummaryChip icon="wallet" label="Staked" value={eur(s.totalStaked)} />
        <SummaryChip icon="clock" label="At risk" value={eur(s.openExposure)} tone="pending" />
        <SummaryChip icon="trophy" label="Settled" value={`${s.wins}–${s.losses}`} />
        <SummaryChip icon="coins" label="Net profit" value={s.settled ? eurSigned(s.profit) : '€0'} tone={s.profit >= 0 ? 'pos' : 'neg'} />
      </div>

      {/* toolbar */}
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', marginBottom: 14 }}>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {filters.map(([id, lab]) => <button key={id} onClick={() => setFilter(id)} style={pill(filter === id)}>{lab}</button>)}
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 6, alignItems: 'center' }}>
          {markets.map(([id, lab]) => <button key={id} onClick={() => setMarket(id)} style={pill(market === id)}>{lab}</button>)}
          <span style={{ width: 1, height: 22, background: 'var(--border)', margin: '0 4px' }} />
          <button onClick={() => setSort(sort === 'newest' ? 'edge' : 'newest')} style={{ ...pill(false), display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            <Icon name="arrow-up-down" size={14} /> {sort === 'newest' ? 'Newest' : 'Edge'}
          </button>
        </div>
      </div>

      {/* table */}
      <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-sm)', overflow: 'hidden' }}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-sans)', fontVariantNumeric: 'tabular-nums', fontSize: 13 }}>
            <thead>
              <tr>
                {['', 'Date', 'Match', 'Market', 'Pick', 'Odds', 'Model', 'Edge', 'Stake', 'Result', 'P&L'].map((h, i) => (
                  <th key={i} style={{
                    textAlign: (i >= 5 && i <= 8) || i === 10 ? 'right' : 'left',
                    padding: '11px 16px', fontSize: 10.5, fontWeight: 700, textTransform: 'uppercase',
                    letterSpacing: '0.04em', color: 'var(--text-muted)', borderBottom: '1px solid var(--border-subtle)',
                    whiteSpace: 'nowrap', background: 'var(--bg-subtle)', position: 'sticky', top: 0,
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((b, i) => {
                const r = rec(b.id); const pnl = pnlOf(b); const placed = r.placed;
                return (
                  <tr key={b.id} style={{
                    borderBottom: i < rows.length - 1 ? '1px solid var(--border-subtle)' : 'none',
                    background: placed ? 'rgba(247,148,30,0.045)' : 'transparent', transition: 'background var(--dur-fast)',
                  }}>
                    <td style={{ padding: `${cellY} 16px` }}><Check on={placed} onClick={() => store.place(b.id, !placed)} /></td>
                    <td style={{ padding: `${cellY} 16px`, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{b.date}{b.date === TODAY ? <span style={{ color: 'var(--gold-600)', fontWeight: 700 }}> ·today</span> : null}</td>
                    <td style={{ padding: `${cellY} 16px`, fontWeight: 500, whiteSpace: 'nowrap' }}>{b.home} <span style={{ color: 'var(--text-muted)' }}>vs</span> {b.away}</td>
                    <td style={{ padding: `${cellY} 16px` }}><Badge variant="neutral" size="sm">{b.market}</Badge></td>
                    <td style={{ padding: `${cellY} 16px`, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>{b.pick}</td>
                    <td style={{ padding: `${cellY} 16px`, textAlign: 'right', fontWeight: 600 }}>{b.odds.toFixed(2)}</td>
                    <td style={{ padding: `${cellY} 16px`, textAlign: 'right', color: 'var(--text-secondary)' }}>{Math.round(b.model * 100)}%</td>
                    <td style={{ padding: `${cellY} 16px`, textAlign: 'right', fontWeight: 600, color: 'var(--edge-pos)' }}>{pct(b.edge * 100, true)}</td>
                    <td style={{ padding: `${cellY} 16px`, textAlign: 'right', whiteSpace: 'nowrap' }}>
                      {placed
                        ? <StakeInput bet={b} compact />
                        : <span style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>{eur(suggestedStake(b))}</span>}
                    </td>
                    <td style={{ padding: `${cellY} 16px`, whiteSpace: 'nowrap' }}><SettleControl bet={b} /></td>
                    <td style={{ padding: `${cellY} 16px`, textAlign: 'right', fontWeight: 700, whiteSpace: 'nowrap', color: pnl == null ? 'var(--text-muted)' : pnl > 0 ? 'var(--win)' : pnl < 0 ? 'var(--loss)' : 'var(--text-primary)' }}>
                      {pnl == null ? '—' : eurSigned(pnl)}
                    </td>
                  </tr>
                );
              })}
              {rows.length === 0 ? (
                <tr><td colSpan={11} style={{ padding: '40px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13.5 }}>No bets match this filter.</td></tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginTop: 14, color: 'var(--text-muted)', fontSize: 12.5 }}>
        <span style={{ fontStyle: 'italic' }}>Bet responsibly. Only stake what you can afford to lose.</span>
      </div>
    </div>
  );
}

function SummaryChip({ icon, label, value, tone }) {
  const c = tone === 'pos' ? 'var(--win)' : tone === 'neg' ? 'var(--loss)' : tone === 'pending' ? 'var(--pending)' : 'var(--text-primary)';
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 10, background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: '9px 14px', boxShadow: 'var(--shadow-xs)' }}>
      <Icon name={icon} size={16} color="var(--warm-400)" />
      <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.2 }}>
        <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{label}</span>
        <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 16, color: c, fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>{value}</span>
      </div>
    </div>
  );
}

Object.assign(window, { AllBets });
