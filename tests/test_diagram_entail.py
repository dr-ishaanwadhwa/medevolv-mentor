"""Entailment check after the word rules (api.diagram_entail; wiki: diagram-validator-lexical-limits). LLM mocked.

The check can only REMOVE boxes and arrows: an item survives only when the verifier says "supported" AND its quote is a
verbatim span of a sentence the item itself cites. Verifier trouble declines "verifier_unavailable", never cached.
"""
import json
import time

import pytest

from api import diagram, diagram_entail as E, diagram_validate as V
from tests.test_api_diagram import CLASSIFY_A, CLASSIFY_G, ONT, env, post, support_all  # noqa: F401  (fixture)
from tests.test_diagram_redteam2 import run
from tests.test_diagram_redteam4 import AMINO_KIDS, BETA_BLOCKERS, COMPARISON, DIGOXIN, RATE_KIDS, cls


def by_label(label, verdict="not_supported", quote=""):
    """A verifier that rejects the box (or an arrow into/out of it, when label is a (src, tgt) pair) and supports the
    rest with a real quote."""
    def decide(it, sents):
        if (it["type"] == "box" and it["label"] == label) or (it["type"] == "arrow" and (it["from"], it["to"]) == label):
            return verdict, quote
        return support_all(it, sents)
    return decide


def labels(d):
    return {n["label"] for n in d["nodes"]}


def arrows(d):
    lab = {n["id"]: n["label"] for n in d["nodes"]}
    return {(lab[e["from"]], lab[e["to"]]) for e in d["edges"]}


# ---------------------------------------------------------------- through the endpoint

def test_supported_items_are_kept_with_their_evidence(env):
    env["llm"]([CLASSIFY_G])
    d = post(env).json()
    assert d["status"] == "ok" and len(d["nodes"]) == 6 and len(d["edges"]) == 4
    assert all(n["evidence"] for n in d["nodes"]) and all(e["evidence"] for e in d["edges"])
    assert E.norm(d["nodes"][0]["evidence"]) in E.norm(CLASSIFY_A)    # a span of the answer, markers stripped
    assert len(env["vcalls"]) == 1
    assert diagram.get_stored(d["diagram_id"])["nodes"][0]["evidence"] == d["nodes"][0]["evidence"]


WARN = "Avoid propranolol in asthma"          # cites [G1] only: "Propranolol must be avoided in asthma [G1]."


def test_not_supported_box_is_dropped_with_its_arrow(env):
    env["llm"]([CLASSIFY_G])
    env["verifier"](by_label(WARN))
    d = post(env).json()
    assert d["status"] == "ok" and WARN not in labels(d)
    assert ("Propranolol", WARN) not in arrows(d) and d["dropped"] == 1 and d["fact_sources"] == []


def test_fabricated_quote_drops_the_box(env):
    env["llm"]([CLASSIFY_G])
    env["verifier"](by_label(WARN, "supported", "Propranolol must be avoided in asthma and COPD"))
    d = post(env).json()
    assert d["status"] == "ok" and WARN not in labels(d)


def test_quote_from_a_sentence_the_box_does_not_cite_drops_it(env):
    """The warning box cites [G1]; the quote is real answer text, but from a [1] sentence."""
    env["llm"]([CLASSIFY_G])
    env["verifier"](by_label(WARN, "supported", "Non-selective beta blockers include propranolol"))
    d = post(env).json()
    assert d["status"] == "ok" and WARN not in labels(d)


def test_quote_normalisation_allows_case_whitespace_and_markers(env):
    env["llm"]([CLASSIFY_G])
    env["verifier"](by_label(WARN, "supported", "propranolol   MUST be avoided in asthma [G1]."))
    assert WARN in labels(post(env).json())


def test_unsupported_arrow_is_dropped_and_never_bridged(env):
    """The warning box's only arrow is rejected: the box is left alone, so it is left out (1 of 6, under V6)."""
    env["llm"]([CLASSIFY_G])
    env["verifier"](by_label(("Propranolol", "Avoid propranolol in asthma")))
    d = post(env).json()
    assert d["status"] == "ok" and "Avoid propranolol in asthma" not in labels(d)
    assert ("Propranolol", "Avoid propranolol in asthma") not in arrows(d)


def test_item_missing_from_the_reply_is_dropped(env):
    env["llm"]([CLASSIFY_G])
    env["verifier"](lambda it, s: None if it.get("label") == WARN else support_all(it, s))
    d = post(env).json()
    assert d["status"] == "ok" and WARN not in labels(d)


def test_graph_falling_apart_declines_too_few_supported_nodes(env):
    env["llm"]([CLASSIFY_G])
    env["verifier"](lambda it, s: ("not_supported", "") if it.get("label") in ("Beta blockers", "Propranolol")
                    else support_all(it, s))
    d = post(env).json()
    assert (d["status"], d["reason"]) == ("declined", "too_few_supported_nodes")


@pytest.mark.parametrize("reply", [RuntimeError("upstream down"), "not json", '{"items": "x"}', '{"items": []}'])
def test_verifier_error_is_verifier_unavailable_and_not_cached(env, monkeypatch, reply):
    env["llm"]([CLASSIFY_G, CLASSIFY_G])

    def bad(*a, **k):
        if isinstance(reply, Exception):
            raise reply
        return reply
    monkeypatch.setattr(E, "chat", bad)
    d = post(env).json()
    assert (d["status"], d["reason"], d["diagram_id"]) == ("declined", "verifier_unavailable", None)
    env["verifier"]()                                                             # the verifier is back: a retry works
    assert post(env).json()["status"] == "ok"


def test_verifier_timeout_is_verifier_unavailable_within_its_own_limit(env, monkeypatch):
    env["llm"]([CLASSIFY_G])
    monkeypatch.setattr(E, "VERIFY_TIMEOUT_S", 2.5)
    monkeypatch.setattr(E, "chat", lambda *a, **k: time.sleep(4) or "{}")
    t = time.monotonic()
    assert post(env).json()["reason"] == "verifier_unavailable"
    assert time.monotonic() - t < 3.5


def test_no_budget_left_declines_without_calling_the_verifier(env, monkeypatch):
    """The verifier only gets what is left of TOTAL_BUDGET_S (D-13): a slow generator leaves it none."""
    monkeypatch.setattr(diagram, "TOTAL_BUDGET_S", 2.2)
    env["llm"]([CLASSIFY_G])
    gen = diagram.chat

    def slow(*a, **k):
        time.sleep(0.6)
        return gen(*a, **k)
    monkeypatch.setattr(diagram, "chat", slow)
    d = post(env).json()
    assert d["reason"] == "verifier_unavailable" and env["vcalls"] == []


def test_ontology_path_is_not_sent_to_the_verifier(env, monkeypatch):
    monkeypatch.setattr(diagram.diagrams, "build_graph", lambda *a, **k: json.loads(json.dumps(ONT)))
    assert post(env).json()["source"] == "ontology" and env["vcalls"] == []


def test_prompt_shows_only_the_cited_sentences_and_every_item(env):
    a = CLASSIFY_A + " Beta blockers are widely prescribed worldwide."         # no marker: never shown
    env["llm"]([CLASSIFY_G])
    post(env, a=a)
    p = env["vcalls"][0]
    assert "widely prescribed" not in p and p.count('"type": "box"') == 6 and p.count('"type": "arrow"') == 4
    assert "[1]" not in p and "Flowchart kind: classification" in p


# ---------------------------------------------------------------- unit: the deterministic post-check

def test_quote_ok_rules():
    texts = ["Cardioselective beta blockers include atenolol and metoprolol [2].", ""]
    assert E.quote_ok("beta blockers include atenolol", texts)
    assert not E.quote_ok("beta blockers include atenolol and propranolol", texts)
    assert not E.quote_ok("", texts) and not E.quote_ok("and", texts) and not E.quote_ok(None, texts)
    assert E.quote_ok("Cardioselective beta blockers include atenolol – and metoprolol".replace(" –", ""), texts)


# ---------------------------------------------------------------- the four flips the word rules still pass (wiki)

KNOWN_FLIPS = {
    "un-listed verb swap (text: freeze initiation)": (
        COMPARISON, cls("Aminoglycosides", [4], [("Accelerate initiation of protein synthesis", [4])] + AMINO_KIDS),
        "Accelerate initiation of protein synthesis"),
    "verb/object swap (text: restores diminished vagal tone and abolishes sympathetic overactivity)": (
        DIGOXIN, cls("Rate slowing", [1], [("Improved circulation restores sympathetic overactivity", [1])] + RATE_KIDS),
        "Improved circulation restores sympathetic overactivity"),
    "inserted only (text: streptomycin binds 30S; others also bind ...)": (
        COMPARISON, cls("Aminoglycosides", [4], [("Only streptomycin binds 30S ribosomes", [4]),
                                                 ("Diffuse through gram-negative porin channels", [4]),
                                                 ("Killing is concentration dependent", [6])]),
        "Only streptomycin binds 30S ribosomes"),
    "absent where the text says occurs": (
        BETA_BLOCKERS, cls("Additional points", [1], [
            ("Partial agonistic (intrinsic sympathomimetic) action is absent in pindolol", [1]),
            ("Cardioselectivity is lost at high doses", [1])]),
        "Partial agonistic (intrinsic sympathomimetic) action is absent in pindolol"),
}


@pytest.mark.parametrize("case", list(KNOWN_FLIPS))
def test_known_flip_passes_word_rules_but_verifier_drops_it(case, monkeypatch):
    answer, graph, bad = KNOWN_FLIPS[case]
    res = run(answer, graph)
    assert res.ok and bad in {n["label"] for n in res.graph["nodes"]}           # the word rules still accept it

    def fake(system, user, **kw):
        sents = {ln.split(": ", 1)[0].split(" ")[0]: ln.split(": ", 1)[1]
                 for ln in user.splitlines() if ln.startswith("S") and ": " in ln}
        out = []
        for ln in user.splitlines():
            if ln.startswith("{"):
                it = json.loads(ln)
                hit = it.get("label") == bad or bad in (it.get("from"), it.get("to"))
                out.append({"id": it["id"], "verdict": "not_supported" if hit else "supported",
                            "quote": "" if hit else " ".join(sents[it["cited_sentences"][0]].split()[:8])})
        return json.dumps({"items": out})
    monkeypatch.setattr(E, "chat", fake)
    chk = E.check(res.graph, answer, prior_dropped=res.dropped)
    assert not chk.ok or bad not in {n["label"] for n in chk.graph["nodes"]}


def test_check_never_adds_or_relabels(monkeypatch):
    res = V.validate(CLASSIFY_G, answer_text=CLASSIFY_A, passage_ns={1, 2}, fact_ns={1})
    before = {(n["id"], n["label"], n["role"]) for n in res.graph["nodes"]}

    def fake(system, user, **kw):
        items = [json.loads(ln) for ln in user.splitlines() if ln.startswith("{")]
        out = [{"id": it["id"], "verdict": "supported", "quote": "beta blockers"} for it in items]
        out.append({"id": "n99", "verdict": "supported", "quote": "beta blockers", "label": "Invented"})
        return json.dumps({"items": out})
    monkeypatch.setattr(E, "chat", fake)
    chk = E.check(res.graph, CLASSIFY_A, prior_dropped=res.dropped)
    after = {(n["id"], n["label"], n["role"]) for n in chk.graph["nodes"]}
    assert after <= before and len(chk.graph["edges"]) <= len(res.graph["edges"])


def test_rules_version_bumped_for_the_cache_key():
    assert V.RULES_VERSION >= 7


def test_quote_may_read_a_list_item_together_with_its_heading():
    """The prompt shows an item under its heading; a quote of the two read together is the answer's own text."""
    a = "**Nonselective (β1 and β2)**\n- Without intrinsic sympathomimetic activity: propranolol, sotalol [3]\n"
    s = [x for x in V.parse_answer(a) if x.mk][0]
    texts = E.sentence_texts(s)
    assert E.quote_ok("Nonselective (β1 and β2) Without intrinsic sympathomimetic activity: propranolol", texts)
    assert E.quote_ok("Nonselective (β1 and β2): Without intrinsic", texts)
    assert not E.quote_ok("Nonselective (β1 and β2) With intrinsic sympathomimetic activity", texts)
