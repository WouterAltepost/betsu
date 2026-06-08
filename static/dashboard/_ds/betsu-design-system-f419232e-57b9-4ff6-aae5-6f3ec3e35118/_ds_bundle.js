/* @ds-bundle: {"format":3,"namespace":"BetsuDesignSystem_f41923","components":[{"name":"Badge","sourcePath":"components/core/Badge.jsx"},{"name":"Button","sourcePath":"components/core/Button.jsx"},{"name":"Card","sourcePath":"components/core/Card.jsx"},{"name":"Logo","sourcePath":"components/core/Logo.jsx"},{"name":"BetCard","sourcePath":"components/data/BetCard.jsx"},{"name":"StatTile","sourcePath":"components/data/StatTile.jsx"}],"sourceHashes":{"components/core/Badge.jsx":"b9c7ecd7c662","components/core/Button.jsx":"776490d7e049","components/core/Card.jsx":"59ce8fda1819","components/core/Logo.jsx":"8f0bd0ab2062","components/data/BetCard.jsx":"c7846fbf5544","components/data/StatTile.jsx":"09b12a1dee1a","ui_kits/dashboard/Dashboard.jsx":"7236496a6f3a","ui_kits/dashboard/data.js":"d111e6597f5f","ui_kits/telegram/Telegram.jsx":"3e9f91022778"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.BetsuDesignSystem_f41923 = window.BetsuDesignSystem_f41923 || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/core/Badge.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * betsu Badge / status pill. Result variants map to the win/loss/pending semantics.
 */
function Badge({
  children,
  variant = 'neutral',
  size = 'md',
  dot = false,
  style = {},
  ...rest
}) {
  const variants = {
    neutral: {
      background: 'var(--bg-subtle)',
      color: 'var(--text-secondary)'
    },
    win: {
      background: 'var(--win-bg)',
      color: 'var(--win)'
    },
    loss: {
      background: 'var(--loss-bg)',
      color: 'var(--loss)'
    },
    pending: {
      background: 'var(--pending-bg)',
      color: 'var(--amber-600)'
    },
    gold: {
      background: 'var(--gold-100)',
      color: 'var(--gold-700)'
    },
    outline: {
      background: 'transparent',
      color: 'var(--text-secondary)',
      boxShadow: 'inset 0 0 0 1px var(--border-strong)'
    }
  };
  const v = variants[variant] || variants.neutral;
  const sizes = {
    sm: {
      fontSize: 10.5,
      padding: '2px 8px',
      gap: 4,
      dot: 5
    },
    md: {
      fontSize: 12,
      padding: '3px 10px',
      gap: 5,
      dot: 6
    }
  };
  const s = sizes[size] || sizes.md;
  const dotColor = {
    win: 'var(--win)',
    loss: 'var(--loss)',
    pending: 'var(--pending)',
    gold: 'var(--gold-500)',
    neutral: 'var(--warm-400)',
    outline: 'var(--warm-400)'
  }[variant];
  return /*#__PURE__*/React.createElement("span", _extends({
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: s.gap,
      padding: s.padding,
      borderRadius: 'var(--radius-full)',
      fontFamily: 'var(--font-sans)',
      fontWeight: 600,
      fontSize: s.fontSize,
      lineHeight: 1.4,
      fontVariantNumeric: 'tabular-nums',
      whiteSpace: 'nowrap',
      ...v,
      ...style
    }
  }, rest), dot ? /*#__PURE__*/React.createElement("span", {
    style: {
      width: s.dot,
      height: s.dot,
      borderRadius: '50%',
      background: dotColor,
      flex: 'none'
    }
  }) : null, children);
}
Object.assign(__ds_scope, { Badge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Badge.jsx", error: String((e && e.message) || e) }); }

// components/core/Button.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
const {
  useState
} = React;

/**
 * betsu Button — primary is solid gold with dark ink (the signature look).
 */
function Button({
  children,
  variant = 'primary',
  size = 'md',
  icon = null,
  iconRight = null,
  fullWidth = false,
  disabled = false,
  onClick,
  type = 'button',
  style = {},
  ...rest
}) {
  const [hover, setHover] = useState(false);
  const [press, setPress] = useState(false);
  const sizes = {
    sm: {
      padding: '0 12px',
      height: 32,
      fontSize: 13,
      gap: 6,
      radius: 'var(--radius-sm)'
    },
    md: {
      padding: '0 16px',
      height: 40,
      fontSize: 14,
      gap: 8,
      radius: 'var(--radius-md)'
    },
    lg: {
      padding: '0 22px',
      height: 48,
      fontSize: 16,
      gap: 9,
      radius: 'var(--radius-md)'
    }
  };
  const s = sizes[size] || sizes.md;
  const variants = {
    primary: {
      base: {
        background: 'var(--gold-500)',
        color: 'var(--accent-fg)',
        border: '1px solid transparent',
        boxShadow: 'var(--shadow-gold)'
      },
      hover: {
        background: 'var(--gold-600)'
      },
      press: {
        background: 'var(--gold-700)'
      }
    },
    secondary: {
      base: {
        background: 'var(--bg-surface)',
        color: 'var(--text-primary)',
        border: '1px solid var(--border-strong)',
        boxShadow: 'var(--shadow-xs)'
      },
      hover: {
        background: 'var(--bg-subtle)'
      },
      press: {
        background: 'var(--warm-150)'
      }
    },
    ghost: {
      base: {
        background: 'transparent',
        color: 'var(--text-secondary)',
        border: '1px solid transparent'
      },
      hover: {
        background: 'var(--bg-hover)',
        color: 'var(--text-primary)'
      },
      press: {
        background: 'var(--warm-150)'
      }
    },
    danger: {
      base: {
        background: 'var(--loss)',
        color: '#fff',
        border: '1px solid transparent'
      },
      hover: {
        background: 'var(--red-600)'
      },
      press: {
        background: 'var(--red-600)'
      }
    }
  };
  const v = variants[variant] || variants.primary;
  const composed = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: s.gap,
    height: s.height,
    padding: s.padding,
    borderRadius: s.radius,
    fontFamily: 'var(--font-sans)',
    fontWeight: 600,
    fontSize: s.fontSize,
    lineHeight: 1,
    cursor: disabled ? 'not-allowed' : 'pointer',
    width: fullWidth ? '100%' : 'auto',
    opacity: disabled ? 0.5 : 1,
    transition: 'background var(--dur-fast) var(--ease-out), transform var(--dur-fast) var(--ease-out)',
    transform: press && !disabled ? 'translateY(1px)' : 'none',
    whiteSpace: 'nowrap',
    userSelect: 'none',
    ...v.base,
    ...(hover && !disabled ? v.hover : {}),
    ...(press && !disabled ? v.press : {}),
    ...style
  };
  return /*#__PURE__*/React.createElement("button", _extends({
    type: type,
    disabled: disabled,
    onClick: onClick,
    style: composed,
    onMouseEnter: () => setHover(true),
    onMouseLeave: () => {
      setHover(false);
      setPress(false);
    },
    onMouseDown: () => setPress(true),
    onMouseUp: () => setPress(false)
  }, rest), icon ? /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      flex: 'none'
    }
  }, icon) : null, children, iconRight ? /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      flex: 'none'
    }
  }, iconRight) : null);
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Button.jsx", error: String((e && e.message) || e) }); }

// components/core/Card.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * betsu Card — white surface, warm hairline border, soft shadow, rounded.
 * Set `highlight` for the gold-bordered "top pick" treatment.
 */
function Card({
  children,
  highlight = false,
  padding = 20,
  elevation = 'sm',
  style = {},
  ...rest
}) {
  const shadow = {
    none: 'none',
    xs: 'var(--shadow-xs)',
    sm: 'var(--shadow-sm)',
    md: 'var(--shadow-md)',
    lg: 'var(--shadow-lg)'
  }[elevation] || 'var(--shadow-sm)';
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      background: 'var(--bg-surface)',
      border: highlight ? '1.5px solid var(--gold-400)' : '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)',
      boxShadow: highlight ? 'var(--shadow-gold)' : shadow,
      padding,
      ...style
    }
  }, rest), children);
}
Object.assign(__ds_scope, { Card });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Card.jsx", error: String((e && e.message) || e) }); }

// components/core/Logo.jsx
try { (() => {
/**
 * betsu Logo — the gradient mark + optional lowercase wordmark.
 * The mark is an <img> to the SVG asset; pass `markSrc` if your path differs.
 */
function Logo({
  size = 32,
  wordmark = true,
  markSrc = 'assets/betsu-logo.svg',
  color = 'var(--text-primary)',
  style = {}
}) {
  return /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: size * 0.34,
      ...style
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: markSrc,
    alt: "betsu",
    width: size,
    height: size,
    style: {
      display: 'block',
      flex: 'none'
    }
  }), wordmark ? /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-display)',
      fontWeight: 800,
      fontSize: size * 0.86,
      letterSpacing: '-0.03em',
      color,
      lineHeight: 1
    }
  }, "betsu") : null);
}
Object.assign(__ds_scope, { Logo });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/core/Logo.jsx", error: String((e && e.message) || e) }); }

// components/data/BetCard.jsx
try { (() => {
/**
 * betsu BetCard — the signature value-bet card. Mirrors the Telegram pick:
 * teams, market, pick @ odds, model% vs market% → edge, stake + ¼-Kelly guide.
 * Set `top` to give the day's best edge the gold "top pick" treatment.
 */
function BetCard({
  rank,
  home,
  away,
  market = '1X2',
  pick,
  odds,
  modelProb,
  marketProb,
  edge,
  stakeUnits = 1,
  kellyUnits,
  contextNote = null,
  top = false,
  style = {}
}) {
  const edgePct = edge * 100;
  const edgeStr = `${edgePct >= 0 ? '+' : ''}${edgePct.toFixed(1)}%`;
  const modelW = Math.max(2, Math.min(100, modelProb * 100));
  const marketW = Math.max(2, Math.min(100, marketProb * 100));
  const label = t => ({
    fontFamily: 'var(--font-sans)',
    fontSize: 11,
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
    color: 'var(--text-muted)'
  });
  return /*#__PURE__*/React.createElement("div", {
    style: {
      background: 'var(--bg-surface)',
      border: top ? '1.5px solid var(--gold-400)' : '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)',
      boxShadow: top ? 'var(--shadow-gold)' : 'var(--shadow-sm)',
      padding: 18,
      fontFamily: 'var(--font-sans)',
      position: 'relative',
      overflow: 'hidden',
      ...style
    }
  }, top ? /*#__PURE__*/React.createElement("div", {
    style: {
      position: 'absolute',
      top: 0,
      left: 0,
      right: 0,
      height: 3,
      background: 'var(--brand-gradient)'
    }
  }) : null, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      marginBottom: 14
    }
  }, rank != null ? /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: 22,
      height: 22,
      borderRadius: 'var(--radius-full)',
      flex: 'none',
      background: top ? 'var(--gold-500)' : 'var(--bg-subtle)',
      color: top ? 'var(--accent-fg)' : 'var(--text-secondary)',
      fontSize: 12,
      fontWeight: 700
    }
  }, rank) : null, /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-display)',
      fontWeight: 700,
      fontSize: 17,
      letterSpacing: '-0.01em',
      color: 'var(--text-primary)',
      flex: 1
    }
  }, home, " ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--text-muted)',
      fontWeight: 500
    }
  }, "vs"), " ", away), /*#__PURE__*/React.createElement("span", {
    style: {
      padding: '3px 10px',
      borderRadius: 'var(--radius-full)',
      background: 'var(--gold-100)',
      color: 'var(--gold-700)',
      fontSize: 11,
      fontWeight: 600,
      whiteSpace: 'nowrap'
    }
  }, market)), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'baseline',
      justifyContent: 'space-between',
      marginBottom: 14
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("span", {
    style: label()
  }, "Pick"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 16,
      fontWeight: 700,
      color: 'var(--text-primary)',
      marginTop: 2
    }
  }, pick)), /*#__PURE__*/React.createElement("div", {
    style: {
      textAlign: 'right'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: label()
  }, "Odds"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 22,
      fontWeight: 700,
      fontFamily: 'var(--font-display)',
      color: 'var(--text-primary)',
      fontVariantNumeric: 'tabular-nums',
      marginTop: 2
    }
  }, odds.toFixed(2)))), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 8,
      marginBottom: 14
    }
  }, /*#__PURE__*/React.createElement(ProbBar, {
    caption: "Model",
    pct: modelProb,
    width: modelW,
    fill: "var(--brand-gradient)"
  }), /*#__PURE__*/React.createElement(ProbBar, {
    caption: "Market",
    pct: marketProb,
    width: marketW,
    fill: "var(--warm-300)",
    muted: true
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      paddingTop: 12,
      borderTop: '1px solid var(--border-subtle)'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      alignItems: 'center',
      gap: 5,
      padding: '4px 11px',
      borderRadius: 'var(--radius-full)',
      background: 'var(--win-bg)',
      color: 'var(--win)',
      fontSize: 13,
      fontWeight: 700,
      fontVariantNumeric: 'tabular-nums'
    }
  }, "edge ", edgeStr), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 12.5,
      color: 'var(--text-secondary)',
      fontVariantNumeric: 'tabular-nums'
    }
  }, "Stake ", /*#__PURE__*/React.createElement("b", {
    style: {
      color: 'var(--text-primary)'
    }
  }, stakeUnits.toFixed(0), "u"), kellyUnits != null ? /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--text-muted)'
    }
  }, `  ·  ¼-Kelly ${kellyUnits.toFixed(2)}`) : null)), contextNote ? /*#__PURE__*/React.createElement("p", {
    style: {
      marginTop: 12,
      fontSize: 12.5,
      fontStyle: 'italic',
      color: 'var(--text-secondary)',
      lineHeight: 1.45
    }
  }, contextNote) : null);
}
function ProbBar({
  caption,
  pct,
  width,
  fill,
  muted = false
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 10
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      width: 48,
      flex: 'none',
      fontSize: 11,
      fontWeight: 600,
      color: muted ? 'var(--text-muted)' : 'var(--text-secondary)'
    }
  }, caption), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1,
      height: 8,
      borderRadius: 'var(--radius-full)',
      background: 'var(--bg-inset)',
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: `${width}%`,
      height: '100%',
      borderRadius: 'var(--radius-full)',
      background: fill
    }
  })), /*#__PURE__*/React.createElement("span", {
    style: {
      width: 38,
      flex: 'none',
      textAlign: 'right',
      fontSize: 12.5,
      fontWeight: 600,
      color: 'var(--text-primary)',
      fontVariantNumeric: 'tabular-nums'
    }
  }, Math.round(pct * 100), "%"));
}
Object.assign(__ds_scope, { BetCard });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/BetCard.jsx", error: String((e && e.message) || e) }); }

// components/data/StatTile.jsx
try { (() => {
/**
 * betsu StatTile — the dashboard metric tile. Big tabular number, uppercase label.
 * `tone` colors the value: pos (green), neg (red), or default ink.
 */
function StatTile({
  label,
  value,
  tone = 'default',
  sub = null,
  icon = null,
  style = {}
}) {
  const valueColor = {
    default: 'var(--text-primary)',
    pos: 'var(--win)',
    neg: 'var(--loss)',
    muted: 'var(--text-muted)',
    gold: 'var(--gold-600)'
  }[tone] || 'var(--text-primary)';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      background: 'var(--bg-surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)',
      padding: '16px 18px',
      boxShadow: 'var(--shadow-sm)',
      display: 'flex',
      flexDirection: 'column',
      gap: 6,
      ...style
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 11,
      fontWeight: 600,
      textTransform: 'uppercase',
      letterSpacing: '0.04em',
      color: 'var(--text-muted)',
      whiteSpace: 'nowrap'
    }
  }, label), icon ? /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'inline-flex',
      color: 'var(--warm-400)'
    }
  }, icon) : null), /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-display)',
      fontWeight: 700,
      fontSize: 30,
      letterSpacing: '-0.02em',
      lineHeight: 1,
      color: valueColor,
      fontVariantNumeric: 'tabular-nums'
    }
  }, value), sub ? /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 12,
      color: 'var(--text-muted)',
      fontVariantNumeric: 'tabular-nums'
    }
  }, sub) : null);
}
Object.assign(__ds_scope, { StatTile });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/data/StatTile.jsx", error: String((e && e.message) || e) }); }

// ui_kits/dashboard/Dashboard.jsx
try { (() => {
// betsu performance dashboard — recreation (light theme).
const {
  useState,
  useEffect,
  useRef
} = React;
const {
  StatTile,
  BetCard,
  Button,
  Badge,
  Logo
} = window.BetsuDesignSystem_f41923;
const D = window.BETSU_DATA;
function Icon({
  name,
  size = 18,
  color = 'currentColor',
  strokeWidth = 1.75
}) {
  const ref = useRef(null);
  useEffect(() => {
    if (window.lucide && ref.current) {
      ref.current.innerHTML = '';
      const el = document.createElement('i');
      el.setAttribute('data-lucide', name);
      ref.current.appendChild(el);
      window.lucide.createIcons({
        attrs: {
          width: size,
          height: size,
          stroke: color,
          'stroke-width': strokeWidth
        },
        nodes: [el]
      });
    }
  }, [name, size, color, strokeWidth]);
  return /*#__PURE__*/React.createElement("span", {
    ref: ref,
    style: {
      display: 'inline-flex',
      width: size,
      height: size
    }
  });
}
function fmtSigned(n, suffix = '', dp = 2) {
  return `${n >= 0 ? '+' : ''}${n.toFixed(dp)}${suffix}`;
}
function Header({
  tab,
  setTab
}) {
  return /*#__PURE__*/React.createElement("header", {
    style: {
      position: 'sticky',
      top: 0,
      zIndex: 10,
      background: 'rgba(251,249,246,0.82)',
      backdropFilter: 'saturate(180%) blur(12px)',
      borderBottom: '1px solid var(--border-subtle)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: 1040,
      margin: '0 auto',
      padding: '0 24px',
      height: 64,
      display: 'flex',
      alignItems: 'center',
      gap: 24
    }
  }, /*#__PURE__*/React.createElement(Logo, {
    size: 30,
    markSrc: "../../assets/betsu-logo.svg"
  }), /*#__PURE__*/React.createElement("nav", {
    style: {
      display: 'flex',
      gap: 4,
      marginLeft: 8
    }
  }, [['overview', 'Performance'], ['today', "Today's card"]].map(([id, label]) => /*#__PURE__*/React.createElement("button", {
    key: id,
    onClick: () => setTab(id),
    style: {
      border: 'none',
      background: tab === id ? 'var(--bg-surface)' : 'transparent',
      boxShadow: tab === id ? 'var(--shadow-xs)' : 'none',
      color: tab === id ? 'var(--text-primary)' : 'var(--text-secondary)',
      fontFamily: 'var(--font-sans)',
      fontWeight: 600,
      fontSize: 14,
      padding: '7px 14px',
      borderRadius: 'var(--radius-md)',
      cursor: 'pointer',
      border: tab === id ? '1px solid var(--border)' : '1px solid transparent'
    }
  }, label))), /*#__PURE__*/React.createElement("div", {
    style: {
      marginLeft: 'auto',
      display: 'flex',
      alignItems: 'center',
      gap: 12
    }
  }, /*#__PURE__*/React.createElement(Badge, {
    variant: "outline",
    size: "md"
  }, "Paper-traded"), /*#__PURE__*/React.createElement(Button, {
    variant: "primary",
    size: "sm",
    icon: /*#__PURE__*/React.createElement(Icon, {
      name: "send",
      size: 15,
      color: "var(--accent-fg)"
    })
  }, "Send card"))));
}
function PnlChart() {
  const ref = useRef(null);
  const chartRef = useRef(null);
  useEffect(() => {
    if (!window.Chart || !ref.current) return;
    if (chartRef.current) chartRef.current.destroy();
    const ctx = ref.current.getContext('2d');
    const grad = ctx.createLinearGradient(0, 0, 0, 220);
    grad.addColorStop(0, 'rgba(247,148,30,0.22)');
    grad.addColorStop(1, 'rgba(247,148,30,0.00)');
    chartRef.current = new window.Chart(ctx, {
      type: 'line',
      data: {
        labels: D.curve.map(c => c.label),
        datasets: [{
          data: D.curve.map(c => c.value),
          borderColor: '#F7941E',
          backgroundColor: grad,
          fill: true,
          tension: 0.32,
          pointRadius: 0,
          pointHoverRadius: 5,
          pointHoverBackgroundColor: '#F7941E',
          borderWidth: 2.5
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            backgroundColor: '#1A1611',
            padding: 10,
            cornerRadius: 8,
            displayColors: false,
            titleFont: {
              family: 'Inter',
              weight: '600'
            },
            bodyFont: {
              family: 'Inter'
            },
            callbacks: {
              title: i => i[0].label,
              label: i => `${i.parsed.y >= 0 ? '+' : ''}${i.parsed.y.toFixed(2)}u cumulative`
            }
          }
        },
        scales: {
          x: {
            grid: {
              display: false
            },
            ticks: {
              color: '#A99E8E',
              font: {
                family: 'Inter',
                size: 11
              }
            },
            border: {
              display: false
            }
          },
          y: {
            grid: {
              color: '#EDE7DD'
            },
            ticks: {
              color: '#A99E8E',
              font: {
                family: 'Inter',
                size: 11
              },
              callback: v => `${v > 0 ? '+' : ''}${v}u`
            },
            border: {
              display: false
            }
          }
        }
      }
    });
    return () => chartRef.current && chartRef.current.destroy();
  }, []);
  return /*#__PURE__*/React.createElement("canvas", {
    ref: ref,
    style: {
      width: '100%',
      height: 220
    }
  });
}
function ResultPill({
  result
}) {
  if (result === 'win') return /*#__PURE__*/React.createElement(Badge, {
    variant: "win",
    dot: true
  }, "win");
  if (result === 'loss') return /*#__PURE__*/React.createElement(Badge, {
    variant: "loss",
    dot: true
  }, "loss");
  return /*#__PURE__*/React.createElement(Badge, {
    variant: "pending",
    dot: true
  }, "pending");
}
function BetsTable() {
  const [sortDesc, setSortDesc] = useState(true);
  const rows = [...D.bets].reverse();
  return /*#__PURE__*/React.createElement("div", {
    style: {
      background: 'var(--bg-surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)',
      boxShadow: 'var(--shadow-sm)',
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '16px 20px',
      borderBottom: '1px solid var(--border-subtle)',
      display: 'flex',
      alignItems: 'center',
      gap: 10
    }
  }, /*#__PURE__*/React.createElement("h3", {
    style: {
      fontSize: 16
    }
  }, "Bet log"), /*#__PURE__*/React.createElement(Badge, {
    variant: "neutral",
    size: "sm"
  }, D.bets.length, " bets"), /*#__PURE__*/React.createElement("span", {
    style: {
      marginLeft: 'auto',
      fontSize: 12,
      color: 'var(--text-muted)'
    }
  }, "Most recent first")), /*#__PURE__*/React.createElement("div", {
    style: {
      overflowX: 'auto'
    }
  }, /*#__PURE__*/React.createElement("table", {
    style: {
      width: '100%',
      borderCollapse: 'collapse',
      fontFamily: 'var(--font-sans)',
      fontVariantNumeric: 'tabular-nums',
      fontSize: 13
    }
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", null, ['Date', 'Match', 'Market', 'Pick', 'Odds', 'Model', 'Edge', 'Result', 'P&L'].map((h, i) => /*#__PURE__*/React.createElement("th", {
    key: h,
    style: {
      textAlign: i >= 4 && i <= 6 || i === 8 ? 'right' : 'left',
      padding: '10px 16px',
      fontSize: 10.5,
      fontWeight: 600,
      textTransform: 'uppercase',
      letterSpacing: '0.04em',
      color: 'var(--text-muted)',
      borderBottom: '1px solid var(--border-subtle)',
      whiteSpace: 'nowrap',
      background: 'var(--bg-subtle)'
    }
  }, h)))), /*#__PURE__*/React.createElement("tbody", null, rows.map((b, i) => /*#__PURE__*/React.createElement("tr", {
    key: i,
    style: {
      borderBottom: i < rows.length - 1 ? '1px solid var(--border-subtle)' : 'none'
    },
    onMouseEnter: e => e.currentTarget.style.background = 'var(--bg-subtle)',
    onMouseLeave: e => e.currentTarget.style.background = 'transparent'
  }, /*#__PURE__*/React.createElement("td", {
    style: {
      padding: '11px 16px',
      color: 'var(--text-muted)',
      whiteSpace: 'nowrap'
    }
  }, b.date), /*#__PURE__*/React.createElement("td", {
    style: {
      padding: '11px 16px',
      fontWeight: 500,
      whiteSpace: 'nowrap'
    }
  }, b.home, " ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--text-muted)'
    }
  }, "vs"), " ", b.away), /*#__PURE__*/React.createElement("td", {
    style: {
      padding: '11px 16px'
    }
  }, /*#__PURE__*/React.createElement(Badge, {
    variant: "neutral",
    size: "sm"
  }, b.market)), /*#__PURE__*/React.createElement("td", {
    style: {
      padding: '11px 16px',
      color: 'var(--text-secondary)',
      whiteSpace: 'nowrap'
    }
  }, b.pick), /*#__PURE__*/React.createElement("td", {
    style: {
      padding: '11px 16px',
      textAlign: 'right',
      fontWeight: 600
    }
  }, b.odds.toFixed(2)), /*#__PURE__*/React.createElement("td", {
    style: {
      padding: '11px 16px',
      textAlign: 'right',
      color: 'var(--text-secondary)'
    }
  }, Math.round(b.model * 100), "%"), /*#__PURE__*/React.createElement("td", {
    style: {
      padding: '11px 16px',
      textAlign: 'right',
      fontWeight: 600,
      color: 'var(--edge-pos)'
    }
  }, fmtSigned(b.edge * 100, '%', 1)), /*#__PURE__*/React.createElement("td", {
    style: {
      padding: '11px 16px'
    }
  }, /*#__PURE__*/React.createElement(ResultPill, {
    result: b.result
  })), /*#__PURE__*/React.createElement("td", {
    style: {
      padding: '11px 16px',
      textAlign: 'right',
      fontWeight: 600,
      color: b.pnl == null ? 'var(--text-muted)' : b.pnl > 0 ? 'var(--win)' : 'var(--loss)'
    }
  }, b.pnl == null ? '—' : fmtSigned(b.pnl, 'u', 2))))))));
}
function Overview() {
  const s = D.summary;
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 24
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: 'repeat(5, 1fr)',
      gap: 12
    }
  }, /*#__PURE__*/React.createElement(StatTile, {
    label: "Record",
    value: `${s.wins}–${s.losses}`,
    sub: `${s.settled} settled`,
    icon: /*#__PURE__*/React.createElement(Icon, {
      name: "trophy",
      size: 16,
      color: "var(--warm-400)"
    })
  }), /*#__PURE__*/React.createElement(StatTile, {
    label: "Hit rate",
    value: `${s.hit_rate}%`,
    sub: "of settled",
    icon: /*#__PURE__*/React.createElement(Icon, {
      name: "target",
      size: 16,
      color: "var(--warm-400)"
    })
  }), /*#__PURE__*/React.createElement(StatTile, {
    label: "P&L",
    value: fmtSigned(s.pnl_units, 'u', 2),
    tone: "pos",
    sub: "units",
    icon: /*#__PURE__*/React.createElement(Icon, {
      name: "coins",
      size: 16,
      color: "var(--warm-400)"
    })
  }), /*#__PURE__*/React.createElement(StatTile, {
    label: "ROI",
    value: fmtSigned(s.roi_pct, '%', 1),
    tone: "pos",
    sub: "vs closing line",
    icon: /*#__PURE__*/React.createElement(Icon, {
      name: "trending-up",
      size: 16,
      color: "var(--warm-400)"
    })
  }), /*#__PURE__*/React.createElement(StatTile, {
    label: "Pending",
    value: s.pending,
    tone: "muted",
    sub: "awaiting result",
    icon: /*#__PURE__*/React.createElement(Icon, {
      name: "clock",
      size: 16,
      color: "var(--warm-400)"
    })
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      background: 'var(--bg-surface)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-lg)',
      boxShadow: 'var(--shadow-sm)',
      padding: 20
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'baseline',
      justifyContent: 'space-between',
      marginBottom: 14
    }
  }, /*#__PURE__*/React.createElement("h3", {
    style: {
      fontSize: 16,
      whiteSpace: 'nowrap'
    }
  }, "Cumulative P&L"), /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 12,
      color: 'var(--text-muted)'
    }
  }, "units, settled bets \xB7 vs closing line")), /*#__PURE__*/React.createElement(PnlChart, null)), /*#__PURE__*/React.createElement(BetsTable, null));
}
function TodayCard() {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 18
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'flex-end',
      justifyContent: 'space-between',
      gap: 16
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h2", {
    style: {
      fontSize: 26,
      marginBottom: 4
    }
  }, "Today's value bets"), /*#__PURE__*/React.createElement("p", {
    style: {
      color: 'var(--text-secondary)',
      fontSize: 14
    }
  }, /*#__PURE__*/React.createElement("b", {
    style: {
      color: 'var(--text-primary)'
    }
  }, "8 matches"), " scanned \xB7 ", /*#__PURE__*/React.createElement("b", {
    style: {
      color: 'var(--text-primary)'
    }
  }, D.today.length, " value bets"), " clear the 5% edge threshold \xB7 ranked by edge")), /*#__PURE__*/React.createElement(Button, {
    variant: "primary",
    icon: /*#__PURE__*/React.createElement(Icon, {
      name: "send",
      size: 16,
      color: "var(--accent-fg)"
    })
  }, "Send to Telegram")), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: 14
    }
  }, D.today.map((b, i) => /*#__PURE__*/React.createElement("div", {
    key: i,
    style: {
      gridColumn: i === 0 ? '1 / -1' : 'auto'
    }
  }, /*#__PURE__*/React.createElement(BetCard, {
    rank: i + 1,
    top: i === 0,
    home: b.home,
    away: b.away,
    market: b.market,
    pick: b.pick,
    odds: b.odds,
    modelProb: b.model,
    marketProb: b.market_p,
    edge: b.edge,
    stakeUnits: b.stake,
    kellyUnits: b.kelly,
    contextNote: b.note
  })))), /*#__PURE__*/React.createElement("p", {
    style: {
      textAlign: 'center',
      color: 'var(--text-muted)',
      fontSize: 13,
      padding: '8px 0 4px',
      fontStyle: 'italic'
    }
  }, "Paper unless you choose to back it. Bet responsibly."));
}
function App() {
  const [tab, setTab] = useState('overview');
  return /*#__PURE__*/React.createElement("div", {
    style: {
      minHeight: '100vh'
    }
  }, /*#__PURE__*/React.createElement(Header, {
    tab: tab,
    setTab: setTab
  }), /*#__PURE__*/React.createElement("main", {
    style: {
      maxWidth: 1040,
      margin: '0 auto',
      padding: '28px 24px 72px'
    }
  }, tab === 'overview' ? /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement("div", {
    style: {
      marginBottom: 22
    }
  }, /*#__PURE__*/React.createElement("h1", {
    style: {
      fontSize: 34,
      letterSpacing: '-0.02em'
    }
  }, "performance"), /*#__PURE__*/React.createElement("p", {
    style: {
      color: 'var(--text-secondary)',
      fontSize: 14,
      marginTop: 4
    }
  }, "Paper-traded unless flagged real. Judged on calibration & ROI, not any single day.")), /*#__PURE__*/React.createElement(Overview, null)) : /*#__PURE__*/React.createElement(TodayCard, null)));
}
ReactDOM.createRoot(document.getElementById('root')).render(/*#__PURE__*/React.createElement(App, null));
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/dashboard/Dashboard.jsx", error: String((e && e.message) || e) }); }

// ui_kits/dashboard/data.js
try { (() => {
// betsu dashboard — fake data for the recreation (World Cup 2026 slate).
window.BETSU_DATA = function () {
  // result: 'win' | 'loss' | 'pending'
  const bets = [{
    date: '06-11',
    home: 'Mexico',
    away: 'Poland',
    market: '1X2',
    pick: 'Home (Mexico)',
    odds: 1.95,
    model: 0.62,
    market_p: 0.51,
    edge: 0.209,
    stake: 1,
    kelly: 0.06,
    result: 'win',
    pnl: 0.95
  }, {
    date: '06-11',
    home: 'Argentina',
    away: 'Saudi Arabia',
    market: '1X2',
    pick: 'Home (Argentina)',
    odds: 1.40,
    model: 0.78,
    market_p: 0.71,
    edge: 0.092,
    stake: 1,
    kelly: 0.07,
    result: 'win',
    pnl: 0.40
  }, {
    date: '06-12',
    home: 'France',
    away: 'Denmark',
    market: 'OU 2.5',
    pick: 'Over 2.5',
    odds: 1.90,
    model: 0.60,
    market_p: 0.53,
    edge: 0.140,
    stake: 1,
    kelly: 0.05,
    result: 'loss',
    pnl: -1.00
  }, {
    date: '06-12',
    home: 'Spain',
    away: 'Croatia',
    market: '1X2',
    pick: 'Home (Spain)',
    odds: 1.75,
    model: 0.64,
    market_p: 0.57,
    edge: 0.120,
    stake: 1,
    kelly: 0.05,
    result: 'win',
    pnl: 0.75
  }, {
    date: '06-13',
    home: 'Brazil',
    away: 'Serbia',
    market: 'BTTS',
    pick: 'BTTS No',
    odds: 2.10,
    model: 0.55,
    market_p: 0.48,
    edge: 0.155,
    stake: 1,
    kelly: 0.05,
    result: 'win',
    pnl: 1.10
  }, {
    date: '06-13',
    home: 'Germany',
    away: 'Japan',
    market: '1X2',
    pick: 'Away (Japan)',
    odds: 4.20,
    model: 0.28,
    market_p: 0.24,
    edge: 0.176,
    stake: 1,
    kelly: 0.04,
    result: 'loss',
    pnl: -1.00
  }, {
    date: '06-14',
    home: 'Portugal',
    away: 'Uruguay',
    market: '1X2',
    pick: 'Draw',
    odds: 3.30,
    model: 0.34,
    market_p: 0.30,
    edge: 0.122,
    stake: 1,
    kelly: 0.04,
    result: 'win',
    pnl: 2.30
  }, {
    date: '06-14',
    home: 'Netherlands',
    away: 'Ecuador',
    market: 'OU 2.5',
    pick: 'Under 2.5',
    odds: 2.05,
    model: 0.55,
    market_p: 0.49,
    edge: 0.128,
    stake: 1,
    kelly: 0.04,
    result: 'loss',
    pnl: -1.00
  }, {
    date: '06-15',
    home: 'England',
    away: 'USA',
    market: '1X2',
    pick: 'Home (England)',
    odds: 1.85,
    model: 0.61,
    market_p: 0.54,
    edge: 0.129,
    stake: 1,
    kelly: 0.05,
    result: 'win',
    pnl: 0.85
  }, {
    date: '06-15',
    home: 'Belgium',
    away: 'Morocco',
    market: '1X2',
    pick: 'Away (Morocco)',
    odds: 3.90,
    model: 0.30,
    market_p: 0.26,
    edge: 0.170,
    stake: 1,
    kelly: 0.04,
    result: 'loss',
    pnl: -1.00
  }];

  // today's fresh card (pending, ranked by edge)
  const today = [{
    date: '06-16',
    home: 'Argentina',
    away: 'Mexico',
    market: '1X2',
    pick: 'Home (Argentina)',
    odds: 1.95,
    model: 0.62,
    market_p: 0.51,
    edge: 0.209,
    stake: 1,
    kelly: 0.05,
    result: 'pending',
    pnl: null,
    note: 'Mexico likely to rotate — group already secured. Heat in Dallas favours the technical side.'
  }, {
    date: '06-16',
    home: 'Croatia',
    away: 'Canada',
    market: 'OU 2.5',
    pick: 'Over 2.5',
    odds: 1.88,
    model: 0.58,
    market_p: 0.53,
    edge: 0.090,
    stake: 1,
    kelly: 0.04,
    result: 'pending',
    pnl: null,
    note: null
  }, {
    date: '06-16',
    home: 'Senegal',
    away: 'Iran',
    market: 'BTTS',
    pick: 'BTTS Yes',
    odds: 2.15,
    model: 0.52,
    market_p: 0.47,
    edge: 0.118,
    stake: 1,
    kelly: 0.04,
    result: 'pending',
    pnl: null,
    note: null
  }];

  // summary
  const settled = bets.filter(b => b.result !== 'pending');
  const wins = settled.filter(b => b.result === 'win').length;
  const losses = settled.filter(b => b.result === 'loss').length;
  const pnl = settled.reduce((a, b) => a + b.pnl, 0);
  const roi = pnl / settled.length * 100;
  const summary = {
    wins,
    losses,
    hit_rate: Math.round(wins / settled.length * 100),
    pnl_units: pnl,
    roi_pct: roi,
    pending: today.length,
    settled: settled.length
  };

  // cumulative P&L curve
  let run = 0;
  const curve = settled.map(b => {
    run += b.pnl;
    return {
      label: `${b.date}`,
      value: +run.toFixed(2)
    };
  });
  return {
    bets: bets.concat(today),
    today,
    summary,
    curve
  };
}();
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/dashboard/data.js", error: String((e && e.message) || e) }); }

// ui_kits/telegram/Telegram.jsx
try { (() => {
// betsu Telegram surface — the daily bet card & results recap as chat messages.
const {
  useState,
  useRef,
  useEffect
} = React;
const {
  Logo,
  Badge
} = window.BetsuDesignSystem_f41923;

// ---- faithful message content (mirrors tools/message.py) ----
const CARD_BETS = [{
  n: 1,
  match: 'Argentina vs Mexico',
  pick: 'Home (Argentina)',
  odds: '1.95',
  model: 62,
  market: 51,
  edge: '+20.9%',
  stake: '1u',
  kelly: '0.05',
  note: 'Mexico likely to rotate — group already secured.'
}, {
  n: 2,
  match: 'Senegal vs Iran',
  pick: 'BTTS Yes',
  odds: '2.15',
  model: 52,
  market: 47,
  edge: '+11.8%',
  stake: '1u',
  kelly: '0.04',
  note: null
}, {
  n: 3,
  match: 'Croatia vs Canada',
  pick: 'Over 2.5',
  odds: '1.88',
  model: 58,
  market: 53,
  edge: '+9.0%',
  stake: '1u',
  kelly: '0.04',
  note: null
}];
function ChatHeader() {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      gap: 12,
      padding: '12px 16px',
      background: 'var(--bg-surface)',
      borderBottom: '1px solid var(--border-subtle)',
      position: 'sticky',
      top: 0,
      zIndex: 5
    }
  }, /*#__PURE__*/React.createElement("img", {
    src: "../../assets/betsu-logo.svg",
    alt: "betsu",
    width: 38,
    height: 38,
    style: {
      borderRadius: '50%',
      boxShadow: 'var(--shadow-xs)'
    }
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      flex: 1
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-display)',
      fontWeight: 700,
      fontSize: 16,
      color: 'var(--text-primary)'
    }
  }, "betsu"), /*#__PURE__*/React.createElement("div", {
    style: {
      fontSize: 12,
      color: 'var(--win)',
      fontWeight: 500
    }
  }, "bot \xB7 online")), /*#__PURE__*/React.createElement(Badge, {
    variant: "outline",
    size: "sm"
  }, "Telegram"));
}
function Bubble({
  children,
  side = 'in',
  time = '09:00',
  tail = true
}) {
  const isIn = side === 'in';
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: isIn ? 'flex-start' : 'flex-end',
      padding: '3px 14px'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      maxWidth: '86%',
      background: isIn ? 'var(--bg-surface)' : 'var(--gold-100)',
      border: '1px solid ' + (isIn ? 'var(--border-subtle)' : 'var(--gold-200)'),
      borderRadius: 16,
      borderBottomLeftRadius: isIn && tail ? 4 : 16,
      borderBottomRightRadius: !isIn && tail ? 4 : 16,
      padding: '9px 12px 7px',
      boxShadow: 'var(--shadow-xs)',
      position: 'relative'
    }
  }, children, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 10.5,
      color: 'var(--text-muted)',
      float: 'right',
      marginLeft: 10,
      marginTop: 4,
      fontVariantNumeric: 'tabular-nums'
    }
  }, time)));
}
const ds = {
  h: {
    fontFamily: 'var(--font-sans)',
    fontWeight: 700,
    fontSize: 14.5,
    color: 'var(--text-primary)'
  },
  sub: {
    fontSize: 12.5,
    color: 'var(--text-secondary)',
    marginTop: 2
  },
  betTitle: {
    fontWeight: 700,
    fontSize: 13.5,
    color: 'var(--text-primary)',
    marginTop: 12
  },
  line: {
    fontSize: 12.5,
    color: 'var(--text-secondary)',
    marginTop: 3,
    fontVariantNumeric: 'tabular-nums'
  },
  strong: {
    color: 'var(--text-primary)',
    fontWeight: 600
  },
  edge: {
    color: 'var(--win)',
    fontWeight: 700
  },
  note: {
    fontSize: 12,
    fontStyle: 'italic',
    color: 'var(--text-muted)',
    marginTop: 3
  },
  rule: {
    height: 1,
    background: 'var(--border-subtle)',
    margin: '11px -2px 0'
  }
};
function CardBubble() {
  return /*#__PURE__*/React.createElement(Bubble, {
    time: "09:00"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 280
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: ds.h
  }, "\u26BD betsu \u2014 2026-06-16"), /*#__PURE__*/React.createElement("div", {
    style: ds.sub
  }, "8 match(es) scanned \xB7 3 value bet(s)"), CARD_BETS.map(b => /*#__PURE__*/React.createElement("div", {
    key: b.n
  }, /*#__PURE__*/React.createElement("div", {
    style: ds.betTitle
  }, b.n, ". ", b.match), /*#__PURE__*/React.createElement("div", {
    style: ds.line
  }, "Pick: ", /*#__PURE__*/React.createElement("span", {
    style: ds.strong
  }, b.pick), " \xA0@ ", /*#__PURE__*/React.createElement("span", {
    style: ds.strong
  }, b.odds)), /*#__PURE__*/React.createElement("div", {
    style: ds.line
  }, "Model ", b.model, "% vs market ", b.market, "% \u2192 edge ", /*#__PURE__*/React.createElement("span", {
    style: ds.edge
  }, b.edge)), /*#__PURE__*/React.createElement("div", {
    style: ds.line
  }, "Stake: ", b.stake, " ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--text-muted)'
    }
  }, "(\xBC-Kelly guide ", b.kelly, ")")), b.note ? /*#__PURE__*/React.createElement("div", {
    style: ds.note
  }, "Context: ", b.note) : null)), /*#__PURE__*/React.createElement("div", {
    style: ds.rule
  }), /*#__PURE__*/React.createElement("div", {
    style: {
      ...ds.line,
      marginTop: 9
    }
  }, "\uD83D\uDCCA Running: ", /*#__PURE__*/React.createElement("span", {
    style: ds.strong
  }, "6-4 (60%)"), " \xB7 ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--win)',
      fontWeight: 600
    }
  }, "+2.4u"), " \xB7 ROI ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--win)',
      fontWeight: 600
    }
  }, "+23.5%")), /*#__PURE__*/React.createElement("div", {
    style: {
      ...ds.note,
      marginTop: 9
    }
  }, "Paper unless you choose to back it. Bet responsibly.")));
}
function RecapBubble() {
  return /*#__PURE__*/React.createElement(Bubble, {
    time: "10:02"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 260
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: ds.h
  }, "\uD83D\uDCCB betsu results \u2014 2026-06-15"), /*#__PURE__*/React.createElement("div", {
    style: ds.sub
  }, "Settled 2 bet(s) today."), /*#__PURE__*/React.createElement("div", {
    style: {
      ...ds.line,
      marginTop: 10
    }
  }, "Record: ", /*#__PURE__*/React.createElement("span", {
    style: ds.strong
  }, "6-4 (60%)")), /*#__PURE__*/React.createElement("div", {
    style: ds.line
  }, "P&L: ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--win)',
      fontWeight: 600
    }
  }, "+2.4u"), " \xB7 ROI ", /*#__PURE__*/React.createElement("span", {
    style: {
      color: 'var(--win)',
      fontWeight: 600
    }
  }, "+23.5%"))));
}
function NoBetBubble() {
  return /*#__PURE__*/React.createElement(Bubble, {
    time: "20:00"
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      width: 250
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: ds.h
  }, "\u26BD betsu \u2014 2026-06-17"), /*#__PURE__*/React.createElement("div", {
    style: ds.sub
  }, "3 match(es) scanned \xB7 0 value bet(s)"), /*#__PURE__*/React.createElement("div", {
    style: {
      ...ds.line,
      marginTop: 8,
      color: 'var(--text-primary)'
    }
  }, "No value bets clear the edge threshold today. Sitting out.")));
}
function DayDivider({
  children
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      justifyContent: 'center',
      padding: '12px 0 8px'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontSize: 11,
      fontWeight: 600,
      color: 'var(--text-muted)',
      background: 'rgba(255,255,255,0.7)',
      padding: '3px 12px',
      borderRadius: 999,
      border: '1px solid var(--border-subtle)',
      whiteSpace: 'nowrap'
    }
  }, children));
}
function Composer({
  onSend
}) {
  const [val, setVal] = useState('');
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 8,
      padding: 12,
      background: 'var(--bg-surface)',
      borderTop: '1px solid var(--border-subtle)',
      alignItems: 'center'
    }
  }, /*#__PURE__*/React.createElement("input", {
    value: val,
    onChange: e => setVal(e.target.value),
    onKeyDown: e => {
      if (e.key === 'Enter' && val.trim()) {
        onSend(val);
        setVal('');
      }
    },
    placeholder: "Message  \xB7  try /today",
    style: {
      flex: 1,
      height: 40,
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius-full)',
      padding: '0 16px',
      fontFamily: 'var(--font-sans)',
      fontSize: 14,
      background: 'var(--bg-page)',
      color: 'var(--text-primary)',
      outline: 'none'
    }
  }), /*#__PURE__*/React.createElement("button", {
    onClick: () => {
      if (val.trim()) {
        onSend(val);
        setVal('');
      }
    },
    style: {
      width: 40,
      height: 40,
      borderRadius: '50%',
      border: 'none',
      background: 'var(--gold-500)',
      color: 'var(--accent-fg)',
      cursor: 'pointer',
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      boxShadow: 'var(--shadow-gold)',
      fontSize: 18,
      fontWeight: 700
    }
  }, "\u2191"));
}
function App() {
  const [showCard, setShowCard] = useState(false);
  const [cmd, setCmd] = useState(null);
  const scrollRef = useRef(null);
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [showCard, cmd]);
  const onSend = text => {
    setCmd(text);
    if (text.trim().toLowerCase().startsWith('/today')) {
      setTimeout(() => setShowCard(true), 450);
    }
  };
  return /*#__PURE__*/React.createElement("div", {
    style: {
      width: 414,
      height: 760,
      margin: '0 auto',
      background: 'var(--bg-page)',
      borderRadius: 28,
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
      border: '1px solid var(--border)',
      boxShadow: 'var(--shadow-xl)'
    }
  }, /*#__PURE__*/React.createElement(ChatHeader, null), /*#__PURE__*/React.createElement("div", {
    ref: scrollRef,
    style: {
      flex: 1,
      overflowY: 'auto',
      paddingBottom: 8,
      background: 'linear-gradient(180deg, var(--warm-50) 0%, var(--gold-100) 220%)'
    }
  }, /*#__PURE__*/React.createElement(DayDivider, null, "June 15"), /*#__PURE__*/React.createElement(RecapBubble, null), /*#__PURE__*/React.createElement(DayDivider, null, "June 16"), /*#__PURE__*/React.createElement(CardBubble, null), cmd ? /*#__PURE__*/React.createElement(Bubble, {
    side: "out",
    time: "09:14"
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-sans)',
      fontSize: 14,
      color: 'var(--text-primary)'
    }
  }, cmd)) : null, showCard ? /*#__PURE__*/React.createElement(CardBubble, null) : null, !cmd ? /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(DayDivider, null, "June 17"), /*#__PURE__*/React.createElement(NoBetBubble, null)) : null), /*#__PURE__*/React.createElement(Composer, {
    onSend: onSend
  }));
}
ReactDOM.createRoot(document.getElementById('root')).render(/*#__PURE__*/React.createElement(App, null));
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/telegram/Telegram.jsx", error: String((e && e.message) || e) }); }

__ds_ns.Badge = __ds_scope.Badge;

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Card = __ds_scope.Card;

__ds_ns.Logo = __ds_scope.Logo;

__ds_ns.BetCard = __ds_scope.BetCard;

__ds_ns.StatTile = __ds_scope.StatTile;

})();
