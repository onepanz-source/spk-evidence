"""S3.7d/3b2b2k/21: prove sealed-input batch readiness for root neurons.

Read-only, trust-conditional admission precheck, NOT consumption or completion.
The finite external seal is the only source of complete external multiplicity;
SERVICE_TIME progress never implies event-time closure. A root has no inbound
network routes. Does not handle nonroot nodes or an open input epoch.
"""
from dataclasses import dataclass

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind, MemoryDomainV0 as Domain
from spk_simulator.owned_shared_event_cycle_v0 import OwnedSharedEventCycleStateV0


@dataclass(frozen=True, slots=True)
class SealedRootBatchCandidateV0:
    epoch_id: str
    node_id: str
    pe_id: str
    event_time: int
    consume_request_id: int
    expected_external_indices: tuple[int, ...]
    resident_external_indices: tuple[int, ...]
    pending_external_indices: tuple[int, ...]
    status: str
    sealed_input_set_complete: bool
    supports_consume_confirmation: bool = False


@dataclass(frozen=True, slots=True)
class SealedRootBatchAnalysisV0:
    profile_id: str
    epoch_id: str
    batches: tuple[SealedRootBatchCandidateV0, ...]
    supports_consume_confirmation: bool = False


def analyze_owned_sealed_root_batches_v0(
    state: OwnedSharedEventCycleStateV0,
) -> SealedRootBatchAnalysisV0:
    """Return exactly identified candidate BATCH_CONSUME input sets for roots.

    Positive readiness means all external occurrences assigned to an individual
    root batch are resident AND no earlier logical-time input for that root
    remains unconsumed. With a separate trusted consumption owner, later
    logical times can become READY after earlier confirmed consumption.
    Does not grant service, remove storage, or certify the effect of consuming.

    A request may be absent/malformed in a caller-authored *static* request set:
    fail closed with ValueError rather than silently forming an unowned batch.
    """
    if type(state) is not OwnedSharedEventCycleStateV0:
        raise TypeError('invalid shared EVENT owner')
    registry = state.dynamic.transit.registry
    network = registry.allocation_ledger.network
    seal = state.seal
    nodes = {node.node_id for node in network.nodes}
    incoming = {edge.target_node for edge in network.edges}
    requests = {r.request_id: r for r in registry.base_requests}
    residents = set(state.external_resident_input_indices)
    consumed = set(state.external_consumed_input_indices)
    arr = seal.binding.arrivals
    by_batch = {}
    for a in arr:
        key = (a.node_id, a.event_time, a.consume_request_id)
        by_batch.setdefault(key, []).append(a)
    # A neuron cannot have more than one BATCH_CONSUME for the same logical
    # time in the closed-input, Network-v0 batch semantics.
    seen_time = set()
    for node, time, _rid in by_batch:
        if (node, time) in seen_time:
            raise ValueError('ambiguous root batch identity at EVENT_TIME')
        seen_time.add((node, time))

    out = []
    times = {}
    for a in arr:
        times.setdefault(a.node_id, set()).add(a.event_time)
    for (node, event_time, rid), items in sorted(by_batch.items()):
        if node not in nodes:
            raise ValueError('unknown sealed root batch node')
        if node in incoming:
            status = 'NONROOT_REQUIRES_CAUSAL_FRONTIER'
            ready = False
        else:
            req = requests.get(rid)
            if (req is None or req.kind is not Kind.BATCH_CONSUME or
                    req.domain is not Domain.EVENT or req.target_id != f'events:{node}' or
                    req.epoch_id != seal.epoch_id or
                    req.event_time != event_time or req.quantity != len(items) or
                    req.target_pe_id != items[0].target_pe_id or
                    req.requester_pe_id != items[0].target_pe_id or
                    any(x.target_pe_id != req.target_pe_id for x in items)):
                raise ValueError('sealed root batch/request identity mismatch')
            expected = {x.input_index for x in items}
            # A consumed historical batch is not available for consumption
            # again; earlier times must be fully consumed first.
            earlier = {a.input_index for a in arr
                       if a.node_id == node and a.event_time < event_time}
            if expected <= consumed:
                status = 'ROOT_INPUT_SET_CONSUMED'
                ready = False
            elif not earlier <= consumed:
                status = 'EARLIER_ROOT_BATCH_UNCONSUMED'
                ready = False
            elif not expected <= residents:
                status = 'SEALED_INPUTS_PENDING'
                ready = False
            else:
                status = 'ROOT_INPUT_SET_READY'
                ready = True
        expected_ids = tuple(x.input_index for x in items)
        present = tuple(i for i in expected_ids if i in residents)
        pending = tuple(i for i in expected_ids if i not in residents)
        out.append(SealedRootBatchCandidateV0(
            seal.epoch_id, node, items[0].target_pe_id, event_time, rid,
            expected_ids, present, pending, status, ready,
        ))
    return SealedRootBatchAnalysisV0(
        seal.profile_id, seal.epoch_id, tuple(out),
    )
