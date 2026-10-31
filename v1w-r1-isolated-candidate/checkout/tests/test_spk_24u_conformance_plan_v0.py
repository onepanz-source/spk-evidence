"""Pure and independently reproducible cross-layer acceptance plan."""
from dataclasses import replace
from pathlib import Path

import pytest

from search import spk_24u_conformance_plan_v0 as plan
from search.spk_24o_semantic_corpus_v0 import catalog_v0
from search.spk_24n_independent_oracle_v0 import execute_v0


def test_source_corpus_is_strictly_pinned():
    assert len(catalog_v0()) == 216
    assert plan.summary_v0()['corpus_sha256'] == plan.EXPECTED_CORPUS_SHA256
    assert len(plan.identity_v0()) == 64


def test_every_case_appears_exactly_once_in_order():
    listed = plan.entries_v0()
    assert tuple(entry.case_id for entry in listed) == tuple(k for k, _ in catalog_v0())
    assert len(set(entry.case_id for entry in listed)) == 216


def test_profiles_graphs_and_input_dimensions_all_covered():
    s = plan.summary_v0()
    assert len(s['profiles']) == len(s['topologies']) == len(s['input_kinds']) == 6
    assert s['source_cases'] == 6 * 6 * 6
    for attr in ('profile', 'graph', 'input_kind'):
        counts = {name: sum(getattr(e, attr) == name for e in plan.entries_v0())
                  for name in {getattr(e, attr) for e in plan.entries_v0()}}
        assert set(counts.values()) == {36}


def test_selected_budget_and_causal_controls_have_grounded_counts():
    s = plan.summary_v0()
    assert (s['selected_budget_cases'], s['selected_budget_probes']) == (36, 102)
    assert (s['selected_causal_cases'], s['selected_causal_probes']) == (30, 90)
    assert all(e.input_kind == 'duplicate' for e in plan.entries_v0()
               if e.boundary_kinds or e.dual_controls)
    assert all(e.boundary_kinds[0] == 'exact_success' for e in plan.entries_v0()
               if e.boundary_kinds)
    assert all(e.dual_controls == ('both', 'events_only', 'batches_only')
               for e in plan.entries_v0() if e.dual_controls)


def test_all_declared_cases_complete_independently_under_reference_ceiling():
    for cid, case in catalog_v0():
        result = execute_v0(case, max_batches=128, max_events=4096)
        assert result['processed_batches'] <= 128, cid
        assert result['processed_events'] <= 4096, cid


def test_drift_is_rejected_before_any_frozen_runtime_usage(monkeypatch):
    monkeypatch.setattr(plan, 'catalog_fingerprint_v0', lambda: '0'*64)
    with pytest.raises(AssertionError, match='corpus identity changed'):
        plan.entries_v0()


def test_pure_planner_does_not_import_frozen_system():
    source = Path(plan.__file__).read_text()
    for name in ('spk_core', 'spk_network', 'spk_compiler', 'spk_architecture',
                 'spk_simulator'):
        assert name not in source


def test_no_plan_case_mutates_original_primitive():
    before = catalog_v0()
    plan.entries_v0()
    assert catalog_v0() == before
