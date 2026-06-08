/* betsu mobile — data visualisations (Chart.js + CSS bars). Values are EUR.
 * Adapted from the repo's charts.jsx, tuned for a ~360px phone column.        */
const { useEffect: _ue, useRef: _ur } = React;

const M_GOLD = '#F7941E', M_INK = '#1A1611', M_GRID = '#EDE7DD', M_MUTE = '#A99E8E';

function ChartEmpty({ height, label }) {
  return (
    <div style={{ height, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 12.5, textAlign: 'center', flexDirection: 'column', gap: 8, padding: '0 20px' }}>
      <Icon name="inbox" size={20} color="var(--warm-300)" />
      <span>{label}</span>
    </div>
  );
}

// ---------- Cumulative P&L curve (€) ----------
function PnlChart({ curve, height = 200 }) {
  const ref = _ur(null), chart = _ur(null);
  _ue(() => {
    if (!window.Chart || !ref.current || !curve.length) return;
    if (chart.current) chart.current.destroy();
    const ctx = ref.current.getContext('2d');
    const grad = ctx.createLinearGradient(0, 0, 0, height);
    grad.addColorStop(0, 'rgba(247,148,30,0.22)');
    grad.addColorStop(1, 'rgba(247,148,30,0)');
    chart.current = new window.Chart(ctx, {
      type: 'line',
      data: {
        labels: curve.map(c => fmtDate(c.label)),
        datasets: [{
          data: curve.map(c => c.value), borderColor: M_GOLD, backgroundColor: grad, fill: true,
          tension: 0.34, pointRadius: 0, pointHoverRadius: 5,
          pointHoverBackgroundColor: M_GOLD, pointHoverBorderColor: '#fff', pointHoverBorderWidth: 2,
          borderWidth: 2.5,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false, animation: { duration: 600 },
        interaction: { intersect: false, mode: 'index' },
        plugins: {
          legend: { display: false },
          tooltip: {
            backgroundColor: M_INK, padding: 9, cornerRadius: 8, displayColors: false,
            titleFont: { family: 'Inter', weight: '600', size: 12 }, bodyFont: { family: 'Inter', size: 12 },
            callbacks: { title: i => i[0].label, label: i => `${i.parsed.y >= 0 ? '+' : '−'}€${Math.abs(Math.round(i.parsed.y))} cumulative` },
          },
        },
        scales: {
          x: { grid: { display: false }, ticks: { color: M_MUTE, font: { family: 'Inter', size: 10 }, maxTicksLimit: 5, autoSkip: true }, border: { display: false } },
          y: { grid: { color: M_GRID }, ticks: { color: M_MUTE, font: { family: 'Inter', size: 10 }, maxTicksLimit: 5, callback: v => `${v >= 0 ? '' : '−'}€${Math.abs(v)}` }, border: { display: false } },
        },
      },
    });
    return () => chart.current && chart.current.destroy();
  }, [height, JSON.stringify(curve)]);
  if (!curve.length) return <ChartEmpty height={height} label="No settled bets yet — place a bet and settle it to build the curve." />;
  return <div style={{ position: 'relative', height, width: '100%' }}><canvas ref={ref} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }} /></div>;
}

// ---------- Calibration plot ----------
function CalibrationChart({ bins, height = 220 }) {
  const ref = _ur(null), chart = _ur(null);
  _ue(() => {
    if (!window.Chart || !ref.current || !bins.length) return;
    if (chart.current) chart.current.destroy();
    const ctx = ref.current.getContext('2d');
    const pts = bins.map(b => ({ x: +(b.predicted * 100).toFixed(1), y: +(b.actual * 100).toFixed(1), n: b.n }));
    const maxN = Math.max(...bins.map(b => b.n), 1);
    chart.current = new window.Chart(ctx, {
      data: {
        datasets: [
          { type: 'line', label: 'perfect', data: [{ x: 15, y: 15 }, { x: 95, y: 95 }], borderColor: 'rgba(169,158,142,0.55)', borderDash: [5, 5], borderWidth: 1.5, pointRadius: 0, fill: false, tension: 0 },
          { type: 'scatter', label: 'betsu', data: pts, backgroundColor: 'rgba(247,148,30,0.85)', borderColor: '#fff', borderWidth: 2, pointRadius: c => 6 + (c.raw.n / maxN) * 9, pointHoverRadius: c => 8 + (c.raw.n / maxN) * 9 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false, animation: { duration: 500 },
        plugins: {
          legend: { display: false },
          tooltip: { backgroundColor: M_INK, padding: 9, cornerRadius: 8, displayColors: false, callbacks: { title: () => '', label: c => [`model ${c.raw.x.toFixed(0)}%  →  actual ${c.raw.y.toFixed(0)}%`, `${c.raw.n} settled in bin`] }, titleFont: { family: 'Inter', size: 12 }, bodyFont: { family: 'Inter', size: 12 } },
        },
        scales: {
          x: { type: 'linear', min: 15, max: 95, title: { display: true, text: 'model probability', color: M_MUTE, font: { family: 'Inter', size: 10, weight: '600' } }, grid: { color: M_GRID }, ticks: { color: M_MUTE, font: { family: 'Inter', size: 10 }, callback: v => `${v}%`, stepSize: 20 }, border: { display: false } },
          y: { type: 'linear', min: 15, max: 95, title: { display: true, text: 'actual hit-rate', color: M_MUTE, font: { family: 'Inter', size: 10, weight: '600' } }, grid: { color: M_GRID }, ticks: { color: M_MUTE, font: { family: 'Inter', size: 10 }, callback: v => `${v}%`, stepSize: 20 }, border: { display: false } },
        },
      },
    });
    return () => chart.current && chart.current.destroy();
  }, [height, JSON.stringify(bins)]);
  if (!bins.length) return <ChartEmpty height={height} label="Settle a few placed bets to see how calibrated the model is." />;
  return <div style={{ position: 'relative', height, width: '100%' }}><canvas ref={ref} style={{ position: 'absolute', inset: 0, width: '100%', height: '100%' }} /></div>;
}

// ---------- ROI by market — CSS diverging bars (€-based ROI) ----------
function MarketBars({ rows }) {
  if (!rows.length) return <div style={{ padding: '16px 0', color: 'var(--text-muted)', fontSize: 13 }}>No settled bets by market yet.</div>;
  const maxAbs = Math.max(...rows.map(r => Math.abs(r.roi)), 10);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {rows.map((r) => {
        const pos = r.roi >= 0;
        const w = (Math.abs(r.roi) / maxAbs) * 50;
        return (
          <div key={r.market} style={{ display: 'grid', gridTemplateColumns: '76px 1fr 54px', alignItems: 'center', gap: 10 }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <span style={{ fontFamily: 'var(--font-sans)', fontWeight: 600, fontSize: 12.5, color: 'var(--text-primary)' }}>{r.market}</span>
              <span style={{ fontSize: 10.5, color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums' }}>{r.n} · {r.hit}%</span>
            </div>
            <div style={{ position: 'relative', height: 20, background: 'var(--bg-inset)', borderRadius: 'var(--radius-full)' }}>
              <div style={{ position: 'absolute', left: '50%', top: -3, bottom: -3, width: 1, background: 'var(--border-strong)' }} />
              <div style={{ position: 'absolute', top: 0, bottom: 0, height: 20, left: pos ? '50%' : `${50 - w}%`, width: `${w}%`, background: pos ? 'var(--brand-gradient)' : 'var(--loss)', borderRadius: 'var(--radius-full)', transition: 'width var(--dur-slow) var(--ease-out)' }} />
            </div>
            <span style={{ textAlign: 'right', fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 14, fontVariantNumeric: 'tabular-nums', color: pos ? 'var(--win)' : 'var(--loss)' }}>
              {pct(r.roi, true, 0)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

Object.assign(window, { PnlChart, CalibrationChart, MarketBars });
