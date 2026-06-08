// betsu dashboard — app shell. The design is fixed (editorial layout, balanced
// gradient, comfortable density); the tweak panel from the prototype is gone.
// Data comes from the server API via the store; the app shows a loading shell
// until the first /api/bets fetch resolves, an error banner if it fails, and a
// toast when a write is reverted.

const FIXED_TW = { layout: 'editorial', gradient: 'balanced', density: 'comfortable' };

function LoadingShell() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontFamily: 'var(--font-sans)', fontSize: 14, gap: 10 }}>
      <Icon name="loader" size={18} color="var(--warm-400)" />
      loading your bets…
    </div>
  );
}

function ErrorBanner({ msg }) {
  return (
    <div style={{ maxWidth: 1180, margin: '12px auto 0', padding: '0 28px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, background: 'var(--loss-bg)', border: '1px solid var(--loss)', color: 'var(--loss)', borderRadius: 'var(--radius-md)', padding: '10px 14px', fontSize: 13.5, fontWeight: 600 }}>
        <Icon name="alert-triangle" size={16} color="var(--loss)" />
        Store unreachable: {msg}
      </div>
    </div>
  );
}

function ToastHost() {
  const store = useBets();
  const t = store.toast();
  if (!t) return null;
  return (
    <div style={{ position: 'fixed', bottom: 22, left: '50%', transform: 'translateX(-50%)', zIndex: 50,
      background: 'var(--warm-900)', color: 'var(--bg-surface)', padding: '10px 16px', borderRadius: 'var(--radius-full)',
      boxShadow: 'var(--shadow-md)', fontFamily: 'var(--font-sans)', fontSize: 13, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 10 }}>
      <Icon name="alert-circle" size={15} color="var(--gold-400)" />
      {t}
      <button onClick={() => store.dismissToast()} style={{ border: 'none', background: 'transparent', color: 'inherit', cursor: 'pointer', opacity: 0.7, padding: 0, display: 'inline-flex' }}>
        <Icon name="x" size={14} />
      </button>
    </div>
  );
}

function App() {
  const store = useBets();
  const [tab, setTab] = React.useState('overview');

  React.useEffect(() => { store.load(); }, []);

  if (!store.loaded()) return <LoadingShell />;

  return (
    <TweakCtx.Provider value={FIXED_TW}>
      <div style={{ minHeight: '100vh' }}>
        {store.error() ? <ErrorBanner msg={store.error()} /> : null}
        <Header tab={tab} setTab={setTab} />
        {tab === 'overview' && <Overview />}
        {tab === 'allbets' && <AllBets />}
        {tab === 'today' && <main style={{ maxWidth: 1040, margin: '0 auto', padding: '28px 28px 80px' }}><TodayView /></main>}
      </div>
      <ToastHost />
    </TweakCtx.Provider>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
