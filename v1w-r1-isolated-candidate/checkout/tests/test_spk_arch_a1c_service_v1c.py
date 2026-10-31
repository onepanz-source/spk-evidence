"""Finite PE service fabric: independent logical/physical-accounting separation."""
from collections import Counter
from dataclasses import replace

import pytest

from search.spk_24o_semantic_corpus_v0 import catalog_v0, catalog_fingerprint_v0
from spk_architecture_v1.pe_fabric_v1a import plan_v1a
from spk_architecture_v1.pe_execution_v1b import (
    execute_on_pes_v1b, PELimitV1b,
)
from spk_architecture_v1.pe_service_v1c import (
    ServicePlanV1c, PEServiceAdmissionV1c, PEQueueOverflowV1c,
    uniform_service_plan_v1c, execute_with_service_v1c,
)

PIN = 'cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5'
REGIMES = ((1, 1), (1, 4096), (4096, 1), (4096, 4096))


def run(case, scheme, pe_slots=1, global_slots=1, queue=4096, **kw):
    fab = plan_v1a(case, scheme)
    plan = uniform_service_plan_v1c(
        fab, pe_slots=pe_slots, fabric_slots_per_tick=global_slots,
        queue_event_capacity_per_pe=queue)
    return execute_with_service_v1c(case, fab, plan, **kw)


def test_pinned_source_identity():
    assert catalog_fingerprint_v0() == PIN
    assert len(catalog_v0()) == 216


@pytest.mark.parametrize('scheme', ('single', 'split', 'spread'))
def test_all_216_four_service_regimes_preserve_complete_a1b_result(scheme):
    for case_id, case in catalog_v0():
        fab = plan_v1a(case, scheme)
        ref = execute_on_pes_v1b(case, fab)
        for pe_cap, global_cap in REGIMES:
            actual = run(case, scheme, pe_cap, global_cap)
            assert actual['result'] == ref['result'], (case_id, scheme, pe_cap, global_cap)
            assert actual['transport'] == ref['transport']
            assert actual['pe_snapshots'] == ref['pe_snapshots']
            ledger = actual['service']['ledger']
            assert len(ledger) == ref['result']['processed_batches']
            last_tick = -1
            counts_global, counts_pe = Counter(), Counter()
            for r in ledger:
                assert r['service_tick'] >= r['logical_timestamp']
                assert r['service_wait_ticks'] == r['service_tick'] - r['logical_timestamp']
                assert r['service_tick'] >= last_tick
                last_tick = r['service_tick']
                counts_global[r['service_tick']] += 1
                counts_pe[(r['service_tick'], r['pe_id'])] += 1
            assert all(x <= global_cap for x in counts_global.values())
            assert all(x <= pe_cap for x in counts_pe.values())
            if (pe_cap, global_cap) == (4096, 4096):
                assert all(r['service_wait_ticks'] == 0 for r in ledger)
                assert not actual['service']['fabric_stall_ticks']
                assert not actual['service']['pe_stall_ticks']


def test_service_capacity_is_independent_of_logical_event_timestamps():
    # Interleaved includes A and B events at the same logical time, but those
    # must remain at that time even when virtual service is postponed.
    case = next(c for n, c in catalog_v0() if n == 'relays/isolated/interleaved')
    congested = run(case, 'single', 1, 1)
    free = run(case, 'single', 4096, 4096)
    assert congested['result'] == free['result']
    assert congested['service']['fabric_stall_ticks'] > 0
    assert congested['service']['pe_stall_ticks'] > 0
    assert congested['service']['max_service_tick'] > free['service']['max_service_tick']


def test_per_pe_contention_separated_from_shared_fabric_contention():
    case = next(c for n, c in catalog_v0() if n == 'relays/isolated/interleaved')
    pe_only = run(case, 'single', 1, 4096)['service']
    shared_only = run(case, 'single', 4096, 1)['service']
    assert pe_only['pe_stall_ticks'] > 0 and pe_only['fabric_stall_ticks'] == 0
    assert shared_only['fabric_stall_ticks'] > 0 and shared_only['pe_stall_ticks'] == 0
    spread = run(case, 'spread', 1, 4096)['service']
    assert spread['pe_stall_ticks'] == 0


def test_ingress_queue_exact_capacity_and_rejection():
    case = next(c for n, c in catalog_v0() if n == 'relays/isolated/duplicate')
    ok = run(case, 'single', queue=2)
    assert ok['result']['processed_events'] == 2
    with pytest.raises(PEQueueOverflowV1c, match='queue_event_capacity'):
        run(case, 'single', queue=1)


def test_routed_queue_overflow_fails_without_successful_receipt():
    # One initial A event creates two deliveries to B on parallel edges.
    case = next(c for n, c in catalog_v0() if n == 'relays/parallel/at_zero')
    with pytest.raises(PEQueueOverflowV1c, match='queue_event_capacity'):
        run(case, 'spread', queue=1)


def test_finite_batch_and_event_budget_classification_preserved():
    case = next(c for _, c in catalog_v0()
                if execute_on_pes_v1b(c, plan_v1a(c, 'single'))['result']['processed_batches'] > 1
                and execute_on_pes_v1b(c, plan_v1a(c, 'single'))['result']['processed_events'] > 1)
    complete = run(case, 'split')
    batches = complete['result']['processed_batches']
    events = complete['result']['processed_events']
    assert run(case, 'split', max_batches=batches)['result'] == complete['result']
    assert run(case, 'split', max_events=events)['result'] == complete['result']
    with pytest.raises(PELimitV1b, match='max_batches'):
        run(case, 'split', max_batches=batches-1)
    with pytest.raises(PELimitV1b, match='max_events'):
        run(case, 'split', max_events=events-1)


def test_service_plan_rejects_boolean_nonpositive_and_missing_pe():
    case = catalog_v0()[0][1]
    fab = plan_v1a(case, 'spread')
    for value in (True, 0, -1, 1.5):
        bad = uniform_service_plan_v1c(fab, pe_slots=value, fabric_slots_per_tick=1)
        with pytest.raises(PEServiceAdmissionV1c):
            execute_with_service_v1c(case, fab, bad)
    good = uniform_service_plan_v1c(fab, pe_slots=1, fabric_slots_per_tick=1)
    for replacement in (
        replace(good, pe_slots=good.pe_slots[:-1]),
        replace(good, pe_slots=good.pe_slots[:1] + (good.pe_slots[0],) + good.pe_slots[2:]),
        replace(good, fabric_slots_per_tick=False),
        replace(good, queue_event_capacity_per_pe=0),
        ServicePlanV1c((('PE999', 1), ('PE1', 1), ('PE2', 1)), 1, 16),
    ):
        with pytest.raises(PEServiceAdmissionV1c):
            execute_with_service_v1c(case, fab, replacement)


def test_ordering_is_deterministic_and_observations_identical():
    case = next(c for n, c in catalog_v0() if n == 'relays/diamond/interleaved')
    flipped = replace(case, events=tuple(reversed(case.events)))
    first = run(case, 'spread')
    second = run(flipped, 'spread')
    assert first == second
    assert first == run(case, 'spread')


def test_capacity_engine_does_not_import_compiler_network_or_oracle():
    from pathlib import Path
    import spk_architecture_v1.pe_service_v1c as m
    text = Path(m.__file__).read_text()
    for needle in ('from spk_compiler', 'import spk_compiler',
                   'from spk_network', 'import spk_network',
                   'from spk_core', 'import spk_core',
                   'execute_v0(', 'execute_manifest_v0(', 'execute_on_pes_v1b('):
        assert needle not in text
