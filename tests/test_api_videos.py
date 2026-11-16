"""POST /api/videos (PRD 4.2, R2). Seam tests through HTTP; YouTube is mocked with httpx.MockTransport.

No test here talks to YouTube: every upstream call goes to a fake transport that records the request.
"""
import asyncio
import json
import logging
import sqlite3
import time
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from api import main, ratelimit, videos

TOPIC = "Nephrotic syndrome"
ROOT = Path(__file__).resolve().parents[1]


def item(vid, *, channel="UCx", title=None, dur="PT20M34S", views="123456", thumb=True):
    sn = {"title": title or f"Lecture {vid}", "channelTitle": f"Channel {channel}", "channelId": channel}
    if thumb:
        sn["thumbnails"] = {"medium": {"url": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg"}}
    return {"id": vid, "snippet": sn, "contentDetails": {"duration": dur}, "statistics": {"viewCount": views}}


class FakeYouTube:
    """Records every request; answers search.list with ids and videos.list with the matching items."""

    def __init__(self, items=None, status=200, body=None, delay=0.0):
        self.items = items if items is not None else [item(f"v{i}") for i in range(6)]
        self.status, self.body, self.delay = status, body, delay
        self.requests: list[httpx.Request] = []

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.delay:
            await asyncio.sleep(self.delay)
        if self.status != 200:
            return httpx.Response(self.status, json=self.body or {})
        if request.url.path.endswith("/search"):
            return httpx.Response(200, json={"items": [{"id": {"kind": "youtube#video", "videoId": it["id"]}}
                                                       for it in self.items]})
        ids = request.url.params["id"].split(",")
        return httpx.Response(200, json={"items": [it for it in self.items if it["id"] in ids]})

    def paths(self):
        return [r.url.path.rsplit("/", 1)[-1] for r in self.requests]


@pytest.fixture
def env(monkeypatch, tmp_path):
    ff = tmp_path / "features.json"
    ff.write_text('{"videos": true}')
    monkeypatch.setenv("FEATURES_FILE", str(ff))
    monkeypatch.setenv("APP_DB", str(tmp_path / "app.db"))
    monkeypatch.setenv("YOUTUBE_API_KEY", "test-key-not-real")
    monkeypatch.setattr(videos, "DATA_DIR", tmp_path)                 # empty allowlist and blocklist by default
    (tmp_path / "video_channels.json").write_text("[]")
    (tmp_path / "video_blocklist.json").write_text("[]")
    ratelimit.reset()
    fake = FakeYouTube()
    real = httpx.AsyncClient

    def client_factory(**kw):
        return real(transport=httpx.MockTransport(fake), **kw)
    monkeypatch.setattr(videos.httpx, "AsyncClient", client_factory)
    yield {"c": TestClient(main.app), "yt": fake, "ff": ff, "dir": tmp_path, "db": tmp_path / "app.db"}
    ratelimit.reset()


def post(env, topic=TOPIC, **extra):
    return env["c"].post("/api/videos", json={"topic": topic, **extra})


# ---------------------------------------------------------------- V-0, V-2

def test_search_parameters_are_exactly_v0(env):
    r = post(env)
    assert r.status_code == 200 and r.json()["source"] == "api"
    search, vids = env["yt"].requests
    assert search.url.path == "/youtube/v3/search"
    assert dict(search.url.params) == {"part": "snippet", "type": "video", "q": "nephrotic syndrome lecture MBBS",
                                       "order": "relevance", "safeSearch": "strict", "relevanceLanguage": "en",
                                       "regionCode": "IN", "maxResults": "15", "key": "test-key-not-real"}
    assert "videoEmbeddable" not in search.url.params
    assert vids.url.path == "/youtube/v3/videos"
    assert vids.url.params["part"] == "snippet,contentDetails,statistics"
    assert vids.url.params["id"] == "v0,v1,v2,v3,v4,v5"


def test_response_shape_label_and_no_related(env):
    body = post(env).json()
    assert set(body) == {"topic", "videos", "fallback_url", "fetched_at", "source", "label"}
    assert "related" not in body
    assert body["label"] == json.loads((ROOT / "shared/copy/videos.json").read_text())["label"]
    assert body["fallback_url"] == "https://www.youtube.com/results?search_query=nephrotic+syndrome+lecture+MBBS"
    card = body["videos"][0]
    assert card == {"video_id": "v0", "title": "Lecture v0", "channel_title": "Channel UCx", "channel_id": "UCx",
                    "thumbnail_url": "https://i.ytimg.com/vi/v0/mqdefault.jpg", "duration_seconds": 1234,
                    "duration_label": "20:34", "view_count": 123456, "watch_url": "https://www.youtube.com/watch?v=v0",
                    "allowlisted": False, "long_lecture": False}


def test_cache_hit_makes_no_youtube_call(env):
    assert post(env).json()["source"] == "api"
    assert len(env["yt"].requests) == 2
    again = post(env, topic="  NEPHROTIC   syndrome ")                 # same normalised topic
    assert again.json()["source"] == "cache"
    assert len(env["yt"].requests) == 2


def test_stale_row_is_refreshed_after_7_days(env, monkeypatch):
    post(env)
    con = sqlite3.connect(env["db"])
    with con:
        con.execute("UPDATE video_cache SET fetched_at = ?", (int(time.time() - 8 * 86400),))
    con.close()
    assert post(env).json()["source"] == "api"
    assert env["yt"].paths() == ["search", "videos", "search", "videos"]


def test_purge_on_write_and_at_startup(env):
    videos.purge()                                                     # creates the tables
    con = sqlite3.connect(env["db"])
    old = int(time.time() - 15 * 86400)
    with con:
        con.execute("INSERT INTO video_cache VALUES ('old topic', '{\"videos\": []}', ?)", (old,))
        con.execute("INSERT INTO video_search_log VALUES (?)", (int(time.time() - 25 * 3600),))
    assert videos._startup_purge in main.app.router.on_startup         # registered as an API startup hook
    videos._startup_purge()
    assert con.execute("SELECT COUNT(*) FROM video_cache").fetchone()[0] == 0
    assert con.execute("SELECT COUNT(*) FROM video_search_log").fetchone()[0] == 0
    with con:
        con.execute("INSERT INTO video_cache VALUES ('old topic', '{\"videos\": []}', ?)", (old,))
    post(env)                                                          # a write purges too
    keys = [r[0] for r in con.execute("SELECT key FROM video_cache")]
    con.close()
    assert keys == ["nephrotic syndrome"]


# ---------------------------------------------------------------- fallback paths (V-4, V-5) and keyless mode

def test_no_key_returns_the_fallback_link_and_calls_nothing(env, monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY")
    body = post(env).json()
    assert body["source"] == "fallback" and body["videos"] == []
    assert body["fallback_url"].startswith("https://www.youtube.com/results?search_query=nephrotic+syndrome")
    assert body["label"] and env["yt"].requests == []


def test_rolling_window_degrades_at_80(env):
    videos.purge()
    now = int(time.time())
    con = sqlite3.connect(env["db"])
    with con:
        con.executemany("INSERT INTO video_search_log VALUES (?)", [(now - 3600,)] * 79)
    con.close()
    assert post(env, topic="topic a").json()["source"] == "api"        # the 80th search is allowed
    assert post(env, topic="topic b").json()["source"] == "fallback"   # 80 in the window: stop calling YouTube
    assert env["yt"].paths() == ["search", "videos"]


def test_window_rows_older_than_24h_do_not_count(env):
    videos.purge()
    con = sqlite3.connect(env["db"])
    with con:
        con.executemany("INSERT INTO video_search_log VALUES (?)", [(int(time.time()) - 25 * 3600,)] * 100)
    con.close()
    assert post(env).json()["source"] == "api"


def test_quota_exceeded_403_is_fallback_200(env):
    env["yt"].status, env["yt"].body = 403, {"error": {"errors": [{"reason": "quotaExceeded"}]}}
    r = post(env)
    assert r.status_code == 200 and r.json()["source"] == "fallback"


def test_timeout_is_fallback_within_3_seconds(env):
    env["yt"].delay = 10
    t0 = time.monotonic()
    r = post(env)
    assert r.status_code == 200 and r.json()["source"] == "fallback"
    assert time.monotonic() - t0 < 3.6


def test_upstream_failure_is_not_cached(env):
    env["yt"].status = 500
    assert post(env).json()["source"] == "fallback"
    env["yt"].status = 200
    assert post(env).json()["source"] == "api"


# ---------------------------------------------------------------- filters and ranking (D-12)

def test_duration_view_clickbait_and_thumbnail_filters():
    items = [item("short", dur="PT3M"), item("ok", dur="PT10M"), item("long", dur="PT2H"),
             item("fewviews", views="100"), item("noviews", views=""), item("bait", title="Renal in 60 seconds"),
             item("nothumb", thumb=False), item("ok", dur="PT10M")]
    cards = videos.rank(items, set(), set())
    assert [c["video_id"] for c in cards] == ["ok", "long"]
    assert cards[1]["long_lecture"] is True and cards[1]["duration_label"] == "2:00:00"


def test_ranking_with_empty_allowlist_shows_at_most_2():
    cards = videos.rank([item(f"v{i}") for i in range(6)], set(), set())
    assert [c["video_id"] for c in cards] == ["v0", "v1"]


def test_ranking_allowlisted_first_max_4_max_2_unlisted():
    items = [item("u1", channel="U"), item("a1", channel="A"), item("u2", channel="U"), item("u3", channel="U"),
             item("a2", channel="A"), item("a3", channel="A")]
    cards = videos.rank(items, {"A"}, set())
    assert [c["video_id"] for c in cards] == ["a1", "a2", "a3", "u1"]
    cards = videos.rank(items, {"B"}, set())                            # nothing allowlisted: API order, 2 cards
    assert [c["video_id"] for c in cards] == ["u1", "a1"]


def test_blocklist_hides_a_video(env):
    (env["dir"] / "video_blocklist.json").write_text(json.dumps([{"video_id": "v0", "note": "reported"}, "v1"]))
    ids = [v["video_id"] for v in post(env).json()["videos"]]
    assert ids == ["v2", "v3"]


def test_allowlist_loader_ignores_unverified_entries(env):
    (env["dir"] / "video_channels.json").write_text(json.dumps([
        {"channel_id": "UCgood", "name": "x", "verified_by": "a person", "verified_on": "2026-11-16", "note": ""},
        {"channel_id": "UCnobody", "name": "y", "verified_by": "", "verified_on": "2026-11-16"},
        {"name": "no id"}, "junk"]))
    assert videos.allowlist() == {"UCgood"}
    (env["dir"] / "video_channels.json").write_text("not json")
    assert videos.allowlist() == set()


def test_shipped_allowlist_and_blocklist_are_valid_json_lists():
    for name in ("video_channels.json", "video_blocklist.json"):
        assert isinstance(json.loads((ROOT / "api/data" / name).read_text()), list)


# ---------------------------------------------------------------- single flight (V-6)

def test_concurrent_requests_share_one_upstream_call(env):
    env["yt"].delay = 0.2

    async def both():
        return await asyncio.gather(videos.videos_for(TOPIC), videos.videos_for(TOPIC.upper()))
    a, b = asyncio.run(both())
    assert a["videos"] == b["videos"] and a["source"] == "api"
    assert env["yt"].paths() == ["search", "videos"]


# ---------------------------------------------------------------- privacy (V-7, V-12)

def test_topic_is_never_logged(env, caplog):
    caplog.set_level(logging.DEBUG)
    post(env, topic="Secret topic phrase")
    assert not any("secret topic phrase" in r.getMessage().lower() for r in caplog.records)


def test_share_payload_drops_youtube_fields(env, monkeypatch, tmp_path):
    payload = {"answer": {"text": "t", "status": "answered", "route": "single", "citations": []}, "spatial": [],
               "topic": "nephrotic syndrome", "related": [{"id": "x", "label": "Proteinuria"}],
               "videos": [{"video_id": "v0", "title": "T", "thumbnail_url": "https://i.ytimg.com/x"}],
               "extra": {"watch_url": "https://www.youtube.com/watch?v=v0", "keep": 1}}
    r = env["c"].post("/api/answers", json={"kind": "chat", "question": "q", "payload": payload})
    assert r.status_code == 200
    stored = env["c"].get(f"/api/answers/{r.json()['id']}").json()["payload"]
    assert stored["topic"] == "nephrotic syndrome" and stored["related"] == payload["related"]
    assert "videos" not in stored and stored["extra"] == {"keep": 1}


def test_cache_holds_only_videos_and_no_question(env):
    post(env)
    con = sqlite3.connect(env["db"])
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    rows = con.execute("SELECT key, json FROM video_cache").fetchall()
    con.close()
    assert rows[0][0] == "nephrotic syndrome" and set(json.loads(rows[0][1])) == {"videos"}
    assert {"video_cache", "video_search_log"} <= tables


# ---------------------------------------------------------------- errors

@pytest.mark.parametrize("body", [{}, {"topic": ""}, {"topic": "x" * 121}, {"topic": "   "}])
def test_bad_topic_422(env, body):
    assert env["c"].post("/api/videos", json=body).status_code == 422
    assert env["yt"].requests == []


def test_flag_off_503(env):
    env["ff"].write_text('{"videos": false}')
    r = post(env)
    assert r.status_code == 503 and r.json()["detail"] == "videos_unavailable"
    assert env["yt"].requests == []


def test_rate_limit_429_after_30_per_minute(env, monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY")
    codes = [post(env).status_code for _ in range(31)]
    assert codes[:30] == [200] * 30 and codes[30] == 429


def test_key_never_in_response(env):
    assert "test-key-not-real" not in post(env).text
