// betsu — three layout directions for the Performance view. Each derives its
// numbers from the live store and passes them down.
const { useMemo: _lum } = React;

function CalNote() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginTop: 12, flexWrap: 'wrap' }}>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 11.5, color: 'var(--text-muted)' }}>
        <span style={{ width: 18, height: 0, borderTop: '1.5px dashed var(--warm-400)' }} /> perfectly calibrated
      </span>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 11.5, color: 'var(--text-muted)' }}>
        <span style={{ width: 11, height: 11, borderRadius: '50%', background: 'rgba(247,148,30,0.85)', border: '2px solid #fff', boxShadow: '0 0 0 1px var(--border)' }} /> betsu · size = sample
      </span>
    </div>
  );
}

const calSub = 'model probability vs realized hit-rate';
const pnlSub = 'cumulative net profit · settled bets';
const mktSub = 'return on stake by market';

// ============ A · EDITORIAL ============
function LayoutEditorial({ perf }) {
  const tw = useTw();
  return (
    <div style={{ maxWidth: 1040, margin: '0 auto', padding: '26px 28px 80px' }}>
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 34, fontFamily: 'var(--font-display)', fontWeight: 800, letterSpacing: '-0.02em' }}>performance</h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: 14, marginTop: 4 }}>Profit &amp; loss on the bets you've actually placed, in €. Judged on calibration &amp; ROI over the tournament.</p>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: dens(tw, 22, 16) }}>
        <VerdictHero perf={perf} variant="band" />
        <StatStrip perf={perf} columns={dens(tw, 5, 6)} />
        <Panel title="Cumulative profit" sub={pnlSub} icon="trending-up">
          <PnlChart curve={perf.curve} height={dens(tw, 250, 210)} />
        </Panel>
        <div style={{ display: 'grid', gridTemplateColumns: '1.05fr 0.95fr', gap: dens(tw, 22, 16) }}>
          <Panel title="Calibration" sub={calSub} icon="target">
            <CalibrationChart bins={perf.bins} height={250} />
            <CalNote />
          </Panel>
          <Panel title="ROI by market" sub={mktSub} icon="layers">
            <div style={{ paddingTop: 8 }}><MarketBars rows={perf.byMarket} /></div>
          </Panel>
        </div>
        <BetLog />
      </div>
    </div>
  );
}

// ============ B · COCKPIT ============
function LayoutCockpit({ perf }) {
  const tw = useTw();
  const s = perf.summary;
  return (
    <div style={{ maxWidth: 1180, margin: '0 auto', padding: '22px 28px 72px' }}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
        <h1 style={{ fontSize: 27, fontFamily: 'var(--font-display)', fontWeight: 800, letterSpacing: '-0.02em' }}>performance</h1>
        <span style={{ fontSize: 12.5, color: 'var(--text-muted)' }}>{s.placedCount} placed · {s.settled} settled · {s.pending} pending</span>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
        <StatStrip perf={perf} columns={6} />
        <div style={{ display: 'grid', gridTemplateColumns: '1.6fr 1fr', gap: 14, alignItems: 'stretch' }}>
          <Panel title="Cumulative profit" sub={pnlSub} icon="trending-up">
            <PnlChart curve={perf.curve} height={300} />
          </Panel>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <Panel title="ROI by market" sub={mktSub} icon="layers" style={{ flex: 'none' }}>
              <div style={{ paddingTop: 4 }}><MarketBars rows={perf.byMarket} compact /></div>
            </Panel>
            <Panel title="Calibration" sub="model% vs actual" icon="target" style={{ flex: 1 }}>
              <CalibrationChart bins={perf.bins} height={180} />
            </Panel>
          </div>
        </div>
        <BetLog />
      </div>
    </div>
  );
}

// ============ C · BRAND-LED ============
function LayoutBrand({ perf }) {
  const tw = useTw();
  const s = perf.summary;
  const tiles = [
    { label: 'Hit rate', value: s.settled ? `${s.hit_rate}%` : '—', sub: 'of settled', icon: 'target' },
    { label: 'Avg edge', value: `+${s.avg_edge}%`, tone: 'gold', sub: 'at entry', icon: 'gauge' },
    { label: 'Best bet', value: s.settled ? eurSigned(s.best) : '€0', tone: 'pos', sub: 'single return', icon: 'flame' },
    { label: 'At risk', value: eur(s.openExposure), tone: 'muted', sub: `${s.pending} pending`, icon: 'clock' },
  ];
  return (
    <div style={{ maxWidth: 1080, margin: '0 auto', padding: '30px 28px 90px' }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: dens(tw, 26, 18) }}>
        <VerdictHero perf={perf} variant="big" />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: dens(tw, 14, 10) }}>
          {tiles.map((it, i) => (
            <StatTile key={i} label={it.label} value={it.value} tone={it.tone} sub={it.sub} icon={<Icon name={it.icon} size={16} color="var(--warm-400)" />} />
          ))}
        </div>
        <Panel title="Cumulative profit" sub={pnlSub} icon="trending-up" pad={dens(tw, 26, 18)}>
          <PnlChart curve={perf.curve} height={dens(tw, 300, 240)} />
        </Panel>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: dens(tw, 22, 16) }}>
          <Panel title="Calibration" sub={calSub} icon="target">
            <CalibrationChart bins={perf.bins} height={260} />
            <CalNote />
          </Panel>
          <Panel title="ROI by market" sub={mktSub} icon="layers">
            <div style={{ paddingTop: 8 }}><MarketBars rows={perf.byMarket} /></div>
          </Panel>
        </div>
        <BetLog />
      </div>
    </div>
  );
}

function Overview() {
  const tw = useTw();
  const store = useBets();
  const perf = _lum(() => computePerf(store.get()), [store.get()]);
  if (tw.layout === 'cockpit') return <LayoutCockpit perf={perf} />;
  if (tw.layout === 'brand') return <LayoutBrand perf={perf} />;
  return <LayoutEditorial perf={perf} />;
}

Object.assign(window, { Overview, LayoutEditorial, LayoutCockpit, LayoutBrand });
