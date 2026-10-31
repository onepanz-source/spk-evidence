"""A3d: independently executed bounded links and lossless source backpressure."""
from dataclasses import replace
import pytest
from search.spk_24o_semantic_corpus_v0 import catalog_v0
from search.spk_24n_differential_evidence_v0 import canonical, EventV0
from spk_architecture_v1.pe_fabric_v1a import SCHEMES, plan_v1a
from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
from spk_architecture_v1.temporal_service_v1b import uniform_causal_service_plan_v1b
from spk_architecture_v1.causal_memory_v1c import (
    execute_causal_memory_v1c, uniform_causal_memory_plan_v1c)
from spk_architecture_v1.causal_transport_v1d import (
    CausalLinkPlanV1d, CausalLinkAdmissionV1d, CausalLinkHorizonV1d,
    CausalOutboxCapacityV1d, execute_causal_transport_v1d)


def example(cid='relays/parallel/at_zero'):
    return next(case for ident, case in catalog_v0() if ident == cid)


def run(case, scheme='spread', *, link=4096, shared=4096, inflight=4096,
        latency=2, mem=1024, service=128, outbox=128, span=4096):
    f = plan_v1a(case, scheme)
    t = TransportPlanV1a(latency, inflight)
    p = uniform_causal_service_plan_v1b(f, pe_slots=service,
                                          fabric_slots_per_tick=service)
    m = uniform_causal_memory_plan_v1c(f, pe_slots=mem, domain_slots=mem,
                                        fabric_slots_per_tick=mem)
    l = CausalLinkPlanV1d(link, shared, outbox, span)
    return execute_causal_transport_v1d(case, f, t, p, m, l)


@pytest.mark.parametrize('scheme', SCHEMES)
def test_all_ideal_links_exactly_reproduce_a3c(scheme):
    for _, case in catalog_v0():
        f = plan_v1a(case, scheme)
        for latency in (0, 2):
            for service, mem in ((128, 1024), (1, 1024)):
                t = TransportPlanV1a(latency)
                p = uniform_causal_service_plan_v1b(f, pe_slots=service,
                                                      fabric_slots_per_tick=service)
                m = uniform_causal_memory_plan_v1c(f, pe_slots=mem,
                            domain_slots=mem, fabric_slots_per_tick=mem)
                a = execute_causal_memory_v1c(case, f, t, p, m)
                b = execute_causal_transport_v1d(case, f, t, p, m, CausalLinkPlanV1d())
                assert canonical(a['result']) == canonical(b['result'])
                assert a['transport']['transfers'] == b['transport']['transfers']
                assert b['transport']['link_congestion_wait_ticks'] == 0
                assert b['transport']['source_blocked_ticks'] == 0


@pytest.mark.parametrize('scheme', SCHEMES)
def test_finite_transport_replays_every_occurrence_without_drops(scheme):
    total_remote = changed = 0
    for _, case in catalog_v0():
        finite = run(case, scheme, link=1, shared=1, inflight=2)
        ideal = run(case, scheme)
        t = finite['transport']
        assert finite['result']['processed_events'] == len(case.events) + len(t['transfers'])
        assert t['cross_pe_occurrences'] == t['delivered_cross_pe_occurrences']
        assert len(t['link_grants']) == t['cross_pe_occurrences']
        assert t['outstanding_outbox_occurrences'] == t['remaining_inflight_occurrences'] == 0
        assert t['link_congestion_wait_ticks'] == sum(
            row['congestion_wait_ticks'] for row in t['link_grants'])
        assert all(row['link_grants'] <= 1 for row in t['outbox_timeline'])
        assert all(row['inflight'] <= 2 for row in t['outbox_timeline'])
        total_remote += t['cross_pe_occurrences']
        changed += canonical(ideal['result']) != canonical(finite['result'])
    if scheme == 'single':
        assert total_remote == changed == 0
    else:
        assert total_remote > 0 and changed > 0


def test_parallel_remote_edges_survive_fifo_credit_limiting():
    case = example()
    obj = run(case, 'spread', link=1, shared=1, inflight=1)
    assert obj['transport']['source_blocked_ticks'] > 0
    assert obj['transport']['link_congestion_wait_ticks'] > 0
    assert obj['transport']['max_outbox_occupancy'] >= 1
    assert len(obj['transport']['link_grants']) == obj['transport']['cross_pe_occurrences']


def test_no_sources_no_link_grants():
    obj = run(example('relays/isolated/idle'), link=1, shared=1, inflight=1)
    assert obj['transport']['link_grants'] == []
    assert obj['result']['processed_events'] == 0


def test_inadequate_outbox_capacity_fails_closed():
    with pytest.raises(CausalOutboxCapacityV1d, match='outbox capacity'):
        run(example(), link=1, shared=1, outbox=1)


def test_short_horizon_fails_without_closed_result():
    with pytest.raises(CausalLinkHorizonV1d, match='max_link_span_ticks'):
        run(example(), link=1, shared=1, inflight=1, span=1)


@pytest.mark.parametrize('broken', [
    (0, 1, 1, 10), (1, 0, 1, 10), (1, 1, 0, 10),
    (1, 1, 1, 0), (True, 1, 1, 10), (1, True, 1, 10),
    (1, 1, True, 10), (1, 1, 1, True),
])
def test_link_plan_rejects_invalid_quotas(broken):
    case = example()
    f = plan_v1a(case, 'spread')
    p = uniform_causal_service_plan_v1b(f, pe_slots=128,
                                          fabric_slots_per_tick=128)
    m = uniform_causal_memory_plan_v1c(f)
    with pytest.raises(CausalLinkAdmissionV1d):
        execute_causal_transport_v1d(case, f, TransportPlanV1a(2), p, m,
                                      CausalLinkPlanV1d(*broken))


def test_sender_backpressure_changes_next_batch_grant_timestamp():
    case = example('relays/parallel/at_zero')
    # Same source can be scheduled twice; its outbox must drain before the next grant.
    case = replace(case, events=tuple(case.events) + (EventV0(1, 'A', 0),))
    base = run(case, link=4096, shared=4096)
    limited = run(case, link=1, shared=1, inflight=1)
    assert limited['transport']['source_blocked_ticks'] > 0
    # Delayed service can change grants, not just post-hoc output timestamps.
    assert canonical(base['service']['grants']) != canonical(limited['service']['grants'])


def test_limited_memory_and_limited_link_do_not_invent_events():
    obj = run(example(), link=1, shared=1, inflight=1, mem=1)
    assert obj['result']['processed_events'] == len(example().events) + len(obj['transport']['transfers'])
    assert obj['memory']['actual_units'] <= obj['memory']['reserved_units']
