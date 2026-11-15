"""First-party anonymous event counters (PRD 5.3).

POST /api/events  {name, props?}   -> 204. Daily counts in SQLite `events(day, name, key, count)`.
GET  /api/events/summary?days=N    -> counts per day, protected by EVENTS_TOKEN (Authorization: Bearer <token>).

Stores no user id, IP, cookie, question, topic or video id. `name`, every props key and every props value must come
from the fixed registry below; anything else is a 422, so free text cannot be smuggled in. Add an event by adding
it here (and to the PRD's metrics table). Rate limited per client IP through api.ratelimit.
"""
from __future__ import annotations

import hmac
import os
import sqlite3
import time

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, field_validator, model_validator

from api import store
from api.ratelimit import limit

DIAGRAM_KINDS = ("classification", "pathway", "sequence", "case", "drug")      # PRD 4.1 kinds

# name -> {prop key: allowed values}. Names are the ones the PRD's metrics use (sections 2.3, 4.1, 4.L, 4.5).
EVENTS: dict[str, dict[str, tuple[str, ...]]] = {
    "landing_view": {},
    "landing_cta": {},
    "ask_from_landing": {},
    "question_sent_from_landing": {},
    "diagram_request": {"kind": DIAGRAM_KINDS},
    "diagram_ok": {"kind": DIAGRAM_KINDS},
    "diagram_sig_fail": {},
    "videos_shown": {"source": ("api", "fallback")},
    "video_click": {},
    "atlas_sex_switch": {"to": ("male", "female")},
}

_SCHEMA = "CREATE TABLE IF NOT EXISTS events (day TEXT NOT NULL, name TEXT NOT NULL, key TEXT NOT NULL, " \
          "count INTEGER NOT NULL, PRIMARY KEY (day, name, key));"

router = APIRouter()


class EventRequest(BaseModel):
    name: str
    props: dict[str, str] | None = None

    @field_validator("name")
    @classmethod
    def _known_name(cls, v: str) -> str:
        if v not in EVENTS:
            raise ValueError("unknown event name")
        return v

    @model_validator(mode="after")
    def _known_props(self) -> "EventRequest":
        allowed = EVENTS[self.name]
        for k, v in (self.props or {}).items():
            if k not in allowed or v not in allowed[k]:
                raise ValueError(f"props not allowed for {self.name}")
        return self


def _conn() -> sqlite3.Connection:
    p = store.db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p)
    con.execute(_SCHEMA)
    return con


def _day() -> str:
    return time.strftime("%Y-%m-%d", time.gmtime())


def record(name: str, props: dict[str, str] | None = None) -> None:
    """Count one event today: one row for the bare name (key '') and one per prop ('kind=pathway')."""
    keys = [""] + [f"{k}={v}" for k, v in sorted((props or {}).items())]
    con = _conn()
    try:
        with con:
            for key in keys:
                con.execute("INSERT INTO events (day, name, key, count) VALUES (?,?,?,1) "
                            "ON CONFLICT(day, name, key) DO UPDATE SET count = count + 1", (_day(), name, key))
    finally:
        con.close()


def summary(days: int) -> list[dict]:
    since = time.strftime("%Y-%m-%d", time.gmtime(time.time() - (days - 1) * 86400))
    con = _conn()
    try:
        rows = con.execute("SELECT day, name, key, count FROM events WHERE day >= ? ORDER BY day DESC, name, key",
                           (since,)).fetchall()
    finally:
        con.close()
    return [{"day": d, "name": n, "key": k, "count": c} for d, n, k, c in rows]


@router.post("/api/events", status_code=204, dependencies=[Depends(limit("events", per_minute=60))])
def post_event(req: EventRequest) -> None:
    record(req.name, req.props)


@router.get("/api/events/summary")
def get_summary(days: int = Query(30, ge=1, le=366), authorization: str | None = Header(None)):
    token = os.getenv("EVENTS_TOKEN") or ""
    if not token:
        raise HTTPException(404, "Not found")                 # feature off until the server .env sets EVENTS_TOKEN
    given = authorization[7:] if authorization and authorization.lower().startswith("bearer ") else ""
    if not hmac.compare_digest(given.encode(), token.encode()):
        raise HTTPException(401, "unauthorized")
    return {"days": days, "rows": summary(days)}
