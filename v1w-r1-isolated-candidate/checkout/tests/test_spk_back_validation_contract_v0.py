"""Conformance and negative witnesses for proposed BV v0 offline trace format.

No training, no network monkey-patching, no mutation of frozen references.
"""
from copy import deepcopy
import json
import math
from pathlib import Path

import pytest

from spk_backvalidation_v0.contract_v0 import (
    BVContractRejected,
    digest,
    strict_loads,
    validate_trace,
)

EXAMPLE = Path(__file__).resolve().parent.parent / "examples" / "spk_bv_v0_distributed_feedback.json"


@pytest.fixture
def trace():
    return strict_loads(EXAMPLE.read_text())


def invalid(trace, mutator):
    d = deepcopy(trace)
    mutator(d)
    with pytest.raises(BVContractRejected):
        validate_trace(d)


def test_valid_parallel_routes_and_distributed_proposals(trace):
    result = validate_trace(trace)
    assert result["status"] == "STRUCTURAL_PASS"
    assert (result["occurrences"], result["assessments"], result["propagations"],
            result["proposals"]) == (3, 1, 2, 2)
    assert result["unique_propagated_receivers"] == 1
    assert result["unique_total_feedback_receivers"] == 2
    assert result["claims_excluded"] == (
        "global-benefit", "causal-credit", "metric-truth", "learning", "promotion", "host-security")


def test_deterministic_digests_and_read_only(trace):
    before = deepcopy(trace)
    a, b = validate_trace(trace), validate_trace(strict_loads(json.dumps(trace)))
    assert a == b
    assert trace == before
    assert digest(trace) == a["trace_sha256"]


def test_multiple_snapshots_same_neuron_allowed(trace):
    d = deepcopy(trace)
    d["contexts"].append({**d["contexts"][0], "id": "laterA", "window_start": 5, "window_end": 5})
    assert validate_trace(d)["status"] == "STRUCTURAL_PASS"


def test_missing_occurrence_identity_or_parallel_dedup_denied(trace):
    invalid(trace, lambda d: d["occurrences"][1].update(id="r1"))


def test_route_must_have_positive_delay(trace):
    invalid(trace, lambda d: d["occurrences"][0].update(delivered_at=0))


def test_parent_cannot_be_unknown_or_future_or_wrong_receiver(trace):
    invalid(trace, lambda d: d["occurrences"][2].update(parent_ids=["phantom"]))
    invalid(trace, lambda d: d["occurrences"][0].update(parent_ids=["r3"]))
    invalid(trace, lambda d: d["occurrences"][2].update(parent_ids=["r3"]))


def test_recurrent_provenance_referential_not_node_acausal(trace):
    # B -> A -> B is a structurally recurrent route at later logical times.
    d = deepcopy(trace)
    d["edges"].extend([
        {"id": "eBA", "source": "B", "target": "A", "source_channel": 0, "target_channel": 0, "delay_ticks": 1},
        {"id": "eAB3", "source": "A", "target": "B", "source_channel": 0, "target_channel": 0, "delay_ticks": 1},
    ])
    d["topology_sha256"] = digest({"nodes": ["A", "B", "C"],
                                      "edges": sorted(d["edges"], key=lambda e: e["id"])})
    d["occurrences"].append({"id": "r4", "source": "B", "target": "A", "emitted_at": 2,
                              "delivered_at": 3, "parent_ids": ["r1"],
                              "source_program_sha256": d["contexts"][1]["program_sha256"],
                              "source_context_id": "ctx_B", "edge_id": "eBA",
                              "source_channel": 0, "target_channel": 0})
    d["occurrences"].append({"id": "r5", "source": "A", "target": "B", "emitted_at": 3,
                              "delivered_at": 4, "parent_ids": ["r4"],
                              "source_program_sha256": d["contexts"][0]["program_sha256"],
                              "source_context_id": "ctx_A", "edge_id": "eAB3",
                              "source_channel": 0, "target_channel": 0})
    assert validate_trace(d)["occurrences"] == 5


def test_cannot_assess_from_nonreceiver(trace):
    invalid(trace, lambda d: d["assessments"][0].update(observer="B"))


def test_no_assessment_before_event_delivery(trace):
    invalid(trace, lambda d: d["assessments"][0].update(observed_at=1))


def test_no_cross_context_or_future_window(trace):
    invalid(trace, lambda d: d["assessments"][0].update(observer_context_id="ctx_A"))
    invalid(trace, lambda d: d["contexts"][2].update(window_start=3))
    invalid(trace, lambda d: d["occurrences"][0].update(source_context_id="ctx_B"))


def test_abstain_is_not_numeric_zero(trace):
    def abstain(d):
        d["assessments"][0].update(status="ABSTAIN", value=None, confidence=None, reason="unknown")
        d["proposals"] = []
    d = deepcopy(trace)
    abstain(d)
    assert validate_trace(d)["assessments"] == 1
    invalid(trace, lambda d: d["assessments"][0].update(status="ABSTAIN", reason="unknown"))
    invalid(trace, lambda d: d["assessments"][0].update(status="ABSTAIN", value=None,
                                                        confidence=None, reason="unknown"))


def test_nonfinite_score_or_confidence_refused(trace):
    for value in [float("nan"), float("inf"), -1.001, 1.001, True]:
        invalid(trace, lambda d, x=value: d["assessments"][0].update(value=x))
    invalid(trace, lambda d: d["assessments"][0].update(confidence=1.001))


def test_feedback_not_an_unrelated_reverse_graph_path(trace):
    invalid(trace, lambda d: d["propagations"][0].update(path=["r3", "r3"]))
    invalid(trace, lambda d: d["propagations"][0].update(path=["r3", "unknown"]))
    invalid(trace, lambda d: d["propagations"][0].update(path=["r1", "r2"]))


def test_deduplication_at_common_ancestor(trace):
    def same_target(d):
        d["propagations"][1].update(path=["r3", "r1"])
    invalid(trace, same_target)


def test_hop_and_record_budgets_enforced(trace):
    invalid(trace, lambda d: d["budgets"].update(max_hops=1))
    invalid(trace, lambda d: d["budgets"].update(max_propagations=1))
    invalid(trace, lambda d: d["budgets"].update(max_occurrences=2))
    invalid(trace, lambda d: d["budgets"].update(max_contexts=2))
    invalid(trace, lambda d: d["budgets"].update(max_parents=1))


def test_proposal_never_promotes_byitself(trace):
    invalid(trace, lambda d: d["proposals"][0].update(status="PROMOTED"))
    invalid(trace, lambda d: d["proposals"][0].update(status="APPROVED"))
    invalid(trace, lambda d: d["proposals"][0].update(candidate_sha256=d["proposals"][0]["from_program_sha256"]))


def test_proposal_must_have_reachable_evidence(trace):
    invalid(trace, lambda d: d["proposals"][0].update(assessment_ids=["a1"]))
    invalid(trace, lambda d: d["proposals"][1].update(propagation_ids=["p1"]))
    invalid(trace, lambda d: d["proposals"][0].update(propagation_ids=["p1", "p1"]))


def test_forged_cross_epoch_context_and_extra_fields_fail_closed(trace):
    invalid(trace, lambda d: d.update(epoch=-1))
    invalid(trace, lambda d: d["occurrences"][0].update(unauthorized_mutation=True))
    invalid(trace, lambda d: d["proposals"][0].update(proposer_context_id="ctx_C"))


def test_json_duplicate_keys_are_refused():
    with pytest.raises(BVContractRejected):
        strict_loads('{"schema":"first","schema":"second"}')


def test_json_nan_and_infinity_are_refused():
    for bad in ('{"x":NaN}', '{"x":Infinity}', '{"x":-Infinity}'):
        with pytest.raises(BVContractRejected):
            strict_loads(bad)


def test_no_feedback_is_not_a_negative_score(trace):
    d = deepcopy(trace)
    d["assessments"] = []
    d["propagations"] = []
    d["proposals"] = []
    assert validate_trace(d)["status"] == "STRUCTURAL_PASS"


def test_abstention_cannot_support_adaptation(trace):
    d = deepcopy(trace)
    d["assessments"][0].update(status="ABSTAIN", value=None, confidence=None, reason="insufficient-data")
    with pytest.raises(BVContractRejected):
        validate_trace(d)


def test_no_negative_budget_or_boolean_quantities(trace):
    invalid(trace, lambda d: d["budgets"].update(max_hops=0))
    invalid(trace, lambda d: d["budgets"].update(max_hops=True))
    invalid(trace, lambda d: d["occurrences"][0].update(emitted_at=True))


def test_context_cannot_contain_future_observations(trace):
    invalid(trace, lambda d: d["contexts"][0].update(window_end=1))
    invalid(trace, lambda d: d["contexts"][2].update(window_end=3))


def test_edge_and_topology_witnesses_are_pinned(trace):
    invalid(trace, lambda d: d["occurrences"][0].update(edge_id="missing"))
    invalid(trace, lambda d: d["occurrences"][0].update(target_channel=1))
    invalid(trace, lambda d: d["edges"][0].update(delay_ticks=2))
    invalid(trace, lambda d: d["budgets"].update(max_edges=2))
    invalid(trace, lambda d: d["budgets"].update(max_nodes=2))


def test_active_program_cannot_change_inside_one_epoch(trace):
    d = deepcopy(trace)
    d["contexts"].append({**d["contexts"][0], "id": "second_A", "window_start": 5,
                          "window_end": 5, "program_sha256": d["contexts"][1]["program_sha256"]})
    with pytest.raises(BVContractRejected):
        validate_trace(d)
