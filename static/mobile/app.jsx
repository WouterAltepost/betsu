/* betsu mobile — Direction A ("Editorial / condensed ledger"), production shell.
 * The fake iPhone bezel is gone: BetsuApp fills the real viewport (header +
 * scrolling screen + bottom tab bar) with iOS safe-area insets, and data comes
 * from the server API via the singleton store (Google Sheets is the source of
 * truth — no localStorage, no demo seed). The app shows a loading shell until the
 * first /api/bets resolves, an error bar if Sheets is unreachable, and a toast
 * when a write is reverted. */
const { useState: _appS, useEffect: _appE } = React;

function LoadingShell() {
  return (
    <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontFamily: 'var(--font-sans)', fontSize: 14, gap: 10 }}>
      <Icon name="loader" size={18} color="var(--warm-400)" />
      loading your bets…
    </div>
  );
}

// Thin error bar below the header, full-width, respecting the screen's side padding.
function ErrorBanner({ msg }) {
  return (
    <div style={{ flex: 'none', padding: '8px 18px 0' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 9, background: 'var(--loss-bg)', border: '1px solid var(--loss)', color: 'var(--loss)', borderRadius: 'var(--radius-md)', padding: '9px 12px', fontSize: 12.5, fontWeight: 600 }}>
        <Icon name="alert-triangle" size={15} color="var(--loss)" />
        <span style={{ minWidth: 0 }}>Store unreachable: {msg}</span>
      </div>
    </div>
  );
}

// Toast host — sits above the bottom tab bar so it never hides behind the nav.
function ToastHost({ store }) {
  const t = store.toast();
  if (!t) return null;
  return (
    <div style={{
      position: 'fixed', left: '50%', transform: 'translateX(-50%)', zIndex: 50,
      bottom: 'calc(env(safe-area-inset-bottom) + 76px)',
      background: 'var(--warm-900)', color: 'var(--bg-surface)', padding: '10px 16px', borderRadius: 'var(--radius-full)',
      boxShadow: 'var(--shadow-md)', fontFamily: 'var(--font-sans)', fontSize: 13, fontWeight: 600,
      display: 'flex', alignItems: 'center', gap: 10, maxWidth: 'calc(100vw - 36px)',
    }}>
      <Icon name="alert-circle" size={15} color="var(--gold-400)" />
      {t}
      <button onClick={() => store.dismissToast()} style={{ border: 'none', background: 'transparent', color: 'inherit', cursor: 'pointer', opacity: 0.7, padding: 0, display: 'inline-flex' }}>
        <Icon name="x" size={14} />
      </button>
    </div>
  );
}

function BetsuApp() {
  const s = useStore(store);
  const [tab, setTab] = _appS('performance');

  _appE(() => { store.load(); }, []);

  if (!s.loaded()) return <LoadingShell />;

  let screen;
  if (tab === 'performance') screen = <PerformanceScreen store={s} variant="editorial" />;
  else if (tab === 'today') screen = <TodayScreen store={s} variant="editorial" />;
  else screen = <AllBetsList store={s} />;

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--bg-page)', fontFamily: 'var(--font-sans)', color: 'var(--text-primary)' }}>
      <AppHeader store={s} />
      {s.error() ? <ErrorBanner msg={s.error()} /> : null}
      <main style={{ flex: 1, overflowY: 'auto', WebkitOverflowScrolling: 'touch', padding: '18px 18px 26px' }}>
        {screen}
      </main>
      <BottomTabBar tab={tab} setTab={setTab} store={s} variant="editorial" />
      <ToastHost store={s} />
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('betsu-root')).render(<BetsuApp />);
