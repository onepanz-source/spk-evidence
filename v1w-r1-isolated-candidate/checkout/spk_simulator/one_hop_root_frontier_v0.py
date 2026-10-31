"""SPK S3.7d/3b2b2k/17: derive one-hop root-source closure obligations.

This module derives root emission cutoff *from owned state*, never from a
caller-authored watermark. It accounts for static manifest deliveries and
sealed external input, but NEVER issues a BATCH_CONSUME certificate. Dynamic
service registration and live ingress are outside this proof boundary.
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
from spk_simulator.owned_root_emission_frontier_v0 import (
    RootEmissionFrontierQueryV0, analyze_owned_root_emission_frontier_v0,
)
from spk_simulator.owned_internal_reads_v0 import OwnedInternalReadStateV0
from spk_simulator.routing_binding_v0 import RoutedBindingManifestV0


@dataclass(frozen=True, slots=True)
class OneHopDestinationQueryV0:
    target_node_id: str
    event_time: int

    def __post_init__(self):
        if (type(self.target_node_id) is not str or not self.target_node_id
                or self.target_node_id.strip() != self.target_node_id):
            raise ValueError('invalid one-hop target')
        if type(self.event_time) is not int or self.event_time < 0:
            raise ValueError('invalid one-hop EVENT_TIME')


@dataclass(frozen=True, slots=True)
class OneHopEdgeEvidenceV0:
    edge_index: int
    source_node_id: str
    required_source_through: int
    source_is_root: bool
    authenticated_root_prefix: bool
    # Negative emission times cannot exist in Network v0.
    vacuous_negative_time: bool


@dataclass(frozen=True, slots=True)
class OneHopDestinationEvidenceV0:
    target_node_id: str
    event_time: int
    edge_evidences: tuple[OneHopEdgeEvidenceV0, ...]
    external_prefix_accounted: bool
    static_manifest_route_ids: tuple[int, ...]
    static_event_resident_ids: tuple[int, ...]
    static_output_pending_ids: tuple[int, ...]
    static_already_consumed_ids: tuple[int, ...]
    external_same_time_resident_ids: tuple[int, ...]
    external_same_time_consumed_ids: tuple[int, ...]
    external_same_time_pending_ids: tuple[int, ...]
    upstream_prefix_authenticated: bool
    static_known_deliveries_present: bool
    status: str
    # Never a consume permission: dynamic route provenance and all-emission
    # exhaustiveness are not owned by this read-only one-hop gate.
    supports_consume_admission: bool = False


@dataclass(frozen=True, slots=True)
class OneHopRootFrontierAnalysisV0:
    profile_id: str
    epoch_id: str
    destinations: tuple[OneHopDestinationEvidenceV0, ...]
    supports_consume_admission: bool = False


def analyze_one_hop_root_frontier_v0(
    architecture: ArchitectureProfileV0,
    network: NetworkV0,
    seal: SealedExternalIngressEpochV0,
    manifest: RoutedBindingManifestV0,
    admission: AtomicEmissionAdmissionV0,
    requests: tuple[MemoryServiceRequestV0, ...],
    graph: AccessDependencyGraphV0,
    state: OwnedInternalReadStateV0,
    *,
    queries: tuple[OneHopDestinationQueryV0, ...],
) -> OneHopRootFrontierAnalysisV0:
    """Audit one-hop prerequisites against the *same* owned snapshot.

    `upstream_prefix_authenticated` only means no new qualifying root
    emissions, plus a sealed external prefix. `static_known_deliveries_present`
    checks pre-existing manifest occurrences only. Neither means that all
    possible dynamic emissions have been registered or that a new batch may
    consume. No claims or service-time cutoffs are accepted from the caller.
    """
    if (type(architecture) is not ArchitectureProfileV0
            or type(network) is not NetworkV0
            or type(seal) is not SealedExternalIngressEpochV0
            or type(manifest) is not RoutedBindingManifestV0
            or type(admission) is not AtomicEmissionAdmissionV0
            or type(graph) is not AccessDependencyGraphV0
            or type(state) is not OwnedInternalReadStateV0):
        raise TypeError('invalid one-hop architectural input')
    if type(requests) is not tuple or any(type(r) is not MemoryServiceRequestV0 for r in requests):
        raise TypeError('invalid one-hop request tuple')
    if type(queries) is not tuple or any(type(q) is not OneHopDestinationQueryV0 for q in queries):
        raise TypeError('invalid one-hop queries')
    if len({(q.target_node_id, q.event_time) for q in queries}) != len(queries):
        raise ValueError('duplicate one-hop query')
    node_ids = {n.node_id for n in network.nodes}
    if any(q.target_node_id not in node_ids for q in queries):
        raise ValueError('unknown one-hop target')
    if (network != state.image.network or seal.epoch_id != state.image.epoch_id
            or seal.epoch_id != manifest.epoch_id or seal.epoch_id != admission.epoch_id
            or seal.profile_id != architecture.profile_id
            or manifest.profile_id != architecture.profile_id
            or admission.profile_id != architecture.profile_id):
        raise ValueError('one-hop network/profile/epoch mismatch')
    # Check validity of manifest topology without assuming that a static route
    # describes every emission the Core could ever compute.
    for bound in manifest.routes:
        o = bound.occurrence
        if not any(e.source_node == o.source_node_id
                   and e.source_channel == o.source_channel
                   and e.target_node == o.target_node_id
                   and e.target_channel == o.target_channel
                   and o.delivery_event_time == o.emission_event_time + e.delay_ticks
                   for e in network.edges):
            raise ValueError('static routing manifest contradicts network topology')
    incoming = {node: [] for node in node_ids}
    for i, edge in enumerate(network.edges):
        if edge.source_node not in node_ids or edge.target_node not in node_ids or edge.delay_ticks <= 0:
            raise ValueError('invalid one-hop edge')
        incoming[edge.target_node].append((i, edge))
    root_sources = {n for n in node_ids if not incoming[n]}
    ordered = tuple(sorted(queries, key=lambda q: (q.target_node_id, q.event_time)))
    unique_root_queries = {
        (e.source_node, q.event_time - e.delay_ticks)
        for q in ordered for _, e in incoming[q.target_node_id]
        if e.source_node in root_sources and q.event_time >= e.delay_ticks
    }
    root_result = analyze_owned_root_emission_frontier_v0(
        architecture, network, seal, manifest, admission, requests, graph, state,
        queries=tuple(RootEmissionFrontierQueryV0(n, t) for n, t in sorted(unique_root_queries)),
    )
    root_proofs = {(x.source_node_id, x.settled_through_event_time):
                   x.source_emission_prefix_certified for x in root_result.evidences}
    boundary = state.owned.boundary.driver.boundary
    external_result = analyze_owned_external_prefix_v0(
        architecture, seal, manifest, boundary,
        queries=tuple(ExternalPrefixQueryV0(q.target_node_id, q.event_time) for q in ordered),
    )
    ext_map = {(x.target_node_id, x.settled_through_event_time): x
               for x in external_result.evidences}
    resident = {o.event_id for o in boundary.storage.admitted_events}
    output = {o.event_id for o in boundary.storage.pending_output}
    consumed = set(boundary.storage.consumed_ids)
    external_resident = set(boundary.ledger.external_resident)
    external_consumed = set(boundary.ledger.external_consumed)
    rows = []
    for query in ordered:
        node, t = query.target_node_id, query.event_time
        edge_proofs = []
        for i, edge in incoming[node]:
            cutoff = t - edge.delay_ticks
            vacuous = cutoff < 0
            is_root = edge.source_node in root_sources
            certified = vacuous or (is_root and root_proofs.get((edge.source_node, cutoff), False))
            edge_proofs.append(OneHopEdgeEvidenceV0(
                i, edge.source_node, cutoff, is_root, bool(certified), vacuous,
            ))
        ext = ext_map[(node, t)]
        exact_external = tuple(a.input_index for a in seal.binding.arrivals
                               if a.node_id == node and a.event_time == t)
        ext_resident = tuple(i for i in exact_external if i in external_resident)
        ext_consumed = tuple(i for i in exact_external if i in external_consumed)
        ext_pending = tuple(i for i in exact_external
                            if i not in external_resident and i not in external_consumed)
        bound_ids = tuple(sorted(r.route_request_id for r in manifest.routes
                                 if r.occurrence.target_node_id == node
                                 and r.occurrence.delivery_event_time == t))
        event_ids = tuple(i for i in bound_ids if i in resident)
        output_ids = tuple(i for i in bound_ids if i in output)
        consumed_ids = tuple(i for i in bound_ids if i in consumed)
        known = len(event_ids) == len(bound_ids) and not consumed_ids
        settled = (bool(edge_proofs) and all(x.authenticated_root_prefix for x in edge_proofs)
                   and ext.sealed_prefix_accounted)
        if not edge_proofs:
            status = 'NO_INCOMING_EDGES'
        elif any(not e.source_is_root and not e.vacuous_negative_time for e in edge_proofs):
            status = 'NONROOT_SOURCE_UNPROVEN'
        elif not all(e.authenticated_root_prefix for e in edge_proofs):
            status = 'ROOT_SOURCE_PREFIX_PENDING'
        elif not ext.sealed_prefix_accounted:
            status = 'EXTERNAL_PREFIX_PENDING'
        elif ext_pending:
            status = 'EXTERNAL_SAME_TIME_PENDING'
        elif ext_consumed:
            status = 'EXTERNAL_SAME_TIME_ALREADY_CONSUMED'
        elif consumed_ids:
            status = 'STATIC_ROUTE_ALREADY_CONSUMED'
        elif not known:
            status = 'STATIC_ROUTE_NOT_RESIDENT'
        else:
            status = 'ONE_HOP_STATIC_PRECONDITIONS_MET'
        rows.append(OneHopDestinationEvidenceV0(
            node, t, tuple(edge_proofs), ext.sealed_prefix_accounted,
            bound_ids, event_ids, output_ids, consumed_ids,
            ext_resident, ext_consumed, ext_pending,
            settled, known, status,
        ))
    return OneHopRootFrontierAnalysisV0(
        architecture.profile_id, seal.epoch_id, tuple(rows),
    )
