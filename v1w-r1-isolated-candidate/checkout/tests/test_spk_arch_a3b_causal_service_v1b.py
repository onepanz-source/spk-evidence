"""Independent A3b causal PE service tests; no frozen Compiler or Network."""
from dataclasses import replace
import pytest

from search.spk_24n_differential_evidence_v0 import canonical, project_v0, EventV0
from search.spk_24o_semantic_corpus_v0 import catalog_v0
from spk_architecture_v1.pe_fabric_v1a import SCHEMES, plan_v1a
from spk_architecture_v1.temporal_transport_v1a import (
    TransportPlanV1a, TransportCapacityV1a, execute_temporal_v1a,
)
from spk_architecture_v1.temporal_service_v1b import (
    CausalServicePlanV1b, CausalServiceAdmissionV1b,
    CausalServiceHorizonV1b, execute_causal_service_v1b,
    uniform_causal_service_plan_v1b,
)


def sample(name):
    return next(c for cid, c in catalog_v0() if cid == name)


def digest(result):
    return canonical(project_v0(result, result['observations']['batches'],
                                result['observations']['routes']))


def plan(fabric, pe=128, shared=128, span=4096):
    return uniform_causal_service_plan_v1b(
        fabric, pe_slots=pe, fabric_slots_per_tick=shared,
        max_service_span_ticks=span)


@pytest.mark.parametrize('scheme', SCHEMES)
def test_full_corpus_ideal_exact_a3a_at_zero_and_positive_remote_latency(scheme):
    for cid, case in catalog_v0():
        fabric = plan_v1a(case, scheme)
        for latency in (0, 2):
            transport = TransportPlanV1a(latency)
            expected = execute_temporal_v1a(case, fabric, transport)
            observed = execute_causal_service_v1b(case, fabric, transport, plan(fabric))
            assert digest(observed['result']) == digest(expected['result']), (cid, latency)
            assert observed['service']['event_weighted_wait_ticks'] == 0
            assert observed['service']['pe_stall_incidents'] == 0
            assert observed['service']['fabric_stall_incidents'] == 0
            assert observed['transport']['delivered_cross_pe_occurrences'] == (
                expected['transport']['delivered_cross_pe_occurrences'])


@pytest.mark.parametrize('mode', ('pe', 'shared', 'both'))
def test_finite_services_conserve_every_event_and_route(mode):
    slots = {'pe': (1, 128), 'shared': (128, 1), 'both': (1, 1)}
    for _, case in catalog_v0():
        for scheme in SCHEMES:
            fabric = plan_v1a(case, scheme)
            for latency in (0, 2):
                local, global_ = slots[mode]
                obj = execute_causal_service_v1b(
                    case, fabric, TransportPlanV1a(latency),
                    plan(fabric, local, global_))
                result, service, trans = obj['result'], obj['service'], obj['transport']
                assert result['processed_events'] == len(case.events) + len(trans['transfers'])
                assert trans['cross_pe_occurrences'] == trans['delivered_cross_pe_occurrences']
                assert trans['remaining_inflight_occurrences'] == 0
                assert len(service['grants']) == result['processed_batches']
                assert all(grant['ready_timestamp'] <= grant['service_timestamp']
                           for grant in service['grants'])
                assert service['event_weighted_wait_ticks'] == sum(
                    grant['wait_ticks'] * len(grant['channels']) for grant in service['grants'])
                for row in trans['transfers']:
                    assert row['delivery_timestamp'] == (row['emission_timestamp']
                            + row['declared_delay_ticks'] +
                            (latency if row['cross_pe'] else 0))
                for tick in service['timeline']:
                    assert tick['fabric_grants'] <= global_
                    assert all(n <= local for _, n in tick['pe_grants'])


def test_shared_capacity_changes_actual_emission_timestamps():
    case = sample('relays/isolated/idle')
    case = replace(case, events=(EventV0(0, 'A', 0), EventV0(0, 'B', 0),
                                 EventV0(0, 'C', 0)))
    fabric = plan_v1a(case, 'spread')
    free = execute_causal_service_v1b(case, fabric, TransportPlanV1a(0), plan(fabric))
    constrained = execute_causal_service_v1b(case, fabric, TransportPlanV1a(0),
                                            plan(fabric, 128, 1))
    assert [x['timestamp'] for x in free['result']['terminal_outputs']] == [0, 0, 0]
    assert [x['timestamp'] for x in constrained['result']['terminal_outputs']] == [0, 1, 2]
    assert constrained['service']['event_weighted_wait_ticks'] == 3
    assert constrained['service']['fabric_stall_incidents'] > 0
    assert constrained['service']['pe_stall_incidents'] == 0


def test_per_pe_slots_independent_of_shared_quota():
    case = sample('relays/isolated/idle')
    case = replace(case, events=(EventV0(0, 'A', 0), EventV0(0, 'B', 0),
                                 EventV0(0, 'C', 0)))
    single = plan_v1a(case, 'single')
    spread = plan_v1a(case, 'spread')
    one = execute_causal_service_v1b(case, single, TransportPlanV1a(0),
                                    plan(single, 1, 128))
    three = execute_causal_service_v1b(case, spread, TransportPlanV1a(0),
                                      plan(spread, 1, 128))
    assert [x['timestamp'] for x in one['result']['terminal_outputs']] == [0, 1, 2]
    assert [x['timestamp'] for x in three['result']['terminal_outputs']] == [0, 0, 0]
    assert one['service']['pe_stall_incidents'] > 0
    assert one['service']['fabric_stall_incidents'] == 0


def test_deferred_batches_retain_ready_tick_identity():
    case = sample('relays/isolated/idle')
    case = replace(case, events=(EventV0(0, 'A', 0), EventV0(0, 'B', 0),
                                 EventV0(1, 'B', 0)))
    fabric = plan_v1a(case, 'spread')
    obj = execute_causal_service_v1b(case, fabric, TransportPlanV1a(0),
                                    plan(fabric, 128, 1))
    b = [x for x in obj['service']['grants'] if x['node_id'] == 'B']
    assert [(x['ready_timestamp'], x['service_timestamp']) for x in b] == [(0, 1), (1, 2)]


def test_parallel_routes_are_distinct_and_coalesce_on_arrival():
    case = sample('relays/parallel/at_zero')
    fabric = plan_v1a(case, 'spread')
    obj = execute_causal_service_v1b(case, fabric, TransportPlanV1a(2),
                                    plan(fabric, 1, 1))
    b = [x for x in obj['service']['grants'] if x['node_id'] == 'B']
    assert b[0]['channels'] == [0, 0]
    assert obj['transport']['cross_pe_occurrences'] >= 2


def test_time_horizon_failure_no_closed_result():
    case = sample('relays/chain/at_zero')
    fabric = plan_v1a(case, 'spread')
    with pytest.raises(CausalServiceHorizonV1b, match='max_service_span'):
        execute_causal_service_v1b(case, fabric, TransportPlanV1a(0),
                                   plan(fabric, 1, 1, 1))


def test_remote_inflight_capacity_exhaustion_not_hidden():
    case = sample('relays/fork/at_zero')
    fabric = plan_v1a(case, 'spread')
    with pytest.raises(TransportCapacityV1a, match='max_inflight'):
        execute_causal_service_v1b(case, fabric,
                                   TransportPlanV1a(2, max_inflight_occurrences=1),
                                   plan(fabric, 1, 1))


@pytest.mark.parametrize('wrong', [
    (True, 1, 100), (0, 1, 100), (1, 0, 100), (1, 1, 0),
    (1, 1, True), (-1, 1, 100),
])
def test_invalid_controller_quotas_rejected(wrong):
    case = sample('relays/chain/at_zero')
    fabric = plan_v1a(case, 'spread')
    with pytest.raises(CausalServiceAdmissionV1b):
        execute_causal_service_v1b(case, fabric, TransportPlanV1a(0),
                                   plan(fabric, *wrong))


def test_duplicate_missing_and_unknown_pe_quota_rejected():
    case = sample('relays/chain/at_zero')
    fabric = plan_v1a(case, 'spread')
    for slots in ((('PE0', 1), ('PE0', 1)),
                  (('PE0', 1),),
                  (('PE0', 1), ('PE1', 1), ('PE99', 1))):
        with pytest.raises(CausalServiceAdmissionV1b):
            execute_causal_service_v1b(case, fabric, TransportPlanV1a(0),
                                       CausalServicePlanV1b(slots, 1))


def test_empty_work_closes_with_no_grants():
    case = sample('relays/isolated/idle')
    fabric = plan_v1a(case, 'spread')
    obj = execute_causal_service_v1b(case, fabric, TransportPlanV1a(2),
                                    plan(fabric, 1, 1))
    assert obj['result']['processed_events'] == 0
    assert obj['service']['grants'] == []
    assert obj['transport']['remaining_inflight_occurrences'] == 0
