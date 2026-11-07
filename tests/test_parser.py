import pytest

from api.metro_client import MetroError, parse_route

SAMPLE = """
  Route (21 stations, 1 interchanges, ~44 min, fare \u20b950)

  [Blue]
    o Rajiv Chowk
    | Ramakrishna Ashram Marg
    * Rajouri Garden
    -> interchange
  [Pink]
    o Rajouri Garden
    | Mayapuri
    * Naraina Vihar
"""


def test_parses_header_and_segments():
    r = parse_route(SAMPLE)
    assert r["found"] is True
    assert (r["stations"], r["interchanges"], r["minutes"], r["fare_inr"]) == (21, 1, 44.0, 50)
    assert [s["line"] for s in r["segments"]] == ["Blue", "Pink"]
    assert r["segments"][0] == {"line": "Blue", "from": "Rajiv Chowk", "to": "Rajouri Garden", "stops": 2}
    assert r["interchange_at"] == ["Rajouri Garden"]


def test_path_does_not_duplicate_interchange_station():
    path = parse_route(SAMPLE)["path"]
    assert path == ["Rajiv Chowk", "Ramakrishna Ashram Marg", "Rajouri Garden", "Mayapuri", "Naraina Vihar"]


def test_no_route():
    assert parse_route("No route found.") == {"found": False}


def test_garbage_raises():
    with pytest.raises(MetroError):
        parse_route("something unexpected")


def test_singular_interchange_and_parenthesised_line_name():
    text = (
        "  Route (6 stations, 1 interchange, ~16 min, fare \u20b930)\n\n"
        "  [Yellow]\n    o Rajiv Chowk\n    * New Delhi\n    -> interchange\n"
        "  [Orange (Airport)]\n    o New Delhi\n    | Shivaji Stadium\n    * Airport(T-3)\n"
    )
    r = parse_route(text)
    assert r["interchanges"] == 1
    assert [s["line"] for s in r["segments"]] == ["Yellow", "Orange (Airport)"]
