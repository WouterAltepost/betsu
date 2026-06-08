/* betsu mobile — shared utilities: Lucide Icon helper + EUR/percent formatters. */
const { useState, useEffect, useRef, useMemo } = React;

// Lucide icon — stroke icons only, per the design system.
function Icon({ name, size = 18, color = 'currentColor', strokeWidth = 1.75, style = {} }) {
  const ref = useRef(null);
  useEffect(() => {
    if (window.lucide && ref.current) {
      ref.current.innerHTML = '';
      const el = document.createElement('i');
      el.setAttribute('data-lucide', name);
      ref.current.appendChild(el);
      window.lucide.createIcons({ attrs: { width: size, height: size, stroke: color, 'stroke-width': strokeWidth }, nodes: [el] });
    }
  }, [name, size, color, strokeWidth]);
  return <span ref={ref} style={{ display: 'inline-flex', width: size, height: size, ...style }} />;
}

// ---- EUR formatters (whole-platform currency) ----
function eur(n) { return '€' + Math.round(Math.abs(n)).toLocaleString('en-IE'); }
function eurSigned(n) { const r = Math.round(n); return (r >= 0 ? '+' : '−') + '€' + Math.abs(r).toLocaleString('en-IE'); }
function pct(n, signed = false, dp = 1) { const v = (signed && n >= 0 ? '+' : n < 0 ? '−' : '') + Math.abs(n).toFixed(dp); return v + '%'; }

// ISO 'YYYY-MM-DD' -> '8 Jun'
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
function fmtDate(isoStr) {
  if (!isoStr) return '';
  const [, m, d] = isoStr.split('-');
  return `${parseInt(d, 10)} ${MONTHS[parseInt(m, 10) - 1]}`;
}

Object.assign(window, { Icon, eur, eurSigned, pct, fmtDate });
