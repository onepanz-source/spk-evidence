"""SPK S3.7d/3b2b2k/10: one owner of computed emission/request identities.

Allocates fresh ROUTE_ENQUEUE request IDs identical to routed occurrence IDs.
The effect is *reservation of namespace*, NOT memory service, OUTPUT admission,
STATE_COMMIT or publication. No ObservedExecutionV0 is read or required.
"""

from dataclasses import dataclass

from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_compiler.pe_admission_v0 import PEAdmissionManifestV0
from spk_network.model_v0 import NetworkV0
from spk_simulator.computed_topology_routing_v0 import (
    ComputedTopologyRoutingV0, derive_computed_topology_routing_v0,
)
from spk_simulator.versioned_core_transition_v0 import (
    PreparedCoreTransitionV0, VersionedNeuronImageV0,
)


def _canonical_request_ids(ids: tuple[int, ...]) -> None:
    if (type(ids) is not tuple or
            any(type(value) is not int or value < 0 for value in ids) or
            ids != tuple(sorted(set(ids)))):
        raise ValueError('noncanonical request IDs')


@dataclass(frozen=True, slots=True)
class OwnedComputedEmissionAllocationV0:
    """A Core-derived atomic emission's reserved request/occurrence namespace."""
    emission_request_id: int
    topology: ComputedTopologyRoutingV0

    @property
    def route_request_ids(self) -> tuple[int, ...]:
        return tuple(x.occurrence.event_id for x in self.topology.routes)


@dataclass(frozen=True, slots=True)
class ComputedEmissionAllocationLedgerV0:
    """Persistent per-epoch request allocator, including completed allocations.

    History is deliberately retained: an epoch-bound retirement policy has not
    yet been specified. Caller must not discard this ledger and reuse its IDs.
    """
    profile_id: str
    epoch_id: str
    network: NetworkV0
    placement: PEAdmissionManifestV0
    existing_request_ids: tuple[int, ...]
    first_dynamic_request_id: int
    next_request_id: int
    allocations: tuple[OwnedComputedEmissionAllocationV0, ...]

    def __post_init__(self):
        _canonical_request_ids(self.existing_request_ids)
        if (type(self.profile_id) is not str or not self.profile_id or
                type(self.epoch_id) is not str or not self.epoch_id):
            raise ValueError('invalid owner profile/epoch')
        if (type(self.network) is not NetworkV0 or
                type(self.placement) is not PEAdmissionManifestV0):
            raise TypeError('invalid frozen topology/placement reference')
        if self.placement.profile_id != self.profile_id:
            raise ValueError('allocation placement profile mismatch')
        if (type(self.first_dynamic_request_id) is not int or
                type(self.next_request_id) is not int or
                self.first_dynamic_request_id < 0 or
                self.next_request_id < self.first_dynamic_request_id):
            raise ValueError('invalid request identity cursor')
        if (self.existing_request_ids and
                self.existing_request_ids[-1] >= self.first_dynamic_request_id):
            raise ValueError('dynamic identity cursor overlaps existing requests')
        if (type(self.allocations) is not tuple or
                any(type(a) is not OwnedComputedEmissionAllocationV0
                    for a in self.allocations)):
            raise TypeError('invalid owned allocations')
        cursor = self.first_dynamic_request_id
        latest_versions: dict[str, int] = {}
        for allocation in self.allocations:
            intent = allocation.topology
            if (type(allocation.emission_request_id) is not int or
                    allocation.emission_request_id != cursor or
                    type(intent) is not ComputedTopologyRoutingV0 or
                    intent.profile_id != self.profile_id or
                    intent.epoch_id != self.epoch_id or
                    not intent.candidate_outputs or
                    intent.required_output_slots != len(intent.routes) or
                    intent.next_event_id != cursor + 1 + len(intent.routes)):
                raise ValueError('noncanonical emission allocation history')
            expected_route_ids = tuple(range(cursor + 1, intent.next_event_id))
            if allocation.route_request_ids != expected_route_ids:
                raise ValueError('route/request identity mismatch')
            if (type(intent.base_version) is not int or intent.base_version < 0 or
                    type(intent.source_node_id) is not str or not intent.source_node_id or
                    intent.base_version <= latest_versions.get(intent.source_node_id, -1)):
                raise ValueError('nonmonotone neuronal version allocation history')
            latest_versions[intent.source_node_id] = intent.base_version
            if any(x.occurrence.epoch_id != self.epoch_id or
                   x.occurrence.source_node_id != intent.source_node_id or
                   x.occurrence.source_pe_id != intent.source_pe_id or
                   x.occurrence.emission_event_time != intent.event_time
                   for x in intent.routes):
                raise ValueError('owned route provenance mismatch')
            cursor = intent.next_event_id
        if cursor != self.next_request_id:
            raise ValueError('request identity cursor/history mismatch')


@dataclass(frozen=True, slots=True)
class ComputedEmissionAllocationStepV0:
    ledger: ComputedEmissionAllocationLedgerV0
    allocation: OwnedComputedEmissionAllocationV0


def initialize_computed_emission_allocation_v0(
    architecture: ArchitectureProfileV0,
    network: NetworkV0,
    placement: PEAdmissionManifestV0,
    image: VersionedNeuronImageV0,
    *,
    existing_request_ids: tuple[int, ...] = (),
    first_dynamic_request_id: int | None = None,
) -> ComputedEmissionAllocationLedgerV0:
    """Initialize AFTER reserving IDs of all already constructed requests.

    Dynamic request IDs are global to an epoch, not per source PE or node.
    """
    if (type(architecture) is not ArchitectureProfileV0 or
            type(network) is not NetworkV0 or
            type(placement) is not PEAdmissionManifestV0 or
            type(image) is not VersionedNeuronImageV0):
        raise TypeError('invalid allocation owner initialization')
    _canonical_request_ids(existing_request_ids)
    if (image.network != network or
            architecture.profile_id != placement.profile_id):
        raise ValueError('allocation network/placement mismatch')
    minimum = existing_request_ids[-1] + 1 if existing_request_ids else 0
    start = minimum if first_dynamic_request_id is None else first_dynamic_request_id
    if type(start) is not int or start < minimum:
        raise ValueError('dynamic identity cursor overlaps existing requests')
    # Validate image and placement before persisting the owner configuration.
    from spk_simulator.versioned_core_transition_v0 import _require_image
    _require_image(network, image)
    pes = {pe.pe_id for pe in architecture.pes}
    expected_nodes = {node.node_id for node in network.nodes}
    placed = []
    for usage in placement.pe_usage:
        if usage.pe_id not in pes:
            raise ValueError('placement references unknown PE')
        placed.extend(usage.node_ids)
    if len(placed) != len(set(placed)) or set(placed) != expected_nodes:
        raise ValueError('placement/network node coverage mismatch')
    return ComputedEmissionAllocationLedgerV0(
        architecture.profile_id, image.epoch_id, network, placement,
        existing_request_ids, start, start, (),
    )


def allocate_computed_emission_v0(
    architecture: ArchitectureProfileV0,
    image: VersionedNeuronImageV0,
    prepared: PreparedCoreTransitionV0,
    ledger: ComputedEmissionAllocationLedgerV0,
) -> ComputedEmissionAllocationStepV0:
    """Atomically allocate EMISSION_RECORD + all ROUTE_ENQUEUE IDs.

    `emission_request_id` is allocated first, then route/event IDs. The
    ledger moves forward even for terminal-only emission (one request ID).
    This does not create MemoryServiceRequestV0, as service-cost mapping and
    destination batch ownership must still be established by the scheduler.
    """
    if (type(architecture) is not ArchitectureProfileV0 or
            type(image) is not VersionedNeuronImageV0 or
            type(prepared) is not PreparedCoreTransitionV0 or
            type(ledger) is not ComputedEmissionAllocationLedgerV0):
        raise TypeError('invalid computed emission allocation input')
    if (ledger.profile_id != architecture.profile_id or
            ledger.epoch_id != image.epoch_id or
            image.network != ledger.network):
        raise ValueError('allocation owner profile/network/epoch mismatch')
    latest = max((a.topology.base_version for a in ledger.allocations
                  if a.topology.source_node_id == prepared.node_id), default=-1)
    if prepared.base_version <= latest:
        raise ValueError('computed emission already allocated or nonmonotone neuron version')
    # Crucial: use the owner cursor, NEVER a caller-supplied event/request ID.
    emission_id = ledger.next_request_id
    topology = derive_computed_topology_routing_v0(
        architecture, ledger.network, ledger.placement, image, prepared,
        first_event_id=emission_id + 1,
    )
    if not topology.candidate_outputs:
        raise ValueError('Core batch has no candidate emission')
    allocation = OwnedComputedEmissionAllocationV0(emission_id, topology)
    successor = ComputedEmissionAllocationLedgerV0(
        ledger.profile_id, ledger.epoch_id, ledger.network, ledger.placement,
        ledger.existing_request_ids, ledger.first_dynamic_request_id,
        topology.next_event_id, ledger.allocations + (allocation,),
    )
    return ComputedEmissionAllocationStepV0(successor, allocation)
