/* betsu mobile — shared building blocks used across screens & both directions.
 * All money is EUR; numbers derive from the live store (placed bets only).     */
const { useState: _us } = React;
const DS = window.BetsuDesignSystem_f41923;
const { StatTile, BetCard, Button, Badge, Logo, Card } = DS;
const LOGO_SRC = 'assets/betsu-logo.svg';

const TABS = [
  ['performance', 'Performance', 'trending-up'],
  ['today', 'Today', 'target'],
  ['allbets', 'All bets', 'receipt-text'],
];

// ---------- App header (clears the status bar / Dynamic Island) ----------
function AppHeader({ store }) {
  const perf = store.computePerf();
  const atRisk = perf.summary.openExposure;
  return (
    <header style={{
      flex: 'none', padding: 'calc(env(safe-area-inset-top) + 12px) 18px 12px',
      background: 'rgba(251,249,246,0.86)', backdropFilter: 'saturate(180%) blur(12px)',
      WebkitBackdropFilter: 'saturate(180%) blur(12px)',
      borderBottom: '1px solid var(--border-subtle)',
      display: 'flex', alignItems: 'center', gap: 10,
    }}>
      <Logo size={26} markSrc={LOGO_SRC} />
      <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 8 }}>
        {atRisk > 0 && (
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)', fontVariantNumeric: 'tabular-nums', background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 'var(--radius-full)', padding: '5px 11px', boxShadow: 'var(--shadow-xs)' }}>
            <Icon name="wallet" size={14} color="var(--warm-400)" />
            {eur(atRisk)} at risk
          </span>
        )}
      </div>
    </header>
  );
}

// ---------- Bottom tab bar ----------
function BottomTabBar({ tab, setTab, store, variant }) {
  const todayCount = store.today().length;
  return (
    <nav style={{
      flex: 'none', display: 'flex', alignItems: 'stretch',
      background: 'rgba(251,249,246,0.92)', backdropFilter: 'saturate(180%) blur(14px)',
      WebkitBackdropFilter: 'saturate(180%) blur(14px)',
      borderTop: '1px solid var(--border-subtle)', paddingBottom: 'calc(env(safe-area-inset-bottom) + 8px)', paddingTop: 7,
    }}>
      {TABS.map(([id, label, icon]) => {
        const active = tab === id;
        const showBadge = id === 'today' && todayCount > 0;
        return (
          <button key={id} onClick={() => setTab(id)} style={{
            flex: 1, border: 'none', background: 'transparent', cursor: 'pointer',
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
            padding: '4px 0 2px', position: 'relative',
            WebkitTapHighlightColor: 'transparent',
          }}>
            {variant === 'bold' && active ? (
              <span style={{
                display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                width: 46, height: 30, borderRadius: 'var(--radius-full)', background: 'var(--gold-100)',
                position: 'relative',
              }}>
                <Icon name={icon} size={21} color="var(--gold-700)" strokeWidth={2} />
                {showBadge ? <TabBadge n={todayCount} /> : null}
              </span>
            ) : (
              <span style={{ position: 'relative', display: 'inline-flex', height: 30, alignItems: 'center' }}>
                <Icon name={icon} size={22} color={active ? 'var(--gold-600)' : 'var(--warm-400)'} strokeWidth={active ? 2 : 1.75} />
                {showBadge ? <TabBadge n={todayCount} /> : null}
              </span>
            )}
            <span style={{
              fontFamily: 'var(--font-sans)', fontSize: 10.5,
              fontWeight: active ? 700 : 500,
              color: active ? 'var(--gold-700)' : 'var(--text-muted)',
              letterSpacing: '0.01em',
            }}>{label}</span>
          </button>
        );
      })}
    </nav>
  );
}
function TabBadge({ n }) {
  return (
    <span style={{
      position: 'absolute', top: -3, right: -9, minWidth: 16, height: 16, padding: '0 4px',
      borderRadius: 'var(--radius-full)', background: 'var(--gold-500)', color: 'var(--accent-fg)',
      fontSize: 10, fontWeight: 800, display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      border: '1.5px solid var(--bg-page)', fontVariantNumeric: 'tabular-nums',
    }}>{n}</span>
  );
}

// ---------- Screen title block ----------
function ScreenTitle({ title, sub, children }) {
  return (
    <div style={{ marginBottom: 16 }}>
      <h1 style={{ fontSize: 28, fontFamily: 'var(--font-display)', fontWeight: 800, letterSpacing: '-0.02em', lineHeight: 1.05 }}>{title}</h1>
      {sub ? <p style={{ color: 'var(--text-secondary)', fontSize: 13.5, marginTop: 5, lineHeight: 1.4 }}>{sub}</p> : null}
      {children}
    </div>
  );
}

// ---------- Titled card wrapper ----------
function Panel({ title, sub, icon, action, children, highlight = false, pad = 16, style = {} }) {
  return (
    <section style={{
      background: 'var(--bg-surface)', border: highlight ? '1.5px solid var(--gold-400)' : '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)', boxShadow: highlight ? 'var(--shadow-gold)' : 'var(--shadow-sm)',
      overflow: 'hidden', display: 'flex', flexDirection: 'column', ...style,
    }}>
      {title ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 9, padding: `${pad}px ${pad}px 0` }}>
          {icon ? <span style={{ display: 'inline-flex', color: 'var(--gold-600)' }}><Icon name={icon} size={16} /></span> : null}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 1, minWidth: 0 }}>
            <h3 style={{ fontSize: 14.5, fontFamily: 'var(--font-display)', fontWeight: 700, letterSpacing: '-0.01em' }}>{title}</h3>
            {sub ? <span style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>{sub}</span> : null}
          </div>
          {action ? <div style={{ marginLeft: 'auto' }}>{action}</div> : null}
        </div>
      ) : null}
      <div style={{ padding: pad, paddingTop: title ? 13 : pad, flex: 1 }}>{children}</div>
    </section>
  );
}

// ---------- Result pill ----------
function ResultPill({ result }) {
  if (result === 'win') return <Badge variant="win" dot>win</Badge>;
  if (result === 'loss') return <Badge variant="loss" dot>loss</Badge>;
  return <Badge variant="pending" dot>pending</Badge>;
}

// ---------- € stake stepper (touch-friendly, step €5) ----------
function StakeStepper({ store, bet, size = 'md' }) {
  const r = store.rec(bet.id);
  const stake = r.stake || 0;
  const h = size === 'sm' ? 32 : 36;
  const btn = (label, on, disabled) => (
    <button onClick={on} disabled={disabled} style={{
      width: h, height: h, flex: 'none', border: 'none', background: 'transparent',
      color: disabled ? 'var(--warm-300)' : 'var(--text-secondary)', cursor: disabled ? 'default' : 'pointer',
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center', WebkitTapHighlightColor: 'transparent',
    }}>
      <Icon name={label} size={size === 'sm' ? 15 : 17} strokeWidth={2.25} />
    </button>
  );
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', height: h,
      border: '1px solid var(--border-strong)', borderRadius: 'var(--radius-full)',
      background: 'var(--bg-surface)', overflow: 'hidden',
    }}>
      {btn('minus', () => store.setStake(bet.id, Math.max(0, stake - 5)), stake <= 0)}
      <span style={{
        minWidth: size === 'sm' ? 48 : 56, textAlign: 'center', fontFamily: 'var(--font-sans)', fontWeight: 700,
        fontSize: size === 'sm' ? 13.5 : 15, color: 'var(--text-primary)', fontVariantNumeric: 'tabular-nums',
      }}>{eur(stake)}</span>
      {btn('plus', () => store.setStake(bet.id, stake + 5))}
    </div>
  );
}

// ---------- Settle control (Win / Loss / pending) ----------
function SettleControl({ store, bet, size = 'md' }) {
  const r = store.rec(bet.id);
  if (!r.placed) return <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>—</span>;
  if (!bet.played) return <Badge variant="pending" dot>pending</Badge>;
  if (r.result === 'pending') {
    const sm = size === 'sm';
    const b = (label, color, bg, on) => (
      <button onClick={on} style={{
        border: `1px solid ${color}`, background: 'var(--bg-surface)', color, cursor: 'pointer',
        fontFamily: 'var(--font-sans)', fontWeight: 700, fontSize: sm ? 11.5 : 12.5,
        padding: sm ? '5px 11px' : '6px 14px', borderRadius: 'var(--radius-full)',
        WebkitTapHighlightColor: 'transparent',
      }}>{label}</button>
    );
    return (
      <div style={{ display: 'inline-flex', gap: 7, alignItems: 'center' }}>
        {b('Win', 'var(--win)', 'var(--win-bg)', () => store.settle(bet.id, 'win'))}
        {b('Loss', 'var(--loss)', 'var(--loss-bg)', () => store.settle(bet.id, 'loss'))}
      </div>
    );
  }
  return (
    <button onClick={() => store.unsettle(bet.id)} title="Tap to change" style={{ border: 'none', background: 'transparent', cursor: 'pointer', padding: 0 }}>
      <ResultPill result={r.result} />
    </button>
  );
}

// ---------- Market chip ----------
function MarketChip({ market }) {
  return (
    <span style={{
      padding: '2px 8px', borderRadius: 'var(--radius-full)', background: 'var(--bg-subtle)',
      color: 'var(--text-secondary)', fontSize: 11, fontWeight: 600, whiteSpace: 'nowrap',
      fontFamily: 'var(--font-sans)',
    }}>{market}</span>
  );
}

Object.assign(window, { AppHeader, BottomTabBar, ScreenTitle, Panel, ResultPill, StakeStepper, SettleControl, MarketChip, LOGO_SRC, TABS });
