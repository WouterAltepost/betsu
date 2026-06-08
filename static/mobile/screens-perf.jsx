/* betsu mobile — Performance screen. Two clearly-separated tracks:
 *   "Your money" — real € P&L on the bets you placed (the headline).
 *   "Model"      — calibration + paper ROI over ALL suggestions (what betsu is
 *                  judged on). The hero treatment differs by direction.        */

function HeroStat({ label, value, tone, onGrad = true }) {
  const c = tone === 'pos' ? 'var(--green-600)' : tone === 'neg' ? 'var(--red-600)' : 'var(--warm-900)';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
      <span style={{ fontFamily: 'var(--font-sans)', fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'rgba(26,22,17,0.55)' }}>{label}</span>
      <span style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 22, letterSpacing: '-0.02em', lineHeight: 1, fontVariantNumeric: 'tabular-nums', color: c, whiteSpace: 'nowrap' }}>{value}</span>
    </div>
  );
}

function VerdictHero({ perf, variant }) {
  const s = perf.summary;
  const pos = s.profit >= 0;
  const none = s.settled === 0;
  const bold = variant === 'bold';
  const stats = [
    { label: 'ROI', value: none ? '—' : pct(s.roi, true), tone: pos ? 'pos' : 'neg' },
    { label: 'Record', value: `${s.wins}–${s.losses}` },
    { label: 'Hit rate', value: none ? '—' : `${s.hit_rate}%` },
  ];
  return (
    <div style={{
      position: 'relative', overflow: 'hidden', background: 'var(--brand-gradient)',
      borderRadius: 'var(--radius-2xl)', boxShadow: bold ? 'var(--shadow-gold)' : 'var(--shadow-md)',
      padding: bold ? '24px 22px 18px' : '22px 20px',
    }}>
      <img src={LOGO_SRC} alt="" style={{ position: 'absolute', right: bold ? -34 : -30, top: '46%', transform: 'translateY(-50%)', width: bold ? 200 : 168, opacity: 0.22, pointerEvents: 'none' }} />
      <div style={{ position: 'relative' }}>
        <span style={{ fontFamily: 'var(--font-sans)', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'rgba(26,22,17,0.62)' }}>
          net profit · {s.settled} settled {s.settled === 1 ? 'bet' : 'bets'}
        </span>
        <div style={{ marginTop: 5 }}>
          <span style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: bold ? 60 : 50, lineHeight: 0.9, letterSpacing: '-0.03em', fontVariantNumeric: 'tabular-nums', color: 'var(--warm-900)', whiteSpace: 'nowrap' }}>
            {none ? '€0' : eurSigned(s.profit)}
          </span>
        </div>
        <p style={{ marginTop: 10, fontSize: 13, color: 'rgba(26,22,17,0.74)', fontWeight: 500, maxWidth: 270, lineHeight: 1.4 }}>
          {none
            ? 'No settled bets yet. Place a few of today’s picks, set your stake, and settle results to start tracking.'
            : pos
              ? `Up across ${s.placedCount} placed bets — ${s.wins}–${s.losses} on ${eur(s.totalStaked)} staked, +${s.avg_edge}% average edge.`
              : `Down across ${s.placedCount} placed bets — ${s.wins}–${s.losses}. Judged over the tournament, not any one day.`}
        </p>
        <div style={{
          marginTop: 16, display: 'grid', gridTemplateColumns: '1fr 1fr 1fr',
          background: bold ? 'rgba(255,255,255,0.32)' : 'transparent',
          borderRadius: bold ? 'var(--radius-md)' : 0, padding: bold ? '12px 14px' : 0,
        }}>
          {stats.map((st, i) => (
            <div key={st.label} style={{ borderLeft: i > 0 && bold ? '1px solid rgba(26,22,17,0.14)' : 'none', paddingLeft: i > 0 && bold ? 14 : 0 }}>
              <HeroStat {...st} />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function StatGrid({ perf }) {
  const s = perf.summary;
  const items = [
    { label: 'Net profit', value: s.settled ? eurSigned(s.profit) : '€0', tone: s.profit >= 0 ? 'pos' : 'neg', sub: 'settled', icon: 'coins' },
    { label: 'ROI', value: s.settled ? pct(s.roi, true) : '—', tone: s.roi >= 0 ? 'pos' : 'neg', sub: 'on turnover', icon: 'trending-up' },
    { label: 'Staked', value: eur(s.totalStaked), sub: `${s.placedCount} placed`, icon: 'layers' },
    { label: 'Pending', value: s.pending, tone: 'muted', sub: `${eur(s.openExposure)} at risk`, icon: 'clock' },
  ];
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
      {items.map((it) => (
        <StatTile key={it.label} label={it.label} value={it.value} tone={it.tone} sub={it.sub} icon={<Icon name={it.icon} size={15} color="var(--warm-400)" />} />
      ))}
    </div>
  );
}

function SectionLabel({ kicker, title, desc }) {
  return (
    <div style={{ marginTop: 6 }}>
      <span style={{ fontFamily: 'var(--font-sans)', fontSize: 10.5, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.07em', color: 'var(--gold-600)' }}>{kicker}</span>
      <h2 style={{ fontSize: 19, fontFamily: 'var(--font-display)', fontWeight: 800, letterSpacing: '-0.02em', marginTop: 2 }}>{title}</h2>
      {desc ? <p style={{ color: 'var(--text-secondary)', fontSize: 12.5, marginTop: 4, lineHeight: 1.4 }}>{desc}</p> : null}
    </div>
  );
}

function ModelStat({ label, value, sub, tone }) {
  const c = tone === 'pos' ? 'var(--win)' : tone === 'neg' ? 'var(--loss)' : 'var(--text-primary)';
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 2, background: 'var(--bg-subtle)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '10px 12px' }}>
      <span style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-muted)' }}>{label}</span>
      <span style={{ fontFamily: 'var(--font-display)', fontWeight: 800, fontSize: 19, letterSpacing: '-0.02em', fontVariantNumeric: 'tabular-nums', color: c }}>{value}</span>
      {sub ? <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>{sub}</span> : null}
    </div>
  );
}

function ModelPerfPanel({ store }) {
  const mp = store.computeModelPerf();
  const tiles = [
    { label: 'Suggestions', value: mp.suggestions, sub: `${mp.settled} settled` },
    { label: 'Paper ROI', value: mp.settled ? pct(mp.roi_units, true) : '—', sub: 'flat 1u / bet', tone: mp.roi_units >= 0 ? 'pos' : 'neg' },
    { label: 'Record', value: `${mp.wins}–${mp.losses}`, sub: mp.settled ? `${mp.hit_rate}% hit` : 'none settled' },
    { label: 'Avg edge', value: `+${mp.avg_edge}%`, sub: 'at entry' },
  ];
  return (
    <Panel title="How betsu’s predictions are doing" sub="Every bet it flagged, win or lose, at a flat stake." icon="activity">
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 9, marginBottom: 16 }}>
        {tiles.map((t) => <ModelStat key={t.label} {...t} />)}
      </div>
      <CalibrationChart bins={mp.bins} height={230} />
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginTop: 10, flexWrap: 'wrap' }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-muted)' }}>
          <span style={{ width: 16, height: 0, borderTop: '1.5px dashed var(--warm-400)' }} /> perfectly calibrated
        </span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 11, color: 'var(--text-muted)' }}>
          <span style={{ width: 11, height: 11, borderRadius: '50%', background: 'rgba(247,148,30,0.85)', border: '2px solid #fff', boxShadow: '0 0 0 1px var(--border)' }} /> betsu · size = sample
        </span>
      </div>
      <p style={{ fontSize: 11.5, color: 'var(--text-muted)', marginTop: 10, lineHeight: 1.5 }}>
        When betsu says “70%”, does that happen about 70% of the time? Points on the diagonal mean perfectly calibrated.
      </p>
    </Panel>
  );
}

function PerformanceScreen({ store, variant }) {
  const perf = store.computePerf();
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <ScreenTitle title="performance" sub="Your real € P&L on the bets you placed, plus how betsu’s model is calibrating over every suggestion." />
      <SectionLabel kicker="Your money" title="Real € profit & loss" desc="On the bets you actually placed, in euros." />
      <VerdictHero perf={perf} variant={variant} />
      <StatGrid perf={perf} />
      <Panel title="Cumulative profit" sub="net profit · settled placed bets" icon="trending-up">
        <PnlChart curve={perf.curve} height={190} />
      </Panel>
      <Panel title="ROI by market" sub="return on stake · placed bets" icon="layers">
        <div style={{ paddingTop: 4 }}><MarketBars rows={perf.byMarket} /></div>
      </Panel>
      <SectionLabel kicker="Model" title="Does it beat the bookmakers?" desc="Measured over every suggestion betsu flagged, not just the bets you placed." />
      <ModelPerfPanel store={store} />
      <p style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: 12, fontStyle: 'italic', padding: '2px 0' }}>
        Paper unless you choose to back it. Bet responsibly.
      </p>
    </div>
  );
}

Object.assign(window, { PerformanceScreen, VerdictHero, StatGrid, ModelPerfPanel, SectionLabel });
