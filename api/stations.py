"""Fuzzy station-name resolution.

Users (and LLMs) write "rajeev chowk metro" or "huda city". The C++ CLI only accepts exact or
unambiguous partial names, so we resolve free text to a canonical station name first.
"""
import re
from dataclasses import dataclass, field
from functools import lru_cache

from rapidfuzz import fuzz, process

from .network import Station, load_stations

_NOISE = re.compile(r"\b(metro|station|stn|mtr)\b")
_NON_ALNUM = re.compile(r"[^a-z0-9]+")

ACCEPT_SCORE = 84.0   # best match must score at least this to be accepted without asking
MARGIN = 4.0          # ...and beat the runner-up (a different station) by this much
MIN_CANDIDATE = 62.0  # below this a match is not even worth suggesting

# Common names that differ from the official station name. Keys are normalised queries.
ALIASES = {
    "huda city centre": "Millennium City Centre Gurugram",  # renamed; the C++ CLI knows this too
    "huda city center": "Millennium City Centre Gurugram",
    "huda city": "Millennium City Centre Gurugram",
    "connaught place": "Rajiv Chowk",
    "cp": "Rajiv Chowk",
}


def normalize(text: str) -> str:
    text = _NOISE.sub(" ", text.lower())
    return _NON_ALNUM.sub(" ", text).strip()


@dataclass
class Resolution:
    status: str  # "exact" | "fuzzy" | "ambiguous" | "not_found"
    station: Station | None = None
    candidates: list[Station] = field(default_factory=list)
    score: float = 0.0


@lru_cache(maxsize=1)
def _index() -> tuple[list[str], list[Station], dict[str, list[Station]]]:
    stations = list(load_stations())
    keys = [normalize(s.name) for s in stations]
    exact: dict[str, list[Station]] = {}
    for key, st in zip(keys, stations):
        exact.setdefault(key, []).append(st)
    return keys, stations, exact


def _clear_winner(nq, keys, best_idx, best_score, runner_up) -> bool:
    """Accept a fuzzy match only if it clearly beats the next different station.

    WRatio rewards partial matches, so near-ties are common ("rajeev chowk" vs other "... chowk").
    A plain character-level ratio breaks those ties in favour of the genuine typo.
    """
    if runner_up is None:
        return True
    if best_score - runner_up[1] >= MARGIN:
        return True
    # A near-tie where the runner-up also contains every word of the query ("airport") is
    # genuinely ambiguous. Otherwise let the character-level ratio decide (it favours real typos).
    if set(nq.split()) <= set(keys[runner_up[2]].split()):
        return False
    return fuzz.ratio(nq, keys[best_idx]) - fuzz.ratio(nq, keys[runner_up[2]]) >= 15


def resolve(query: str) -> Resolution:
    keys, stations, exact = _index()
    nq = normalize(query)
    if not nq:
        return Resolution("not_found")

    if nq in ALIASES:
        nq = normalize(ALIASES[nq])

    hits = exact.get(nq)
    if hits:
        if len(hits) == 1:
            return Resolution("exact", hits[0], [hits[0]], 100.0)
        return Resolution("ambiguous", None, hits, 100.0)

    matches = process.extract(nq, keys, scorer=fuzz.WRatio, limit=6)
    if not matches or matches[0][1] < MIN_CANDIDATE:
        return Resolution("not_found")

    best_key, best_score, best_idx = matches[0]
    best = stations[best_idx]
    runner_up = next((m for m in matches[1:] if stations[m[2]].id != best.id), None)
    if best_score >= ACCEPT_SCORE and _clear_winner(nq, keys, best_idx, best_score, runner_up):
        return Resolution("fuzzy", best, [best], float(best_score))

    cands: list[Station] = []
    for _, score, idx in matches:
        if score >= MIN_CANDIDATE and stations[idx] not in cands:
            cands.append(stations[idx])
    return Resolution("ambiguous", None, cands[:5], float(best_score))


def search(query: str, limit: int = 10) -> list[tuple[Station, float]]:
    """Ranked station suggestions for autocomplete-style lookups."""
    keys, stations, _ = _index()
    nq = normalize(query)
    if not nq:
        return [(s, 0.0) for s in stations[:limit]]
    out = []
    for _, score, idx in process.extract(nq, keys, scorer=fuzz.WRatio, limit=limit):
        if score >= MIN_CANDIDATE:
            out.append((stations[idx], float(score)))
    return out
