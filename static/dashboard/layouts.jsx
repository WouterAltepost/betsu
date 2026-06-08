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

const pnlSub = 'cumulative net profit · settled placed bets';
const mktSub = 'return on stake by market · placed bets';

// Below this many settled suggestions the calibration scatter is too sparse to
// mean anything, so we show a placeholder instead of a near-empty plot.
const MODEL_CAL_MIN = 20;

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

// Shown below the threshold instead of a near-empty scatter.
function CalPlaceholder({ settled }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      gap: 8, textAlign: 'center', minHeight: 180, padding: '24px 16px',
      background: 'var(--bg-subtle)', border: '1px dashed var(--border-strong)', borderRadius: 'var(--radius-md)',
    }}>
      <Icon name="scatter-chart" size={22} color="var(--warm-400)" />
      <p style={{ fontSize: 13.5, fontWeight: 600, color: 'var(--text-secondary)', maxWidth: 420 }}>
        Calibration needs a larger sample to mean anything.
      </p>
      <p style={{ fontSize: 12.5, color: 'var(--text-muted)', maxWidth: 420 }}>
        {settled} settled so far. This chart appears once {MODEL_CAL_MIN} bets have settled, then shows whether a "70%" call really wins about 70% of the time.
      </p>
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
  const enoughForCal = mp.settled >= MODEL_CAL_MIN;
  return (
    <Panel title="How betsu's predictions are doing" sub="Every bet betsu flagged, win or lose, as if you backed them all at a flat stake. The honest scoreboard for the model, separate from what you chose to place." icon="activity">
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 18 }}>
        {tiles.map((t, i) => <ModelStat key={i} {...t} />)}
      </div>
      {enoughForCal ? (
        <>
          <CalibrationChart bins={mp.bins} height={250} />
          <CalNote />
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 12, lineHeight: 1.5 }}>
            Calibration asks: when betsu says "70%", does that happen about 70% of the time? Points sitting on the diagonal line mean perfectly calibrated.
          </p>
        </>
      ) : (
        <CalPlaceholder settled={mp.settled} />
      )}
    </Panel>
  );
}

// ============ Editorial layout ============
function LayoutEditorial({ perf }) {
  const tw = useTw();
  return (
    <div style={{ maxWidth: CONTENT_MAX, margin: '0 auto', padding: '26px 20px 80px' }}>
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

        <SectionLabel kicker="Model" title="Does the strategy beat the bookmakers?" desc="Two simple questions. Does betsu make money against the book (Paper ROI), and are its probabilities honest (Calibration). Measured over every suggestion it flagged, not just the bets you placed." />
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
