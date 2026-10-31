"""SPK S3.7d/3b2b2k/15: prove emission cutoffs for root neurons only.

The finite external ingress seal is the epoch trust root. A SOURCE_EMISSION
frontier is emitted ONLY for nodes with zero incoming network edges, after
verifying all sealed external occurrences at or before T were consumed and
have authenticated Core STATE_COMMIT receipts. No timeouts, idle heuristics,
or caller-authored watermarks are accepted.

This is a read-only, closed-input, root-only proof. It cannot certify nodes with
incoming edges, autonomous live ingress, dynamic batch admission, or deadlock.
"""
from dataclasses import dataclass

from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_network.model_v0 import NetworkV0
from spk_simulator.access_dependencies_v0 import AccessDependencyGraphV0
from spk_simulator.atomic_emission_admission_v0 import AtomicEmissionAdmissionV0
from spk_simulator.owned_external_ingress_prefix_v0 import (
    ExternalPrefixQueryV0, SealedExternalIngressEpochV0,
    analyze_owned_external_prefix_v0,
)
from spk_simulator.owned_internal_reads_v0 import (
    OwnedInternalReadStateV0, audit_committed_internal_history_v0,
)
from spk_simulator.routing_binding_v0 import RoutedBindingManifestV0
from spk_simulator.serialized_internal_graph_v0 import (
    serialize_internal_access_graph_v0,
)


@dataclass(frozen=True, slots=True)
class RootEmissionFrontierQueryV0:
    source_node_id: str
    settled_through_event_time: int

    def __post_init__(self):
        if (type(self.source_node_id) is not str or not self.source_node_id
                or self.source_node_id.strip() != self.source_node_id):
            raise ValueError('invalid root source node')
        if (type(self.settled_through_event_time) is not int
                or self.settled_through_event_time < 0):
            raise ValueError('invalid root frontier EVENT_TIME')


@dataclass(frozen=True, slots=True)
class RootEmissionFrontierEvidenceV0:
    source_node_id: str
    settled_through_event_time: int
    required_external_input_indices: tuple[int, ...]
    consumed_external_input_indices: tuple[int, ...]
    committed_batch_request_ids: tuple[int, ...]
    status: str
    source_emission_prefix_certified: bool
    # This certificate cannot by itself authorize any BATCH_CONSUME.
    supports_consume_admission: bool = False


@dataclass(frozen=True, slots=True)
class RootEmissionFrontierAnalysisV0:
    profile_id: str
    epoch_id: str
    evidences: tuple[RootEmissionFrontierEvidenceV0, ...]
    supports_consume_admission: bool = False


def analyze_owned_root_emission_frontier_v0(
    architecture: ArchitectureProfileV0,
    network: NetworkV0,
    seal: SealedExternalIngressEpochV0,
    manifest: RoutedBindingManifestV0,
    admission: AtomicEmissionAdmissionV0,
    requests: tuple[MemoryServiceRequestV0, ...],
    graph: AccessDependencyGraphV0,
    state: OwnedInternalReadStateV0,
    *,
    queries: tuple[RootEmissionFrontierQueryV0, ...],
) -> RootEmissionFrontierAnalysisV0:
    """Derive a ROOT source cutoff from real input-consumption/commit history.

    Conditional on a trusted single-owner snapshot and a *sealed*, finite
    input epoch. A valid cutoff at T means this root cannot produce a *new*
    emission with EVENT_TIME <= T. Known routed outputs may still await physical
    delivery, so destination batch closure needs additional independent proofs.
    """
    if (type(architecture) is not ArchitectureProfileV0 or
            type(network) is not NetworkV0 or
            type(seal) is not SealedExternalIngressEpochV0 or
            type(manifest) is not RoutedBindingManifestV0 or
            type(admission) is not AtomicEmissionAdmissionV0 or
            type(graph) is not AccessDependencyGraphV0 or
            type(state) is not OwnedInternalReadStateV0):
        raise TypeError('invalid root frontier architectural input')
    if (type(requests) is not tuple or
            any(type(r) is not MemoryServiceRequestV0 for r in requests)):
        raise TypeError('invalid root frontier requests')
    if (type(queries) is not tuple or
            any(type(q) is not RootEmissionFrontierQueryV0 for q in queries)):
        raise TypeError('invalid root frontier queries')
    if len({(q.source_node_id, q.settled_through_event_time) for q in queries}) != len(queries):
        raise ValueError('duplicate root frontier query')
    node_ids = tuple(sorted(x.node_id for x in network.nodes))
    if len(node_ids) != len(set(node_ids)) or node_ids != seal.node_ids:
        raise ValueError('root frontier network/seal node mismatch')
    if (architecture.profile_id != seal.profile_id or
            architecture.profile_id != manifest.profile_id or
            architecture.profile_id != admission.profile_id or
            seal.epoch_id != manifest.epoch_id or
            seal.epoch_id != admission.epoch_id or
            seal.epoch_id != state.image.epoch_id or
            state.image.network != network):
        raise ValueError('root frontier profile, epoch or image mismatch')
    if any(q.source_node_id not in node_ids for q in queries):
        raise ValueError('unknown root frontier source')
    for e in network.edges:
        if (e.source_node not in node_ids or e.target_node not in node_ids or
                type(e.delay_ticks) is not int or e.delay_ticks < 1):
            raise ValueError('invalid root frontier network edge')

    boundary = state.owned.boundary.driver.boundary
    # Validate the actual owned storage/ingress ledger against the finite seal.
    prefixes = analyze_owned_external_prefix_v0(
        architecture, seal, manifest, boundary,
        queries=tuple(ExternalPrefixQueryV0(q.source_node_id, q.settled_through_event_time)
                      for q in queries),
    )
    ext_by_query = {(x.target_node_id, x.settled_through_event_time): x
                    for x in prefixes.evidences}
    # This replays real Core commits from the initial frozen image and checks
    # P/S reads, confirmed service, receipts, and atomic published fan-out.
    audit_committed_internal_history_v0(
        network, state, requests, graph,
        architecture=architecture, manifest=manifest, admission=admission,
    )
    serialized = serialize_internal_access_graph_v0(requests, graph)
    if serialized.graph != graph:
        raise ValueError('root frontier requires serialized STATE dependencies')
    batches_by_node = {}
    for batch in serialized.batches:
        batches_by_node.setdefault(batch.node_id, []).append(batch)
    commits = {x.commit_request_id: x for x in state.commits}
    if len(commits) != len(state.commits):
        raise ValueError('duplicate root commit evidence')
    witnesses = {x.consume_request_id: x for x in state.pending_batches}
    if len(witnesses) != len(state.pending_batches):
        raise ValueError('duplicate root batch witness')
    seen_routes = {x.occurrence.target_node_id for x in manifest.routes}
    ext_arrivals = {a.input_index: a for a in seal.binding.arrivals}
    consumed = set(boundary.ledger.external_consumed)

    results = []
    for q in sorted(queries, key=lambda x: (x.source_node_id, x.settled_through_event_time)):
        node, time = q.source_node_id, q.settled_through_event_time
        prefix = ext_by_query[(node, time)]
        indices = prefix.known_input_indices
        consumed_indices = tuple(i for i in indices if i in consumed)
        relevant = [b for b in batches_by_node.get(node, ()) if b.event_time <= time]
        confirmed_ids = tuple(sorted(b.state_commit_request_id for b in relevant
                                     if b.state_commit_request_id in commits))
        status = 'SOURCE_PREFIX_CERTIFIED'
        if any(e.target_node == node for e in network.edges):
            status = 'INBOUND_EDGES_UNPROVEN'
        elif node in seen_routes:
            # A manifest contradicting an edge-free node is not a proof root.
            status = 'INCONSISTENT_ROUTE_MANIFEST'
        elif not prefix.sealed_prefix_accounted:
            status = 'EXTERNAL_PREFIX_PENDING'
        elif consumed_indices != indices:
            status = 'EXTERNAL_EVENTS_UNCONSUMED'
        elif len(confirmed_ids) != len(relevant):
            status = 'ROOT_BATCH_COMMIT_PENDING'
        else:
            expected: dict[int, int] = {}
            invalid = False
            for batch in relevant:
                witness = witnesses.get(batch.consume_request_id)
                evidence = commits.get(batch.state_commit_request_id)
                if (witness is None or evidence is None or
                        witness.node_id != node or witness.event_time != batch.event_time or
                        witness.epoch_id != seal.epoch_id or
                        witness.consume_request_id != evidence.preparation.consume_request_id or
                        witness.route_request_ids or not witness.external_input_indices):
                    invalid = True
                    break
                for idx in witness.external_input_indices:
                    arrival = ext_arrivals.get(idx)
                    if (arrival is None or arrival.node_id != node or
                            arrival.event_time != batch.event_time or
                            arrival.consume_request_id != batch.consume_request_id or
                            idx not in consumed or idx in expected):
                        invalid = True
                        break
                    expected[idx] = batch.consume_request_id
                if invalid:
                    break
            if invalid or set(expected) != set(indices):
                status = 'ROOT_INPUT_COMMIT_MISMATCH'
        results.append(RootEmissionFrontierEvidenceV0(
            node, time, indices, consumed_indices, confirmed_ids,
            status, status == 'SOURCE_PREFIX_CERTIFIED',
        ))
    return RootEmissionFrontierAnalysisV0(
        seal.profile_id, seal.epoch_id, tuple(results),
    )
