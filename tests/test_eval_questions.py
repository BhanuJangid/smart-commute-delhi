import json
from pathlib import Path

from api.stations import resolve

QUESTIONS = json.loads((Path(__file__).resolve().parent.parent / "eval" / "questions.json").read_text(encoding="utf-8"))
VALID_TOOLS = {"get_shortest_route", "search_dmrc_info", "search_station_info"}


def test_expected_tools_are_real_tools():
    for case in QUESTIONS:
        assert set(case["expected_tools"]) <= VALID_TOOLS, case


def test_expected_stations_are_canonical_names():
    for case in QUESTIONS:
        for key in ("src", "dst"):
            if key in case:
                res = resolve(case[key])
                assert res.status == "exact" and res.station.name == case[key], case
