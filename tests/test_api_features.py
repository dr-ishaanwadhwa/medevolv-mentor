"""GET /api/features: runtime flags from a JSON file with an mtime cache (PRD 5.6, D-9)."""
import json
import os

import pytest
from fastapi.testclient import TestClient

from api import features, main


@pytest.fixture
def ff(monkeypatch, tmp_path):
    p = tmp_path / "features.json"
    monkeypatch.setenv("FEATURES_FILE", str(p))
    return p


def get():
    r = TestClient(main.app).get("/api/features")
    assert r.status_code == 200
    return r.json()


ALL_FALSE = {"diagram": False, "videos": False, "female_atlas": False}


def test_missing_file_means_all_false(ff):
    assert get() == ALL_FALSE


@pytest.mark.parametrize("content", ["not json", "[]", '"x"', "", "null"])
def test_unreadable_or_wrong_shape_means_all_false(ff, content):
    ff.write_text(content)
    assert get() == ALL_FALSE


def test_reads_flags_and_only_literal_true_counts(ff):
    ff.write_text(json.dumps({"diagram": True, "videos": "true", "female_atlas": 1, "extra": True}))
    assert get() == {"diagram": True, "videos": False, "female_atlas": False}     # no extra keys leak either


def test_flip_is_picked_up_without_restart_even_with_same_size_and_atomic_mv(ff, tmp_path):
    ff.write_text('{"videos": false}')
    assert get()["videos"] is False
    tmp = tmp_path / "f.tmp"                                     # the documented flip: write a temp file, then mv
    tmp.write_text('{"videos": true }')                          # same length as before
    os.replace(tmp, ff)
    assert get()["videos"] is True
    ff.unlink()
    assert get() == ALL_FALSE


def test_ratelimit_key_is_server_only_and_defaults_on(ff):
    assert features.flag("ratelimit") is True
    ff.write_text('{"ratelimit": false}')
    assert features.flag("ratelimit") is False and "ratelimit" not in get()
    ff.write_text('{"ratelimit": "no"}')
    assert features.flag("ratelimit") is True                    # non-boolean falls back to the default
