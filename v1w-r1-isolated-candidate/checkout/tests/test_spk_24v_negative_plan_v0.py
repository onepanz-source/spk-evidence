"""Pure SPK 24v negative coverage plan; independent from frozen modules."""
from collections import Counter
from dataclasses import replace
import pytest

from search import spk_24v_negative_plan_v0 as plan
from search.spk_24o_semantic_corpus_v0 import catalog_v0


def test_complete_source_identity():
    assert len(plan.checked_catalog_v0()) == 216
    assert plan.summary_v0()['corpus_sha256'] == plan.EXPECTED_CORPUS


def test_all_seven_invalid_requests_for_every_source():
    entries = plan.negative_plan_v0()
    assert len(entries) == 1512
    groups = Counter(e.case_id for e in entries)
    assert len(groups) == 216 and set(groups.values()) == {7}
    assert len(set(entries)) == len(entries)


def test_all_profiles_topologies_and_input_patterns_present():
    ids = [e.case_id for e in plan.negative_plan_v0()]
    assert len({cid.split('/')[0] for cid in ids}) == 6
    assert len({cid.split('/')[1] for cid in ids}) == 6
    assert len({cid.split('/')[2] for cid in ids}) == 6


def test_observer_batch_plan_covers_six_by_six():
    cases = plan.observer_plan_v0()
    assert len(cases) == 36 and len(set(cases)) == 36
    assert all(cid.endswith('/at_zero') for cid in cases)


def test_route_fault_plan_has_only_nonempty_graphs():
    assert len(plan.route_plan_v0()) == 5
    assert all(cid.startswith('relays/') for cid in plan.route_plan_v0())
    assert all('/isolated/' not in cid for cid in plan.route_plan_v0())


def test_observer_budget_fault_plan_has_simultaneous_ingress():
    ids = plan.budget_observer_plan_v0()
    assert len(ids) == 36
    source = dict(catalog_v0())
    assert all(len(source[cid].events) == 2 for cid in ids)
    assert all(source[cid].events[0] == source[cid].events[1] for cid in ids)


def test_identity_is_repeatable():
    assert plan.identity_v0() == plan.identity_v0()
    assert len(plan.identity_v0()) == 64


def test_mutation_plan_remains_explicit_and_stable():
    assert plan.MUTATIONS == (
        'wrong_pin', 'malformed_pin', 'zero_batches', 'boolean_events',
        'truncated_manifest', 'wrong_root_shape', 'nontext_manifest',
    )


def test_bad_corpus_identity_rejected(monkeypatch):
    monkeypatch.setattr(plan, 'catalog_fingerprint_v0', lambda: '0'*64)
    with pytest.raises(AssertionError, match='changed'):
        plan.negative_plan_v0()


def test_summary_contract_counts():
    summary = plan.summary_v0()
    assert summary['cases'] == 216
    assert summary['negative_admissions'] == 1512
    assert summary['observer_batch_cases'] == 36
    assert summary['observer_route_cases'] == 5
    assert summary['observer_budget_cases'] == 36
    assert summary['compiler_invalid_ir_cases'] == 36
