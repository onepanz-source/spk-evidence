"""SPK S3.7d/3b2b2k/23: physically witnessed root EVENT to Core handoff.

The ONLY producer of new witnesses is the owned root physical-consume step.
A witness is an input receipt, NOT P/S service authority, state commit, OUTPUT
admission or a proof of an arbitrary initial snapshot's history.
"""
from dataclasses import dataclass

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_simulator.owned_root_batch_consumption_v0 import (
    OwnedRootBatchConsumptionStepV0, advance_owned_root_batch_consumption_v0,
)
from spk_simulator.owned_shared_event_cycle_v0 import OwnedSharedEventCycleStateV0
from spk_simulator.versioned_core_transition_v0 import (
    VersionedNeuronImageV0, PreparedCoreTransitionV0,
    prepare_core_transition_v0,
)
from spk_simulator.witnessed_core_input_v0 import WitnessedCoreInputBatchV0


def _binding(state, rid):
    registry = state.dynamic.transit.registry
    requests = {req.request_id: req for req in registry.base_requests}
    request = requests.get(rid)
    if request is None or request.kind is not Kind.BATCH_CONSUME:
        raise ValueError('witness references unknown root BATCH_CONSUME')
    arrivals = tuple(a for a in state.seal.binding.arrivals if a.consume_request_id == rid)
    if not arrivals:
        raise ValueError('witness has no sealed external inputs')
    node, timestamp, pe = arrivals[0].node_id, arrivals[0].event_time, arrivals[0].target_pe_id
    inbound = {edge.target_node for edge in registry.allocation_ledger.network.edges}
    if node in inbound:
        raise ValueError('nonroot EVENT consumption cannot authorize root Core input')
    if (any((a.node_id, a.event_time, a.target_pe_id) != (node, timestamp, pe) for a in arrivals)
            or request.target_id != f'events:{node}' or request.event_time != timestamp
            or request.target_pe_id != pe or request.epoch_id != state.seal.epoch_id
            or request.quantity != len(arrivals)):
        raise ValueError('inconsistent sealed batch provenance')
    return arrivals


def _witness(state, rid, boundary):
    arrivals = _binding(state, rid)
    return WitnessedCoreInputBatchV0(
        rid, state.seal.epoch_id, arrivals[0].node_id,
        arrivals[0].event_time, arrivals[0].target_pe_id,
        tuple(sorted(a.channel for a in arrivals)), (),
        tuple(sorted(a.input_index for a in arrivals)), boundary,
    )


@dataclass(frozen=True, slots=True)
class OwnedRootCoreHandoffStateV0:
    shared: OwnedSharedEventCycleStateV0
    witnesses: tuple[WitnessedCoreInputBatchV0, ...] = ()

    def __post_init__(self):
        if type(self.shared) is not OwnedSharedEventCycleStateV0:
            raise TypeError('invalid shared EVENT state')
        if (type(self.witnesses) is not tuple or
                any(type(x) is not WitnessedCoreInputBatchV0 for x in self.witnesses)):
            raise TypeError('invalid root input witnesses')
        ids = tuple(x.consume_request_id for x in self.witnesses)
        if ids != tuple(sorted(set(ids))):
            raise ValueError('noncanonical root witness IDs')
        confirmed = {x.request_id: x for x in self.shared.dynamic.transit.service.confirmed}
        consumed = set(self.shared.external_consumed_input_indices)
        witnessed = set()
        for receipt in self.witnesses:
            confirmation = confirmed.get(receipt.consume_request_id)
            if (confirmation is None or
                    confirmation.confirmation_boundary != receipt.service_boundary or
                    receipt.service_boundary > self.shared.dynamic.transit.service.next_service_tick):
                raise ValueError('root witness without authenticated service confirmation')
            expected = _witness(self.shared, receipt.consume_request_id, receipt.service_boundary)
            if receipt != expected:
                raise ValueError('root witness does not match physical sealed provenance')
            event_ids = set(receipt.external_input_indices)
            if event_ids & witnessed:
                raise ValueError('external occurrence replayed by root witnesses')
            witnessed.update(event_ids)
        if witnessed != consumed:
            raise ValueError('root witness/tombstone coverage mismatch')


@dataclass(frozen=True, slots=True)
class OwnedRootCoreHandoffStepV0:
    service_tick: int
    consume_step: OwnedRootBatchConsumptionStepV0
    newly_witnessed: tuple[WitnessedCoreInputBatchV0, ...]
    state: OwnedRootCoreHandoffStateV0


def advance_owned_root_core_handoff_v0(state: OwnedRootCoreHandoffStateV0) -> OwnedRootCoreHandoffStepV0:
    """Execute ONE physical owner boundary and retain exact newly consumed Core inputs.

    Never accepts user-supplied 'consumed' IDs. P/S, Core commit, emission and
    routing remain OUTSIDE this service authority.
    """
    if type(state) is not OwnedRootCoreHandoffStateV0:
        raise TypeError('invalid root Core handoff state')
    # Re-audit even if state was constructed through unusual means.
    state.__post_init__()
    step = advance_owned_root_batch_consumption_v0(state.shared)
    confirmation = tuple(step.confirmed_consume_request_ids)
    inputs = tuple(_witness(step.state, rid, step.service_tick) for rid in confirmation)
    newly_consumed = set(step.newly_consumed_external_input_indices)
    if set(i for w in inputs for i in w.external_input_indices) != newly_consumed:
        raise ValueError('physical EVENT consumption/receipt mismatch')
    next_witnesses = tuple(sorted(state.witnesses + inputs, key=lambda x: x.consume_request_id))
    successor = OwnedRootCoreHandoffStateV0(step.state, next_witnesses)
    return OwnedRootCoreHandoffStepV0(step.service_tick, step, inputs, successor)


def preview_witnessed_root_core_v0(
    state: OwnedRootCoreHandoffStateV0,
    image: VersionedNeuronImageV0,
    *, consume_request_id: int,
) -> PreparedCoreTransitionV0:
    """Pure Core calculation over consumed channels. NOT an authorized P/S read.

    It DOES NOT confirm PROGRAM_REFERENCE/STATE_LOAD/STATE_COMMIT and MUST NOT
    be used by the scheduler to publish OUTPUT. For integration validation only.
    """
    if type(state) is not OwnedRootCoreHandoffStateV0:
        raise TypeError('invalid root Core handoff state')
    state.__post_init__()
    if type(image) is not VersionedNeuronImageV0:
        raise TypeError('invalid neuron image')
    if (image.network != state.shared.dynamic.transit.registry.allocation_ledger.network
            or image.epoch_id != state.shared.seal.epoch_id):
        raise ValueError('root Core image/network or epoch mismatch')
    if type(consume_request_id) is not int or consume_request_id < 0:
        raise ValueError('invalid consume request ID')
    witnesses = {x.consume_request_id: x for x in state.witnesses}
    witness = witnesses.get(consume_request_id)
    if witness is None:
        raise ValueError('cannot preview Core without physical EVENT consumption witness')
    return prepare_core_transition_v0(
        image.network, image, node_id=witness.node_id,
        timestamp=witness.event_time, channels=witness.channels,
    )
