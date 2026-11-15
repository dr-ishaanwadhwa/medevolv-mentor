"""Shared rate limiter (api/ratelimit.py): bucket maths with a fake clock, then the HTTP seam, including the
uvicorn proxy-header handling that deploy/v2/Dockerfile.api configures (real client IP behind Caddy)."""
import json

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from api import features, ratelimit
from api.ratelimit import DailyCap, TokenBucket, limit

# The exact value in deploy/v2/Dockerfile.api: every private range, so any docker network matches.
FORWARDED_ALLOW_IPS = "172.16.0.0/12,10.0.0.0/8,192.168.0.0/16"
CADDY = ("172.18.0.5", 40000)


@pytest.fixture(autouse=True)
def clean(monkeypatch, tmp_path):
    monkeypatch.setenv("FEATURES_FILE", str(tmp_path / "features.json"))
    ratelimit.reset()
    yield
    ratelimit.reset()


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_bucket_allows_burst_then_refills():
    clk = Clock()
    b = TokenBucket(per_minute=3, clock=clk)
    assert [b.allow("a") for _ in range(4)] == [True, True, True, False]
    assert b.allow("other")                                     # keys are independent
    clk.t += 20                                                 # 3/min = one token per 20 s
    assert b.allow("a") and not b.allow("a")
    assert 1 <= b.retry_after("a") <= 21


def test_bucket_memory_is_bounded(monkeypatch):
    monkeypatch.setattr(ratelimit, "MAX_BUCKETS", 50)
    clk = Clock()
    b = TokenBucket(per_minute=60, clock=clk)
    for i in range(50):
        b.allow(f"ip{i}")
    clk.t += 3600                                               # all idle for an hour
    b.allow("fresh")
    assert len(b._b) < 50


def test_daily_cap_resets_at_midnight():
    day = ["2026-11-15"]
    cap = DailyCap(2, today=lambda: day[0])
    assert [cap.take() for _ in range(3)] == [True, True, False] and cap.used() == 2
    day[0] = "2026-11-16"
    assert cap.take() and cap.used() == 1


def mini_app(per_minute=2):
    app = FastAPI()

    @app.get("/x", dependencies=[Depends(limit("t", per_minute))])
    def x():
        return {"ok": True}

    return app


def behind_caddy(app):
    """What uvicorn does with `--proxy-headers --forwarded-allow-ips <ranges>`, with Caddy as the peer."""
    return TestClient(ProxyHeadersMiddleware(app, trusted_hosts=FORWARDED_ALLOW_IPS), client=CADDY)


def test_429_with_retry_after_and_detail():
    c = TestClient(mini_app(2))
    assert [c.get("/x").status_code for _ in range(2)] == [200, 200]
    r = c.get("/x")
    assert r.status_code == 429 and r.json() == {"detail": "rate_limited"} and int(r.headers["retry-after"]) >= 1


def test_limit_is_per_real_client_ip_behind_the_proxy():
    c = behind_caddy(mini_app(2))
    h = lambda ip: {"X-Forwarded-For": ip}                      # noqa: E731 - what Caddy sets
    assert [c.get("/x", headers=h("203.0.113.7")).status_code for _ in range(3)] == [200, 200, 429]
    assert c.get("/x", headers=h("203.0.113.8")).status_code == 200      # a different user is not throttled


def test_spoofed_x_forwarded_for_does_not_buy_a_fresh_bucket():
    c = behind_caddy(mini_app(2))
    # Caddy appends the real peer address; the client's own claim is on the left and is ignored.
    for fake in ("1.1.1.1", "2.2.2.2", "3.3.3.3"):
        r = c.get("/x", headers={"X-Forwarded-For": f"{fake}, 203.0.113.7"})
    assert r.status_code == 429


def test_xff_from_an_untrusted_peer_is_ignored():
    c = TestClient(ProxyHeadersMiddleware(mini_app(2), trusted_hosts=FORWARDED_ALLOW_IPS), client=("198.51.100.9", 1))
    codes = [c.get("/x", headers={"X-Forwarded-For": f"9.9.9.{i}"}).status_code for i in range(3)]
    assert codes == [200, 200, 429]                             # keyed on the peer, not the header


def test_without_forwarded_allow_ips_every_user_shares_the_proxy_ip():
    """The bug the Dockerfile fix removes: default trusted_hosts is 127.0.0.1, so Caddy's XFF is not believed."""
    c = TestClient(ProxyHeadersMiddleware(mini_app(2), trusted_hosts="127.0.0.1"), client=CADDY)
    codes = [c.get("/x", headers={"X-Forwarded-For": f"203.0.113.{i}"}).status_code for i in range(3)]
    assert codes == [200, 200, 429]                             # three different users, one shared bucket


def test_ratelimit_kill_switch_in_features_file(tmp_path):
    c = TestClient(mini_app(1))
    assert c.get("/x").status_code == 200 and c.get("/x").status_code == 429
    (tmp_path / "features.json").write_text(json.dumps({"ratelimit": False}))
    assert [c.get("/x").status_code for _ in range(5)] == [200] * 5
    assert features.flag("ratelimit") is False


def test_dockerfile_wires_the_forwarded_allow_ips_flag():
    from pathlib import Path
    df = (Path(__file__).resolve().parent.parent / "deploy/v2/Dockerfile.api").read_text()
    assert "--proxy-headers" in df and f'"--forwarded-allow-ips", "{FORWARDED_ALLOW_IPS}"' in df
