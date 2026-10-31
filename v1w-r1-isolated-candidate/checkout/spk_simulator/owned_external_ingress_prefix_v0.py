"""SPK S3.7d/3b2b2k/14: reconcile a sealed finite external-input prefix.

The seal is an explicit *epoch input contract*. Only relative to that contract
can the absence of further external occurrences be concluded. The ledger and
physical snapshot must agree with the seal. This module does not settle source
neuronal emissions or authorize BATCH_CONSUME.
"""
from dataclasses import dataclass

from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_network.model_v0 import NetworkV0
from spk_simulator.external_ingress_v0 import (
    ExternalIngressBindingV0, BoundExternalArrivalV0, BatchIngressReleaseV0,
)
from spk_simulator.backpressure_boundary_v0 import BackpressureBoundaryStateV0
from spk_simulator.routing_binding_v0 import RoutedBindingManifestV0
from spk_simulator.event_reservation_v0 import event_reservation_usage_v0


@dataclass(frozen=True, slots=True)
class SealedExternalIngressEpochV0:
    """Immutable declaration of ALL permitted initial inputs for one epoch.

    Caller must install this as the single owner's immutable initialization
    contract. It cannot prove that an open/live ingress source has stopped.
    """
    profile_id: str
    epoch_id: str
    node_ids: tuple[str, ...]
    binding: ExternalIngressBindingV0


@dataclass(frozen=True, slots=True)
class ExternalPrefixQueryV0:
    target_node_id: str
    event_time: int

    def __post_init__(self):
        if (type(self.target_node_id) is not str or not self.target_node_id
                or self.target_node_id.strip() != self.target_node_id):
            raise ValueError('invalid external prefix target')
        if type(self.event_time) is not int or self.event_time < 0:
            raise ValueError('invalid external prefix EVENT_TIME')


@dataclass(frozen=True, slots=True)
class ExternalPrefixEvidenceV0:
    target_node_id: str
    settled_through_event_time: int
    known_input_indices: tuple[int, ...]
    resident_input_indices: tuple[int, ...]
    consumed_input_indices: tuple[int, ...]
    pending_input_indices: tuple[int, ...]
    # Only under the sealed finite-input assumption, not for live ingress.
    sealed_prefix_accounted: bool
    status: str
    supports_consume_admission: bool = False


@dataclass(frozen=True, slots=True)
class ExternalPrefixAnalysisV0:
    profile_id: str
    epoch_id: str
    last_service_boundary: int | None
    evidences: tuple[ExternalPrefixEvidenceV0, ...]
    supports_consume_admission: bool = False


def seal_finite_external_ingress_v0(
    architecture: ArchitectureProfileV0,
    network: NetworkV0,
    binding: ExternalIngressBindingV0,
    *,
    epoch_id: str = 'E0',
) -> SealedExternalIngressEpochV0:
    """Validate and freeze a CLOSED initial-input schedule, including multiplicity.

    The explicit seal is a trust root, not an inferred property of runtime idle.
    It is appropriate for finite offline simulation, not live/open ingress.
    """
    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError('invalid ingress architecture')
    if type(network) is not NetworkV0:
        raise TypeError('invalid ingress network')
    if type(binding) is not ExternalIngressBindingV0:
        raise TypeError('invalid ingress binding')
    if type(epoch_id) is not str or not epoch_id or epoch_id.strip() != epoch_id:
        raise ValueError('invalid ingress epoch')
    nodes = tuple(sorted(node.node_id for node in network.nodes))
    if len(nodes) != len(set(nodes)):
        raise ValueError('duplicate ingress network node')
    pes = {pe.pe_id for pe in architecture.pes}
    arrivals = binding.arrivals
    if (type(arrivals) is not tuple or
            any(type(x) is not BoundExternalArrivalV0 for x in arrivals)):
        raise TypeError('invalid sealed arrival records')
    if tuple(x.input_index for x in arrivals) != tuple(range(len(arrivals))):
        raise ValueError('noncanonical sealed input indices')
    by_id = {}
    for a in arrivals:
        if (a.node_id not in nodes or a.target_pe_id not in pes
                or type(a.event_time) is not int or a.event_time < 0
                or type(a.channel) is not int or a.channel < 0
                or type(a.arrival_boundary) is not int or a.arrival_boundary < 0
                or type(a.consume_request_id) is not int or a.consume_request_id < 0):
            raise ValueError('invalid sealed arrival identity, time or target')
        by_id[a.input_index] = a
    if (type(binding.batch_releases) is not tuple or
            any(type(x) is not BatchIngressReleaseV0 for x in binding.batch_releases)):
        raise TypeError('invalid sealed batch releases')
    seen = set()
    for batch in binding.batch_releases:
        if (type(batch.consume_request_id) is not int or batch.consume_request_id < 0
                or type(batch.ready_boundary) is not int or batch.ready_boundary < 0
                or type(batch.input_indices) is not tuple or
                tuple(sorted(set(batch.input_indices))) != batch.input_indices):
            raise ValueError('invalid sealed batch release')
        for idx in batch.input_indices:
            if (type(idx) is not int or idx not in by_id or idx in seen
                    or by_id[idx].consume_request_id != batch.consume_request_id
                    or by_id[idx].arrival_boundary > batch.ready_boundary):
                raise ValueError('inconsistent sealed input batch/release')
            seen.add(idx)
    if seen != set(by_id):
        raise ValueError('sealed ingress does not cover all external indices')
    return SealedExternalIngressEpochV0(
        architecture.profile_id, epoch_id, nodes, binding,
    )


def analyze_owned_external_prefix_v0(
    architecture: ArchitectureProfileV0,
    seal: SealedExternalIngressEpochV0,
    manifest: RoutedBindingManifestV0,
    boundary: BackpressureBoundaryStateV0,
    *,
    queries: tuple[ExternalPrefixQueryV0, ...],
) -> ExternalPrefixAnalysisV0:
    """Check exact external-prefix accounting against a boundary-owned ledger.

    No externally supplied watermarks are accepted. A positive row establishes
    only a finite-ingress-prefix fact under the immutable seal, NOT batch closure:
    source emission frontiers and already-registered routes remain independent.
    """
    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError('invalid prefix architecture')
    if type(seal) is not SealedExternalIngressEpochV0:
        raise TypeError('invalid external ingress seal')
    if type(manifest) is not RoutedBindingManifestV0:
        raise TypeError('invalid prefix routing manifest')
    if type(boundary) is not BackpressureBoundaryStateV0:
        raise TypeError('invalid prefix boundary snapshot')
    if (type(queries) is not tuple or
            any(type(q) is not ExternalPrefixQueryV0 for q in queries)):
        raise TypeError('invalid prefix queries')
    if len(queries) != len(set((q.target_node_id, q.event_time) for q in queries)):
        raise ValueError('duplicate prefix queries')
    if (architecture.profile_id != seal.profile_id or
            manifest.profile_id != seal.profile_id or
            manifest.epoch_id != seal.epoch_id or
            boundary.storage.profile_id != seal.profile_id or
            boundary.storage.epoch_id != seal.epoch_id or
            boundary.ledger.profile_id != seal.profile_id or
            boundary.ledger.epoch_id != seal.epoch_id or
            boundary.arbiter.profile_id != seal.profile_id or
            boundary.arbiter.epoch_id != seal.epoch_id):
        raise ValueError('external prefix profile/epoch mismatch')
    if boundary.ledger.ingress != seal.binding:
        raise ValueError('external ingress seal modified in owned snapshot')
    if any(q.target_node_id not in seal.node_ids for q in queries):
        raise ValueError('external prefix refers to unknown node')
    # Also validates event occupancy, route provenance and finite PE capacity.
    event_reservation_usage_v0(architecture, boundary.storage,
                               manifest, boundary.ledger)
    last = boundary.arbiter.last_service_boundary
    if last is not None and (type(last) is not int or last < 0):
        raise ValueError('invalid current SERVICE_TIME boundary')
    resident = set(boundary.ledger.external_resident)
    consumed = set(boundary.ledger.external_consumed)
    accounted = resident | consumed
    arrivals = seal.binding.arrivals
    for a in arrivals:
        if a.input_index in accounted and (last is None or a.arrival_boundary > last):
            raise ValueError('external occurrence accounted before its SERVICE_TIME')
        if last is not None and a.arrival_boundary <= last and a.input_index not in accounted:
            raise ValueError('due external occurrence missing from boundary history')

    rows = []
    for q in sorted(queries, key=lambda x: (x.target_node_id, x.event_time)):
        indices = tuple(a.input_index for a in arrivals
                        if a.node_id == q.target_node_id and a.event_time <= q.event_time)
        rr = tuple(i for i in indices if i in resident)
        cc = tuple(i for i in indices if i in consumed)
        pp = tuple(i for i in indices if i not in accounted)
        covered = not pp
        rows.append(ExternalPrefixEvidenceV0(
            q.target_node_id, q.event_time, indices, rr, cc, pp,
            covered, 'ACCOUNTED_SEALED_PREFIX' if covered else 'PENDING_EXTERNAL_INPUT',
        ))
    return ExternalPrefixAnalysisV0(
        seal.profile_id, seal.epoch_id, last, tuple(rows),
    )
