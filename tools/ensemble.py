"""
ensemble.py — blend predictor probabilities into one 1X2 distribution.

Each predictor returns {"1","X","2"} that sums to 1. We combine them with the
weights in config.ENSEMBLE_WEIGHTS, renormalising over whichever predictors are
actually present for a match (so a missing layer never breaks the blend).

The optional "llm" layer is an ADJUSTMENT, not a base predictor: it nudges the
blended probabilities up or down (e.g. key injury, dead rubber) by a bounded
factor, then we renormalise. This keeps stats in charge and lets news fine-tune.

    blend({"market": {...}, "elo": {...}}, llm_adjust={"1": +0.05}) -> {...}
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ENSEMBLE_WEIGHTS

OUTCOMES = ("1", "X", "2")


def _normalise(p):
    total = sum(p[o] for o in OUTCOMES)
    if total <= 0:
        return {o: 1 / 3 for o in OUTCOMES}
    return {o: p[o] / total for o in OUTCOMES}


def blend(predictions, llm_adjust=None):
    """
    predictions: dict mapping predictor name -> {"1","X","2"} probs.
                 Only names present in ENSEMBLE_WEIGHTS contribute.
    llm_adjust:  optional dict of additive nudges per outcome, e.g.
                 {"2": +0.04, "1": -0.04}. Bounded and renormalised.
    Returns blended {"1","X","2"}.
    """
    present = {n: p for n, p in predictions.items()
               if n in ENSEMBLE_WEIGHTS and p is not None}
    if not present:
        return {o: 1 / 3 for o in OUTCOMES}

    wsum = sum(ENSEMBLE_WEIGHTS[n] for n in present)
    blended = {o: 0.0 for o in OUTCOMES}
    for name, probs in present.items():
        w = ENSEMBLE_WEIGHTS[name] / wsum
        norm = _normalise(probs)
        for o in OUTCOMES:
            blended[o] += w * norm[o]

    if llm_adjust:
        for o in OUTCOMES:
            blended[o] = max(0.0, blended[o] + llm_adjust.get(o, 0.0))
        blended = _normalise(blended)

    return {o: round(blended[o], 4) for o in OUTCOMES}


if __name__ == "__main__":
    demo = {
        "market": {"1": 0.55, "X": 0.27, "2": 0.18},
        "elo":    {"1": 0.60, "X": 0.25, "2": 0.15},
    }
    print("blend:", blend(demo))
    print("with llm nudge to away:", blend(demo, llm_adjust={"2": 0.06, "1": -0.06}))
