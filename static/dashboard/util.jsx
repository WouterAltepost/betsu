// betsu dashboard redesign — shared utilities (Icon, formatters, tweak context).
const { useState, useEffect, useRef, useMemo, createContext, useContext } = React;

// Lucide icon helper — stroke icons only, per the design system.
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

function fmtSigned(n, suffix = '', dp = 2) {
  if (n == null) return '—';
  return `${n >= 0 ? '+' : ''}${n.toFixed(dp)}${suffix}`;
}

// Shared content width so the Header, all three tabs, and the Today main never
// drift apart. Tunable; the user eyeballs this on the live deploy.
const CONTENT_MAX = 1280;

// Tweak context: layout direction, gradient intensity, density.
const TweakCtx = createContext({ layout: 'editorial', gradient: 'balanced', density: 'comfortable' });
const useTw = () => useContext(TweakCtx);

// density helpers
function dens(tw, comfy, compact) { return tw.density === 'compact' ? compact : comfy; }

Object.assign(window, { Icon, fmtSigned, TweakCtx, useTw, dens, CONTENT_MAX });
