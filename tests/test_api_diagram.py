"""POST /api/diagram and GET /api/diagram/{id} (PRD 4.1, R1). Seam tests through HTTP; the LLM is mocked."""
import json
import sqlite3
import time
import unicodedata

import pytest
from fastapi.testclient import TestClient

from api import diagram, main, ratelimit
from api.ratelimit import DailyCap
from tests.test_api import client as chat_client, stream  # noqa: F401  (stubbed chat stream fixture)

SECRET = "test-secret-not-real"

CLASSIFY_Q = "Classify beta blockers"
CLASSIFY_A = ("Beta blockers are classified into non-selective and cardioselective agents [1]. "
              "Non-selective beta blockers include propranolol and timolol [1]. "
              "Cardioselective beta blockers include atenolol and metoprolol [2]. "
              "Propranolol must be avoided in asthma [G1].")
CITS = [{"index": 1, "book": "Tripathi Pharmacology", "edition": "8", "chapter": "Adrenergic drugs", "pages": "140",
         "section_id": "kdt/s1"},
        {"index": 2, "book": "Tripathi Pharmacology", "edition": "8", "chapter": "Adrenergic drugs", "pages": "141",
         "section_id": "kdt/s2"}]
GCITS = [{"n": 1, "fact_id": "g-abc", "book": "Goodman & Gilman", "edition": "", "chapter": "Beta blockers", "pages": "301"}]

CLASSIFY_G = {"kind": "classification", "title": "Classification of beta blockers", "nodes": [
    {"id": "a", "label": "Beta blockers", "role": "start", "cites": ["1"]},
    {"id": "b", "label": "Non-selective beta blockers", "cites": ["1"]},
    {"id": "c", "label": "Cardioselective beta blockers", "cites": ["1"]},
    {"id": "d", "label": "Propranolol", "cites": ["1"]},
    {"id": "e", "label": "Atenolol", "cites": ["2"]},
    {"id": "f", "label": "Avoid propranolol in asthma", "role": "warning", "cites": ["G1"]}],
    "edges": [{"from": "a", "to": "b", "label": "includes", "cites": ["1"]},
              {"from": "a", "to": "c", "label": "includes", "cites": ["1"]},
              {"from": "b", "to": "d", "label": "includes", "cites": ["1"]},
              {"from": "c", "to": "e", "label": "includes", "cites": ["2"]},
              {"from": "d", "to": "f", "label": "", "cites": ["G1"]}]}

SEQ_A = ("Angiotensin II stimulates aldosterone release [1]. Aldosterone increases sodium reabsorption [1]. "
         "Sodium retention raises blood volume [2].")


def seq_graph(**edge_over):
    edges = [{"from": "a", "to": "b", "label": "activates", "cites": ["1"]},
             {"from": "b", "to": "c", "label": "increases", "cites": ["1"]},
             {"from": "c", "to": "d", "label": "increases", "cites": ["2"]}]
    for i, e in edge_over.items():
        edges[int(i[1:])] = e
    return {"kind": "sequence", "title": "RAAS", "nodes": [
        {"id": "a", "label": "Angiotensin II", "cites": ["1"]}, {"id": "b", "label": "Aldosterone release", "cites": ["1"]},
        {"id": "c", "label": "Sodium reabsorption", "cites": ["1"]}, {"id": "d", "label": "Blood volume", "cites": ["2"]}],
        "edges": edges}


@pytest.fixture
def env(monkeypatch, tmp_path):
    ff = tmp_path / "features.json"
    ff.write_text('{"diagram": true}')
    monkeypatch.setenv("FEATURES_FILE", str(ff))
    monkeypatch.setenv("APP_DB", str(tmp_path / "app.db"))
    monkeypatch.setenv("DIAGRAM_SIG_SECRET", SECRET)
    monkeypatch.setattr(diagram, "_cap", DailyCap(300))
    monkeypatch.setattr(diagram.diagrams, "build_graph", lambda *a, **k: None)       # no ontology hit by default
    ratelimit.reset()
    calls = []

    def llm(replies):
        it = iter(replies)

        def fake(system, user, **kw):
            calls.append(user)
            r = next(it)
            if isinstance(r, Exception):
                raise r
            return r if isinstance(r, str) else json.dumps(r)
        monkeypatch.setattr(diagram, "chat", fake)
    llm([])
    return {"c": TestClient(main.app), "llm": llm, "calls": calls, "ff": ff, "db": tmp_path / "app.db"}


def body(q=CLASSIFY_Q, a=CLASSIFY_A, cits=CITS, gcits=GCITS, sig=None, **extra):
    return {"question": q, "answer_text": a, "citations": cits, "graph_citations": gcits,
            "answer_sig": sig or diagram.sign_answer(q, a, cits, gcits), **extra}


def post(env, **kw):
    return env["c"].post("/api/diagram", json=body(**kw))


def walk_keys(o):
    if isinstance(o, dict):
        for k, v in o.items():
            yield k
            yield from walk_keys(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk_keys(v)


# ---------------------------------------------------------------- certified (ontology) path

ONT = {"kind": "case", "subject": "Hypertension", "title": "Hypertension: textbook overview for revision",
       "groups": [{"id": "g1", "title": "Presentation"}, {"id": "g2", "title": "First line"}],
       "nodes": [{"id": "n1", "label": "Hypertension", "role": "start", "group": None, "cites": [{"kind": "fact", "n": 1}]},
                 {"id": "n2", "label": "Headache", "role": "step", "group": "g1", "cites": [{"kind": "fact", "n": 1}]},
                 {"id": "n3", "label": "Thiazide 12.5 mg daily", "role": "step", "group": "g2",
                  "cites": [{"kind": "fact", "n": 2}]}],
       "edges": [{"from": "n1", "to": "n2", "label": "", "cites": [{"kind": "fact", "n": 1}]},
                 {"from": "n1", "to": "n3", "label": "", "cites": [{"kind": "fact", "n": 2}]}],
       "facts": [{"n": 1, "fact_id": "F-1", "fact": "SECRET FACT TEXT", "cite": "x", "quote": "SECRET QUOTE",
                  "prov": {"book": "Harrison", "edition": "21", "chapter": "Hypertension", "pages": "2072"}},
                 {"n": 2, "fact_id": "F-2", "fact": "SECRET FACT TEXT", "cite": "x", "quote": "SECRET QUOTE",
                  "prov": {"book": "Harrison", "edition": "21", "chapter": "Hypertension", "pages": "2080"}}]}


def test_ontology_path_returns_pointers_only_and_fact_cites(env, monkeypatch):
    monkeypatch.setattr(diagram.diagrams, "build_graph", lambda *a, **k: json.loads(json.dumps(ONT)))
    r = post(env)
    assert r.status_code == 200
    d = r.json()
    assert (d["status"], d["source"], d["kind"], d["version"]) == ("ok", "ontology", "case", 2)
    assert d["diagram_id"] and not env["calls"]                                   # no LLM on the certified path
    assert "SECRET" not in r.text and not {"quote", "fact"} & set(walk_keys(d))
    assert all("cites" not in g for g in d["groups"])
    assert all(c["kind"] == "fact" for n in d["nodes"] for c in n["cites"])       # D-11: never a passage index
    assert d["fact_sources"] == [{"n": 1, "fact_id": "F-1", "book": "Harrison", "edition": "21", "chapter": "Hypertension",
                                  "pages": "2072"},
                                 {"n": 2, "fact_id": "F-2", "book": "Harrison", "edition": "21", "chapter": "Hypertension",
                                  "pages": "2080"}]
    assert "mg" not in d["nodes"][2]["label"] and "daily" not in d["nodes"][2]["label"]   # no doses in boxes


# ---------------------------------------------------------------- answer path

def test_answer_path_classification_with_graph_fact(env):
    env["llm"]([CLASSIFY_G])
    d = post(env).json()
    assert (d["status"], d["source"], d["kind"]) == ("ok", "answer", "classification")
    assert len(d["nodes"]) == 6 and d["dropped"] == 0
    warn = next(n for n in d["nodes"] if n["role"] == "warning")
    assert warn["cites"] == [{"kind": "fact", "n": 1}]                            # [G1] keeps the answer's number
    assert d["fact_sources"] == GCITS
    assert all(n["cites"] for n in d["nodes"]) and all(e["cites"] for e in d["edges"])


def test_prompt_carries_only_the_answer_and_markers(env):
    env["llm"]([CLASSIFY_G])
    post(env)
    assert CLASSIFY_A in env["calls"][0] and "G1" in env["calls"][0]


@pytest.mark.parametrize("bad_edge, why", [
    ({"from": "d", "to": "c", "label": "increases", "cites": ["2"]}, "reversed"),
    ({"from": "c", "to": "d", "label": "decreases", "cites": ["2"]}, "antonym"),
])
def test_bad_edges_are_dropped_and_never_bridged(env, bad_edge, why):
    env["llm"]([seq_graph(e2=bad_edge)])
    d = post(env, q="RAAS", a=SEQ_A, gcits=[]).json()
    # the only edge to d fails, d would be disconnected: the diagram declines rather than bridging
    assert d["status"] == "declined" and d["reason"] == "too_few_supported_nodes", why


def test_negated_sentence_fails_the_edge(env):
    a = SEQ_A.replace("Sodium retention raises blood volume [2].", "Sodium retention does not raise blood volume [2].")
    env["llm"]([seq_graph()])
    d = post(env, q="RAAS", a=a, gcits=[]).json()
    assert d["status"] == "declined"


def test_valid_sequence_keeps_verbs(env):
    env["llm"]([seq_graph()])
    d = post(env, q="RAAS", a=SEQ_A, gcits=[]).json()
    assert d["status"] == "ok" and [e["label"] for e in d["edges"]] == ["activates", "increases", "increases"]


def test_edge_verb_outside_the_kind_list_is_blanked(env):
    g = seq_graph(e0={"from": "a", "to": "b", "label": "cures", "cites": ["1"]})
    env["llm"]([g])
    d = post(env, q="RAAS", a=SEQ_A, gcits=[]).json()
    assert d["status"] == "ok" and d["edges"][0]["label"] == ""


def test_new_number_in_a_node_is_dropped(env):
    g = json.loads(json.dumps(CLASSIFY_G))
    g["nodes"][4]["label"] = "Atenolol 2nd generation"                            # "2" is not in the cited sentence
    env["llm"]([g])
    d = post(env).json()
    assert d["status"] in ("ok", "declined")
    assert not any("2nd" in n["label"] for n in d["nodes"])


def test_uncited_or_unknown_cites_fail_and_too_many_failures_decline(env):
    g = json.loads(json.dumps(CLASSIFY_G))
    for n in g["nodes"][1:4]:
        n["cites"] = ["7"]                                                        # [7] is not in the answer
    env["llm"]([g])
    d = post(env).json()
    assert d["status"] == "declined" and d["reason"] == "too_few_supported_nodes"


def test_malformed_json_retried_once_then_generator_error(env):
    env["llm"](["not json", "still not json"])
    d = post(env).json()
    assert d == {**d, "status": "declined", "reason": "generator_error"} and len(env["calls"]) == 2
    assert "rejected" in env["calls"][1]


def test_malformed_then_valid_recovers(env):
    env["llm"](["```json\n{oops", CLASSIFY_G])
    assert post(env).json()["status"] == "ok"


def test_llm_exception_and_hang_become_generator_error_and_are_not_cached(env, monkeypatch):
    env["llm"]([RuntimeError("upstream down")])
    assert post(env).json()["reason"] == "generator_error"
    monkeypatch.setattr(diagram, "TOTAL_BUDGET_S", 0.3)

    def hang(*a, **k):
        time.sleep(1.0)
        return json.dumps(CLASSIFY_G)
    monkeypatch.setattr(diagram, "chat", hang)
    t = time.monotonic()
    assert post(env).json()["reason"] == "generator_error"
    assert time.monotonic() - t < 0.9
    env["llm"]([CLASSIFY_G])                                                      # a retry may now succeed
    assert post(env).json()["status"] == "ok"


def test_too_few_cited_sentences_declines_without_llm(env):
    d = post(env, a="Beta blockers are drugs [1]. They lower heart rate [1].").json()
    assert d["reason"] == "too_few_supported_nodes" and not env["calls"]


def test_patient_scoped_question_declines(env):
    d = post(env, q="Should I take propranolol for my mother's asthma?").json()
    assert d["status"] == "declined" and not env["calls"]


# ---------------------------------------------------------------- cache, storage, shared read

def test_cache_hit_skips_llm_and_raw_question_is_never_stored(env):
    env["llm"]([CLASSIFY_G])
    d1 = post(env).json()
    d2 = post(env).json()
    assert d1 == d2 and len(env["calls"]) == 1
    con = sqlite3.connect(env["db"])
    dump = "\n".join(con.iterdump())
    assert CLASSIFY_Q not in dump and "Classify" not in dump


def test_get_stored_diagram_and_404(env):
    env["llm"]([CLASSIFY_G])
    d = post(env).json()
    g = env["c"].get(f"/api/diagram/{d['diagram_id']}")
    assert g.status_code == 200 and g.json() == d
    assert env["c"].get("/api/diagram/nope").status_code == 404


def test_racing_identical_requests_share_one_diagram_id(env, monkeypatch):
    # both requests miss the cache (as two tabs posting at once would); the second must not replace the first's row
    monkeypatch.setattr(diagram, "_cache_get", lambda key: None)
    env["llm"]([CLASSIFY_G, CLASSIFY_G])
    d1 = post(env).json()
    d2 = post(env).json()
    assert d1["diagram_id"] == d2["diagram_id"]
    assert env["c"].get(f"/api/diagram/{d1['diagram_id']}").status_code == 200


def test_expired_rows_are_gone(env, monkeypatch):
    env["llm"]([CLASSIFY_G])
    d = post(env).json()
    con = sqlite3.connect(env["db"])
    with con:
        con.execute("UPDATE diagram_cache SET created_at=?", (time.time() - 91 * 86400,))
    assert env["c"].get(f"/api/diagram/{d['diagram_id']}").status_code == 404


# ---------------------------------------------------------------- authenticity, limits, flags

def test_bad_signature_403_and_no_secret_403(env, monkeypatch):
    r = post(env, sig="0" * 64)
    assert r.status_code == 403 and r.json() == {"detail": "bad_signature"}
    b = body()
    monkeypatch.delenv("DIAGRAM_SIG_SECRET")
    assert env["c"].post("/api/diagram", json=b).status_code == 403


def test_signature_survives_nfd_crlf_key_order_and_extra_keys(env):
    book = "Ganong’s Physiology é"
    cits = [{**CITS[0], "book": book}, CITS[1]]
    sig = diagram.sign_answer(CLASSIFY_Q, CLASSIFY_A.replace(". ", ".\n"), cits, GCITS)
    sent = [dict(reversed(list({**cits[0], "book": unicodedata.normalize("NFD", book), "cited": True,
                                "excerpt": "x"}.items()))), CITS[1]]
    env["llm"]([CLASSIFY_G])
    r = env["c"].post("/api/diagram", json=body(a=CLASSIFY_A.replace(". ", ".\r\n"), cits=sent, sig=sig))
    assert r.status_code == 200


def test_changed_text_float_index_unsorted(env):
    good = body()
    assert env["c"].post("/api/diagram", json={**good, "answer_text": good["answer_text"] + "x"}).status_code == 403
    fl = [{**CITS[0], "index": 1.0}, CITS[1]]
    assert env["c"].post("/api/diagram", json={**good, "citations": fl}).status_code == 422
    assert env["c"].post("/api/diagram", json={**good, "citations": [CITS[0] | {"index": "1"}, CITS[1]]}).status_code == 422
    assert env["c"].post("/api/diagram", json={**good, "citations": list(reversed(CITS))}).status_code == 422


def test_flag_off_503_for_post_and_get(env):
    env["ff"].write_text('{"diagram": false}')
    assert post(env).status_code == 503 and post(env).json() == {"detail": "diagram_unavailable"}
    assert env["c"].get("/api/diagram/abc").status_code == 503


def test_rate_limit_429_after_10_per_minute(env):
    env["llm"]([CLASSIFY_G])
    codes = [post(env).status_code for _ in range(11)]
    assert codes[:10] == [200] * 10 and codes[10] == 429


def test_daily_cap_gives_budget_and_is_not_cached(env, monkeypatch):
    monkeypatch.setattr(diagram, "_cap", DailyCap(0))
    d = post(env).json()
    assert d["reason"] == "budget" and not env["calls"]
    monkeypatch.setattr(diagram, "_cap", DailyCap(5))
    env["llm"]([CLASSIFY_G])
    assert post(env).json()["status"] == "ok"


# ---------------------------------------------------------------- the chat stream signs; /api/diagram accepts it

def test_answer_event_signature_round_trip(chat_client, monkeypatch, tmp_path):  # noqa: F811
    monkeypatch.setenv("DIAGRAM_SIG_SECRET", SECRET)
    monkeypatch.setenv("APP_DB", str(tmp_path / "app.db"))
    ff = tmp_path / "f.json"
    ff.write_text('{"diagram": true}')
    monkeypatch.setenv("FEATURES_FILE", str(ff))
    ratelimit.reset()
    ans = stream(chat_client)[2][1]
    assert ans["answer_sig"] and ans["graph_citations"] == []
    b = {"question": "Inferior MI?", "answer_text": ans["text"], "citations": ans["citations"],
         "graph_citations": ans["graph_citations"], "answer_sig": ans["answer_sig"]}
    r = chat_client.post("/api/diagram", json=b)
    assert r.status_code == 200 and r.json()["status"] == "declined"             # one cited sentence: declines, not 403
    assert chat_client.post("/api/diagram", json={**b, "answer_text": b["answer_text"] + "!"}).status_code == 403


def test_no_secret_means_no_signature_on_the_answer(chat_client, monkeypatch):  # noqa: F811
    monkeypatch.delenv("DIAGRAM_SIG_SECRET", raising=False)
    assert stream(chat_client)[2][1]["answer_sig"] is None


def test_graph_citation_pointers_parse_the_fact_line():
    lines = ["Propranolol is contraindicated in asthma (Goodman & Gilman, Beta blockers, pp. 301-302)",
             "No cite here"]
    out = diagram.graph_citation_pointers(lines, [2, 1, 9])
    assert [p["n"] for p in out] == [1, 2]
    assert out[0]["book"] == "Goodman & Gilman" and out[0]["chapter"] == "Beta blockers" and out[0]["pages"] == "301-302"
    assert out[1]["book"] == "Clinical knowledge graph" and out[1]["pages"] == ""


def test_patient_scoped_or_declined_answers_are_not_signed(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setenv("DIAGRAM_SIG_SECRET", SECRET)

    def ans(status):
        return SimpleNamespace(text=CLASSIFY_A, status=status, cited=[1], hits=[], graph_cited=[],
                               plan=SimpleNamespace(route="single", graph_facts=[]))
    assert main._answer_event(ans("answered"), CLASSIFY_Q).answer_sig
    assert main._answer_event(ans("answered"), "My father has asthma, should he take propranolol?").answer_sig is None
    assert main._answer_event(ans("insufficient"), CLASSIFY_Q).answer_sig is None
