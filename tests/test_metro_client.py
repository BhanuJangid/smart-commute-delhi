import pytest

from api.metro_client import MetroError, find_route
from api.network import load_stations
from tests.conftest import needs_binary

pytestmark = needs_binary


def test_known_route():
    r = find_route("Rithala", "Millennium City Centre Gurugram")
    assert r["found"] and r["stations"] == 33 and r["interchanges"] == 2
    assert r["path"][0] == "Rithala" and r["path"][-1] == "Millennium City Centre Gurugram"
    assert len(r["path"]) == r["stations"]


def test_least_interchange_mode():
    r = find_route("Rajiv Chowk", "Dwarka", "least_interchange")
    assert r["found"] and r["interchanges"] == 0 and r["mode"] == "least_interchange"


def test_unknown_station_raises():
    with pytest.raises(MetroError):
        find_route("Nowhereville", "Rajiv Chowk")


def test_invalid_mode():
    with pytest.raises(ValueError):
        find_route("Rajiv Chowk", "Dwarka", "scenic")


def test_every_station_is_routable_from_rajiv_chowk():
    for st in load_stations():
        if st.name == "Rajiv Chowk":
            continue
        r = find_route("Rajiv Chowk", st.name)
        assert r["found"], f"no route to {st.name}"
