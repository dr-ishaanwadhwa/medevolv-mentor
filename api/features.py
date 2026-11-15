"""Runtime feature flags (PRD 5.6, D-9): a small JSON file on the VM, read with an mtime cache on every call, so a
flip needs no restart and no deploy.   GET /api/features -> {"diagram": bool, "videos": bool, "female_atlas": bool}

The file path is FEATURES_FILE (default <repo>/var/features.json). Missing, unreadable, malformed or non-object
file means every flag is false. Only a literal JSON `true` turns a flag on. `ratelimit` is a server-only kill
switch (default ON, false = limiter off); it is never returned to the browser.
"""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from fastapi import APIRouter, Response

CLIENT_FLAGS = ("diagram", "videos", "female_atlas")
SERVER_DEFAULTS = {"ratelimit": True}      # server-only keys and their value when the file says nothing

router = APIRouter()
_lock = threading.Lock()
_cache: dict = {"sig": None, "data": {}}


def features_path() -> Path:
    return Path(os.getenv("FEATURES_FILE") or Path(__file__).resolve().parent.parent / "var" / "features.json")


def _read() -> dict:
    """The parsed file, cached until its (mtime, size) changes. {} on any problem."""
    p = features_path()
    try:
        st = p.stat()
        sig = (str(p), st.st_mtime_ns, st.st_size)
    except OSError:
        sig = None
    with _lock:
        if sig == _cache["sig"]:
            return _cache["data"]
        data: dict = {}
        if sig is not None:
            try:
                raw = json.loads(p.read_text(encoding="utf-8"))
                data = raw if isinstance(raw, dict) else {}
            except (OSError, ValueError):
                data = {}
        _cache["sig"], _cache["data"] = sig, data
        return data


def flags() -> dict[str, bool]:
    data = _read()
    return {k: data.get(k) is True for k in CLIENT_FLAGS}


def flag(name: str) -> bool:
    """One flag. Client flags default false; server keys use SERVER_DEFAULTS; anything else is false."""
    if name in SERVER_DEFAULTS:
        v = _read().get(name)
        return v if isinstance(v, bool) else SERVER_DEFAULTS[name]
    return flags().get(name, False)


@router.get("/api/features")
async def get_features(response: Response) -> dict[str, bool]:
    response.headers["Cache-Control"] = "no-cache"
    return flags()
