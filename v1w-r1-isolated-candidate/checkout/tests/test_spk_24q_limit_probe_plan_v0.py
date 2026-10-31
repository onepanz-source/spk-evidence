"""Pure independent plan tests; deliberately no frozen SPK imports."""
import pytest

from search.spk_24n_independent_oracle_v0 import execute_v0, OracleLimitV0
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24q_limit_probe_plan_v0 import (
    BudgetProbeV0, plan_v0, plan_summary_v0, probes_for_case_v0,
)


def test_plan_is_full_deterministic_216_case_corpus():
    s = plan_summary_v0()
    assert s == {
        'case_count': 216, 'probe_count': 558, 'closed_probes': 216,
        'event_limit_probes': 174, 'batch_limit_probes': 168,
        'corpus_sha256': 'cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5',
    }
    assert s['corpus_sha256'] == catalog_fingerprint_v0()
    assert len({cid for cid, _, _ in plan_v0()}) == 216


def test_plan_preserves_original_noncanonical_guard_program():
    cid, case, probes = next(x for x in plan_v0() if x[0].startswith('guard_overwrite/'))
    assert ('CMP', 1) in case.nodes[1].instructions
    assert ('CMP', 3) in case.nodes[1].instructions
    assert len(probes) >= 1


def test_all_558_expected_outcomes_are_actually_observed_by_independent_oracle():
    for cid, case, probes in plan_v0():
        for probe in probes:
            kw = dict(max_batches=probe.max_batches, max_events=probe.max_events)
            if probe.expected_status == 'CLOSED':
                assert execute_v0(case, **kw)['processed_events'] >= 0
            else:
                with pytest.raises(OracleLimitV0) as error:
                    execute_v0(case, **kw)
                assert str(error.value) == probe.expected_reason, (cid, probe)


def test_all_budgets_strictly_positive_and_single_reason():
    for _, _, probes in plan_v0():
        for probe in probes:
            assert type(probe.max_batches) is type(probe.max_events) is int
            assert probe.max_batches > 0 and probe.max_events > 0
            assert probe.expected_reason in (None, 'max_events', 'max_batches')
            assert (probe.expected_status == 'CLOSED') == (probe.expected_reason is None)


def test_plan_has_no_ambiguous_simultaneous_budget_failure():
    for _, _, probes in plan_v0():
        for probe in probes:
            if probe.expected_reason == 'max_events':
                assert probe.max_batches == 128
            if probe.expected_reason == 'max_batches':
                assert probe.max_events == 4096


def test_reject_empty_case_id():
    _, case, _ = plan_v0()[0]
    with pytest.raises(ValueError, match='case_id'):
        probes_for_case_v0('', case)


def test_plan_is_deterministic_across_invocations():
    assert plan_v0() == plan_v0()
