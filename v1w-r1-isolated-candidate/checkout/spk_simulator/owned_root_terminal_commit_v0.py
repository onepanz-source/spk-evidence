"""SPK k24d: narrow, replay-audited terminal STATE_COMMIT handoff.

The k24b input remains an immutable, *historical* snapshot.  Its service
history is a trust root.  Every NEW terminal quantum is reconstructed from
that boundary; no k24b implementation is altered or invoked during replay.

Scope: one fully consumed root batch, one output-free commit, one PE service
clock.  No general inter-owner exclusion, crash durability or authentication
of a forged installation snapshot is claimed.
"""
from dataclasses import dataclass

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_simulator.causal_service_quantum_v0 import (
    ServiceQuantumSliceV0, ServiceQuantumStateV0,
    advance_service_quantum_v0,
)
from spk_simulator.owned_root_single_clock_v0 import OwnedRootSingleClockStateV0
from spk_simulator.serialized_internal_graph_v0 import serialize_internal_access_graph_v0
from spk_simulator.versioned_core_transition_v0 import (
    VersionedNeuronImageV0, CoreStateCommitReceiptV0,
    commit_core_transition_v0,
)


@dataclass(frozen=True, slots=True)
class TerminalCommitQuantumV0:
    """One *replayable* service boundary, not a caller-authorized effect."""
    service_tick: int
    slices: tuple[ServiceQuantumSliceV0, ...]
    work_finished_request_ids: tuple[int, ...]
    confirmed_request_ids: tuple[int, ...]
    receipt: CoreStateCommitReceiptV0 | None


def _handoff_contract(root: OwnedRootSingleClockStateV0):
    if type(root) is not OwnedRootSingleClockStateV0:
        raise TypeError('terminal commit requires k24b root snapshot')
    root.__post_init__()
    shared = root.shared
    registry = shared.dynamic.transit.registry
    service = shared.dynamic.transit.service
    serialized = serialize_internal_access_graph_v0(registry.base_requests, registry.base_graph)
    if serialized.graph != registry.base_graph or len(serialized.batches) != 1:
        raise ValueError('terminal handoff requires one serialized root batch')
    batch = serialized.batches[0]
    by_id = {x.request_id: x for x in registry.base_requests}
    if (len(by_id) != 4 or set(by_id) != {
        batch.program_request_id, batch.state_load_request_id,
        batch.consume_request_id, batch.state_commit_request_id,
    } or by_id[batch.state_commit_request_id].kind is not Kind.STATE_COMMIT):
        raise ValueError('terminal handoff requires exactly one canonical batch')
    completed = {x.request_id for x in service.confirmed}
    required = {batch.program_request_id, batch.state_load_request_id,
                batch.consume_request_id}
    if (completed != required or service.partial or service.awaiting_confirmation):
        raise ValueError('handoff requires all P/S/EVENT effects confirmed and no pending work')
    if (len(root.prepared) != 1 or root.prepared[0].consume_request_id != batch.consume_request_id
            or len(root.witnesses) != 1 or root.witnesses[0].consume_request_id != batch.consume_request_id):
        raise ValueError('terminal handoff requires unique witnessed Core preparation')
    arrival_ids = {a.input_index for a in shared.seal.binding.arrivals}
    if (not arrival_ids or set(shared.external_consumed_input_indices) != arrival_ids
            or shared.external_resident_input_indices):
        raise ValueError('terminal handoff requires all sealed inputs consumed')
    if root.prepared[0].transition.candidate_outputs:
        raise ValueError('output-bearing Core transition requires STATE/OUTPUT owner')
    # Reconstruct transition from the same frozen Core and historical image.
    if root.prepared[0].transition.base_version != 0:
        raise ValueError('terminal handoff requires an uncommitted S image')
    return registry, batch, root.prepared[0].transition


def _next(root, service, image):
    registry, batch, prepared = _handoff_contract(root)
    rid = batch.state_commit_request_id
    waiting = {x.request_id: x for x in service.awaiting_confirmation}
    confirmed = {x.request_id for x in service.confirmed}
    if confirmed - {batch.program_request_id, batch.state_load_request_id,
                    batch.consume_request_id, rid}:
        raise ValueError('unexpected confirmed terminal request')
    if rid in confirmed:
        raise ValueError('terminal commit already confirmed')
    if any(x.request_id != rid for x in service.partial + service.awaiting_confirmation):
        raise ValueError('noncommit service entered terminal owner')
    if rid in waiting:
        if waiting[rid].finish_boundary > service.next_service_tick:
            raise ValueError('premature STATE_COMMIT confirmation')
        # Compute the versioned write BEFORE constructing the new confirmed
        # service state; either both escape together or neither does.
        result = commit_core_transition_v0(image.network, image, prepared)
        if result.receipt.candidate_outputs:
            raise ValueError('terminal commit cannot publish OUTPUT')
        confirmation, dispatch = (rid,), ()
        after_image, receipt = result.state, result.receipt
    else:
        confirmation, dispatch = (), (rid,)
        after_image, receipt = image, None
    quantum = advance_service_quantum_v0(
        registry.architecture, registry.staged_requests, registry.staged_graph,
        service, confirmed_request_ids=confirmation,
        owned_service_request_ids=dispatch, ingress=root.shared.seal.binding,
    )
    if any(x.request_id != rid for x in quantum.slices):
        raise ValueError('noncommit service quantum forbidden')
    if not confirmation and not quantum.slices:
        raise ValueError('STATE_COMMIT failed to progress')
    event = TerminalCommitQuantumV0(
        quantum.service_tick, quantum.slices,
        quantum.work_finished_request_ids, quantum.confirmed_request_ids, receipt,
    )
    return quantum.state, after_image, event


def _replay(root, events):
    _handoff_contract(root)
    if type(events) is not tuple or any(type(x) is not TerminalCommitQuantumV0 for x in events):
        raise TypeError('noncanonical terminal quantum history')
    service = root.shared.dynamic.transit.service
    image = root.image
    committed = False
    for claimed in events:
        if committed:
            raise ValueError('terminal service attempted after committed state')
        service, image, expected = _next(root, service, image)
        if claimed != expected:
            raise ValueError('terminal quantum not reconstructible from handoff')
        committed = expected.receipt is not None
    return service, image, committed


@dataclass(frozen=True, slots=True)
class OwnedRootTerminalCommitStateV0:
    handoff: OwnedRootSingleClockStateV0
    service: ServiceQuantumStateV0
    image: VersionedNeuronImageV0
    quanta: tuple[TerminalCommitQuantumV0, ...] = ()

    def __post_init__(self):
        if type(self.service) is not ServiceQuantumStateV0 or type(self.image) is not VersionedNeuronImageV0:
            raise TypeError('invalid terminal service or neuron image')
        actual_service, actual_image, _ = _replay(self.handoff, self.quanta)
        if self.service != actual_service or self.image != actual_image:
            raise ValueError('terminal service/S version differs from executed replay')

    @property
    def committed(self) -> bool:
        return bool(self.quanta and self.quanta[-1].receipt is not None)


@dataclass(frozen=True, slots=True)
class OwnedRootTerminalCommitStepV0:
    quantum: TerminalCommitQuantumV0
    state: OwnedRootTerminalCommitStateV0


def handoff_owned_root_terminal_commit_v0(root: OwnedRootSingleClockStateV0):
    """Transfer *protocol* authority at a closed root boundary.

    The caller must not continue advancing its old k24b reference.  Python
    cannot revoke a separately retained immutable reference; external single
    owner orchestration remains a trust assumption, not a proven capability.
    """
    _handoff_contract(root)
    return OwnedRootTerminalCommitStateV0(
        root, root.shared.dynamic.transit.service, root.image,
    )


def advance_owned_root_terminal_commit_v0(state: OwnedRootTerminalCommitStateV0):
    """Spend one terminal SERVICE_TIME quantum or confirm finished S write."""
    if type(state) is not OwnedRootTerminalCommitStateV0:
        raise TypeError('invalid terminal commit owner')
    state.__post_init__()
    if state.committed:
        raise ValueError('terminal owner already committed')
    service, image, event = _next(state.handoff, state.service, state.image)
    successor = OwnedRootTerminalCommitStateV0(
        state.handoff, service, image, state.quanta + (event,),
    )
    return OwnedRootTerminalCommitStepV0(event, successor)
