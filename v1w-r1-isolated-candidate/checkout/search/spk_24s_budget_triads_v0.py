"""SPK 24s: causal budget-boundary controls without a tie-priority axiom.

Pure, bounded plan. A dual-eligible final batch is tested three ways:
  both violated; only events violated; only batches violated.
The independent engine proves each failure reason in its declared domain.
No frozen imports; its tie reason is retained only as implementation evidence.
"""
from __future__ import annotations

from dataclasses import dataclass

from search.spk_24n_independent_oracle_v0 import execute_v0, OracleLimitV0
from search.spk_24r_dual_limit_plan_v0 import plan_v0 as dual_plan_v0, check_eligibility_v0
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0


@dataclass(frozen=True)
class ControlV0:
    case_id: str
    condition: str
    max_batches: int
    max_events: int
    expected_violated: tuple[str, ...]
    independent_reason: str


def controls_for_v0(case, probe):
    """Produce controls at the SAME unprocessed batch, never at another point."""
    proof = check_eligibility_v0(case, probe)
    if not proof['both_eligible']:
        raise AssertionError('not a simultaneously eligible prefix')
    b, e, k = probe.prior_batches, probe.prior_events, probe.pending_batch_events
    choices = (
        ('both', b, e, ('max_batches', 'max_events')),
        ('events_only', b + 1, e, ('max_events',)),
        ('batches_only', b, e + k, ('max_batches',)),
    )
    result = []
    for condition, batch_limit, event_limit, violated in choices:
        # Reconstruct both inequalities independently of either runtime.
        actual = tuple(name for name, bad in (
            ('max_batches', b >= batch_limit),
            ('max_events', e + k > event_limit),
        ) if bad)
        if actual != violated:
            raise AssertionError('causal budget isolation failed: ' + condition)
        try:
            execute_v0(case, max_batches=batch_limit, max_events=event_limit)
        except OracleLimitV0 as exc:
            reason = str(exc)
        else:
            raise AssertionError('control unexpectedly completed: ' + condition)
        if reason not in violated:
            raise AssertionError('independent interpreter chose noneligible cause')
        if len(violated) == 1 and reason != violated[0]:
            raise AssertionError('independent interpreter rejected isolated cause')
        result.append(ControlV0(probe.case_id, condition, batch_limit,
                                event_limit, violated, reason))
    return tuple(result)


def plan_v0():
    return tuple((cid, case, controls_for_v0(case, probe))
                 for cid, case, probe in dual_plan_v0())


def summary_v0():
    ps = plan_v0()
    return {
        'case_count': 216,
        'triad_count': len(ps),
        'control_probes': sum(len(ctrl) for _, _, ctrl in ps),
        'dual_probes': sum(c.condition == 'both' for _, _, ctrl in ps for c in ctrl),
        'events_only_probes': sum(c.condition == 'events_only' for _, _, ctrl in ps for c in ctrl),
        'batches_only_probes': sum(c.condition == 'batches_only' for _, _, ctrl in ps for c in ctrl),
        'corpus_sha256': catalog_fingerprint_v0(),
    }
