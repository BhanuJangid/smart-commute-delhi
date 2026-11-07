import pytest

from api.network import load_stations
from api.stations import resolve


@pytest.mark.parametrize(
    "query, expected",
    [
        ("Rajiv Chowk", "Rajiv Chowk"),
        ("rajiv chowk metro station", "Rajiv Chowk"),
        ("rajeev chowk", "Rajiv Chowk"),
        ("connaught place", "Rajiv Chowk"),
        ("huda city centre", "Millennium City Centre Gurugram"),
        ("kashmiri gate", "Kashmere Gate"),
        ("noida city center", "Noida City Centre"),
        ("new dehli", "New Delhi"),
    ],
)
def test_resolves_to_canonical_name(query, expected):
    res = resolve(query)
    assert res.station is not None and res.station.name == expected


def test_ambiguous_returns_candidates_not_a_guess():
    res = resolve("airport")
    assert res.status == "ambiguous" and res.station is None
    assert {"Airport(T-3)", "Terminal-1 IGI Airport"} <= {c.name for c in res.candidates}


@pytest.mark.parametrize("query", ["", "metro", "zzqqxx"])
def test_unknown_is_not_found(query):
    assert resolve(query).status == "not_found"


def test_every_station_resolves_to_itself():
    for st in load_stations():
        res = resolve(st.name)
        assert res.station is not None and res.station.id == st.id, st.name


def test_station_metadata():
    kg = next(s for s in load_stations() if s.name == "Kashmere Gate")
    assert set(kg.lines) == {"Red", "Violet", "Yellow"} and kg.is_interchange
