import pytest
from fastapi.testclient import TestClient

from api.main import app
from tests.conftest import needs_binary

client = TestClient(app)


def test_health():
    body = client.get("/health").json()
    assert body["status"] == "ok" and body["stations"] == 250


def test_station_search():
    hits = client.get("/stations", params={"q": "hauz khas"}).json()
    assert hits[0]["name"] == "Hauz Khas"


@needs_binary
def test_route_with_informal_names():
    r = client.get("/route", params={"src": "rithala", "dst": "huda city centre"})
    assert r.status_code == 200
    body = r.json()
    assert body["from"] == "Rithala" and body["to"] == "Millennium City Centre Gurugram"
    assert body["interchanges"] == 2


@needs_binary
def test_route_reports_typo_correction():
    body = client.get("/route", params={"src": "rajeev chowk", "dst": "AIIMS"}).json()
    assert body["corrections"]["source"]["used"] == "Rajiv Chowk"


@needs_binary
def test_ambiguous_station_gives_409_with_candidates():
    r = client.get("/route", params={"src": "airport", "dst": "AIIMS"})
    assert r.status_code == 409
    assert "Airport(T-3)" in r.json()["detail"]["source"]["candidates"]


@needs_binary
def test_unknown_station_gives_404():
    assert client.get("/route", params={"src": "zzqqxx", "dst": "AIIMS"}).status_code == 404


@needs_binary
def test_same_station_gives_422():
    assert client.get("/route", params={"src": "AIIMS", "dst": "aiims"}).status_code == 422


@needs_binary
def test_fare():
    body = client.get("/fare", params={"src": "AIIMS", "dst": "Noida City Centre"}).json()
    assert body["fare_inr"] > 0 and "estimate" in body["note"].lower()


def test_chat_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert client.post("/chat", json={"message": "hi"}).status_code == 503


def test_chat_validates_input():
    assert client.post("/chat", json={"message": ""}).status_code == 422
