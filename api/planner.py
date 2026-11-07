"""Resolves free-text station names, then asks the C++ engine for the route.

Shared by the REST endpoints and the LangChain tool so both behave identically.
"""
from . import metro_client
from .stations import Resolution, resolve


def _describe(res: Resolution) -> dict:
    return {
        "status": res.status,
        "candidates": [s.name for s in res.candidates],
    }


def plan_route(source: str, destination: str, mode: str = "fastest") -> dict:
    """Return {"status": "ok", ...route...} or {"status": "needs_clarification"|"not_found"|"same_station", ...}."""
    src, dst = resolve(source), resolve(destination)

    problems = {}
    for label, query, res in (("source", source, src), ("destination", destination, dst)):
        if res.status == "not_found":
            problems[label] = {"query": query, **_describe(res)}
        elif res.status == "ambiguous":
            problems[label] = {"query": query, **_describe(res)}
    if problems:
        kind = "not_found" if all(p["status"] == "not_found" for p in problems.values()) else "needs_clarification"
        return {"status": kind, "problems": problems}

    assert src.station and dst.station
    if src.station.id == dst.station.id:
        return {"status": "same_station", "station": src.station.name}

    route = metro_client.find_route(src.station.name, dst.station.name, mode)
    route["status"] = "ok" if route.get("found") else "no_route"
    # Tell the caller when a typo was auto-corrected so it can mention it.
    corrections = {}
    if src.status == "fuzzy":
        corrections["source"] = {"typed": source, "used": src.station.name}
    if dst.status == "fuzzy":
        corrections["destination"] = {"typed": destination, "used": dst.station.name}
    if corrections:
        route["corrections"] = corrections
    return route
