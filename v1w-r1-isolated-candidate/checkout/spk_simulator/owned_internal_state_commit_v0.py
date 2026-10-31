"""S3.7d/3b2b2k/6: authenticated, versioned, output-free STATE_COMMIT.

Only the no-candidate-output path is supported. Nonempty output must be admitted
in a future atomic STATE/OUTPUT owner. No trace-derived state can be committed.
"""
from dataclasses import dataclass, replace

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind, MemoryDomainV0 as Domain
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_network.model_v0 import NetworkV0
from spk_simulator.access_dependencies_v0 import AccessDependencyGraphV0
from spk_simulator.routing_binding_v0 import RoutedBindingManifestV0
from spk_simulator.causal_service_quantum_v0 import ServiceQuantumStateV0, ServiceConfirmedV0
from spk_simulator.owned_internal_reads_v0 import (
    OwnedInternalReadStateV0, OwnedInternalCommitEvidenceV0,
    audit_committed_internal_history_v0,
)
from spk_simulator.serialized_internal_graph_v0 import serialize_internal_access_graph_v0
from spk_simulator.versioned_core_transition_v0 import commit_core_transition_v0


@dataclass(frozen=True, slots=True)
class OwnedInternalStateCommitStepV0:
    request_id: int
    evidence: OwnedInternalCommitEvidenceV0
    state: OwnedInternalReadStateV0


def commit_owned_internal_state_v0(
    network: NetworkV0,
    manifest: RoutedBindingManifestV0,
    requests: tuple[MemoryServiceRequestV0, ...],
    graph: AccessDependencyGraphV0,
    state: OwnedInternalReadStateV0,
    *,
    commit_request_id: int,
) -> OwnedInternalStateCommitStepV0:
    """Commit one finished, causally ready STATE_COMMIT with no Core outputs.

    The unit of atomicity here is a versioned S write + service confirmation.
    It does not claim atomic OUTPUT effects, and forbids candidate emissions.
    """
    if (type(network) is not NetworkV0 or type(state) is not OwnedInternalReadStateV0 or
        type(manifest) is not RoutedBindingManifestV0):
        raise TypeError('invalid network or internal owner state')
    if type(requests) is not tuple or any(type(x) is not MemoryServiceRequestV0 for x in requests):
        raise TypeError('invalid requests')
    if type(graph) is not AccessDependencyGraphV0:
        raise TypeError('invalid graph')
    if type(commit_request_id) is not int or commit_request_id < 0:
        raise ValueError('invalid commit request ID')
    if manifest.epoch_id != state.image.epoch_id:
        raise ValueError('routing/neuronal epoch mismatch')
    serialized = serialize_internal_access_graph_v0(requests, graph)
    if serialized.graph != graph:
        raise ValueError('STATE_COMMIT graph must already contain serialized dependencies')
    batches = {x.state_commit_request_id: x for x in serialized.batches}
    binding = batches.get(commit_request_id)
    if binding is None:
        raise ValueError('commit request has no serialized neuronal batch')
    by_id = {r.request_id: r for r in requests}
    req = by_id[commit_request_id]
    if (req.kind is not Kind.STATE_COMMIT or req.domain is not Domain.STATE or
        req.target_id != f'state:{binding.node_id}' or
        req.epoch_id != state.image.epoch_id or
        req.event_time != binding.event_time or
        req.target_pe_id != binding.target_pe_id or req.quantity != 1):
        raise ValueError('STATE_COMMIT target / epoch / PE mismatch')
    svc = state.owned.boundary.service
    awaiting = {x.request_id: x for x in svc.awaiting_confirmation}
    confirmed = {x.request_id for x in svc.confirmed}
    if commit_request_id not in awaiting or awaiting[commit_request_id].finish_boundary > svc.next_service_tick:
        raise ValueError('STATE_COMMIT service has not finished')
    pred = next(x for x in graph.dependencies if x.request_id == commit_request_id)
    prev = pred.predecessor_ids if hasattr(pred, 'predecessor_ids') else pred.predecessors
    if not set(prev) <= confirmed:
        raise ValueError('STATE_COMMIT causal predecessors unconfirmed')
    if binding.previous_commit_request_id is not None and binding.previous_commit_request_id not in confirmed:
        raise ValueError('previous neuron commit unconfirmed')
    snapshots = audit_committed_internal_history_v0(network, state, requests, graph)
    prepared_items = [p for p in state.prepared if p.consume_request_id == binding.consume_request_id]
    if len(prepared_items) != 1:
        raise ValueError('STATE_COMMIT has no unique owned Core preparation')
    prep = prepared_items[0]
    batch = next((b for b in state.pending_batches if b.consume_request_id == binding.consume_request_id), None)
    by_read = {x.request_id: x for x in state.reads}
    p = by_read.get(binding.program_request_id)
    s = by_read.get(binding.state_load_request_id)
    if (prep.program_read_request_id != binding.program_request_id or
        prep.state_read_request_id != binding.state_load_request_id or
        batch is None or p is None or s is None or
        p.kind is not Kind.PROGRAM_REFERENCE or s.kind is not Kind.STATE_LOAD or
        (p.request_id not in confirmed or s.request_id not in confirmed or
         batch.consume_request_id not in confirmed)):
        raise ValueError('missing confirmed P/S/EVENT input for Core STATE_COMMIT')
    # Reconcile exactly the consumed route/external identities against the
    # controller's retained tombstones, not just caller-provided channels.
    storage = state.owned.boundary.driver.boundary.storage
    boundary_ledger = state.owned.boundary.driver.boundary.ledger
    routes = {x.route_request_id: x for x in manifest.routes}
    arrivals = {x.input_index: x for x in boundary_ledger.ingress.arrivals}
    if (len(routes) != len(manifest.routes) or
        len(arrivals) != len(boundary_ledger.ingress.arrivals) or
        not (batch.route_request_ids or batch.external_input_indices) or
        not set(batch.route_request_ids) <= set(storage.consumed_ids) or
        not set(batch.external_input_indices) <= set(boundary_ledger.external_consumed)):
        raise ValueError('STATE_COMMIT lacks retained EVENT consumption evidence')
    occurrences = []
    for rid in batch.route_request_ids:
        r = routes.get(rid)
        if r is None or r.consume_request_id != batch.consume_request_id:
            raise ValueError('STATE_COMMIT route not bound to consumed batch')
        x = r.occurrence
        occurrences.append((x.target_node_id, x.target_pe_id, x.delivery_event_time, x.target_channel))
    for idx in batch.external_input_indices:
        a = arrivals.get(idx)
        if a is None or a.consume_request_id != batch.consume_request_id:
            raise ValueError('STATE_COMMIT external arrival not bound to consumed batch')
        occurrences.append((a.node_id, a.target_pe_id, a.event_time, a.channel))
    if (any((node, pe, t) != (binding.node_id, binding.target_pe_id, binding.event_time)
            for node, pe, t, _ in occurrences) or
        tuple(sorted(ch for _, _, _, ch in occurrences)) != batch.channels):
        raise ValueError('STATE_COMMIT witnessed channels disagree with EVENT ledger')
    trans = prep.transition
    if (trans.node_id != binding.node_id or trans.event_time != binding.event_time or
        trans.epoch_id != binding.epoch_id or trans.channels != batch.channels or
        trans.candidate_outputs):
        raise ValueError('OUTPUT-bearing or mismatched Core transition requires atomic OUTPUT owner')
    current = next(x for x in state.image.neurons if x.node_id == binding.node_id)
    if (current.version != trans.base_version or
        s.state_version != current.version or s.raw != current.raw or
        s.last_timestamp != current.last_timestamp or
        snapshots.get((s.node_id, s.state_version)) != current):
        raise ValueError('stale STATE_LOAD or Core base version')
    node = next(x for x in network.nodes if x.node_id == binding.node_id)
    if p.config != node.config or p.program != node.program:
        raise ValueError('PROGRAM_REFERENCE did not read active program')
    write = commit_core_transition_v0(network, state.image, trans)
    evidence = OwnedInternalCommitEvidenceV0(
        commit_request_id, prep, write.receipt, svc.next_service_tick,
    )
    after_svc = ServiceQuantumStateV0(
        next_service_tick=svc.next_service_tick,
        partial=svc.partial,
        awaiting_confirmation=tuple(x for x in svc.awaiting_confirmation
                                    if x.request_id != commit_request_id),
        confirmed=tuple(sorted(svc.confirmed +
            (ServiceConfirmedV0(commit_request_id, svc.next_service_tick),),
            key=lambda x: x.request_id)),
    )
    after_owned = replace(state.owned,
        boundary=replace(state.owned.boundary, service=after_svc))
    after = replace(state, owned=after_owned, image=write.state,
        prepared=tuple(x for x in state.prepared if x.consume_request_id != binding.consume_request_id),
        commits=state.commits + (evidence,))
    # Rebuild history from the frozen initial Core program and all retained
    # actual witnessed inputs; failure means no successor state escapes.
    audit_committed_internal_history_v0(network, after, requests, graph)
    return OwnedInternalStateCommitStepV0(commit_request_id, evidence, after)
