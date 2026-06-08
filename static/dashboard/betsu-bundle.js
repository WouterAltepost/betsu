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
      fontVariantNumeric: 'tabular-nums',
      whiteSpace: 'nowrap'
    }
  }, "betsu size ", /*#__PURE__*/React.createElement("b", {
    style: {
      color: 'var(--text-primary)'
    }
  }, kellyUnits != null ? "€" + Math.round(kellyUnits * 1000) : "—"))), contextNote ? /*#__PURE__*/React.createElement("p", {
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

__ds_ns.Badge = __ds_scope.Badge;

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Card = __ds_scope.Card;

__ds_ns.Logo = __ds_scope.Logo;

__ds_ns.BetCard = __ds_scope.BetCard;

__ds_ns.StatTile = __ds_scope.StatTile;

})();
