// betsu dashboard redesign — app shell + tweak wiring.

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "layout": "editorial",
  "gradient": "balanced",
  "density": "comfortable"
}/*EDITMODE-END*/;

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [tab, setTab] = React.useState('overview');
  const tw = { layout: t.layout, gradient: t.gradient, density: t.density };

  return (
    <TweakCtx.Provider value={tw}>
      <div style={{ minHeight: '100vh' }}>
        <Header tab={tab} setTab={setTab} />
        {tab === 'overview' && <Overview />}
        {tab === 'allbets' && <AllBets />}
        {tab === 'today' && <main style={{ maxWidth: 1040, margin: '0 auto', padding: '28px 28px 80px' }}><TodayView /></main>}
      </div>

      <TweaksPanel>
        <TweakSection label="Layout direction" />
        <TweakRadio label="Direction" value={t.layout}
          options={[
            { value: 'editorial', label: 'Editorial' },
            { value: 'cockpit', label: 'Cockpit' },
            { value: 'brand', label: 'Brand-led' },
          ]}
          onChange={(v) => setTweak('layout', v)} />
        <div style={{ fontSize: 11.5, color: 'var(--text-muted)', lineHeight: 1.45, padding: '2px 2px 4px' }}>
          {t.layout === 'editorial' && 'Calm centered column — verdict band, then charts stacked with generous rhythm.'}
          {t.layout === 'cockpit' && 'Dense bento — six-tile strip, large P&L with calibration + market stacked beside it.'}
          {t.layout === 'brand' && 'Gradient-forward — a big net-profit hero leads, bold display type throughout.'}
        </div>

        <TweakSection label="Brand gradient" />
        <TweakRadio label="Intensity" value={t.gradient}
          options={[
            { value: 'subtle', label: 'Subtle' },
            { value: 'balanced', label: 'Balanced' },
            { value: 'bold', label: 'Bold' },
          ]}
          onChange={(v) => setTweak('gradient', v)} />

        <TweakSection label="Density" />
        <TweakRadio label="Spacing" value={t.density}
          options={[
            { value: 'comfortable', label: 'Comfortable' },
            { value: 'compact', label: 'Compact' },
          ]}
          onChange={(v) => setTweak('density', v)} />
      </TweaksPanel>
    </TweakCtx.Provider>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
