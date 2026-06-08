// betsu — the Performance view (editorial layout). Two clearly-separated tracks:
//   "Your money"  — real € P&L on the bets you actually placed (the headline).
//   "Model"       — calibration + paper ROI over ALL suggestions, placed or not;
//                   this is what betsu is judged on. Don't bury the distinction.
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

const calSub = 'model probability vs realized hit-rate · all settled suggestions';
const pnlSub = 'cumulative net profit · settled placed bets';
const mktSub = 'return on stake by market · placed bets';

// Section divider — keeps the "your money" vs "model" framing explicit.
function SectionLabel({ kicker, title, desc }) {
  return (
    <div style={{ marginTop: 10 }}>
      <span style={{ fontFamily: 'var(--font-sans)', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--gold-600)' }}>{kicker}</span>
      <h2 style={{ fontSize: 22, fontFamily: 'var(--font-display)', fontWeight: 800, letterSpacing: '-0.02em', marginTop: 2 }}>{title}</h2>
      {desc ? <p style={{ color: 'var(--text-secondary)', fontSize: 13.5, marginTop: 3, maxWidth: 620 }}>{desc}</p> : null}
    </div>
  );
}

// ---- Model performance (all suggestions, paper) ----
function ModelStat({ label, value, sub, tone }) {
  const c = tone === 'pos' ? 'var(--win)' : tone === 'neg' ? 'var(--loss)' : 'var(--text-primary)';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3, background: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '12px 14px' }}>
      <span style={{ fontSize: 10.5, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-muted)' }}>{label}</span>
      <span style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 22, letterSpacing: '-0.02em', fontVariantNumeric: 'tabular-nums', color: c }}>{value}</span>
      {sub ? <span style={{ fontSize: 11.5, color: 'var(--text-muted)' }}>{sub}</span> : null}
    </div>
  );
}

function ModelPerfPanel() {
  const mp = computeModelPerf();
  const tiles = [
    { label: 'Suggestions', value: mp.suggestions, sub: `${mp.settled} settled` },
    { label: 'Paper ROI', value: mp.settled ? pct(mp.roi_units, true) : '—', sub: 'flat 1u / bet', tone: mp.roi_units >= 0 ? 'pos' : 'neg' },
    { label: 'Record', value: `${mp.wins}–${mp.losses}`, sub: mp.settled ? `${mp.hit_rate}% hit` : 'none settled' },
    { label: 'Avg edge', value: `+${mp.avg_edge}%`, sub: 'at entry' },
  ];
  return (
    <Panel title="Model — all suggestions (paper)" sub="calibration & paper ROI vs the closing line, across every bet betsu flagged — not just the ones you placed" icon="activity">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 18 }}>
        {tiles.map((t, i) => <ModelStat key={i} {...t} />)}
      </div>
      <CalibrationChart bins={mp.bins} height={250} />
      <CalNote />
    </Panel>
  );
}

// ============ Editorial layout ============
function LayoutEditorial({ perf }) {
  const tw = useTw();
  return (
    <div style={{ maxWidth: 1040, margin: '0 auto', padding: '26px 28px 80px' }}>
      <div style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 34, fontFamily: 'var(--font-display)', fontWeight: 800, letterSpacing: '-0.02em' }}>performance</h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: 14, marginTop: 4 }}>Your real € P&amp;L on the bets you placed, plus how betsu's model is calibrating over every suggestion.</p>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: dens(tw, 22, 16) }}>
        <SectionLabel kicker="Your money" title="Real € profit & loss" desc="On the bets you actually placed, in euros. The headline betsu wants you to feel." />
        <VerdictHero perf={perf} variant="band" />
        <StatStrip perf={perf} columns={dens(tw, 5, 6)} />
        <Panel title="Cumulative profit" sub={pnlSub} icon="trending-up">
          <PnlChart curve={perf.curve} height={dens(tw, 250, 210)} />
        </Panel>
        <Panel title="ROI by market" sub={mktSub} icon="layers">
          <div style={{ paddingTop: 8 }}><MarketBars rows={perf.byMarket} /></div>
        </Panel>
        <BetLog />

        <SectionLabel kicker="Model" title="Calibration & paper ROI" desc="Over all suggestions, placed or not — flat 1-unit paper stakes. This is what betsu is judged on over the tournament, independent of what you chose to back." />
        <ModelPerfPanel />
      </div>
    </div>
  );
}

function Overview() {
  const store = useBets();
  const perf = _lum(() => computePerf(store.get()), [store.get()]);
  return <LayoutEditorial perf={perf} />;
}

Object.assign(window, { Overview, LayoutEditorial, ModelPerfPanel, SectionLabel });
