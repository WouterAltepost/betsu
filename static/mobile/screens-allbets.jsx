/* betsu mobile — "All bets" ledger, the master record: tick what you placed, set
 * the € stake, settle the result. Two directions share the filter engine:
 *   Direction A (editorial) — condensed, tappable rows that expand for actions.
 *   Direction B (bold)      — one spacious card per bet with inline actions.     */
const { useState: _abs } = React;

function abPill(active) {
  return {
    border: '1px solid', borderColor: active ? 'var(--gold-400)' : 'var(--border)',
    background: active ? 'var(--gold-100)' : 'var(--bg-surface)',
    color: active ? 'var(--gold-700)' : 'var(--text-secondary)',
    fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 12.5, padding: '6px 13px',
    borderRadius: 'var(--radius-full)', cursor: 'pointer', whiteSpace: 'nowrap', flex: 'none',
    WebkitTapHighlightColor: 'transparent',
  };
}

function useLedger(store) {
  const [filter, setFilter] = _abs('all');
  const [market, setMarket] = _abs('all');
  const [sort, setSort] = _abs('newest');
  const rec = (id) => store.rec(id);
  const TODAY = store.TODAY;
  const isSettled = (b) => { const x = rec(b.id).result; return x === 'win' || x === 'loss'; };
  let rows = store.catalog.filter(b => {
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
  return { filter, setFilter, market, setMarket, sort, setSort, rows, rec, TODAY };
}

function pnlOf(store, b) { const r = store.rec(b.id); if (r.result === 'win') return r.stake * (b.odds - 1); if (r.result === 'loss') return -r.stake; return null; }

// ---------- Summary chips ----------
function LedgerSummary({ store }) {
  const s = store.computePerf().summary;
  const chips = [
    { icon: 'layers', label: 'Placed', value: `${s.placedCount}` },
    { icon: 'wallet', label: 'Staked', value: eur(s.totalStaked) },
    { icon: 'clock', label: 'At risk', value: eur(s.openExposure), tone: 'pending' },
    { icon: 'trophy', label: 'Settled', value: `${s.wins}–${s.losses}` },
    { icon: 'coins', label: 'Net', value: s.settled ? eurSigned(s.profit) : '€0', tone: s.profit >= 0 ? 'pos' : 'neg' },
  ];
  return (
    <div className="hscroll" style={{ display: 'flex', gap: 9, overflowX: 'auto', margin: '0 -18px', padding: '0 18px 2px' }}>
      {chips.map((c) => {
        const col = c.tone === 'pos' ? 'var(--win)' : c.tone === 'neg' ? 'var(--loss)' : c.tone === 'pending' ? 'var(--pending)' : 'var(--text-primary)';
        return (
          <div key={c.label} style={{ display: 'inline-flex', alignItems: 'center', gap: 9, background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-md)', padding: '8px 12px', boxShadow: 'var(--shadow-xs)', flex: 'none' }}>
            <Icon name={c.icon} size={15} color="var(--warm-400)" />
            <div style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.15 }}>
              <span style={{ fontSize: 9.5, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{c.label}</span>
              <span style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 15, color: col, fontVariantNumeric: 'tabular-nums', whiteSpace: 'nowrap' }}>{c.value}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ---------- Toolbar (single clean row: status + market) ----------
function LedgerToolbar({ ledger }) {
  const { filter, setFilter, market, setMarket } = ledger;
  const statuses = [['all', 'All'], ['placed', 'Placed'], ['pending', 'Pending'], ['win', 'Wins'], ['loss', 'Losses']];
  const markets = [['1X2', '1X2'], ['OU 2.5', 'O/U'], ['BTTS', 'BTTS']];
  return (
    <div className="hscroll" style={{ display: 'flex', gap: 7, overflowX: 'auto', margin: '0 -18px', padding: '0 18px', alignItems: 'center' }}>
      {statuses.map(([id, lab]) => <button key={id} onClick={() => setFilter(id)} style={abPill(filter === id)}>{lab}</button>)}
      <span style={{ width: 1, height: 20, background: 'var(--border)', margin: '0 1px', flex: 'none' }} />
      {markets.map(([id, lab]) => <button key={id} onClick={() => setMarket(market === id ? 'all' : id)} style={abPill(market === id)}>{lab}</button>)}
    </div>
  );
}

// =================== Direction A — condensed expandable rows ===================
function LedgerRow({ store, bet, expanded, onToggle, isLast }) {
  const r = store.rec(bet.id);
  const placed = r.placed;
  const settled = r.result === 'win' || r.result === 'loss';
  const pnl = pnlOf(store, bet);
  const isToday = bet.date === store.TODAY;
  return (
    <div style={{ borderBottom: isLast ? 'none' : '1px solid var(--border-subtle)', background: placed ? 'rgba(247,148,30,0.045)' : 'transparent' }}>
      <div onClick={onToggle} style={{ display: 'flex', alignItems: 'center', gap: 11, padding: '12px 14px', cursor: 'pointer', WebkitTapHighlightColor: 'transparent' }}>
        <Check on={placed} onClick={(e) => { e.stopPropagation(); store.place(bet.id, !placed); }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 7 }}>
            <span style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 14.5, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {bet.home} <span style={{ color: 'var(--text-muted)', fontWeight: 500 }}>v</span> {bet.away}
            </span>
            <span style={{ marginLeft: 'auto', fontSize: 11, color: isToday ? 'var(--gold-600)' : 'var(--text-muted)', fontWeight: isToday ? 700 : 500, whiteSpace: 'nowrap', flex: 'none' }}>{isToday ? 'today' : fmtDate(bet.date)}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
            <MarketChip market={bet.market} />
            <span style={{ fontSize: 12, color: 'var(--text-secondary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{bet.pick}</span>
            <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)', fontVariantNumeric: 'tabular-nums', flex: 'none' }}>@{bet.odds.toFixed(2)}</span>
            <span style={{ fontSize: 12, fontWeight: 700, color: 'var(--edge-pos)', fontVariantNumeric: 'tabular-nums', flex: 'none' }}>{pct(bet.edge * 100, true, 0)}</span>
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4, flex: 'none' }}>
          {settled ? (
            <span style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 14, fontVariantNumeric: 'tabular-nums', color: pnl > 0 ? 'var(--win)' : pnl < 0 ? 'var(--loss)' : 'var(--text-primary)' }}>{eurSigned(pnl)}</span>
          ) : placed ? (
            <Badge variant="pending" size="sm" dot>open</Badge>
          ) : null}
          <Icon name={expanded ? 'chevron-up' : 'chevron-down'} size={16} color="var(--warm-400)" />
        </div>
      </div>
      {expanded ? (
        <div style={{ padding: '2px 14px 16px 47px', display: 'flex', flexDirection: 'column', gap: 12 }}>
          {!placed ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
              <Button variant="secondary" size="sm" icon={<Icon name="circle-plus" size={15} />} onClick={() => store.place(bet.id, true)}>Place this bet</Button>
              <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>model {Math.round(bet.model * 100)}% · suggested {eur(store.suggested(bet))}</span>
            </div>
          ) : (
            <React.Fragment>
              <LedgerField label="Your stake"><StakeStepper store={store} bet={bet} size="sm" /></LedgerField>
              <LedgerField label="Result">
                <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                  <SettleControl store={store} bet={bet} size="sm" />
                  <button onClick={() => store.place(bet.id, false)} style={{ border: 'none', background: 'transparent', color: 'var(--text-muted)', fontSize: 12, cursor: 'pointer', fontFamily: 'var(--font-sans)', fontWeight: 600 }}>Remove</button>
                </div>
              </LedgerField>
            </React.Fragment>
          )}
        </div>
      ) : null}
    </div>
  );
}

function LedgerField({ label, children }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <span style={{ width: 76, flex: 'none', fontSize: 10.5, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-muted)' }}>{label}</span>
      {children}
    </div>
  );
}

function Check({ on, onClick }) {
  return (
    <button onClick={onClick} aria-pressed={on} style={{
      width: 24, height: 24, flex: 'none', cursor: 'pointer', borderRadius: 7,
      border: on ? '1.5px solid var(--gold-500)' : '1.5px solid var(--border-strong)',
      background: on ? 'var(--gold-500)' : 'var(--bg-surface)',
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center', padding: 0,
      WebkitTapHighlightColor: 'transparent',
    }}>
      {on ? <Icon name="check" size={15} color="var(--accent-fg)" strokeWidth={3} /> : null}
    </button>
  );
}

function AllBetsList({ store }) {
  const ledger = useLedger(store);
  const [openId, setOpenId] = _abs(null);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      <ScreenTitle title="all bets" sub="Tick the bets you placed, set your stake in €, and settle the result. Your P&L is computed from these." />
      <LedgerSummary store={store} />
      <LedgerToolbar ledger={ledger} />
      <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-sm)', overflow: 'hidden' }}>
        {ledger.rows.length === 0 ? (
          <div style={{ padding: '36px 20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13.5 }}>No bets match this filter.</div>
        ) : ledger.rows.map((b, i) => (
          <LedgerRow key={b.id} store={store} bet={b} expanded={openId === b.id} onToggle={() => setOpenId(openId === b.id ? null : b.id)} isLast={i === ledger.rows.length - 1} />
        ))}
      </div>
      <p style={{ color: 'var(--text-muted)', fontSize: 12, fontStyle: 'italic', textAlign: 'center' }}>Bet responsibly. Only stake what you can afford to lose.</p>
    </div>
  );
}

Object.assign(window, { AllBetsList });
