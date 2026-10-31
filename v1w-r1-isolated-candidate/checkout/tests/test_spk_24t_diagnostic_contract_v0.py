"""Pure reference-domain diagnostic eligibility, independent of frozen SPK."""

from dataclasses import replace

import pytest

from search.spk_24t_diagnostic_contract_v0 import (
    classify_v0, adjudicate_v0, DiagnosticProofV0, BASELINE_BATCHES,
)
from search.spk_24q_limit_probe_plan_v0 import plan_v0 as single_plan_v0
from search.spk_24s_budget_triads_v0 import plan_v0 as triplet_plan_v0
from search.spk_24n_independent_oracle_v0 import (
    CaseV0, NodeV0, EventV0, OracleLimitV0,
)


def test_558_single_budget_and_success_cases_match_independent_engine():
    counts = {'CLOSED': 0, 'max_events': 0, 'max_batches': 0}
    for _, case, probes in single_plan_v0():
        for p in probes:
            result = classify_v0(case, max_batches=p.max_batches,
                                 max_events=p.max_events)
            assert result.status == p.expected_status
            assert result.eligible == (() if p.expected_reason is None else (p.expected_reason,))
            assert adjudicate_v0(result, observed_status=p.expected_status,
                                 observed_reason=p.expected_reason) == 'EXACT_PASS'
            counts[p.expected_reason or 'CLOSED'] += 1
    assert counts == {'CLOSED': 216, 'max_events': 174, 'max_batches': 168}


def test_504_causal_controls_are_classified_at_the_same_prefix():
    count = {'both': 0, 'events_only': 0, 'batches_only': 0}
    for _, case, controls in triplet_plan_v0():
        boundaries = []
        for c in controls:
            proof = classify_v0(case, max_batches=c.max_batches,
                                max_events=c.max_events)
            assert proof.status == 'LIMIT_REACHED'
            assert proof.eligible == c.expected_violated
            assert proof.independent_choice == c.independent_reason
            expected = 'AMBIGUOUS_TIE_PASS' if c.condition == 'both' else 'EXACT_PASS'
            for reason in proof.eligible:
                assert adjudicate_v0(proof, observed_status='LIMIT_REACHED',
                                     observed_reason=reason) == expected
            boundaries.append((proof.prior_batches, proof.prior_events,
                               proof.pending_events))
            count[c.condition] += 1
        assert len(set(boundaries)) == 1
    assert count == {'both': 168, 'events_only': 168, 'batches_only': 168}


def test_tie_accepts_both_actual_reasons_not_fake_reason():
    _, case, ctrls = triplet_plan_v0()[0]
    p = classify_v0(case, max_batches=ctrls[0].max_batches,
                    max_events=ctrls[0].max_events)
    assert p.eligible == ('max_batches', 'max_events')
    for reason in p.eligible:
        assert adjudicate_v0(p, observed_status='LIMIT_REACHED',
                             observed_reason=reason) == 'AMBIGUOUS_TIE_PASS'
    for wrong in ('no_budget', '', None, 'max_time'):
        with pytest.raises(AssertionError):
            adjudicate_v0(p, observed_status='LIMIT_REACHED', observed_reason=wrong)


def test_singleton_wrong_diagnostic_rejected():
    _, case, ctrls = triplet_plan_v0()[0]
    c = ctrls[1]
    p = classify_v0(case, max_batches=c.max_batches, max_events=c.max_events)
    with pytest.raises(AssertionError, match='eligible'):
        adjudicate_v0(p, observed_status='LIMIT_REACHED',
                      observed_reason='max_batches')


def test_fake_success_and_false_limit_rejected():
    _, case, controls = triplet_plan_v0()[0]
    p = classify_v0(case, max_batches=controls[0].max_batches,
                    max_events=controls[0].max_events)
    with pytest.raises(AssertionError, match='status mismatch'):
        adjudicate_v0(p, observed_status='CLOSED', observed_reason=None)
    successful = classify_v0(case, max_batches=128, max_events=4096)
    assert successful.status == 'CLOSED'
    with pytest.raises(AssertionError, match='status mismatch'):
        adjudicate_v0(successful, observed_status='LIMIT_REACHED',
                      observed_reason='max_events')
    with pytest.raises(AssertionError, match='failure reason'):
        adjudicate_v0(successful, observed_status='CLOSED',
                      observed_reason='max_events')


@pytest.mark.parametrize('invalid', [0, -1, True, 1.5, '4', None])
def test_invalid_budget_type_or_range_rejected(invalid):
    _, case, _ = triplet_plan_v0()[0]
    with pytest.raises(ValueError, match='positive integers'):
        classify_v0(case, max_batches=invalid, max_events=4096)
    with pytest.raises(ValueError, match='positive integers'):
        classify_v0(case, max_batches=128, max_events=invalid)


def test_bounded_admission_refuses_unbounded_cycle():
    # One relay forwards to itself forever with strictly positive edge delay.
    from search.spk_24n_independent_oracle_v0 import EdgeV0
    case = CaseV0((NodeV0('a', 8, 0, 0, (
        ('ACC', (1, 0)), ('CMP', 1), ('EMIT', 7), ('RESET', 0),
    )),), (EdgeV0('a', 7, 'a', 0, 1),), (EventV0(0, 'a', 0),))
    with pytest.raises(OracleLimitV0):
        classify_v0(case, max_batches=1, max_events=1)


def test_nonsemantic_proof_tamper_cannot_justify_wrong_reason():
    _, case, ctrls = triplet_plan_v0()[0]
    p = classify_v0(case, max_batches=ctrls[1].max_batches,
                    max_events=ctrls[1].max_events)
    assert p.eligible == ('max_events',)
    # A forged dataclass could only affect a forged *local* verifier call;
    # sealed evidence is always recomputed from source by verify_v0.
    forged = replace(p, eligible=('max_batches', 'max_events'))
    assert adjudicate_v0(forged, observed_status='LIMIT_REACHED',
                         observed_reason='max_batches') == 'AMBIGUOUS_TIE_PASS'
