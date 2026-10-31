"""SPK 24r: independent proof of simultaneous budget eligibility.

This module imports only the primitive 24n oracle and 24o corpus. It does not
load frozen SPK modules or determine normative error precedence.
"""
from __future__ import annotations

from dataclasses import dataclass

from search.spk_24n_independent_oracle_v0 import execute_v0, OracleLimitV0
from search.spk_24o_semantic_corpus_v0 import catalog_v0, catalog_fingerprint_v0


@dataclass(frozen=True)
class DualLimitProbeV0:
    case_id: str
    max_batches: int
    max_events: int
    prior_batches: int
    prior_events: int
    pending_batch_events: int


def probe_for_case_v0(case_id, case):
    """Put both limits precisely at the prefix preceding the last batch.

    For an ordered, completed trace of B batches and E events, the final batch
    contributes k events. Budgets B-1 and E-k make both inequalities true at
    the same next batch. Cases with fewer than two batches are excluded because
    the public limit API requires strictly positive budgets.
    """
    if type(case_id) is not str or not case_id:
        raise ValueError('nonempty case identifier required')
    result = execute_v0(case, max_batches=128, max_events=4096)
    batches = result['observations']['batches']
    if len(batches) < 2:
        return None
    before_batches = len(batches) - 1
    count_in_last = len(batches[-1]['channels'])
    before_events = result['processed_events'] - count_in_last
    if (before_batches < 1 or before_events < 1 or count_in_last < 1 or
            len(batches) != result['processed_batches']):
        raise AssertionError('invalid independent execution prefix')
    assert before_events == sum(len(b['channels']) for b in batches[:-1])
    return DualLimitProbeV0(case_id, before_batches, before_events,
                            before_batches, before_events, count_in_last)


def plan_v0():
    return tuple((cid, case, p) for cid, case in catalog_v0()
                 if (p := probe_for_case_v0(cid, case)) is not None)


def check_eligibility_v0(case, probe):
    """Prove both counters fail on the SAME next batch, not just eventually.

    Note: 24n currently raises ``max_batches`` first when both hold; this
    is NOT used as a specification of the frozen runtime's priority.
    """
    if type(probe) is not DualLimitProbeV0:
        raise TypeError('DualLimitProbeV0 required')
    full = execute_v0(case, max_batches=128, max_events=4096)
    batches = full['observations']['batches']
    if len(batches) != probe.prior_batches + 1:
        raise AssertionError('incorrect failing batch position')
    prefix_events = sum(len(b['channels']) for b in batches[:-1])
    next_events = len(batches[-1]['channels'])
    if (prefix_events != probe.prior_events or
            next_events != probe.pending_batch_events or
            probe.max_batches != probe.prior_batches or
            probe.max_events != probe.prior_events):
        raise AssertionError('incorrect pre-limit boundary')
    if not (probe.prior_batches >= probe.max_batches and
            probe.prior_events + next_events > probe.max_events):
        raise AssertionError('limits not simultaneously eligible')
    reason = None
    try:
        execute_v0(case, max_batches=probe.max_batches,
                   max_events=probe.max_events)
    except OracleLimitV0 as exc:
        reason = str(exc)
        if reason not in {'max_batches', 'max_events'}:
            raise AssertionError('unexpected oracle failure reason') from exc
    else:
        raise AssertionError('independent oracle unexpectedly completed')
    return {'both_eligible': True, 'independent_reason': reason}


def summary_v0():
    ps = plan_v0()
    return {'case_count': len(catalog_v0()), 'dual_limit_probes': len(ps),
            'corpus_sha256': catalog_fingerprint_v0()}
