"""POST /api/events and GET /api/events/summary (PRD 5.3): enum-only, anonymous daily counters."""
import sqlite3

import pytest
from fastapi.testclient import TestClient

from api import events, main, ratelimit


@pytest.fixture
def c(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_DB", str(tmp_path / "app.db"))
    monkeypatch.setenv("FEATURES_FILE", str(tmp_path / "features.json"))
    monkeypatch.delenv("EVENTS_TOKEN", raising=False)
    ratelimit.reset()
    yield TestClient(main.app)
    ratelimit.reset()


def rows(tmp_path):
    con = sqlite3.connect(tmp_path / "app.db")
    try:
        return con.execute("SELECT name, key, count FROM events ORDER BY name, key").fetchall()
    finally:
        con.close()


def test_counts_are_aggregated_per_day_name_and_key(c, tmp_path):
    for _ in range(3):
        assert c.post("/api/events", json={"name": "landing_view"}).status_code == 204
    assert c.post("/api/events", json={"name": "diagram_ok", "props": {"kind": "pathway"}}).status_code == 204
    assert rows(tmp_path) == [("diagram_ok", "", 1), ("diagram_ok", "kind=pathway", 1), ("landing_view", "", 3)]


def test_table_has_no_identifying_columns(c, tmp_path):
    c.post("/api/events", json={"name": "landing_cta"})
    con = sqlite3.connect(tmp_path / "app.db")
    cols = [r[1] for r in con.execute("PRAGMA table_info(events)")]
    con.close()
    assert cols == ["day", "name", "key", "count"]


@pytest.mark.parametrize("body", [
    {"name": "free text about a patient"},                              # unknown name
    {"name": "landing_view", "props": {"kind": "pathway"}},             # props not allowed for this event
    {"name": "diagram_ok", "props": {"kind": "my question text"}},      # value outside the enum
    {"name": "diagram_ok", "props": {"topic": "nephrotic syndrome"}},   # key outside the enum
    {"name": "diagram_ok", "props": {"kind": 3}},                       # non-string value
    {"props": {}},                                                      # missing name
    {"name": ["diagram_ok"]},
])
def test_free_text_and_unknown_enums_are_422(c, body, tmp_path):
    assert c.post("/api/events", json=body).status_code == 422
    assert not (tmp_path / "app.db").exists() or rows(tmp_path) == []


def test_rate_limited_per_client_ip(c):
    codes = [c.post("/api/events", json={"name": "landing_view"}).status_code for _ in range(62)]
    assert codes[:60] == [204] * 60 and codes[60:] == [429, 429]


def test_summary_needs_the_server_token(c, monkeypatch):
    c.post("/api/events", json={"name": "video_click"})
    assert c.get("/api/events/summary").status_code == 404                         # EVENTS_TOKEN unset: endpoint off
    monkeypatch.setenv("EVENTS_TOKEN", "s3cret")
    assert c.get("/api/events/summary").status_code == 401
    assert c.get("/api/events/summary", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert c.get("/api/events/summary?token=s3cret").status_code == 401            # never accepted in the URL
    r = c.get("/api/events/summary?days=7", headers={"Authorization": "Bearer s3cret"})
    assert r.status_code == 200 and r.json()["days"] == 7
    assert [(x["name"], x["key"], x["count"]) for x in r.json()["rows"]] == [("video_click", "", 1)]


def test_every_registered_event_is_postable(c):
    for name, props in events.EVENTS.items():
        body = {"name": name, "props": {k: v[0] for k, v in props.items()}} if props else {"name": name}
        assert c.post("/api/events", json=body).status_code == 204, name
