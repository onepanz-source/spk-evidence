"""Integration of Network provenance, causal scheduling, and finite ownership."""
from dataclasses import replace

import pytest

from spk_architecture.arbitration_v0 import default_arbitration_policy_v0
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_simulator.access_dependencies_v0 import build_access_dependencies_v0
from spk_simulator.causal_scheduler_v0 import schedule_causal_services_v0
from spk_simulator.event_storage_v0 import RoutedStorageBlockedV0
from spk_simulator.routed_service_replay_v0 import replay_routed_service_ownership_v0
from tests.test_routing_binding_v0 import setup_case


def integrated_case(*, output=3, events=3, same_pe=False):
    args, binding, _ = setup_case(output=output, events=events, same_pe=same_pe)
    network, observed, placement, plan, provenance, initial, architecture = args
    requests = []
    for ref in plan.references:
        intent = ref.intent
        target = plan.catalog.get(ref.target_id)
        requests.append(MemoryServiceRequestV0(
            request_id=intent.request_id,
            principal_id=f'compiler-s37c-{intent.request_id}',
            activity=intent.activity,
            profile_id='s37c-units-v0',
            epoch_id=intent.epoch_id,
            requester_pe_id=intent.pe_id,
            target_pe_id=target.pe_id,
            target_id=ref.target_id,
            domain=target.domain,
            kind=intent.kind,
            quantity=intent.quantity,
            service_units=1,
            event_time=intent.event_time,
        ))
    requests = tuple(requests)
    graph = build_access_dependencies_v0(
        network, observed, placement, plan, provenance, initial,
    )
    schedule = schedule_causal_services_v0(
        architecture, requests, graph, default_arbitration_policy_v0(),
    )
    return architecture, binding, plan, requests, schedule


def run(args):
    return replay_routed_service_ownership_v0(*args)


def with_completion(args, request_id, tick):
    arch, manifest, plan, requests, schedule = args
    completions = tuple(
        replace(c, completion_tick=tick) if c.request_id == request_id else c
        for c in schedule.completions
    )
    slices = tuple(
        replace(s, service_tick=tick - 1) if s.request_id == request_id else s
        for s in schedule.slices
    )
    schedule = replace(schedule, completions=completions, slices=slices,
                       total_service_ticks=max(
                           schedule.total_service_ticks, tick))
    return arch, manifest, plan, requests, schedule


def test_end_to_end_replay_with_real_network_fixture():
    arch, binding, plan, reqs, schedule = integrated_case()
    result = run((arch, binding, plan, reqs, schedule))
    assert len(binding.routes) == 3
    assert len(result.transitions) == 9
    assert set(result.final_state.consumed_ids) == {
        item.route_request_id for item in binding.routes
    }
    assert not result.final_state.pending_output
    assert not result.final_state.admitted_events


def test_distinct_parallel_routes():
    result = run(integrated_case())
    offers = [x.route_request_id for x in result.transitions
              if x.operation == 'OFFER']
    admits = [x.route_request_id for x in result.transitions
              if x.operation == 'ADMIT']
    consumes = [x.route_request_id for x in result.transitions
                if x.operation == 'CONSUME']
    assert len(set(offers)) == len(offers) == 3
    assert sorted(offers) == sorted(admits) == sorted(consumes)


def test_event_logical_timestamps_do_not_change():
    args = integrated_case()
    original = tuple((x.occurrence.emission_event_time,
                      x.occurrence.delivery_event_time) for x in args[1].routes)
    run(args)
    assert original == tuple((x.occurrence.emission_event_time,
                             x.occurrence.delivery_event_time) for x in args[1].routes)


def test_two_pes_output_capacity():
    result = run(integrated_case())
    assert dict(result.peak_output_by_pe)['PE0'] == 3
    assert dict(result.peak_output_by_pe)['PE1'] == 0


def test_same_pe_destination():
    result = run(integrated_case(same_pe=True))
    assert set(result.final_state.consumed_ids)
    assert dict(result.peak_routed_events_by_pe)['PE0'] > 0


def test_output_full_is_explicitly_rejected():
    with pytest.raises(RoutedStorageBlockedV0) as exc:
        run(integrated_case(output=1))
    assert exc.value.domain == 'OUTPUT'


def test_routed_event_full_is_explicitly_rejected():
    with pytest.raises(RoutedStorageBlockedV0) as exc:
        run(integrated_case(events=1))
    assert exc.value.domain == 'EVENT'


def test_replay_is_deterministic():
    args = integrated_case()
    assert run(args) == run(args)


def test_missing_completion_rejected():
    arch, binding, plan, requests, schedule = integrated_case()
    with pytest.raises(ValueError, match='coverage'):
        run((arch, binding, plan, requests,
             replace(schedule, completions=schedule.completions[:-1])))


def test_duplicate_completion_rejected():
    arch, binding, plan, requests, schedule = integrated_case()
    with pytest.raises(ValueError, match='coverage'):
        run((arch, binding, plan, requests,
             replace(schedule, completions=schedule.completions
                     + (schedule.completions[0],))))


def test_missing_service_slice_rejected():
    arch, binding, plan, requests, schedule = integrated_case()
    with pytest.raises(ValueError, match='missing service slices'):
        run((arch, binding, plan, requests,
             replace(schedule, slices=schedule.slices[:-1])))


def test_inconsistent_service_units_rejected():
    arch, binding, plan, requests, schedule = integrated_case()
    with pytest.raises(ValueError, match='service conservation'):
        run((arch, binding, plan, requests,
             replace(schedule, slices=(replace(schedule.slices[0], granted_units=99),)
                     + schedule.slices[1:])))


def test_reject_route_completion_before_emission():
    args = integrated_case()
    route = args[1].routes[0]
    source = next(ref.intent.request_id for ref in args[2].references
                  if ref.intent.node_id == route.occurrence.source_node_id
                  and ref.intent.event_time == route.occurrence.emission_event_time
                  and ref.intent.kind.value == 'EMISSION_RECORD')
    emission_tick = next(c.completion_tick for c in args[4].completions
                         if c.request_id == source)
    with pytest.raises(ValueError, match='noncausal'):
        run(with_completion(args, route.route_request_id, emission_tick))


def test_reject_consume_completion_before_admission():
    args = integrated_case()
    route = args[1].routes[0]
    route_tick = next(c.completion_tick for c in args[4].completions
                      if c.request_id == route.route_request_id)
    with pytest.raises(ValueError, match='noncausal'):
        run(with_completion(args, route.consume_request_id, route_tick))


def test_epoch_mismatch_rejected():
    arch, binding, plan, requests, schedule = integrated_case()
    with pytest.raises(ValueError, match='epoch mismatch'):
        run((arch, binding, replace(plan, epoch_id='different'), requests, schedule))


def test_tampered_route_node_identity_rejected():
    arch, binding, plan, requests, schedule = integrated_case()
    route_id = binding.routes[0].route_request_id
    refs = tuple(replace(ref, intent=replace(ref.intent, node_id='wrong'))
                 if ref.intent.request_id == route_id else ref
                 for ref in plan.references)
    with pytest.raises(ValueError, match='route/emission/consumption'):
        run((arch, binding, replace(plan, references=refs), requests, schedule))


def test_source_pe_mismatch_rejected():
    arch, binding, plan, requests, schedule = integrated_case()
    rid = binding.routes[0].route_request_id
    changed = tuple(replace(req, requester_pe_id='PE1') if req.request_id == rid
                    else req for req in requests)
    with pytest.raises(ValueError):
        run((arch, binding, plan, changed, schedule))


def test_wrong_route_service_target_rejected():
    arch, binding, plan, requests, schedule = integrated_case()
    rid = binding.routes[0].route_request_id
    changed = tuple(replace(req, target_pe_id='PE0') if req.request_id == rid
                    else req for req in requests)
    with pytest.raises(ValueError):
        run((arch, binding, plan, changed, schedule))
