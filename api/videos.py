"""Suggested YouTube videos (PRD 4.2): POST /api/videos {topic, subject?}.

Works without a key: with no YOUTUBE_API_KEY (or quota used up, or any upstream trouble) the answer is the fallback,
a `youtube.com/results` link built from the topic label only. With a key, a cache miss costs exactly one `search.list`
and one `videos.list` (YouTube Data API v3), and the result is cached per normalised topic.

Rules that keep us inside the YouTube API terms and our own privacy promise:
  * The query is the structured topic label + " lecture MBBS" (never the question or answer prose); it travels in the
    POST body, and nothing here logs it with an IP.
  * YouTube data lives ONLY in `video_cache` ($APP_DB): refreshed after 7 days, deleted after 14 (on every write and at
    API startup), so nothing can reach the 30-day storage limit. `video_search_log` keeps bare timestamps for the
    rolling 24 h search counter (degrade to the fallback at 80 searches).
  * Thumbnails, titles and channel names are passed through unmodified; links are canonical watch URLs.
  * Ranking: allowlisted channels first (api/data/video_channels.json, team-verified, empty by default), then the rest
    in API order; at most 4 cards and at most 2 that are not allowlisted. Blocklisted ids
    (api/data/video_blocklist.json) are never shown.
Copy (`label`) mirrors shared/copy/videos.json (a test keeps them equal).
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sqlite3
import time
from pathlib import Path
from urllib.parse import quote_plus

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api import events, features, store
from api.ratelimit import limit

LABEL = "External videos from YouTube. Not from your textbooks and not checked by MedEvolv."   # = shared/copy/videos.json
TTL_S = 7 * 86400              # refresh after this
PURGE_S = 14 * 86400           # delete after this (always under YouTube's 30-day limit)
WINDOW_S = 24 * 3600
SEARCH_BUDGET = 80             # search.list calls in any rolling 24 h before we stop calling YouTube (V-4)
TIMEOUT_S = 3.0                # whole upstream exchange (V-5)
MIN_S, LONG_S = 4 * 60, 90 * 60  # drop under 4 min; over 90 min is kept but labelled "Long lecture" (PRD 4.2)
QUICK_S = 15 * 60
VIEW_FLOOR = 5000              # a target from the research note, tune later
MAX_CARDS, MAX_UNLISTED = 4, 2
SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
VIDEOS_URL = "https://www.googleapis.com/youtube/v3/videos"
DATA_DIR = Path(__file__).resolve().parent / "data"
CLICKBAIT = ("shortcut", "mnemonic only", "in 1 minute", "in 60 seconds", "#shorts", "trick to remember", "prank",
             "reaction", "you won't believe", "shocking")

router = APIRouter()
_inflight: dict[str, asyncio.Future] = {}


# ---------------------------------------------------------------- helpers

def norm_topic(topic: str) -> str:
    return re.sub(r"\s+", " ", (topic or "").strip().lower())


def query_for(topic: str) -> str:
    return f"{norm_topic(topic)} lecture MBBS"


def fallback_url(topic: str) -> str:
    return "https://www.youtube.com/results?search_query=" + quote_plus(query_for(topic))


def search_params(topic: str, key: str) -> dict:
    """V-0, exactly. `videoEmbeddable` is deliberately not set."""
    return {"part": "snippet", "type": "video", "q": query_for(topic), "order": "relevance", "safeSearch": "strict",
            "relevanceLanguage": "en", "regionCode": "IN", "maxResults": 15, "key": key}


def parse_duration(iso: str) -> int | None:
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m or not any(m.groups()):
        return None
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def duration_label(sec: int) -> str:
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _load_json(name: str) -> list:
    try:
        v = json.loads((DATA_DIR / name).read_text(encoding="utf-8"))
        return v if isinstance(v, list) else []
    except (OSError, ValueError):
        return []


def allowlist() -> set[str]:
    """Channel ids a named person verified (entries without channel_id, verified_by and verified_on are ignored)."""
    return {e["channel_id"] for e in _load_json("video_channels.json")
            if isinstance(e, dict) and all(isinstance(e.get(k), str) and e[k].strip()
                                           for k in ("channel_id", "verified_by", "verified_on"))}


def blocklist() -> set[str]:
    out = set()
    for e in _load_json("video_blocklist.json"):
        vid = e if isinstance(e, str) else e.get("video_id") if isinstance(e, dict) else None
        if isinstance(vid, str) and vid.strip():
            out.add(vid.strip())
    return out


def _key() -> str:
    return os.getenv("YOUTUBE_API_KEY", "").strip()


# ---------------------------------------------------------------- storage

_SCHEMA = ("CREATE TABLE IF NOT EXISTS video_cache (key TEXT PRIMARY KEY, json TEXT NOT NULL, fetched_at INTEGER NOT NULL);"
           "CREATE TABLE IF NOT EXISTS video_search_log (ts INTEGER NOT NULL);")


def _conn() -> sqlite3.Connection:
    p = store.db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p)
    con.executescript(_SCHEMA)
    return con


def purge(now: float | None = None) -> None:
    """Delete cache rows older than 14 days and search-log rows older than 24 h (on every write and at startup)."""
    now = time.time() if now is None else now
    con = _conn()
    try:
        with con:
            con.execute("DELETE FROM video_cache WHERE fetched_at < ?", (int(now - PURGE_S),))
            con.execute("DELETE FROM video_search_log WHERE ts < ?", (int(now - WINDOW_S),))
    finally:
        con.close()


def _cache_get(key: str) -> tuple[dict, int] | None:
    con = _conn()
    try:
        row = con.execute("SELECT json, fetched_at FROM video_cache WHERE key=?", (key,)).fetchone()
    finally:
        con.close()
    return (json.loads(row[0]), row[1]) if row else None


def _cache_put(key: str, payload: dict, now: float) -> None:
    purge(now)
    con = _conn()
    try:
        with con:
            con.execute("INSERT OR REPLACE INTO video_cache (key, json, fetched_at) VALUES (?,?,?)",
                        (key, json.dumps(payload, ensure_ascii=False), int(now)))
    finally:
        con.close()


def searches_last_24h(now: float | None = None) -> int:
    now = time.time() if now is None else now
    con = _conn()
    try:
        return con.execute("SELECT COUNT(*) FROM video_search_log WHERE ts >= ?", (int(now - WINDOW_S),)).fetchone()[0]
    finally:
        con.close()


def _log_search(now: float) -> None:
    con = _conn()
    try:
        with con:
            con.execute("DELETE FROM video_search_log WHERE ts < ?", (int(now - WINDOW_S),))
            con.execute("INSERT INTO video_search_log (ts) VALUES (?)", (int(now),))
    finally:
        con.close()


# ---------------------------------------------------------------- upstream + ranking

async def _fetch(topic: str, key: str) -> list[dict]:
    """One search.list + one videos.list. Raises on any HTTP or network problem (the caller falls back)."""
    async with httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT_S)) as client:
        r = await client.get(SEARCH_URL, params=search_params(topic, key))
        r.raise_for_status()
        ids = [it["id"]["videoId"] for it in r.json().get("items", [])
               if isinstance(it.get("id"), dict) and it["id"].get("videoId")]
        if not ids:
            return []
        r2 = await client.get(VIDEOS_URL, params={"part": "snippet,contentDetails,statistics", "id": ",".join(ids),
                                                  "key": key})
        r2.raise_for_status()
        by_id = {it.get("id"): it for it in r2.json().get("items", [])}
    return [by_id[i] for i in dict.fromkeys(ids) if i in by_id]       # API order, duplicates dropped


def rank(items: list[dict], allow: set[str], block: set[str]) -> list[dict]:
    """Filters (duration, views, clickbait, blocklist, duplicates) then the one ranking rule (see module doc)."""
    cards, seen = [], set()
    for it in items:
        vid, sn = it.get("id"), it.get("snippet") or {}
        if not vid or vid in seen or vid in block:
            continue
        seen.add(vid)
        sec = parse_duration((it.get("contentDetails") or {}).get("duration", ""))
        try:
            views = int((it.get("statistics") or {}).get("viewCount", ""))
        except ValueError:
            views = None
        title = sn.get("title") or ""
        if sec is None or sec < MIN_S or views is None or views < VIEW_FLOOR:
            continue
        if any(c in title.lower() for c in CLICKBAIT):
            continue
        thumb = ((sn.get("thumbnails") or {}).get("medium") or {}).get("url")
        if not thumb:
            continue
        cards.append({"video_id": vid, "title": title, "channel_title": sn.get("channelTitle") or "",
                      "channel_id": sn.get("channelId") or "", "thumbnail_url": thumb, "duration_seconds": sec,
                      "duration_label": duration_label(sec), "view_count": views,
                      "watch_url": f"https://www.youtube.com/watch?v={vid}",
                      "allowlisted": (sn.get("channelId") or "") in allow, "long_lecture": sec > LONG_S})
    listed = [c for c in cards if c["allowlisted"]]
    unlisted = [c for c in cards if not c["allowlisted"]][:MAX_UNLISTED]
    return (listed + unlisted)[:MAX_CARDS]


def _response(topic: str, videos: list[dict], source: str, fetched_at: float | None) -> dict:
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(fetched_at)) if fetched_at else None
    return {"topic": norm_topic(topic), "videos": videos, "fallback_url": fallback_url(topic), "fetched_at": stamp,
            "source": source, "label": LABEL}


async def videos_for(topic: str) -> dict:
    key_api = _key()
    ck = norm_topic(topic)
    now = time.time()
    hit = await asyncio.to_thread(_cache_get, ck)
    if hit and now - hit[1] < TTL_S:
        return _response(topic, hit[0]["videos"], "cache", hit[1])
    if not key_api:
        return _response(topic, [], "fallback", None)
    fut = _inflight.get(ck)
    if fut is not None:                                              # V-6 single flight
        return await asyncio.shield(fut)
    fut = asyncio.get_running_loop().create_future()
    _inflight[ck] = fut
    try:
        res = await _miss(topic, ck, key_api)
        fut.set_result(res)
        return res
    except BaseException as e:                                       # pragma: no cover - _miss never raises
        fut.set_exception(e)
        raise
    finally:
        _inflight.pop(ck, None)


async def _miss(topic: str, ck: str, key_api: str) -> dict:
    now = time.time()
    if await asyncio.to_thread(searches_last_24h, now) >= SEARCH_BUDGET:
        return _response(topic, [], "fallback", None)
    await asyncio.to_thread(_log_search, now)
    try:
        items = await asyncio.wait_for(_fetch(topic, key_api), timeout=TIMEOUT_S)
    except Exception:                                                # noqa: BLE001 - 403 quota, timeout, anything: fallback
        return _response(topic, [], "fallback", None)
    cards = rank(items, allowlist(), blocklist())
    await asyncio.to_thread(_cache_put, ck, {"videos": cards}, now)
    return _response(topic, cards, "api", now)


# ---------------------------------------------------------------- shares carry the topic, never YouTube data (V-12)

YT_FIELDS = frozenset({"videos", "video_id", "channel_title", "channel_id", "thumbnail_url",
                       "duration_seconds", "duration_label", "view_count", "watch_url", "allowlisted", "long_lecture"})


def strip_youtube(obj):
    """A copy of a share payload with every YouTube metadata field removed, at any depth (V-3, V-12)."""
    if isinstance(obj, dict):
        return {k: strip_youtube(v) for k, v in obj.items() if k not in YT_FIELDS}
    if isinstance(obj, list):
        return [strip_youtube(v) for v in obj]
    return obj


# ---------------------------------------------------------------- endpoint

class VideosRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=120)
    subject: str | None = Field(default=None, max_length=120)


@router.on_event("startup")
def _startup_purge() -> None:
    try:
        purge()
    except Exception:                                                # noqa: BLE001 - a read-only disk must not stop the API
        pass


@router.post("/api/videos", dependencies=[Depends(limit("videos", per_minute=30))])
async def post_videos(req: VideosRequest):
    if not features.flag("videos"):
        raise HTTPException(503, "videos_unavailable")
    if not norm_topic(req.topic):
        raise HTTPException(422, "topic is empty")
    res = await videos_for(req.topic)
    try:
        events.record("videos_shown", {"source": "fallback" if res["source"] == "fallback" else "api"})
    except Exception:                                                # noqa: BLE001 - counters never break the request
        pass
    return res
