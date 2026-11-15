"""Records what the pipeline did for one question, step by step, so the UI can show the whole process.

    tr = trace.start(listener)       # listener(step) is called as each step lands (live progress in the UI)
    ... answer(question) ...         # pipeline code calls trace.record(...) at each stage
    tr.steps                         # list[Step] in order, each with its own duration

Recording is a no-op when no trace is active, so CLI runs and the eval harness are unaffected.
"""
from __future__ import annotations

import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Callable

STAGES = {   # stage -> (icon, plain-language label) used by the UI
    "guard": ("🛡️", "Safety check"),
    "route": ("🧭", "Routing"),
    "link": ("🔗", "Symptom linking"),
    "graph": ("🕸️", "Knowledge graph"),
    "decompose": ("🧩", "Question splitting"),
    "retrieve": ("📖", "Textbook search"),
    "filter": ("🧹", "Evidence filter"),
    "evidence": ("📋", "Evidence assembled"),
    "llm": ("🤖", "Language model"),
    "cite": ("🔎", "Citation check"),
    "crosscheck": ("✅", "Graph cross-check"),
    "safety": ("🩺", "Patient safety check"),
    "refuse": ("⛔", "Declined"),
}


@dataclass
class Step:
    stage: str
    title: str
    detail: str = ""
    status: str = "ok"            # ok | warn | stop
    data: dict = field(default_factory=dict)
    ms: float = 0.0               # time spent in this step

    @property
    def icon(self) -> str:
        return STAGES.get(self.stage, ("•", ""))[0]


@dataclass
class Trace:
    listener: Callable[[Step], None] | None = None
    steps: list[Step] = field(default_factory=list)
    t0: float = field(default_factory=time.perf_counter)

    @property
    def total_ms(self) -> float:
        return (time.perf_counter() - self.t0) * 1000


_current: ContextVar[Trace | None] = ContextVar("trace", default=None)


def start(listener: Callable[[Step], None] | None = None) -> Trace:
    tr = Trace(listener=listener)
    _current.set(tr)
    return tr


def stop() -> None:
    _current.set(None)


def active() -> bool:
    return _current.get() is not None


def record(stage: str, title: str, detail: str = "", status: str = "ok", ms: float = 0.0, **data) -> None:
    tr = _current.get()
    if tr is None:
        return
    s = Step(stage, title, detail, status, data, ms)
    tr.steps.append(s)
    if tr.listener:
        try:
            tr.listener(s)
        except Exception:          # a UI glitch must never break answering
            pass


class timer:
    """with trace.timer() as t: ... ; t.ms"""
    def __enter__(self):
        self._t = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.ms = (time.perf_counter() - self._t) * 1000
        return False
