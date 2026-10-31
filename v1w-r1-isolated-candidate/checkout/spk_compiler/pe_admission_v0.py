"""SPK Processing Element admission v0.

Static node placement and architectural capacity checks.
No scheduling, timing or host-memory assumptions.
"""

from dataclasses import dataclass

from spk_network.model_v0 import NetworkV0
from spk_architecture.profile_v0 import ArchitectureProfileV0


class PEAdmissionRejectedV0(ValueError):
    code = "ADMISSION_REJECTED"

    def __init__(self, pe_id, metric, required, capacity):
        self.pe_id = pe_id
        self.metric = metric
        self.required = required
        self.capacity = capacity
        super().__init__(
            f"{pe_id}: {metric} required={required}, "
            f"capacity={capacity}"
        )


@dataclass(frozen=True, slots=True)
class NodePlacementV0:
    node_id: str
    pe_id: str

    def __post_init__(self):
        for name in ("node_id", "pe_id"):
            value = getattr(self, name)
            if (
                type(value) is not str
                or not value
                or value.strip() != value
            ):
                raise ValueError(f"invalid {name}")


@dataclass(frozen=True, slots=True)
class PEUsageV0:
    pe_id: str
    node_ids: tuple[str, ...]
    program_used: int
    program_capacity: int
    state_used: int
    state_capacity: int

    # Available capacities, NOT runtime reservations.
    event_capacity: int
    output_capacity: int
    observation_capacity: int
    accesses_per_service_tick: int


@dataclass(frozen=True, slots=True)
class PEAdmissionManifestV0:
    profile_id: str
    node_count: int
    pe_count: int
    total_program_slots: int
    total_state_slots: int
    cross_pe_edges: int
    pe_usage: tuple[PEUsageV0, ...]


def _capacity_check(pe_id, metric, required, capacity):
    if required > capacity:
        raise PEAdmissionRejectedV0(
            pe_id, metric, required, capacity
        )


def admit_pe_mapping_v0(
    network: NetworkV0,
    architecture: ArchitectureProfileV0,
    placements: tuple[NodePlacementV0, ...],
) -> PEAdmissionManifestV0:
    """Validate explicit node placement on abstract PEs."""

    if type(network) is not NetworkV0:
        raise TypeError("expected NetworkV0")

    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError("expected ArchitectureProfileV0")

    if type(placements) is not tuple:
        raise TypeError("placements must be a tuple")

    known_nodes = {
        node.node_id for node in network.nodes
    }
    known_pes = {
        pe.pe_id for pe in architecture.pes
    }

    mapping = {}

    for item in placements:
        if type(item) is not NodePlacementV0:
            raise TypeError("invalid node placement")

        if item.node_id not in known_nodes:
            raise ValueError(
                f"unknown node: {item.node_id}"
            )

        if item.pe_id not in known_pes:
            raise ValueError(
                f"unknown PE: {item.pe_id}"
            )

        if item.node_id in mapping:
            raise ValueError(
                f"duplicate node placement: {item.node_id}"
            )

        mapping[item.node_id] = item.pe_id

    if set(mapping) != known_nodes:
        missing = sorted(known_nodes - set(mapping))
        raise ValueError(
            f"incomplete node placement: {missing}"
        )

    usage = []

    for pe in architecture.pes:
        assigned = tuple(
            node for node in network.nodes
            if mapping[node.node_id] == pe.pe_id
        )

        program_used = sum(
            len(node.program.instructions)
            for node in assigned
        )

        state_used = len(assigned)

        _capacity_check(
            pe.pe_id,
            "program_slots",
            program_used,
            pe.program_slots,
        )

        _capacity_check(
            pe.pe_id,
            "state_slots",
            state_used,
            pe.state_slots,
        )

        usage.append(
            PEUsageV0(
                pe_id=pe.pe_id,
                node_ids=tuple(
                    node.node_id for node in assigned
                ),
                program_used=program_used,
                program_capacity=pe.program_slots,
                state_used=state_used,
                state_capacity=pe.state_slots,
                event_capacity=pe.event_slots,
                output_capacity=pe.output_slots,
                observation_capacity=pe.observation_slots,
                accesses_per_service_tick=(
                    pe.accesses_per_service_tick
                ),
            )
        )

    cross_pe_edges = sum(
        mapping[edge.source_node]
        != mapping[edge.target_node]
        for edge in network.edges
    )

    return PEAdmissionManifestV0(
        profile_id=architecture.profile_id,
        node_count=len(network.nodes),
        pe_count=len(architecture.pes),
        total_program_slots=sum(
            item.program_used for item in usage
        ),
        total_state_slots=sum(
            item.state_used for item in usage
        ),
        cross_pe_edges=cross_pe_edges,
        pe_usage=tuple(usage),
    )
