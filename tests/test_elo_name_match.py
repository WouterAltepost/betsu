"""
test_elo_name_match.py — regression guard for the elo.py team-name resolver.

The danger this locks down: a fuzzy MIS-match in lookup_rating hands a team the
WRONG Elo rating (silently corrupting the Poisson lambdas, the blend, and any
bet off it). token_sort_ratio scores some distinct 2026 qualifiers high enough
to cross-resolve at the old threshold (Australia vs Austria = 87.5; Iran/Iraq,
Slovakia/Slovenia same class). These tests assert:

  1. Every plausible odds-API spelling of a qualifier (exact, accented, common
     variant) resolves to that team's OWN seed.
  2. The confusable country pairs never cross-resolve.
  3. is_seeded stays False for genuinely unknown teams (run_daily's guard).
  4. get_rating for an exact seed name is unchanged.

Runs standalone (no pytest needed):
    python tests/test_elo_name_match.py
Also discoverable by pytest if installed.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools import elo

RATINGS = elo.load_ratings()


# Plausible odds-API / feed spellings -> the canonical seed key they MUST hit.
# Covers exact names, accent variants, punctuation variants, and the known
# alias spellings. Every entry must resolve via exact/normalized/alias — fuzzy
# is only a defensive net and nothing here should depend on it.
VARIANT_SPELLINGS = {
    # Host nation, the original alias case.
    "USA": "United States",
    "United States of America": "United States",
    "United States": "United States",
    # Accent folding.
    "Curaçao": "Curacao",
    "Türkiye": "Turkey",
    "Turkiye": "Turkey",
    # Côte d'Ivoire spellings.
    "Côte d'Ivoire": "Ivory Coast",
    "Cote d'Ivoire": "Ivory Coast",
    "Ivory Coast": "Ivory Coast",
    # Cape Verde.
    "Cabo Verde": "Cape Verde",
    "Cape Verde Islands": "Cape Verde",
    # Czechia.
    "Czech Republic": "Czechia",
    # South Korea.
    "Korea Republic": "South Korea",
    "Republic of Korea": "South Korea",
    "Korea, Republic of": "South Korea",
    # Iran.
    "IR Iran": "Iran",
    "Iran Islamic Republic": "Iran",
    "Islamic Republic of Iran": "Iran",
    # Bosnia and Herzegovina.
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    # DR Congo.
    "DR Congo": "DR Congo",
    "Congo DR": "DR Congo",
    "Democratic Republic of the Congo": "DR Congo",
    # Republic of Ireland.
    "Ireland": "Republic of Ireland",
    "Republic of Ireland": "Republic of Ireland",
    # The confusable pairs, spelled exactly — each must hit its own seed.
    "Australia": "Australia",
    "Austria": "Austria",
    "Iran": "Iran",
    "Iraq": "Iraq",
    "Slovakia": "Slovakia",
    "Slovenia": "Slovenia",
}

# Pairs that must NEVER cross-resolve: feeding the first must not return the
# second's rating (and the values differ in the seed, so a swap is detectable).
CONFUSABLE_PAIRS = [
    ("Austria", "Australia"),
    ("Australia", "Austria"),
    ("Iran", "Iraq"),
    ("Iraq", "Iran"),
    ("Slovakia", "Slovenia"),
    ("Slovenia", "Slovakia"),
]

# Clearly non-international club / test sides — must stay unseeded so the
# run_daily guard drops the Elo layer instead of inventing an edge.
UNKNOWN_SIDES = [
    "Manchester United",
    "Real Madrid CF",
    "Random FC",
    "Boca Juniors",
    "",
    "   ",
]


def _check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def test_every_seed_resolves_to_itself():
    """Exact canonical name -> its own key and rating (the strongest guarantee,
    covering every seeded qualifier)."""
    for key in RATINGS:
        rating, matched = elo.lookup_rating(key, RATINGS)
        _check(matched == key, f"{key!r} resolved to {matched!r}, not itself")
        _check(rating == RATINGS[key], f"{key!r} got rating {rating}, not {RATINGS[key]}")


def test_variant_spellings_resolve_to_correct_seed():
    for spelling, expected in VARIANT_SPELLINGS.items():
        _check(expected in RATINGS, f"test bug: {expected!r} not a seed key")
        rating, matched = elo.lookup_rating(spelling, RATINGS)
        _check(matched == expected,
               f"{spelling!r} resolved to {matched!r}, expected {expected!r}")
        _check(rating == RATINGS[expected],
               f"{spelling!r} got rating {rating}, expected {RATINGS[expected]}")


def test_confusable_pairs_never_cross_resolve():
    for query, must_not_be in CONFUSABLE_PAIRS:
        rating, matched = elo.lookup_rating(query, RATINGS)
        _check(matched != must_not_be,
               f"{query!r} cross-resolved to {must_not_be!r}")
        _check(rating != RATINGS[must_not_be] or RATINGS.get(query) == RATINGS[must_not_be],
               f"{query!r} returned {must_not_be!r}'s rating {rating}")


def test_unknown_sides_stay_unseeded():
    for name in UNKNOWN_SIDES:
        _check(not elo.is_seeded(name, RATINGS),
               f"{name!r} unexpectedly resolved to a seed")
        _check(elo.get_rating(name, RATINGS) == elo.DEFAULT_RATING,
               f"{name!r} did not fall back to DEFAULT_RATING")


def test_get_rating_exact_unchanged():
    for key in ("Spain", "Argentina", "Brazil", "United States", "Qatar"):
        _check(elo.get_rating(key, RATINGS) == RATINGS[key],
               f"get_rating({key!r}) changed")


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failures = 0
    for t in tests:
        try:
            t()
            print(f"  ok   {t.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"  FAIL {t.__name__}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
