"""Tiny SQLite store for saved answers and feedback. APP_DB env var, default var/app.db in the repo root
(never under data/, which is a symlink to the shared checkout)."""
from __future__ import annotations

import json
import os
import secrets
import sqlite3
import time
from pathlib import Path

MAX_PAYLOAD_BYTES = 200 * 1024
_SCHEMA = """
CREATE TABLE IF NOT EXISTS answers (id TEXT PRIMARY KEY, kind TEXT NOT NULL, question TEXT NOT NULL,
                                    payload TEXT NOT NULL, created_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, answer_id TEXT, question TEXT,
                                     kind TEXT NOT NULL, note TEXT, created_at REAL NOT NULL);
"""


class PayloadTooLarge(ValueError):
    pass


def db_path() -> Path:
    return Path(os.getenv("APP_DB") or Path(__file__).resolve().parent.parent / "var" / "app.db")


def _conn() -> sqlite3.Connection:
    p = db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(p)
    con.executescript(_SCHEMA)
    if "target_id" not in {r[1] for r in con.execute("PRAGMA table_info(feedback)")}:     # added with diagram/video reports
        con.execute("ALTER TABLE feedback ADD COLUMN target_id TEXT")
    return con


def save_answer(kind: str, question: str, payload: dict) -> str:
    blob = json.dumps(payload, ensure_ascii=False)
    if len(blob.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise PayloadTooLarge(f"payload exceeds {MAX_PAYLOAD_BYTES // 1024} KB")
    con = _conn()
    try:
        for _ in range(5):
            aid = secrets.token_urlsafe(6)
            try:
                with con:
                    con.execute("INSERT INTO answers VALUES (?,?,?,?,?)", (aid, kind, question, blob, time.time()))
                return aid
            except sqlite3.IntegrityError:
                continue
        raise RuntimeError("could not allocate an id")
    finally:
        con.close()


def get_answer(aid: str) -> dict | None:
    con = _conn()
    try:
        row = con.execute("SELECT id, kind, question, payload, created_at FROM answers WHERE id=?", (aid,)).fetchone()
    finally:
        con.close()
    return None if row is None else {"id": row[0], "kind": row[1], "question": row[2],
                                     "payload": json.loads(row[3]), "created_at": row[4]}


# A "Report this video" keeps the YouTube video id for 30 days, then the id is cleared and the report row stays
# (YouTube API data retention, PRD V-3; purged on every write so no scheduler is needed).
VIDEO_ID_TTL_S = 30 * 86400


def purge_video_ids(con: sqlite3.Connection, now: float | None = None) -> None:
    con.execute("UPDATE feedback SET target_id=NULL WHERE kind='video_bad' AND target_id IS NOT NULL AND created_at < ?",
                ((now if now is not None else time.time()) - VIDEO_ID_TTL_S,))


def add_feedback(answer_id: str | None, question: str | None, kind: str, note: str | None,
                 target_id: str | None = None) -> None:
    con = _conn()
    try:
        with con:
            purge_video_ids(con)
            con.execute("INSERT INTO feedback (answer_id, question, kind, note, created_at, target_id) VALUES (?,?,?,?,?,?)",
                        (answer_id, question, kind, note, time.time(), target_id))
    finally:
        con.close()
