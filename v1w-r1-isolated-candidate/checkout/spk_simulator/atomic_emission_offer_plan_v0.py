"""SPK S3.7d/3b2b1: deterministic finite OUTPUT admission for atomic emissions.

A pure pre-service decision. The caller authenticates causal readiness and
remains responsible for driving the boundary controller and future retries.
"""
from dataclasses import dataclass

from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_simulator.atomic_emission_admission_v0 import AtomicEmissionAdmissionV0
from spk_simulator.backpressure_boundary_v0 import BackpressureBoundaryStateV0
from spk_simulator.event_reservation_v0 import event_reservation_usage_v0
from spk_simulator.event_storage_v0 import routed_storage_usage_v0
from spk_simulator.routing_binding_v0 import RoutedBindingManifestV0


@dataclass(frozen=True, slots=True)
class BlockedAtomicEmissionV0:
    emission_request_id: int
    source_pe_id: str
    required_output_slots: int
    free_output_slots: int


@dataclass(frozen=True, slots=True)
class AtomicEmissionOfferPlanV0:
    """Proposed all-or-nothing offers, not a completed emission or reservation."""
    admitted_emission_ids: tuple[int, ...]
    blocked: tuple[BlockedAtomicEmissionV0, ...]
    routed_offers: tuple[int, ...]
    pe_free_after: tuple[tuple[str, int], ...]


def plan_atomic_emission_offers_v0(
    architecture: ArchitectureProfileV0,
    manifest: RoutedBindingManifestV0,
    admission: AtomicEmissionAdmissionV0,
    state: BackpressureBoundaryStateV0,
    *,
    ready_emission_ids: tuple[int, ...] = (),
) -> AtomicEmissionOfferPlanV0:
    """Select indivisible output groups under finite per-PE OUTPUT capacity.

    IDs in ready_emission_ids MUST be supplied only after causal readiness is
    proved by the future scheduler. Waiting emissions remain uncompleted and
    retain their upstream dependency state, not unbounded OUTPUT occupants.
    No mutation, physical concurrency, deadlock inference or EVENT_TIME change.
    """
    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError('invalid architecture')
    if type(manifest) is not RoutedBindingManifestV0:
        raise TypeError('invalid manifest')
    if type(admission) is not AtomicEmissionAdmissionV0:
        raise TypeError('invalid atomic emission admission')
    if type(state) is not BackpressureBoundaryStateV0:
        raise TypeError('invalid boundary state')
    if (type(ready_emission_ids) is not tuple or
            any(type(i) is not int or i < 0 for i in ready_emission_ids) or
            len(ready_emission_ids) != len(set(ready_emission_ids))):
        raise ValueError('invalid ready emission identities')
    if not (architecture.profile_id == manifest.profile_id == admission.profile_id
            == state.storage.profile_id == state.ledger.profile_id
            == state.arbiter.profile_id):
        raise ValueError('profile mismatch')
    if not (manifest.epoch_id == admission.epoch_id == state.storage.epoch_id
            == state.ledger.epoch_id == state.arbiter.epoch_id):
        raise ValueError('epoch mismatch')

    # Reject internally corrupted state, unknown PE, or hidden over-allocation.
    event_reservation_usage_v0(architecture, state.storage, manifest, state.ledger)
    usage = {row.pe_id: row for row in routed_storage_usage_v0(
        architecture, state.storage,
    )}
    pes = {pe.pe_id: pe for pe in architecture.pes}
    grouped = {g.emission_request_id: g for g in admission.groups}
    if len(grouped) != len(admission.groups):
        raise ValueError('duplicate emission groups')
    routes = {r.route_request_id: r for r in manifest.routes}
    if admission.routed_occurrence_count != len(routes):
        raise ValueError('atomic emission route coverage mismatch')
    accounted = []
    seen_emissions = set()
    for group in admission.groups:
        if (group.source_pe_id not in pes or
                group.required_output_slots != len(group.route_request_ids) or
                group.output_capacity != pes[group.source_pe_id].output_slots or
                group.required_output_slots > group.output_capacity or
                group.route_request_ids != tuple(sorted(set(group.route_request_ids)))):
            raise ValueError('invalid atomic group capacity/identity')
        key = (group.source_node_id, group.emission_event_time)
        if key in seen_emissions:
            raise ValueError('duplicate logical emission group')
        seen_emissions.add(key)
        for rid in group.route_request_ids:
            route = routes.get(rid)
            if route is None or route.occurrence.source_pe_id != group.source_pe_id:
                raise ValueError('atomic group route mismatch')
            if (route.occurrence.source_node_id != group.source_node_id or
                    route.occurrence.emission_event_time != group.emission_event_time):
                raise ValueError('atomic group emission identity mismatch')
        accounted.extend(group.route_request_ids)
    if (tuple(sorted(accounted)) != tuple(sorted(routes)) or
            admission.routed_occurrence_count != len(routes) or
            admission.zero_fanout_emission_count != sum(
                not g.route_request_ids for g in admission.groups)):
        raise ValueError('atomic emission coverage mismatch')
    if set(ready_emission_ids) - set(grouped):
        raise ValueError('unknown ready emission')

    # Even a group admitted statically may be blocked by live OUTPUT occupancy.
    already = (set(e.event_id for e in state.storage.pending_output) |
               set(e.event_id for e in state.storage.admitted_events) |
               set(state.storage.consumed_ids))
    pending_ids = {ev.event_id for ev in state.storage.pending_output}
    if (set(state.arbiter.waiting_route_ids) - pending_ids or
            set(state.arbiter.waiting_route_ids) & set(state.ledger.reserved_routes)):
        raise ValueError('invalid waiting route ownership')
    free = {pe_id: row.output_capacity - row.pending_output
            for pe_id, row in usage.items()}
    accepted, blocked, offers = [], [], []
    for group_id in sorted(ready_emission_ids):
        group = grouped[group_id]
        if any(rid in already for rid in group.route_request_ids):
            raise ValueError('emission already published or partially published')
        pe_id = group.source_pe_id
        if group.required_output_slots > free[pe_id]:
            blocked.append(BlockedAtomicEmissionV0(
                group_id, pe_id, group.required_output_slots, free[pe_id],
            ))
            continue
        accepted.append(group_id)
        offers.extend(group.route_request_ids)
        free[pe_id] -= group.required_output_slots

    return AtomicEmissionOfferPlanV0(
        admitted_emission_ids=tuple(accepted),
        blocked=tuple(blocked),
        routed_offers=tuple(sorted(offers)),
        pe_free_after=tuple(sorted(free.items())),
    )
