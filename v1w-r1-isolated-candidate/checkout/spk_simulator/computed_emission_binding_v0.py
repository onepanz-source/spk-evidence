"""SPK S3.7d/3b2b2k/7: bind real Core output candidates to declared routes.

A fail-closed *pre-transaction* gate, not STATE/OUTPUT atomic publication.
The manifest is still provided, not independently created by this function.
"""
from collections import Counter
from dataclasses import dataclass

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind, MemoryDomainV0 as Domain
from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_network.model_v0 import NetworkV0
from spk_simulator.atomic_emission_admission_v0 import AtomicEmissionAdmissionV0
from spk_simulator.routing_binding_v0 import RoutedBindingManifestV0
from spk_simulator.versioned_core_transition_v0 import (
    VersionedNeuronImageV0, PreparedCoreTransitionV0,
    prepare_core_transition_v0,
)


@dataclass(frozen=True, slots=True)
class ComputedEmissionBindingV0:
    emission_request_id: int
    source_node_id: str
    source_pe_id: str
    event_time: int
    candidate_outputs: tuple[tuple[int, int], ...]
    route_request_ids: tuple[int, ...]
    terminal_channels: tuple[int, ...]
    required_output_slots: int


def bind_computed_emission_v0(
    architecture: ArchitectureProfileV0,
    network: NetworkV0,
    image: VersionedNeuronImageV0,
    prepared: PreparedCoreTransitionV0,
    manifest: RoutedBindingManifestV0,
    admission: AtomicEmissionAdmissionV0,
    requests: tuple[MemoryServiceRequestV0, ...],
    *,
    emission_request_id: int,
) -> ComputedEmissionBindingV0:
    """Compare a *recomputed* Core emission with one complete declared fan-out.

    The returned binding is neither permission to start service nor evidence of
    a completed STATE_COMMIT or OUTPUT publication. EVENT_TIME is not SERVICE_TIME.
    """
    if (type(architecture) is not ArchitectureProfileV0 or
            type(network) is not NetworkV0 or
            type(image) is not VersionedNeuronImageV0 or
            type(prepared) is not PreparedCoreTransitionV0 or
            type(manifest) is not RoutedBindingManifestV0 or
            type(admission) is not AtomicEmissionAdmissionV0):
        raise TypeError('invalid Core / architecture / emission binding input')
    if (type(requests) is not tuple or
            any(type(x) is not MemoryServiceRequestV0 for x in requests)):
        raise TypeError('invalid emission service requests')
    if type(emission_request_id) is not int or emission_request_id < 0:
        raise ValueError('invalid emission request ID')
    if (architecture.profile_id != admission.profile_id or
            manifest.profile_id != admission.profile_id or
            manifest.epoch_id != admission.epoch_id or
            image.epoch_id != admission.epoch_id):
        raise ValueError('emission profile / epoch mismatch')
    reqs = {x.request_id: x for x in requests}
    if len(reqs) != len(requests):
        raise ValueError('duplicate service request')
    groups = {x.emission_request_id: x for x in admission.groups}
    if len(groups) != len(admission.groups):
        raise ValueError('duplicate emission group')
    group = groups.get(emission_request_id)
    req = reqs.get(emission_request_id)
    if group is None or req is None:
        raise ValueError('Core emission has no declared emission request/group')
    # A declaration is not an output computation. Verify the latter using
    # the frozen Core independently of the supplied preparation/result fields.
    expected = prepare_core_transition_v0(
        network, image, node_id=prepared.node_id,
        timestamp=prepared.event_time, channels=prepared.channels,
    )
    if expected != prepared:
        raise ValueError('prepared Core result mismatch')
    candidates = prepared.candidate_outputs
    if not candidates:
        raise ValueError('declared emission has no computed Core outputs')
    pes = {x.pe_id: x for x in architecture.pes}
    pe = pes.get(group.source_pe_id)
    nodes = {n.node_id for n in network.nodes}
    if (pe is None or group.source_node_id not in nodes or
            req.kind is not Kind.EMISSION_RECORD or req.domain is not Domain.EVENT or
            req.epoch_id != admission.epoch_id or
            req.event_time != prepared.event_time or
            req.target_pe_id != group.source_pe_id or
            req.target_id != f'outputs:{prepared.node_id}' or
            req.quantity != len(candidates) or
            group.source_node_id != prepared.node_id or
            group.emission_event_time != prepared.event_time):
        raise ValueError('emission request / Core / group identity mismatch')
    if (group.output_capacity != pe.output_slots or
            group.required_output_slots != len(group.route_request_ids) or
            group.required_output_slots > pe.output_slots or
            group.route_request_ids != tuple(sorted(set(group.route_request_ids)))):
        raise ValueError('invalid finite OUTPUT group capacity')
    routes = {r.route_request_id: r for r in manifest.routes}
    if len(routes) != len(manifest.routes):
        raise ValueError('duplicate route identity')
    if not set(group.route_request_ids) <= routes.keys():
        raise ValueError('emission group references unknown routes')
    accounted = [rid for g in admission.groups for rid in g.route_request_ids]
    if (len(accounted) != len(set(accounted)) or
            set(accounted) != set(routes) or
            admission.routed_occurrence_count != len(routes) or
            admission.zero_fanout_emission_count != sum(
                not g.route_request_ids for g in admission.groups
            )):
        raise ValueError('global emission/route coverage mismatch')
    edge_by_channel = {}
    for e in network.edges:
        if e.source_node == prepared.node_id:
            edge_by_channel.setdefault(e.source_channel, []).append(e)
    expected_routes = Counter()
    terminal = []
    for t, channel in candidates:
        if t != prepared.event_time:
            raise ValueError('Core output EVENT_TIME mismatch')
        selected = edge_by_channel.get(channel, ())
        if not selected:
            terminal.append(channel)
        for edge in selected:
            expected_routes[(prepared.node_id, channel,
                             edge.target_node, edge.target_channel,
                             t, t + edge.delay_ticks)] += 1
    actual_routes = Counter()
    for rid in group.route_request_ids:
        route = routes[rid]
        oc = route.occurrence
        if (oc.source_node_id != prepared.node_id or
                oc.source_pe_id != group.source_pe_id or
                oc.emission_event_time != prepared.event_time):
            raise ValueError('route source/PE/EVENT_TIME mismatch')
        actual_routes[(oc.source_node_id, oc.source_channel,
                       oc.target_node_id, oc.target_channel,
                       oc.emission_event_time, oc.delivery_event_time)] += 1
    if actual_routes != expected_routes:
        raise ValueError('computed Core fan-out disagrees with routed occurrences')
    return ComputedEmissionBindingV0(
        emission_request_id, prepared.node_id, group.source_pe_id,
        prepared.event_time, candidates, group.route_request_ids,
        tuple(terminal), group.required_output_slots,
    )
