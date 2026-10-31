"""SPK Compiler C1: deterministic Network IR -> admitted network pipeline.

This is a compiler for the abstract SPK simulator, not a machine-code
backend. It neither executes programs nor asserts dynamic feasibility.
"""

from dataclasses import dataclass

from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_compiler.network_ir_v0 import (
    dumps_network_ir_v0,
    loads_network_ir_v0,
)
from spk_compiler.pe_admission_v0 import (
    NodePlacementV0,
    PEAdmissionManifestV0,
    admit_pe_mapping_v0,
)
from spk_compiler.resource_admission_v0 import (
    AdmissionManifestV0,
    ResourceProfileV0,
    admit_network_v0,
)
from spk_network.events_v0 import NetworkEventV0
from spk_network.model_v0 import NetworkV0


@dataclass(frozen=True, slots=True)
class CompiledNetworkV0:
    """Admitted simulator input, not binary machine code.

    All constituent objects must themselves obey their v0 immutable
    contracts. The manifest is deliberately not a serialized C2 format.
    """

    canonical_network_ir: str
    network: NetworkV0
    initial_events: tuple[NetworkEventV0, ...]
    resource_profile: ResourceProfileV0
    architecture: ArchitectureProfileV0
    placements: tuple[NodePlacementV0, ...]
    resource_admission: AdmissionManifestV0
    pe_admission: PEAdmissionManifestV0


def compile_network_ir_v0(
    network_ir_json: str,
    initial_events: tuple[NetworkEventV0, ...],
    resource_profile: ResourceProfileV0,
    architecture: ArchitectureProfileV0,
    placements: tuple[NodePlacementV0, ...],
) -> CompiledNetworkV0:
    """Validate IR and both static admission gates, then return a result.

    This operation is pure and fail-closed. No partial result is produced.
    Program/node declaration order and event multiplicity are preserved;
    the explicit placements are canonicalized by node ID.
    """
    if type(network_ir_json) is not str:
        raise TypeError("network_ir_json must be a string")
    if type(initial_events) is not tuple or any(
        type(event) is not NetworkEventV0 for event in initial_events
    ):
        raise TypeError("initial_events must be a tuple of NetworkEventV0")
    if type(resource_profile) is not ResourceProfileV0:
        raise TypeError("invalid resource profile")
    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError("invalid architecture profile")
    if type(placements) is not tuple or any(
        type(item) is not NodePlacementV0 for item in placements
    ):
        raise TypeError("placements must be a tuple of NodePlacementV0")

    # The existing strict codec owns all schema and version validation.
    network = loads_network_ir_v0(network_ir_json)
    if type(network) is not NetworkV0:
        raise TypeError("Network IR decoder returned an invalid network")

    # A stable representation is regenerated from the decoded network.
    # This avoids treating insignificant input whitespace as compilation state.
    canonical_ir = dumps_network_ir_v0(network)
    if type(canonical_ir) is not str:
        raise TypeError("Network IR encoder returned non-text")
    if loads_network_ir_v0(canonical_ir) != network:
        raise ValueError("Network IR canonical roundtrip mismatch")

    logical = admit_network_v0(network, initial_events, resource_profile)
    physical = admit_pe_mapping_v0(network, architecture, placements)

    ordered_placements = tuple(sorted(placements, key=lambda p: p.node_id))
    return CompiledNetworkV0(
        canonical_network_ir=canonical_ir,
        network=network,
        initial_events=initial_events,
        resource_profile=resource_profile,
        architecture=architecture,
        placements=ordered_placements,
        resource_admission=logical,
        pe_admission=physical,
    )
