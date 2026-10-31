"""SPK 24q: pure bounded budget-plan generation, independent of frozen modules.

The budget probes are based on full successful independent executions. They
cannot prove frozen-runtime behavior and must be checked by a separate runner.
"""
from __future__ import annotations

from dataclasses import dataclass

from search.spk_24n_independent_oracle_v0 import execute_v0
from search.spk_24o_semantic_corpus_v0 import catalog_v0, catalog_fingerprint_v0


@dataclass(frozen=True)
class BudgetProbeV0:
    case_id: str
    kind: str
    max_batches: int
    max_events: int
    expected_status: str
    expected_reason: str | None


def probes_for_case_v0(case_id, case):
    """Exact-success plus independently predicted single-budget exhaustion.

    Never test ambiguous dual-limit precedence here; another gate must define
    that contract before checking it. Never use an invalid zero budget.
    """
    if type(case_id) is not str or not case_id:
        raise ValueError('case_id must be nonempty')
    result = execute_v0(case, max_batches=128, max_events=4096)
    batches, events = result['processed_batches'], result['processed_events']
    probes = [BudgetProbeV0(case_id, 'exact_success', max(1, batches),
                            max(1, events), 'CLOSED', None)]
    if events > 1:
        probes.append(BudgetProbeV0(case_id, 'event_limit', 128,
                                    events - 1, 'LIMIT_REACHED', 'max_events'))
    if batches > 1:
        probes.append(BudgetProbeV0(case_id, 'batch_limit', batches - 1,
                                    4096, 'LIMIT_REACHED', 'max_batches'))
    return tuple(probes)


def plan_v0():
    return tuple((cid, case, probes_for_case_v0(cid, case))
                 for cid, case in catalog_v0())


def plan_summary_v0():
    entries = plan_v0()
    return {
        'case_count': len(entries),
        'probe_count': sum(len(p) for _, _, p in entries),
        'closed_probes': sum(p.expected_status == 'CLOSED'
                             for _, _, pp in entries for p in pp),
        'event_limit_probes': sum(p.expected_reason == 'max_events'
                                  for _, _, pp in entries for p in pp),
        'batch_limit_probes': sum(p.expected_reason == 'max_batches'
                                  for _, _, pp in entries for p in pp),
        'corpus_sha256': catalog_fingerprint_v0(),
    }
