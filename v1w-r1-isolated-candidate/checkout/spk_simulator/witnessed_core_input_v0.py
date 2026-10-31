"""SPK S3.7d/3b2b2k/3: connect *actual* EVENT consumption to Core batch inputs.

This boundary executes the existing self-framed, bounded service controller. It
never accepts caller-authored 'consumed' IDs, service completions, or channels.
The resulting batch is a witnessed INPUT, not a state/read/commit authority.
The manifest is still trace-derived: end-to-end non-circular execution is NOT
established until outputs are generated from independent Core computations.
"""
from dataclasses import dataclass

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_architecture.access_v0 import MemoryDomainV0 as Domain
from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_network.model_v0 import NetworkV0
from spk_simulator.access_dependencies_v0 import AccessDependencyGraphV0
from spk_simulator.atomic_emission_admission_v0 import AtomicEmissionAdmissionV0
from spk_simulator.external_ingress_v0 import ExternalIngressBindingV0
from spk_simulator.owned_service_autoframe_v0 import (
    AutoFramedOwnedTickV0, advance_autoframed_owned_tick_v0,
)
from spk_simulator.owned_service_tick_v0 import OwnedServiceTickStateV0
from spk_simulator.routing_binding_v0 import RoutedBindingManifestV0


@dataclass(frozen=True, slots=True)
class WitnessedCoreInputBatchV0:
    """Immutable receipt of one *entire* BATCH_CONSUME from the bounded driver."""
    consume_request_id: int
    epoch_id: str
    node_id: str
    event_time: int
    target_pe_id: str
    channels: tuple[int, ...]
    route_request_ids: tuple[int, ...]
    external_input_indices: tuple[int, ...]
    service_boundary: int


@dataclass(frozen=True, slots=True)
class WitnessedCoreInputTickV0:
    owned_tick: AutoFramedOwnedTickV0
    consumed_batches: tuple[WitnessedCoreInputBatchV0, ...]


def advance_witnessed_core_input_tick_v0(
    architecture: ArchitectureProfileV0,
    network: NetworkV0,
    manifest: RoutedBindingManifestV0,
    admission: AtomicEmissionAdmissionV0,
    requests: tuple[MemoryServiceRequestV0, ...],
    graph: AccessDependencyGraphV0,
    state: OwnedServiceTickStateV0,
    *,
    ingress: ExternalIngressBindingV0 | None = None,
    allow_owned_internal_awaiting: bool = False,
    deferred_emission_ids: tuple[int, ...] = (),
) -> WitnessedCoreInputTickV0:
    """Run one owner-controlled tick and reconstruct exact consumed Core inputs.

    EVENT_TIME is determined from routed/external occurrences, never inferred
    from SERVICE_TIME. Route IDs and external indices are separate namespaces.
    No persistent neuron state is changed and no internal P/S request confirmed.
    """
    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError('invalid architecture')
    if type(network) is not NetworkV0:
        raise TypeError('invalid network')
    if type(manifest) is not RoutedBindingManifestV0:
        raise TypeError('invalid routing manifest')
    if type(admission) is not AtomicEmissionAdmissionV0:
        raise TypeError('invalid emission admission')
    if type(graph) is not AccessDependencyGraphV0:
        raise TypeError('invalid dependency graph')
    if type(state) is not OwnedServiceTickStateV0:
        raise TypeError('invalid owned tick state')
    if type(requests) is not tuple or any(type(r) is not MemoryServiceRequestV0 for r in requests):
        raise TypeError('invalid requests')
    if ingress is not None and type(ingress) is not ExternalIngressBindingV0:
        raise TypeError('invalid ingress')
    if not (manifest.profile_id == admission.profile_id == architecture.profile_id):
        raise ValueError('profile mismatch')
    if manifest.epoch_id != admission.epoch_id:
        raise ValueError('epoch mismatch')
    if ingress is None and state.boundary.driver.boundary.ledger.ingress.arrivals:
        raise ValueError('ingress binding required')

    nodes = {n.node_id for n in network.nodes}
    by_id = {r.request_id: r for r in requests}
    if len(by_id) != len(requests):
        raise ValueError('duplicate requests')
    route_by_id = {r.route_request_id: r for r in manifest.routes}
    if len(route_by_id) != len(manifest.routes):
        raise ValueError('duplicate route identities')
    external_arrivals = state.boundary.driver.boundary.ledger.ingress.arrivals
    ext_by_id = {e.input_index: e for e in external_arrivals}
    if len(ext_by_id) != len(external_arrivals):
        raise ValueError('duplicate external occurrence identities')
    if ingress is not None and ingress != state.boundary.driver.boundary.ledger.ingress:
        raise ValueError('external ingress mismatch')

    # Fail closed for malformed declared EVENT provenance before advancing state.
    for route in manifest.routes:
        occ = route.occurrence
        consume = by_id.get(route.consume_request_id)
        if (consume is None or consume.kind is not Kind.BATCH_CONSUME
                or consume.target_id != f'events:{occ.target_node_id}'
                or consume.domain is not Domain.EVENT
                or consume.target_pe_id != occ.target_pe_id
                or consume.epoch_id != manifest.epoch_id
                or occ.epoch_id != manifest.epoch_id
                or occ.target_node_id not in nodes
                or occ.source_node_id not in nodes):
            raise ValueError('invalid routed input binding')
    for arrival in external_arrivals:
        consume = by_id.get(arrival.consume_request_id)
        if (consume is None or consume.kind is not Kind.BATCH_CONSUME
                or consume.target_id != f'events:{arrival.node_id}'
                or consume.domain is not Domain.EVENT
                or consume.target_pe_id != arrival.target_pe_id
                or consume.epoch_id != manifest.epoch_id
                or arrival.node_id not in nodes):
            raise ValueError('invalid external input binding')

    # The real controller generates the frame, performs storage transitions,
    # witnesses effects and feeds only witnessed completion IDs to the quantum.
    tick = advance_autoframed_owned_tick_v0(
        architecture, manifest, admission, requests, graph, state,
        ingress=ingress, allow_owned_internal_awaiting=allow_owned_internal_awaiting,
        deferred_emission_ids=deferred_emission_ids,
    )
    authority = tick.result.authenticated_effects
    actual_route = {o.occurrence_id for o in authority.driver_step.transition.boundary.operations
                    if o.operation == 'CONSUME_ROUTE'}
    actual_external = {o.occurrence_id for o in authority.driver_step.transition.boundary.operations
                       if o.operation == 'CONSUME_EXTERNAL'}
    witnessed_route = set()
    witnessed_external = set()
    records = []
    for effect in authority.effects:
        if effect.kind is not Kind.BATCH_CONSUME:
            continue
        request = by_id.get(effect.request_id)
        if request is None or request.kind is not Kind.BATCH_CONSUME:
            raise ValueError('unbound BATCH_CONSUME completion')
        routes = effect.route_request_ids
        external = effect.external_input_indices
        if (type(routes) is not tuple or type(external) is not tuple
                or not (routes or external)
                or routes != tuple(sorted(set(routes)))
                or external != tuple(sorted(set(external)))):
            raise ValueError('invalid consumed occurrence identities')
        expected_routes = {r.route_request_id for r in manifest.routes
                           if r.consume_request_id == effect.request_id}
        expected_external = {a.input_index for a in external_arrivals
                             if a.consume_request_id == effect.request_id}
        if set(routes) != expected_routes or set(external) != expected_external:
            raise ValueError('partial or extraneous batch consumption')
        if not set(routes) <= actual_route or not set(external) <= actual_external:
            raise ValueError('consumption lacks boundary evidence')
        if effect.service_boundary != tick.frame.service_boundary:
            raise ValueError('effect boundary mismatch')
        if effect.request_id not in authority.confirmed_request_ids or effect.request_id not in tick.result.quantum.confirmed_request_ids:
            raise ValueError('batch service completion not confirmed')

        occurrences = [route_by_id[rid].occurrence for rid in routes]
        arrivals = [ext_by_id[idx] for idx in external]
        node_ids = {x.target_node_id for x in occurrences} | {x.node_id for x in arrivals}
        event_times = {x.delivery_event_time for x in occurrences} | {x.event_time for x in arrivals}
        pe_ids = {x.target_pe_id for x in occurrences} | {x.target_pe_id for x in arrivals}
        if (len(node_ids) != 1 or len(event_times) != 1 or len(pe_ids) != 1):
            raise ValueError('mixed node, EVENT_TIME, or PE in consumed batch')
        node_id, event_time, pe_id = next(iter(node_ids)), next(iter(event_times)), next(iter(pe_ids))
        if (request.target_id != f'events:{node_id}' or request.target_pe_id != pe_id
                or request.event_time != event_time or request.epoch_id != manifest.epoch_id
                or request.domain is not Domain.EVENT):
            raise ValueError('consumed batch/request identity mismatch')
        channels = tuple(sorted([x.target_channel for x in occurrences] + [x.channel for x in arrivals]))
        if not channels or len(channels) != request.quantity:
            raise ValueError('consumed batch quantity mismatch')
        records.append(WitnessedCoreInputBatchV0(
            effect.request_id, manifest.epoch_id, node_id, event_time, pe_id,
            channels, routes, external, effect.service_boundary,
        ))
        witnessed_route.update(routes)
        witnessed_external.update(external)
    if (witnessed_route != actual_route or witnessed_external != actual_external
            or len(records) != len({b.consume_request_id for b in records})):
        raise ValueError('unattributed EVENT consumption')
    return WitnessedCoreInputTickV0(tick, tuple(sorted(records, key=lambda b: b.consume_request_id)))


@dataclass(frozen=True, slots=True)
class StagedWitnessedCoreTickV0:
    """Speculative Core calculations; neither serviced P/S reads nor commits."""
    consumed_tick: WitnessedCoreInputTickV0
    prepared_transitions: tuple


def advance_and_stage_witnessed_core_tick_v0(
    architecture: ArchitectureProfileV0,
    network: NetworkV0,
    image,
    manifest: RoutedBindingManifestV0,
    admission: AtomicEmissionAdmissionV0,
    requests: tuple[MemoryServiceRequestV0, ...],
    graph: AccessDependencyGraphV0,
    state: OwnedServiceTickStateV0,
    *,
    ingress: ExternalIngressBindingV0 | None = None,
) -> StagedWitnessedCoreTickV0:
    """Compute speculative Core transitions from witnessed EVENT consumptions.

    Crucially, does NOT commit the state image, confirm internal P/S requests,
    or publish candidate outputs. Each prepared item still needs explicit
    PROGRAM_REFERENCE/STATE_LOAD service authority and a future state-commit
    gate. Multiple same-node batches in one boundary are refused because their
    intermediate state versions cannot be serialized without real commits.
    """
    from spk_simulator.versioned_core_transition_v0 import (
        VersionedNeuronImageV0, prepare_core_transition_v0,
    )
    if type(image) is not VersionedNeuronImageV0:
        raise TypeError('invalid versioned neuron image')
    if image.network != network or image.epoch_id != manifest.epoch_id:
        raise ValueError('versioned neuron image/network/epoch mismatch')
    witnessed = advance_witnessed_core_input_tick_v0(
        architecture, network, manifest, admission, requests, graph,
        state, ingress=ingress,
    )
    seen_nodes = set()
    proposed = []
    for batch in witnessed.consumed_batches:
        if batch.node_id in seen_nodes:
            raise ValueError('multiple same-node Core batches require serialized state commits')
        seen_nodes.add(batch.node_id)
        proposed.append(prepare_core_transition_v0(
            network, image, node_id=batch.node_id,
            timestamp=batch.event_time, channels=batch.channels,
        ))
    return StagedWitnessedCoreTickV0(witnessed, tuple(proposed))
