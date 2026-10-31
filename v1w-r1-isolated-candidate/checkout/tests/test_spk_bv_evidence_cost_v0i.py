"""BV v0i contract tests: do not import frozen simulator or mutate sources."""
from dataclasses import replace
import random
import pytest
from spk_bv_research.evidence_cost_v0i import (
    BudgetProfile, EvidenceCostContractError, EvidenceCostLedger, Reception,
)
from spk_bv_research.stress_v0i import fixture


def r(**kw):
    default = dict(transmission_id="t1", epoch=1, observed_tick=2, batch_tick=1,
                   origin="a", batch_id="b1", receiver="z", context_id="c1",
                   evidence_code="uninterpreted", link_id="l1", path_id="p1",
                   transport_units=1)
    return Reception(**(default | kw))


def test_528_33_495_exact_and_budgets():
    ledger = EvidenceCostLedger(BudgetProfile(
        max_transmissions=528, max_votes=33, max_units_per_tick=250,
        per_link_units_per_tick={"link-0": 60}))
    ledger.ingest_all(fixture())
    s = ledger.snapshot()
    assert (s["physical_transmissions"], s["distinct_contextual_votes"],
            s["additional_transmissions_over_vote_count"], s["transport_units"]) == (528, 33, 495, 528)
    assert s["identified_batches"] == 33
    assert len(s["budget_overloads"]) > 0
    assert s["observed_neurons"] == 64


def test_context_and_batch_identity_not_collapsed():
    l = EvidenceCostLedger()
    l.ingest_all([r(), r(transmission_id="t2", path_id="p2"),
                  r(transmission_id="t3", batch_id="b2"),
                  r(transmission_id="t4", context_id="c2"),
                  r(transmission_id="t5", receiver="other")])
    s = l.snapshot()
    assert s["physical_transmissions"] == 5
    assert s["distinct_contextual_votes"] == 4
    assert s["additional_transmissions_over_vote_count"] == 1


def test_two_distinct_batches_with_same_birth_tick():
    l = EvidenceCostLedger()
    l.ingest(r(batch_id="b1"))
    l.ingest(r(transmission_id="t2", batch_id="b2"))
    assert l.snapshot()["distinct_contextual_votes"] == 2


def test_same_batch_new_arrival_tick_stays_same_vote():
    l = EvidenceCostLedger()
    l.ingest(r())
    l.ingest(r(transmission_id="t2", observed_tick=3))
    assert l.snapshot()["distinct_contextual_votes"] == 1
    assert len(l.snapshot()["per_tick_units"]) == 2


def test_identical_transport_replay_not_double_charged():
    l = EvidenceCostLedger()
    assert l.ingest(r()) is True
    assert l.ingest(r()) is False
    assert l.snapshot()["transport_units"] == 1


@pytest.mark.parametrize("field,value", [
    ("receiver", "other"), ("context_id", "other"),
    ("path_id", "other"), ("transport_units", 2),
    ("observed_tick", 3), ("evidence_code", "other"),
])
def test_transmission_id_collision_rejected_atomic(field, value):
    l = EvidenceCostLedger()
    l.ingest(r())
    before = l.snapshot()
    with pytest.raises(EvidenceCostContractError, match="transmission ID"):
        l.ingest(replace(r(), **{field: value}))
    assert l.snapshot() == before


def test_conflicting_vote_token_rejected_atomic():
    l = EvidenceCostLedger()
    l.ingest(r())
    before = l.snapshot()
    with pytest.raises(EvidenceCostContractError, match="conflicting"):
        l.ingest(r(transmission_id="t2", evidence_code="different"))
    assert l.snapshot() == before


def test_batch_identity_rebirth_rejected_atomic():
    l = EvidenceCostLedger()
    l.ingest(r())
    before = l.snapshot()
    with pytest.raises(EvidenceCostContractError, match="birth tick"):
        l.ingest(r(transmission_id="t2", batch_tick=2))
    assert l.snapshot() == before


def test_origin_separates_batch_namespace():
    l = EvidenceCostLedger()
    l.ingest_all([r(), r(transmission_id="t2", origin="other", batch_tick=2)])
    assert l.snapshot()["identified_batches"] == 2


def test_epoch_separates_transmission_namespace():
    l = EvidenceCostLedger()
    l.ingest_all([r(), r(epoch=2)])
    assert l.snapshot()["physical_transmissions"] == 2
    assert l.snapshot()["distinct_contextual_votes"] == 2


def test_idempotence_and_input_order_permutations():
    samples = list(fixture())
    a = EvidenceCostLedger(); a.ingest_all(samples)
    b = EvidenceCostLedger(); b.ingest_all(reversed(samples))
    c = EvidenceCostLedger()
    random.Random(4).shuffle(samples)
    c.ingest_all(samples)
    assert a.snapshot() == b.snapshot() == c.snapshot()


def test_extra_route_modifies_physical_but_not_logical_hash():
    a = EvidenceCostLedger(); a.ingest(r())
    b = EvidenceCostLedger(); b.ingest(r()); b.ingest(r(transmission_id="t2", path_id="p2"))
    assert a.snapshot()["contextual_vote_sha256"] == b.snapshot()["contextual_vote_sha256"]
    assert a.snapshot()["physical_sha256"] != b.snapshot()["physical_sha256"]


def test_symbolic_token_is_not_quality_score():
    a = EvidenceCostLedger(); a.ingest(r(evidence_code="not-a-truth-claim"))
    s = a.snapshot()
    assert "truth" in s["excluded_claims"]
    assert "causal-credit" in s["excluded_claims"]
    assert not any("quality" in name or "reward" in name for name in s)


def test_budget_overload_does_not_discard_receipt():
    l = EvidenceCostLedger(BudgetProfile(max_units_per_tick=2,
                                           per_link_units_per_tick={"l1": 2}))
    l.ingest_all([r(transport_units=2), r(transmission_id="t2", transport_units=3)])
    s = l.snapshot()
    assert s["transport_units"] == 5
    assert {x["kind"] for x in s["budget_overloads"]} == {"tick", "link"}


def test_limit_fail_closed_without_partial_ingest():
    l = EvidenceCostLedger(BudgetProfile(max_transmissions=1, max_votes=1))
    l.ingest(r())
    with pytest.raises(EvidenceCostContractError, match="transmission-memory"):
        l.ingest(r(transmission_id="t2", receiver="other"))
    assert l.snapshot()["physical_transmissions"] == 1


def test_vote_memory_limit():
    l = EvidenceCostLedger(BudgetProfile(max_transmissions=2, max_votes=1))
    l.ingest(r())
    with pytest.raises(EvidenceCostContractError, match="vote-memory"):
        l.ingest(r(transmission_id="t2", batch_id="b2"))


@pytest.mark.parametrize("updates", [
    {"epoch": True}, {"observed_tick": -1}, {"batch_tick": 3},
    {"transport_units": 0}, {"transport_units": 2.0},
    {"receiver": "x y"}, {"transmission_id": ""},
    {"context_id": "../bad?"}, {"evidence_code": "t" * 97},
])
def test_malformed_receipts_are_rejected(updates):
    with pytest.raises(EvidenceCostContractError):
        r(**updates)


def test_reception_schema_strict_and_roundtrip():
    original = r()
    assert Reception.from_dict(original.as_dict()) == original
    with pytest.raises(EvidenceCostContractError):
        Reception.from_dict(original.as_dict() | {"extra": 1})
    data = original.as_dict(); del data["batch_id"]
    with pytest.raises(EvidenceCostContractError):
        Reception.from_dict(data)


def test_empty_ledger_ratio_undefined_without_zero_division():
    l = EvidenceCostLedger()
    s = l.snapshot()
    assert s["physical_transmissions"] == 0
    assert s["physical_per_vote_denominator"] == 0
    assert s["transport_units"] == 0


def test_ndjson_cli_validates_and_exports(tmp_path):
    import json, subprocess, sys
    trace = tmp_path / "trace.ndjson"
    trace.write_text("\n".join(json.dumps(record.as_dict()) for record in [
        r(), r(transmission_id="t2", path_id="p2")]) + "\n")
    proc = subprocess.run([sys.executable, "-m", "search.spk_bv_v0i_ingest_ndjson",
                           "--input", str(trace), "--max-units-per-tick", "1"],
                          text=True, capture_output=True)
    assert proc.returncode == 0, proc.stderr
    d = json.loads(proc.stdout)
    assert d["physical_transmissions"] == 2
    assert d["distinct_contextual_votes"] == 1
    assert d["budget_overloads"][0]["kind"] == "tick"


def test_ndjson_cli_rejects_provenance_mismatch(tmp_path):
    import json, subprocess, sys
    trace = tmp_path / "bad.ndjson"
    trace.write_text("\n".join(json.dumps(record.as_dict()) for record in [
        r(), r(transmission_id="t2", evidence_code="other")]) + "\n")
    proc = subprocess.run([sys.executable, "-m", "search.spk_bv_v0i_ingest_ndjson",
                           "--input", str(trace)], text=True, capture_output=True)
    assert proc.returncode == 2
    assert "line 2" in proc.stderr
    assert "conflicting" in proc.stderr
    assert not proc.stdout
