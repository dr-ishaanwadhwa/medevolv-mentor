import json

from rag import hubs


def _rec(hub_id, kind, hub_label, mid, mlabel, tier="T2", evidence=None):
    return {"hub_id": hub_id, "hub_type": kind, "hub_label": hub_label, "member_id": mid, "member_label": mlabel,
            "member_type": "TherapeuticAgent", "tier": tier, "method": "test", "evidence": evidence}


def _use(tmp_path, monkeypatch, rows):
    p = tmp_path / "hubs.jsonl"
    p.write_text("\n".join(json.dumps(r) for r in rows))
    monkeypatch.setattr(hubs, "PATH", p)
    hubs._load.cache_clear()


def test_missing_file_returns_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(hubs, "PATH", tmp_path / "nope.jsonl")
    hubs._load.cache_clear()
    assert hubs.hubs_for("x") == [] and hubs.members("h") == [] and hubs.all_hubs() == []


def test_query_api_and_tiers(tmp_path, monkeypatch):
    _use(tmp_path, monkeypatch, [
        _rec("c1", "drug_class", "Macrolides", "d1", "Azithromycin", "T3", "harrison/1"),
        _rec("c1", "drug_class", "Macrolides", "d2", "Clarithromycin", "T3", "harrison/2"),
        _rec("m1", "mechanism", "COX-1", "d1", "Azithromycin"),
    ])
    got = hubs.hubs_for(" azithromycin ")
    assert {r["hub_id"] for r in got} == {"c1", "m1"} and all(r["tier"] in ("T2", "T3") for r in got)
    assert [r["member_label"] for r in hubs.members("c1", k=1)] == ["Azithromycin"]
    assert hubs.all_hubs("drug_class") == [{"hub_id": "c1", "hub_type": "drug_class", "hub_label": "Macrolides",
                                            "tier": "T3", "n_members": 2}]
    assert len(hubs.all_hubs()) == 2


def test_returned_records_are_copies(tmp_path, monkeypatch):
    _use(tmp_path, monkeypatch, [_rec("c1", "drug_class", "A", "d1", "B", "T3")])
    hubs.hubs_for("b")[0]["tier"] = "T1"
    assert hubs.hubs_for("b")[0]["tier"] == "T3"


def test_built_data_never_claims_certified():
    # only checks the real file when it has been built
    hubs._load.cache_clear()
    rows, _, _ = hubs._load()
    assert all(r["tier"] in ("T2", "T3") for r in rows)
    assert all(r["evidence"] for r in rows if r["hub_type"] == "drug_class")
