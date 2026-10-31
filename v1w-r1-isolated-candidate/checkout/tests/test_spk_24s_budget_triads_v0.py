"""Pure, independent tests of 24s causal error-priority controls."""
from dataclasses import replace

import pytest

from search.spk_24r_dual_limit_plan_v0 import plan_v0 as dual_plan_v0
from search.spk_24s_budget_triads_v0 import controls_for_v0, plan_v0, summary_v0


def test_causal_plan_has_168_unique_three_way_controls():
    plan = plan_v0()
    summary = summary_v0()
    assert len(plan) == 168
    assert summary['control_probes'] == 504
    assert summary['dual_probes'] == 168
    assert summary['events_only_probes'] == 168
    assert summary['batches_only_probes'] == 168
    assert summary['corpus_sha256'] == 'cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5'
    assert len({cid for cid, _, _ in plan}) == 168


@pytest.mark.parametrize('profile', ('relays', 'threshold', 'decay', 'double_emit', 'guard_overwrite', 'fractional'))
def test_controls_isolate_exactly_one_condition_or_both(profile):
    rows = [(cid, ctrl) for cid, _, ctrl in plan_v0() if cid.startswith(profile + '/')]
    assert rows
    for cid, ctrl in rows:
        assert len(ctrl) == 3
        assert tuple(c.condition for c in ctrl) == ('both', 'events_only', 'batches_only')
        a, b, c = ctrl
        assert a.case_id == b.case_id == c.case_id == cid
        assert a.expected_violated == ('max_batches', 'max_events')
        assert b.expected_violated == ('max_events',)
        assert c.expected_violated == ('max_batches',)
        assert b.independent_reason == 'max_events'
        assert c.independent_reason == 'max_batches'
        assert a.max_events == b.max_events
        assert a.max_batches == c.max_batches
        assert b.max_batches == a.max_batches + 1
        assert c.max_events > a.max_events
        # Tie precedence is NOT a normative test oracle.
        assert a.independent_reason in a.expected_violated


def test_bad_prefix_is_rejected_without_runtime_import():
    _, case, probe = dual_plan_v0()[0]
    with pytest.raises(AssertionError, match='incorrect pre-limit boundary'):
        controls_for_v0(case, replace(probe, prior_events=probe.prior_events+1))


def test_out_of_range_events_control_rejected():
    _, case, probe = dual_plan_v0()[0]
    with pytest.raises(AssertionError):
        controls_for_v0(case, replace(probe, max_events=probe.max_events+1))


def test_controls_do_not_import_frozen_runtime():
    from pathlib import Path
    import search.spk_24s_budget_triads_v0 as m
    source = Path(m.__file__).read_text()
    assert 'from spk_network' not in source
    assert 'from spk_compiler' not in source
    assert 'from spk_core' not in source
    assert 'run_network_v0(' not in source
