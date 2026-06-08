// betsu — shared building blocks. All money is EUR; all numbers derive from
// the live store (placed bets only).
const { useState: _us } = React;
const { StatTile, BetCard, Button, Badge, Logo, Card } = window.BetsuDesignSystem_f41923;
const LOGO_SRC = 'assets/betsu-logo.svg';
const TABS = [['overview', 'Performance'], ['allbets', 'All bets'], ['today', 'Today']];

// ---------- Header ----------
function Header({ tab, setTab }) {
  const store = useBets();
  const perf = computePerf(store.get());
  return (
    <header style={{
      position: 'sticky', top: 0, zIndex: 20,
      background: 'rgba(251,249,246,0.82)', backdropFilter: 'saturate(180%) blur(12px)',
      WebkitBackdropFilter: 'saturate(180%) blur(12px)', borderBottom: '1px solid var(--border-subtle)',
    }}>
      <div style={{ maxWidth: 1180, margin: '0 auto', padding: '0 28px', height: 62, display: 'flex', alignItems: 'center', gap: 20 }}>
        <Logo size={30} markSrc={LOGO_SRC} />
        <nav style={{ display: 'flex', gap: 4, marginLeft: 6 }}>
          {TABS.map(([id, label]) => (
            <button key={id} onClick={() => setTab(id)} style={{
              background: tab === id ? 'var(--bg-surface)' : 'transparent',
              boxShadow: tab === id ? 'var(--shadow-xs)' : 'none',
              color: tab === id ? 'var(--text-primary)' : 'var(--text-secondary)',
              fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 14,
              padding: '7px 14px', borderRadius: 'var(--radius-md)', cursor: 'pointer',
              border: tab === id ? '1px solid var(--border)' : '1px solid transparent',
              transition: 'all var(--dur-fast) var(--ease-out)',
            }}>{label}</button>
          ))}
        </nav>
        <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 12 }}>
          {perf.summary.openExposure > 0 ? (
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12.5, fontWeight: 600, color: 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums' }}>
              <Icon name="wallet" size={15} color="var(--warm-400)" />
              {eur(perf.summary.openExposure)} at risk
            </span>
          ) : null}
          <Button variant="primary" size="sm" icon={<Icon name="send" size={15} color="var(--accent-fg)" />}>Send card</Button>
        </div>
      </div>
    </header>
  );
}

// ---------- Titled card wrapper ----------
function Panel({ title, sub, icon, action, children, highlight = false, pad, style = {} }) {
  const tw = useTw();
  const p = pad ?? dens(tw, 22, 16);
  return (
    <section style={{
      background: 'var(--bg-surface)', border: highlight ? '1.5px solid var(--gold-400)' : '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)', boxShadow: highlight ? 'var(--shadow-gold)' : 'var(--shadow-sm)',
      overflow: 'hidden', display: 'flex', flexDirection: 'column', ...style,
    }}>
      {(title || action) && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: `${p}px ${p}px ${title ? 0 : p}px` }}>
          {icon ? <span style={{ display: 'inline-flex', color: 'var(--gold-600)' }}><Icon name={icon} size={17} /></span> : null}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            <h3 style={{ fontSize: 15.5, fontFamily: 'var(--font-display)', fontWeight: 700, letterSpacing: '-0.01em' }}>{title}</h3>
            {sub ? <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{sub}</span> : null}
          </div>
          {action ? <div style={{ marginLeft: 'auto' }}>{action}</div> : null}
        </div>
      )}
      <div style={{ padding: p, paddingTop: title ? dens(tw, 16, 12) : p, flex: 1 }}>{children}</div>
    </section>
  );
}

// ---------- Verdict hero ----------
function VerdictHero({ perf, variant = 'band' }) {
  const tw = useTw();
  const s = perf.summary;
  const pos = s.profit >= 0;
  const big = variant === 'big';
  const gwash = { subtle: 'var(--brand-gradient-soft)', balanced: 'var(--brand-gradient)', bold: 'var(--brand-gradient)' }[tw.gradient];
  const onGrad = tw.gradient === 'subtle';
  const none = s.settled === 0;
  return (
    <div style={{
      position: 'relative', overflow: 'hidden', background: gwash, borderRadius: 'var(--radius-2xl)',
      border: onGrad ? '1px solid var(--gold-300)' : 'none',
      boxShadow: tw.gradient === 'bold' ? 'var(--shadow-gold)' : 'var(--shadow-md)',
      padding: big ? '40px 40px' : dens(tw, '28px 30px', '22px 24px'),
    }}>
      <img src={LOGO_SRC} alt="" style={{ position: 'absolute', right: big ? -40 : -28, top: '50%', transform: 'translateY(-50%)', width: big ? 280 : 190, opacity: onGrad ? 0.5 : 0.22, pointerEvents: 'none' }} />
      <div style={{ position: 'relative', display: 'flex', flexDirection: big ? 'column' : 'row', alignItems: big ? 'flex-start' : 'flex-end', gap: big ? 18 : 36, flexWrap: 'wrap' }}>
        <div style={{ flex: big ? 'none' : 1, minWidth: 240 }}>
          <span style={{ fontFamily: 'var(--font-sans)', fontSize: 11.5, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'rgba(26,22,17,0.62)' }}>
            net profit · {s.settled} settled {s.settled === 1 ? 'bet' : 'bets'}
          </span>
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 14, marginTop: 6 }}>
            <span style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: big ? 88 : 62, lineHeight: 0.92, letterSpacing: '-0.03em', fontVariantNumeric: 'tabular-nums', color: 'var(--warm-900)', whiteSpace: 'nowrap' }}>
              {none ? '€0' : eurSigned(s.profit)}
            </span>
          </div>
          <p style={{ marginTop: big ? 12 : 8, fontSize: big ? 16 : 14, color: 'rgba(26,22,17,0.72)', fontWeight: 500, maxWidth: 460, lineHeight: 1.4 }}>
            {none
              ? 'No settled bets yet. Tick the bets you placed under “All bets”, set your stake, and settle results to start tracking.'
              : pos
                ? `Up across ${s.placedCount} placed bets — ${s.wins}–${s.losses}, ${s.hit_rate}% hit-rate on ${eur(s.totalStaked)} staked at an average +${s.avg_edge}% edge.`
                : `Down across ${s.placedCount} placed bets — ${s.wins}–${s.losses} so far. Judged over the tournament, not any single day.`}
          </p>
        </div>
        <div style={{ display: 'flex', gap: big ? 28 : 22, flexWrap: 'wrap' }}>
          <HeroStat label="ROI" value={none ? '—' : pct(s.roi, true)} tone={pos ? 'pos' : 'neg'} big={big} />
          <HeroStat label="Record" value={`${s.wins}–${s.losses}`} big={big} />
          <HeroStat label="Hit rate" value={none ? '—' : `${s.hit_rate}%`} big={big} />
        </div>
      </div>
    </div>
  );
}
function HeroStat({ label, value, tone, big }) {
  const c = tone === 'pos' ? 'var(--green-600)' : tone === 'neg' ? 'var(--red-600)' : 'var(--warm-900)';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      <span style={{ fontFamily: 'var(--font-sans)', fontSize: 10.5, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'rgba(26,22,17,0.55)' }}>{label}</span>
      <span style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: big ? 34 : 26, letterSpacing: '-0.02em', lineHeight: 1, fontVariantNumeric: 'tabular-nums', color: c, whiteSpace: 'nowrap' }}>{value}</span>
    </div>
  );
}

// ---------- Stat strip ----------
function StatStrip({ perf, columns }) {
  const tw = useTw();
  const s = perf.summary;
  const cols = columns || 5;
  const items = [
    { label: 'Net profit', value: s.settled ? eurSigned(s.profit) : '€0', tone: s.profit >= 0 ? 'pos' : 'neg', sub: 'settled', icon: 'coins' },
    { label: 'ROI', value: s.settled ? pct(s.roi, true) : '—', tone: s.roi >= 0 ? 'pos' : 'neg', sub: 'on turnover', icon: 'trending-up' },
    { label: 'Record', value: `${s.wins}–${s.losses}`, sub: `${s.settled} settled`, icon: 'trophy' },
    { label: 'Hit rate', value: s.settled ? `${s.hit_rate}%` : '—', sub: 'of settled', icon: 'target' },
    { label: 'Staked', value: eur(s.totalStaked), sub: `${s.placedCount} placed`, icon: 'layers' },
    { label: 'Pending', value: s.pending, tone: 'muted', sub: `${eur(s.openExposure)} at risk`, icon: 'clock' },
  ].slice(0, cols);
  return (
    <div style={{ display: 'grid', gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: dens(tw, 12, 10) }}>
      {items.map((it, i) => (
        <StatTile key={i} label={it.label} value={it.value} tone={it.tone} sub={it.sub} icon={<Icon name={it.icon} size={16} color="var(--warm-400)" />} />
      ))}
    </div>
  );
}

// ---------- Result pill ----------
function ResultPill({ result }) {
  if (result === 'win') return <Badge variant="win" dot>win</Badge>;
  if (result === 'loss') return <Badge variant="loss" dot>loss</Badge>;
  return <Badge variant="pending" dot>pending</Badge>;
}

// ---------- Bet log (Performance) — your placed bets, read-only ----------
function BetLog({ limit }) {
  const tw = useTw();
  const store = useBets();
  const [filter, setFilter] = _us('all');
  const recOf = (id) => store.rec(id);
  let rows = window.BETSU_DATA.catalog.filter(b => recOf(b.id).placed);
  rows = [...rows].sort((a, b) => (a.date === b.date ? (a.id < b.id ? 1 : -1) : (a.date < b.date ? 1 : -1)));
  if (filter === 'win' || filter === 'loss') rows = rows.filter(r => recOf(r.id).result === filter);
  else if (filter === 'pending') rows = rows.filter(r => { const x = recOf(r.id).result; return x !== 'win' && x !== 'loss'; });
  else if (['1X2', 'OU 2.5', 'BTTS'].includes(filter)) rows = rows.filter(r => r.market === filter);
  if (limit) rows = rows.slice(0, limit);
  const cellY = dens(tw, '11px', '8px');
  const filters = [['all', 'All'], ['win', 'Wins'], ['loss', 'Losses'], ['pending', 'Pending'], ['1X2', '1X2'], ['OU 2.5', 'O/U'], ['BTTS', 'BTTS']];
  const pnlOf = (b) => { const r = recOf(b.id); if (r.result === 'win') return r.stake * (b.odds - 1); if (r.result === 'loss') return -r.stake; return null; };
  return (
    <div style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-lg)', boxShadow: 'var(--shadow-sm)', overflow: 'hidden' }}>
      <div style={{ padding: dens(tw, '16px 20px', '12px 16px'), borderBottom: '1px solid var(--border-subtle)', display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
        <h3 style={{ fontSize: 15.5, fontFamily: 'var(--font-display)', fontWeight: 700 }}>Your placed bets</h3>
        <Badge variant="neutral" size="sm">{rows.length}</Badge>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 4, flexWrap: 'wrap' }}>
          {filters.map(([id, lab]) => (
            <button key={id} onClick={() => setFilter(id)} style={{
              border: '1px solid', borderColor: filter === id ? 'var(--gold-400)' : 'var(--border)',
              background: filter === id ? 'var(--gold-100)' : 'var(--bg-surface)',
              color: filter === id ? 'var(--gold-700)' : 'var(--text-secondary)',
              fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 12, padding: '4px 10px',
              borderRadius: 'var(--radius-full)', cursor: 'pointer', transition: 'all var(--dur-fast) var(--ease-out)',
            }}>{lab}</button>
          ))}
        </div>
      </div>
      {rows.length === 0 ? (
        <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13.5 }}>
          No bets placed yet. Open <b style={{ color: 'var(--text-secondary)' }}>All bets</b> to tick the ones you backed.
        </div>
      ) : (
        <div style={{ overflowX: 'auto', maxHeight: limit ? 'none' : 520, overflowY: limit ? 'visible' : 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontFamily: 'var(--font-sans)', fontVariantNumeric: 'tabular-nums', fontSize: 13 }}>
            <thead>
              <tr>
                {['Date', 'Match', 'Market', 'Pick', 'Odds', 'Stake', 'Model', 'Edge', 'Result', 'P&L'].map((h, i) => (
                  <th key={h} style={{
                    textAlign: (i >= 4 && i <= 7) || i === 9 ? 'right' : 'left',
                    padding: '10px 16px', fontSize: 10.5, fontWeight: 700, textTransform: 'uppercase',
                    letterSpacing: '0.04em', color: 'var(--text-muted)', borderBottom: '1px solid var(--border-subtle)',
                    whiteSpace: 'nowrap', background: 'var(--bg-subtle)', position: 'sticky', top: 0,
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((b, i) => {
                const r = recOf(b.id); const pnl = pnlOf(b);
                return (
                  <tr key={b.id} style={{ borderBottom: i < rows.length - 1 ? '1px solid var(--border-subtle)' : 'none', transition: 'background var(--dur-fast)' }}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-subtle)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                    <td style={{ padding: `${cellY} 16px`, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>{b.date}</td>
                    <td style={{ padding: `${cellY} 16px`, fontWeight: 500, whiteSpace: 'nowrap' }}>{b.home} <span style={{ color: 'var(--text-muted)' }}>vs</span> {b.away}</td>
                    <td style={{ padding: `${cellY} 16px` }}><Badge variant="neutral" size="sm">{b.market}</Badge></td>
                    <td style={{ padding: `${cellY} 16px`, color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>{b.pick}</td>
                    <td style={{ padding: `${cellY} 16px`, textAlign: 'right', fontWeight: 600 }}>{b.odds.toFixed(2)}</td>
                    <td style={{ padding: `${cellY} 16px`, textAlign: 'right', fontWeight: 600 }}>{eur(r.stake)}</td>
                    <td style={{ padding: `${cellY} 16px`, textAlign: 'right', color: 'var(--text-secondary)' }}>{Math.round(b.model * 100)}%</td>
                    <td style={{ padding: `${cellY} 16px`, textAlign: 'right', fontWeight: 600, color: 'var(--edge-pos)' }}>{pct(b.edge * 100, true)}</td>
                    <td style={{ padding: `${cellY} 16px` }}><ResultPill result={r.result} /></td>
                    <td style={{ padding: `${cellY} 16px`, textAlign: 'right', fontWeight: 700, color: pnl == null ? 'var(--text-muted)' : pnl > 0 ? 'var(--win)' : pnl < 0 ? 'var(--loss)' : 'var(--text-primary)' }}>
                      {pnl == null ? '—' : eurSigned(pnl)}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ---------- Today's suggestions with inline place control ----------
function PlaceControl({ bet }) {
  const store = useBets();
  const r = store.rec(bet.id);
  const [editing, setEditing] = _us(false);
  if (!r.placed) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border-subtle)' }}>
        <Button variant="secondary" size="sm" icon={<Icon name="circle-plus" size={15} />} onClick={() => { store.place(bet.id, true); setEditing(true); }}>
          Place this bet
        </Button>
        <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>suggested {eur(suggestedStake(bet))}</span>
      </div>
    );
  }
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 12, paddingTop: 12, borderTop: '1px solid var(--border-subtle)' }}>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, color: 'var(--win)', fontWeight: 700, fontSize: 13 }}>
        <Icon name="circle-check" size={16} color="var(--win)" /> Placed
      </span>
      <StakeInput bet={bet} />
      <button onClick={() => store.place(bet.id, false)} style={{ marginLeft: 'auto', border: 'none', background: 'transparent', color: 'var(--text-muted)', fontSize: 12.5, cursor: 'pointer', fontFamily: 'var(--font-sans)', fontWeight: 600 }}>Remove</button>
    </div>
  );
}

function StakeInput({ bet, compact = false }) {
  const store = useBets();
  const r = store.rec(bet.id);
  return (
    <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
      <span style={{ position: 'relative', display: 'inline-flex', alignItems: 'center' }}>
        <span style={{ position: 'absolute', left: 9, fontSize: 13, color: 'var(--text-muted)', pointerEvents: 'none' }}>€</span>
        <input
          type="number" min="0" step="5" value={r.stake || ''}
          onChange={(e) => store.setStake(bet.id, e.target.value)}
          placeholder={String(suggestedStake(bet))}
          style={{
            width: compact ? 78 : 92, height: 34, padding: '0 10px 0 20px',
            border: '1px solid var(--border-strong)', borderRadius: 'var(--radius-sm)',
            fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 14, color: 'var(--text-primary)',
            fontVariantNumeric: 'tabular-nums', background: 'var(--bg-surface)', outline: 'none',
          }}
          onFocus={(e) => e.target.style.borderColor = 'var(--gold-400)'}
          onBlur={(e) => e.target.style.borderColor = 'var(--border-strong)'}
        />
      </span>
    </div>
  );
}

function TodayView() {
  const store = useBets();
  const today = window.BETSU_DATA.today;
  const placedCount = today.filter(b => store.rec(b.id).placed).length;
  const staked = today.reduce((a, b) => a + (store.rec(b.id).placed ? store.rec(b.id).stake : 0), 0);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 16, flexWrap: 'wrap' }}>
        <div>
          <h2 style={{ fontSize: 28, fontFamily: 'var(--font-display)', fontWeight: 800, letterSpacing: '-0.02em' }}>today's value bets</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: 14, marginTop: 4 }}>
            <b style={{ color: 'var(--text-primary)' }}>8 matches</b> scanned · <b style={{ color: 'var(--text-primary)' }}>{today.length} value bets</b> clear the 5% edge threshold · {placedCount} placed{staked ? `, ${eur(staked)} staked` : ''}
          </p>
        </div>
        <Button variant="primary" icon={<Icon name="send" size={16} color="var(--accent-fg)" />}>Send to Telegram</Button>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
        {today.map((b, i) => (
          <div key={b.id} style={{ gridColumn: i === 0 ? '1 / -1' : 'auto' }}>
            <Card highlight={i === 0} padding={0} style={{ overflow: 'hidden' }}>
              <div style={{ padding: 18, paddingBottom: 0 }}>
                <BetCard rank={i + 1} top={i === 0} home={b.home} away={b.away} market={b.market}
                  pick={b.pick} odds={b.odds} modelProb={b.model} marketProb={b.market_p}
                  edge={b.edge} stakeUnits={1} kellyUnits={b.kelly} contextNote={b.note}
                  style={{ border: 'none', boxShadow: 'none', padding: 0 }} />
              </div>
              <div style={{ padding: '0 18px 16px' }}><PlaceControl bet={b} /></div>
            </Card>
          </div>
        ))}
      </div>
      <p style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: 13, padding: '8px 0 4px', fontStyle: 'italic' }}>
        Bet responsibly. Only stake what you can afford to lose.
      </p>
    </div>
  );
}

Object.assign(window, { Header, Panel, VerdictHero, StatStrip, BetLog, TodayView, ResultPill, StakeInput, PlaceControl });
