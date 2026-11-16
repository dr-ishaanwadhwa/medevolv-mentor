"""Feedback retention: a reported YouTube video id is cleared after 30 days (PRD V-3); the report row stays."""
import sqlite3
import time

from api import store


def test_video_report_ids_are_cleared_after_30_days(monkeypatch, tmp_path):
    monkeypatch.setenv("APP_DB", str(tmp_path / "app.db"))
    store.add_feedback(None, None, "video_bad", None, target_id="old-video")
    store.add_feedback(None, None, "diagram_wrong", None, target_id="old-diagram")
    con = sqlite3.connect(tmp_path / "app.db")
    with con:
        con.execute("UPDATE feedback SET created_at=?", (time.time() - 31 * 86400,))
    store.add_feedback(None, None, "video_bad", None, target_id="new-video")     # any write purges
    rows = dict(con.execute("SELECT target_id IS NULL, COUNT(*) FROM feedback WHERE kind='video_bad' GROUP BY 1"))
    assert rows == {0: 1, 1: 1}
    assert con.execute("SELECT target_id FROM feedback WHERE kind='diagram_wrong'").fetchone()[0] == "old-diagram"
