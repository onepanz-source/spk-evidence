"""SPK S3.7d/3b2b2k/9: route real Core candidates using frozen topology.

An immutable *intent generator*, not a manifest of service requests or
proof of a delivered/published spike. No functional trace is consulted.
"""
from dataclasses import dataclass

from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_compiler.pe_admission_v0 import PEAdmissionManifestV0
from spk_network.model_v0 import NetworkV0
from spk_network.events_v0 import NetworkEventV0
from spk_simulator.event_storage_v0 import RoutedOccurrenceV0
from spk_simulator.versioned_core_transition_v0 import (
    PreparedCoreTransitionV0, VersionedNeuronImageV0, prepare_core_transition_v0,
)


class ComputedFanoutCapacityV0(RuntimeError):
    code = 'COMPUTED_FANOUT_EXCEEDS_OUTPUT'

    def __init__(self, source_node_id: str, pe_id: str, required: int, capacity: int):
        self.source_node_id = source_node_id
        self.pe_id = pe_id
        self.required = required
        self.capacity = capacity
        super().__init__(f'{self.code}: node={source_node_id}, PE={pe_id}, '
                         f'required={required}, capacity={capacity}')


@dataclass(frozen=True, slots=True)
class ComputedRouteIntentV0:
    """One physical edge traversed by one candidate Core output."""
    output_index: int
    edge_index: int
    occurrence: RoutedOccurrenceV0


@dataclass(frozen=True, slots=True)
class ComputedTopologyRoutingV0:
    profile_id: str
    epoch_id: str
    source_node_id: str
    source_pe_id: str
    event_time: int
    base_version: int
    candidate_outputs: tuple[tuple[int, int], ...]
    routes: tuple[ComputedRouteIntentV0, ...]
    terminal_outputs: tuple[NetworkEventV0, ...]
    required_output_slots: int
    next_event_id: int


def derive_computed_topology_routing_v0(
    architecture: ArchitectureProfileV0,
    network: NetworkV0,
    placement: PEAdmissionManifestV0,
    image: VersionedNeuronImageV0,
    prepared: PreparedCoreTransitionV0,
    *,
    first_event_id: int,
    used_event_ids: tuple[int, ...] = (),
) -> ComputedTopologyRoutingV0:
    """Compute fan-out from Core and Network edges, preserving parallel edges.

    `first_event_id` is an allocation *proposal*. The authoritative owner must
    persist `next_event_id` atomically with accepted publication to prevent
    replay across independent executions. No OUTPUT capacity is reserved here.
    """
    if (type(architecture) is not ArchitectureProfileV0
            or type(network) is not NetworkV0
            or type(placement) is not PEAdmissionManifestV0
            or type(image) is not VersionedNeuronImageV0
            or type(prepared) is not PreparedCoreTransitionV0):
        raise TypeError('invalid architecture/network/placement/Core input')
    if type(first_event_id) is not int or first_event_id < 0:
        raise ValueError('invalid event identity cursor')
    if (type(used_event_ids) is not tuple
            or any(type(x) is not int or x < 0 for x in used_event_ids)
            or used_event_ids != tuple(sorted(set(used_event_ids)))):
        raise ValueError('noncanonical used event identities')
    if used_event_ids and used_event_ids[-1] >= first_event_id:
        raise ValueError('event identity cursor overlaps retained history')
    if architecture.profile_id != placement.profile_id:
        raise ValueError('architecture/placement profile mismatch')
    if image.epoch_id != prepared.epoch_id or image.network != network:
        raise ValueError('Core image/epoch mismatch')

    pes = {p.pe_id: p for p in architecture.pes}
    node_ids = {n.node_id for n in network.nodes}
    if len(node_ids) != len(network.nodes):
        raise ValueError('duplicate network node')
    node_pe = {}
    for usage in placement.pe_usage:
        if usage.pe_id not in pes:
            raise ValueError('placement references unknown PE')
        for node_id in usage.node_ids:
            if node_id in node_pe:
                raise ValueError('duplicate node placement')
            node_pe[node_id] = usage.pe_id
    if set(node_pe) != node_ids:
        raise ValueError('placement/network node mismatch')

    # Reject changed Core outputs and stale state; the caller cannot dictate
    # the emission channels or their EVENT_TIME.
    expected = prepare_core_transition_v0(
        network, image, node_id=prepared.node_id,
        timestamp=prepared.event_time, channels=prepared.channels,
    )
    if prepared != expected:
        raise ValueError('computed Core preparation mismatch')
    source_id = prepared.node_id
    source_pe_id = node_pe[source_id]
    out_by_channel = {}
    for index, edge in enumerate(network.edges):
        if edge.source_node not in node_pe or edge.target_node not in node_pe:
            raise ValueError('network edge references unknown node')
        if edge.delay_ticks <= 0:
            raise ValueError('nonpositive route EVENT_TIME delay')
        if edge.source_node == source_id:
            out_by_channel.setdefault(edge.source_channel, []).append((index, edge))
    for channel in out_by_channel:
        out_by_channel[channel].sort(key=lambda pair: (
            pair[1].target_node, pair[1].target_channel,
            pair[1].delay_ticks, pair[0],
        ))

    route_intents = []
    terminal = []
    for output_index, (event_time, channel) in enumerate(prepared.candidate_outputs):
        if event_time != prepared.event_time:
            raise ValueError('Core candidate has mismatched EVENT_TIME')
        edges = out_by_channel.get(channel, ())
        if not edges:
            terminal.append(NetworkEventV0(event_time, source_id, channel))
        for edge_index, edge in edges:
            event_id = first_event_id + len(route_intents)
            occurrence = RoutedOccurrenceV0(
                event_id, image.epoch_id, source_id, source_pe_id,
                channel, edge.target_node, node_pe[edge.target_node],
                edge.target_channel, event_time, event_time + edge.delay_ticks,
            )
            route_intents.append(ComputedRouteIntentV0(
                output_index, edge_index, occurrence,
            ))
    required_slots = len(route_intents)
    capacity = pes[source_pe_id].output_slots
    if required_slots > capacity:
        raise ComputedFanoutCapacityV0(
            source_id, source_pe_id, required_slots, capacity,
        )
    return ComputedTopologyRoutingV0(
        architecture.profile_id, image.epoch_id, source_id, source_pe_id,
        prepared.event_time, prepared.base_version,
        prepared.candidate_outputs, tuple(route_intents), tuple(terminal),
        required_slots, first_event_id + required_slots,
    )
