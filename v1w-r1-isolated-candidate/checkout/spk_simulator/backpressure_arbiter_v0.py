"""SPK S3.7d/3a: deterministic single-owner, finite-slot route arbitration.

Pure admission over output-owned, provenance-bound events. It is not a live
scheduler, external ingress buffer, hardware lock or deadlock detector.
"""
from dataclasses import dataclass

from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_simulator.event_reservation_v0 import (
    EventReservationStateV0, EventSlotUnavailableV0,
    event_reservation_usage_v0, reserve_routed_event_slot_v0,
)
from spk_simulator.event_storage_v0 import RoutedStorageStateV0
from spk_simulator.routing_binding_v0 import RoutedBindingManifestV0


@dataclass(frozen=True, slots=True)
class BackpressureArbiterStateV0:
    """Pending route IDs are metadata, NOT additional event storage."""
    profile_id: str
    epoch_id: str
    last_service_boundary: int | None = None
    waiting_route_ids: tuple[int, ...] = ()

    def __post_init__(self):
        for name in ('profile_id', 'epoch_id'):
            val = getattr(self, name)
            if type(val) is not str or not val or val.strip() != val:
                raise ValueError(f'invalid {name}')
        if (self.last_service_boundary is not None and
                (type(self.last_service_boundary) is not int or
                 self.last_service_boundary < 0)):
            raise ValueError('invalid last SERVICE_TIME boundary')
        if (type(self.waiting_route_ids) is not tuple or
                any(type(rid) is not int or rid < 0 for rid in self.waiting_route_ids) or
                len(set(self.waiting_route_ids)) != len(self.waiting_route_ids)):
            raise ValueError('invalid waiting route IDs')
        if self.last_service_boundary is None and self.waiting_route_ids:
            raise ValueError('initial state cannot contain waiting routes')


@dataclass(frozen=True, slots=True)
class BackpressureDenialV0:
    route_request_id: int
    target_pe_id: str
    claimed: int
    capacity: int
    service_boundary: int


@dataclass(frozen=True, slots=True)
class BackpressureArbitrationResultV0:
    state: BackpressureArbiterStateV0
    ledger: EventReservationStateV0
    granted_route_ids: tuple[int, ...]
    denied: tuple[BackpressureDenialV0, ...]
    """Caller-owned storage is unchanged; denied events remain in source OUTPUT."""


def arbitrate_routed_reservations_v0(
    architecture: ArchitectureProfileV0,
    manifest: RoutedBindingManifestV0,
    storage: RoutedStorageStateV0,
    ledger: EventReservationStateV0,
    state: BackpressureArbiterStateV0,
    *,
    service_boundary: int,
    newly_ready_route_ids: tuple[int, ...] = (),
) -> BackpressureArbitrationResultV0:
    """Reserve as many route slots as possible, retaining all denied outputs.

    A single caller owns the ledger; old waiters precede new requests, and
    simultaneous new requests are ordered by request ID. Different PEs can
    advance independently. No retries occur unless the caller invokes another
    boundary; blocked event payloads remain in source output_slots.
    """
    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError('invalid architecture')
    if type(manifest) is not RoutedBindingManifestV0:
        raise TypeError('invalid routing binding')
    if type(storage) is not RoutedStorageStateV0:
        raise TypeError('invalid storage')
    if type(ledger) is not EventReservationStateV0:
        raise TypeError('invalid reservation ledger')
    if type(state) is not BackpressureArbiterStateV0:
        raise TypeError('invalid arbiter state')
    if type(service_boundary) is not int or service_boundary < 0:
        raise ValueError('invalid SERVICE_TIME boundary')
    if (state.last_service_boundary is not None and
            service_boundary <= state.last_service_boundary):
        raise ValueError('arbiter boundaries must be strictly increasing')
    if (architecture.profile_id != state.profile_id or
            manifest.profile_id != state.profile_id or
            storage.profile_id != state.profile_id or
            ledger.profile_id != state.profile_id or
            manifest.epoch_id != state.epoch_id or
            storage.epoch_id != state.epoch_id or
            ledger.epoch_id != state.epoch_id):
        raise ValueError('profile or epoch mismatch')
    if (type(newly_ready_route_ids) is not tuple or
            any(type(rid) is not int or rid < 0 for rid in newly_ready_route_ids) or
            len(set(newly_ready_route_ids)) != len(newly_ready_route_ids)):
        raise ValueError('invalid newly ready routes')
    if set(newly_ready_route_ids) & set(state.waiting_route_ids):
        raise ValueError('previous waiter supplied as newly ready')

    # Validate the complete input snapshot first, including capacity claims.
    event_reservation_usage_v0(architecture, storage, manifest, ledger)
    all_route_ids = {route.route_request_id for route in manifest.routes}
    eligible = state.waiting_route_ids + tuple(sorted(newly_ready_route_ids))
    held = {ev.event_id for ev in storage.pending_output}
    for rid in eligible:
        if rid not in all_route_ids:
            raise ValueError('unknown route request identity')
        if rid not in held:
            raise ValueError('arbitration requires retained source output')
        if rid in ledger.reserved_routes:
            raise ValueError('route is already reserved')

    next_ledger = ledger
    granted = []
    denied = []
    waiting = []
    for rid in eligible:
        try:
            next_ledger = reserve_routed_event_slot_v0(
                architecture, storage, manifest, next_ledger, rid,
            )
        except EventSlotUnavailableV0 as exc:
            denied.append(BackpressureDenialV0(
                rid, exc.pe_id, exc.occupied, exc.capacity, service_boundary,
            ))
            waiting.append(rid)
        else:
            granted.append(rid)

    return BackpressureArbitrationResultV0(
        state=BackpressureArbiterStateV0(
            state.profile_id, state.epoch_id, service_boundary, tuple(waiting),
        ),
        ledger=next_ledger,
        granted_route_ids=tuple(granted),
        denied=tuple(denied),
    )
