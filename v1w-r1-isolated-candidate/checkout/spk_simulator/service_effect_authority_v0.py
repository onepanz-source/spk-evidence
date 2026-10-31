"""SPK S3.7d/3b2b2e: authenticate select service completions by replaying bounded storage.

This pure gate witnesses *only* output publication, route delivery and complete
batch input consumption. It does NOT authorize service starts, verify an entire
causal execution or confirm internal/non-storage request kinds.
"""
from dataclasses import dataclass

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_simulator.atomic_emission_admission_v0 import AtomicEmissionAdmissionV0
from spk_simulator.bounded_backpressure_driver_v0 import (
    BackpressureServiceFrameV0, BoundedBackpressureStateV0,
    BackpressureStepV0, advance_bounded_backpressure_v0,
)
from spk_simulator.causal_service_quantum_v0 import ServiceQuantumStateV0
from spk_simulator.routing_binding_v0 import RoutedBindingManifestV0


@dataclass(frozen=True, slots=True)
class ConfirmedStorageEffectV0:
    request_id: int
    kind: Kind
    service_boundary: int
    route_request_ids: tuple[int, ...] = ()
    external_input_indices: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class ServiceEffectAuthorityResultV0:
    driver_state: BoundedBackpressureStateV0
    driver_step: BackpressureStepV0
    confirmed_request_ids: tuple[int, ...]
    effects: tuple[ConfirmedStorageEffectV0, ...]
    granted_route_request_ids: tuple[int, ...]


def authenticate_service_storage_effects_v0(
    architecture: ArchitectureProfileV0,
    manifest: RoutedBindingManifestV0,
    admission: AtomicEmissionAdmissionV0,
    requests: tuple[MemoryServiceRequestV0, ...],
    service_state: ServiceQuantumStateV0,
    driver_state: BoundedBackpressureStateV0,
    frame: BackpressureServiceFrameV0,
) -> ServiceEffectAuthorityResultV0:
    """Apply one *real* driver boundary; derive evidence, never accept caller confirmations.

    All requested storage effects must have completed their service work before
    the boundary. A BATCH_CONSUME must consume its entire declared set of
    routed and external input occurrences atomically. Memory grants returned
    here are evidence of route reservation, NOT permission to start a request
    without the causal frontier check.
    """
    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError('invalid architecture')
    if type(manifest) is not RoutedBindingManifestV0:
        raise TypeError('invalid routing manifest')
    if type(admission) is not AtomicEmissionAdmissionV0:
        raise TypeError('invalid emission admission')
    if type(service_state) is not ServiceQuantumStateV0:
        raise TypeError('invalid service state')
    if type(driver_state) is not BoundedBackpressureStateV0:
        raise TypeError('invalid driver state')
    if type(frame) is not BackpressureServiceFrameV0:
        raise TypeError('invalid driver frame')
    if (type(requests) is not tuple or
            any(type(x) is not MemoryServiceRequestV0 for x in requests)):
        raise TypeError('invalid service requests')
    if frame.service_boundary != service_state.next_service_tick:
        raise ValueError('SERVICE_TIME boundary/state mismatch')
    if not (architecture.profile_id == manifest.profile_id == admission.profile_id
            == driver_state.boundary.storage.profile_id
            == driver_state.boundary.ledger.profile_id):
        raise ValueError('architecture/profile mismatch')
    if (manifest.epoch_id != admission.epoch_id
            or manifest.epoch_id != driver_state.boundary.storage.epoch_id
            or manifest.epoch_id != driver_state.boundary.ledger.epoch_id):
        raise ValueError('epoch mismatch')
    by_id = {request.request_id: request for request in requests}
    if len(by_id) != len(requests):
        raise ValueError('duplicate request')
    finished = {x.request_id: x.finish_boundary for x in service_state.awaiting_confirmation}
    completed = {x.request_id for x in service_state.confirmed}
    partial = {x.request_id for x in service_state.partial}
    if (set(finished) | completed | partial) - set(by_id):
        raise ValueError('service request identity mismatch')

    groups = {group.emission_request_id: group for group in admission.groups}
    routes = {route.route_request_id: route for route in manifest.routes}
    if len(groups) != len(admission.groups) or len(routes) != len(manifest.routes):
        raise ValueError('duplicate bound identity')
    if set(groups) - set(by_id) or set(routes) - set(by_id):
        raise ValueError('missing storage-effect service request')
    for emission in admission.groups:
        request = by_id[emission.emission_request_id]
        if (request.kind is not Kind.EMISSION_RECORD or
                request.target_pe_id != emission.source_pe_id):
            raise ValueError('emission request/kind/PE mismatch')
    for route in manifest.routes:
        request = by_id[route.route_request_id]
        if (request.kind is not Kind.ROUTE_ENQUEUE or
                request.target_pe_id != route.occurrence.target_pe_id):
            raise ValueError('route request/kind/PE mismatch')
        target = by_id.get(route.consume_request_id)
        if (target is None or target.kind is not Kind.BATCH_CONSUME or
                target.target_pe_id != route.occurrence.target_pe_id):
            raise ValueError('route consume request mismatch')

    arrivals = {x.input_index: x for x in driver_state.boundary.ledger.ingress.arrivals}
    if len(arrivals) != len(driver_state.boundary.ledger.ingress.arrivals):
        raise ValueError('duplicate external input index')
    for arrival in arrivals.values():
        target = by_id.get(arrival.consume_request_id)
        if (target is None or target.kind is not Kind.BATCH_CONSUME or
                target.target_pe_id != arrival.target_pe_id):
            raise ValueError('external consume request mismatch')

    def finished_at_boundary(rid: int):
        if rid not in finished or finished[rid] > frame.service_boundary:
            raise ValueError(f'storage effect without finished service: {rid}')

    # Validate caller actions against service work *before* running the driver.
    # Missing batch-input identities may not be interpreted as partial consume.
    for rid in frame.new_ready_emission_ids + frame.route_commits:
        finished_at_boundary(rid)
    expected_by_consume = {}
    for route in manifest.routes:
        expected_by_consume.setdefault(route.consume_request_id, [set(), set()])[0].add(route.route_request_id)
    for arrival in arrivals.values():
        expected_by_consume.setdefault(arrival.consume_request_id, [set(), set()])[1].add(arrival.input_index)
    actual_by_consume = {}
    for route_id in frame.route_consumptions:
        if route_id not in routes:
            raise ValueError('unbound route consumption')
        actual_by_consume.setdefault(routes[route_id].consume_request_id, [set(), set()])[0].add(route_id)
    for input_id in frame.external_consumptions:
        if input_id not in arrivals:
            raise ValueError('unbound external consumption')
        actual_by_consume.setdefault(arrivals[input_id].consume_request_id, [set(), set()])[1].add(input_id)
    for rid, observed in actual_by_consume.items():
        finished_at_boundary(rid)
        if observed != expected_by_consume[rid]:
            raise ValueError('partial batch input consumption')

    # Driver is executed here. The result's operations come from bounded,
    # provenance-bound storage transitions, not invented caller acknowledgments.
    next_driver, driver_step = advance_bounded_backpressure_v0(
        architecture, manifest, admission, driver_state, frame,
    )
    transition = driver_step.transition
    offered = {x.occurrence_id for x in transition.boundary.operations if x.operation == 'OFFER'}
    committed = {x.occurrence_id for x in transition.boundary.operations if x.operation == 'COMMIT'}
    consumed_route = {x.occurrence_id for x in transition.boundary.operations if x.operation == 'CONSUME_ROUTE'}
    consumed_external = {x.occurrence_id for x in transition.boundary.operations if x.operation == 'CONSUME_EXTERNAL'}
    if committed != set(frame.route_commits):
        raise ValueError('route commits lack boundary evidence')
    if (consumed_route != set(frame.route_consumptions) or
            consumed_external != set(frame.external_consumptions)):
        raise ValueError('consumption lacks boundary evidence')

    result = []
    for rid in transition.admitted_emission_ids:
        finished_at_boundary(rid)
        group = groups[rid]
        if not set(group.route_request_ids) <= offered:
            raise ValueError('atomic emission publication evidence mismatch')
        result.append(ConfirmedStorageEffectV0(
            rid, Kind.EMISSION_RECORD, frame.service_boundary, route_request_ids=group.route_request_ids,
        ))
    for rid in sorted(committed):
        finished_at_boundary(rid)
        result.append(ConfirmedStorageEffectV0(
            rid, Kind.ROUTE_ENQUEUE, frame.service_boundary, route_request_ids=(rid,),
        ))
    for rid, parts in sorted(actual_by_consume.items()):
        result.append(ConfirmedStorageEffectV0(
            rid, Kind.BATCH_CONSUME, frame.service_boundary,
            route_request_ids=tuple(sorted(parts[0])),
            external_input_indices=tuple(sorted(parts[1])),
        ))
    ids = [item.request_id for item in result]
    if len(ids) != len(set(ids)):
        raise ValueError('service effect confirmed twice')
    ordered = tuple(sorted(result, key=lambda item: item.request_id))
    return ServiceEffectAuthorityResultV0(
        driver_state=next_driver,
        driver_step=driver_step,
        confirmed_request_ids=tuple(item.request_id for item in ordered),
        effects=ordered,
        granted_route_request_ids=tuple(sorted(transition.granted_route_ids)),
    )
