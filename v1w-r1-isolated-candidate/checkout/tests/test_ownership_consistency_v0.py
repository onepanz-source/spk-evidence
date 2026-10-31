"""S3.7c/2: exercise the public ownership/occupancy consistency API."""
from dataclasses import replace

import pytest

from spk_architecture.arbitration_v0 import default_arbitration_policy_v0
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_simulator.access_dependencies_v0 import build_access_dependencies_v0
from spk_simulator.causal_scheduler_v0 import schedule_causal_services_v0
from spk_simulator.event_buffer_audit_v0 import EventBufferOverflowV0, audit_event_buffers_v0
from spk_simulator.event_storage_v0 import RoutedStorageBlockedV0
from spk_simulator.external_ingress_v0 import (
    ExternalArrivalV0, ExternalIngressPlanV0, bind_external_ingress_v0,
)
from spk_simulator.ownership_consistency_v0 import audit_ownership_consistency_v0
from spk_simulator.routed_service_replay_v0 import replay_routed_service_ownership_v0
from spk_network.events_v0 import NetworkEventV0
from tests.test_routing_binding_v0 import setup_case


def context(*, output=3, events=3, same_pe=False, initial=None):
    args, binding, _ = setup_case(
        output=output, events=events, same_pe=same_pe, initial=initial,
    )
    network, observed, placement, plan, provenance, initial_events, arch = args
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
        network, observed, placement, plan, provenance, initial_events,
    )
    schedule = schedule_causal_services_v0(
        arch, requests, graph, default_arbitration_policy_v0(),
    )
    return (network, observed, placement, arch, plan, provenance,
            initial_events, requests, schedule)


def run(ctx, *, ingress=None):
    return audit_ownership_consistency_v0(*ctx, ingress=ingress)


def dynamic(ctx, boundary):
    network, observed, placement, arch, plan, provenance, initial, reqs, _ = ctx
    ingress = bind_external_ingress_v0(
        plan, provenance, initial,
        ExternalIngressPlanV0(tuple(ExternalArrivalV0(i, boundary)
                                    for i in range(len(initial)))),
    )
    graph = build_access_dependencies_v0(
        network, observed, placement, plan, provenance, initial,
    )
    schedule = schedule_causal_services_v0(
        arch, reqs, graph, default_arbitration_policy_v0(), ingress=ingress,
    )
    return ctx[:-1] + (schedule,), ingress


def usage(result, pe_id):
    return next(x for x in result.pe_usage if x.pe_id == pe_id)


def test_real_observed_network_routing_reconciled():
    result = run(context())
    assert len(result.routing_binding.routes) == 3
    assert result.event_buffer_audit.routed_count == 3
    assert result.event_buffer_audit.initial_count == 1


def test_complete_peak_b_and_output_peak_a():
    ctx = context()
    result = run(ctx)
    assert usage(result, 'PE0').peak_pending_output == 3

    # Three routes target PE1, but need not be resident at once.
    done = {c.request_id: c.completion_tick for c in ctx[-1].completions}
    deltas = {}
    assert len(result.routing_binding.routes) == 3

    for route in result.routing_binding.routes:
        assert route.occurrence.target_pe_id == 'PE1'
        arrival = done[route.route_request_id]
        consumption = done[route.consume_request_id]
        deltas[arrival] = deltas.get(arrival, 0) + 1
        deltas[consumption] = deltas.get(consumption, 0) - 1

    occupied = peak = 0
    for tick in sorted(deltas):
        occupied += deltas[tick]
        assert occupied >= 0
        peak = max(peak, occupied)

    assert occupied == 0
    assert usage(result, 'PE1').peak_total_events == peak
    assert usage(result, 'PE1').peak_routed_events == peak


def test_external_is_included_in_source_pe_peak():
    result = run(context())
    assert usage(result, 'PE0').peak_total_events == 1
    assert usage(result, 'PE0').peak_routed_events == 0


def test_no_unowned_or_unconsumed_occurrences():
    result = run(context())
    assert all(p.final_total_events == 0 for p in result.pe_usage)
    assert result.ownership_replay.final_state.pending_output == ()
    assert result.ownership_replay.final_state.admitted_events == ()
    assert len(result.ownership_replay.final_state.consumed_ids) == 3


def test_duplicate_parallel_routes_remain_distinct():
    result = run(context())
    r = result.routing_binding.routes
    assert r[0].occurrence == replace(r[1].occurrence,
                                      event_id=r[0].route_request_id)
    assert len({x.route_request_id for x in r}) == 3


def test_same_pe_uses_shared_event_capacity():
    result = run(context(same_pe=True))
    assert len(result.routing_binding.routes) == 3
    assert usage(result, 'PE0').peak_routed_events >= 1
    assert usage(result, 'PE0').peak_total_events >= 1
    assert usage(result, 'PE1').peak_total_events == 0


def test_full_audit_equal_to_standalone():
    ctx = context()
    result = run(ctx)
    assert result.event_buffer_audit == audit_event_buffers_v0(
        ctx[3], ctx[4], ctx[5], ctx[7], ctx[8], ctx[6],
    )


def test_routed_replay_equal_to_standalone():
    ctx = context()
    result = run(ctx)
    assert result.ownership_replay == replay_routed_service_ownership_v0(
        ctx[3], result.routing_binding, ctx[4], ctx[7], ctx[8],
    )


def test_route_completion_boundaries_exact():
    ctx = context()
    result = run(ctx)
    done = {c.request_id: c.completion_tick for c in ctx[8].completions}
    for route in result.routing_binding.routes:
        assert any(t.operation == 'ADMIT'
                   and t.route_request_id == route.route_request_id
                   and t.service_boundary == done[route.route_request_id]
                   for t in result.ownership_replay.transitions)


def test_legacy_external_preload_at_zero():
    result = run(context())
    assert any(x.service_tick == 0 and x.pe_id == 'PE0'
               and x.external_enqueued == 1
               for x in result.event_buffer_audit.boundaries)


def test_reproducibility():
    ctx = context()
    assert run(ctx) == run(ctx)


def test_output_overflow_is_fail_closed():
    with pytest.raises(RoutedStorageBlockedV0) as ex:
        run(context(output=1))
    assert ex.value.domain == 'OUTPUT'


def test_routed_buffer_overflow_is_fail_closed():
    with pytest.raises((RoutedStorageBlockedV0, EventBufferOverflowV0)):
        run(context(events=1))


def test_missing_completion_rejected():
    ctx = context()
    broken = replace(ctx[-1], completions=ctx[-1].completions[:-1])
    with pytest.raises(ValueError):
        run(ctx[:-1] + (broken,))


def test_repeated_completion_rejected():
    ctx = context()
    broken = replace(ctx[-1], completions=ctx[-1].completions
                     + (ctx[-1].completions[0],))
    with pytest.raises(ValueError):
        run(ctx[:-1] + (broken,))


def test_forged_initial_occurrences_rejected():
    ctx = context()
    with pytest.raises(ValueError):
        run(ctx[:6] + ((NetworkEventV0(2, 'A', 0),
                         NetworkEventV0(2, 'A', 0)),) + ctx[7:])


def test_epoch_mismatch_rejected():
    ctx = context()
    with pytest.raises(ValueError):
        run(ctx[:4] + (replace(ctx[4], epoch_id='DIFFERENT'),) + ctx[5:])


def test_dynamic_external_ingress_uses_actual_boundary():
    ctx, ingress = dynamic(context(), 4)
    result = run(ctx, ingress=ingress)
    assert any(b.external_enqueued == 1 and b.service_tick == 4
               for b in result.event_buffer_audit.boundaries)
    assert not any(b.external_enqueued and b.service_tick == 0
                   for b in result.event_buffer_audit.boundaries)


def test_late_external_cannot_be_consumed_on_old_schedule():
    ctx = context()
    ingress = bind_external_ingress_v0(
        ctx[4], ctx[5], ctx[6], ExternalIngressPlanV0((ExternalArrivalV0(0, 99),)),
    )
    with pytest.raises(ValueError):
        run(ctx, ingress=ingress)


def test_invalid_ingress_binding_rejected():
    with pytest.raises(TypeError):
        run(context(), ingress='invalid')
