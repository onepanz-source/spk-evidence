"""SPK S3.7d/1: bounded, pure event-slot reservation transitions.

Pre-scheduler admission primitive, NOT a live causal scheduler. The caller must
supply authoritative upstream route and ingress bindings and must enforce
SERVICE_TIME readiness. No unbounded external buffering is implied.
"""
from dataclasses import dataclass, replace

from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_simulator.event_storage_v0 import (
    RoutedStorageStateV0, routed_storage_usage_v0,
)
from spk_simulator.external_ingress_v0 import (
    ExternalIngressBindingV0, BoundExternalArrivalV0,
)
from spk_simulator.routing_binding_v0 import (
    RoutedBindingManifestV0, admit_bound_routed_event_v0,
    consume_bound_routed_event_v0,
)


class EventSlotUnavailableV0(RuntimeError):
    """Capacity denial. Immutable input states remain unchanged."""

    code = "EVENT_SLOT_UNAVAILABLE"

    def __init__(self, pe_id: str, occupied: int, capacity: int):
        self.pe_id = pe_id
        self.occupied = occupied
        self.capacity = capacity
        super().__init__(
            f"event slots exhausted on {pe_id}: claimed={occupied}, capacity={capacity}"
        )


@dataclass(frozen=True, slots=True)
class EventReservationStateV0:
    """Event-slot claims and external residency, scoped to a single epoch.

    All tuples contain distinct occurrence IDs. External identities are
    indices into the upstream ExternalIngressBindingV0, not spike payloads.
    Neither a reservation nor an external arrival mutates EVENT_TIME.
    """

    profile_id: str
    epoch_id: str
    ingress: ExternalIngressBindingV0
    reserved_routes: tuple[int, ...] = ()
    external_resident: tuple[int, ...] = ()
    external_consumed: tuple[int, ...] = ()

    def __post_init__(self):
        for field in ('profile_id', 'epoch_id'):
            val = getattr(self, field)
            if type(val) is not str or not val or val.strip() != val:
                raise ValueError(f'invalid {field}')
        if type(self.ingress) is not ExternalIngressBindingV0:
            raise TypeError('invalid external ingress binding')
        for field in ('reserved_routes', 'external_resident', 'external_consumed'):
            items = getattr(self, field)
            if type(items) is not tuple or any(type(i) is not int or i < 0 for i in items):
                raise TypeError(f'invalid {field}')
            if items != tuple(sorted(set(items))):
                raise ValueError(f'noncanonical {field}')
        if set(self.external_resident) & set(self.external_consumed):
            raise ValueError('external event simultaneously resident and consumed')


@dataclass(frozen=True, slots=True)
class PEEventReservationUsageV0:
    pe_id: str
    capacity: int
    external_resident: int
    routed_admitted: int
    reserved: int
    claimed: int
    free: int


def _bound(architecture, storage, manifest, ledger):
    """Validate the complete immutable snapshot against its bindings."""
    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError('invalid architecture')
    if type(storage) is not RoutedStorageStateV0:
        raise TypeError('invalid routed storage')
    if type(manifest) is not RoutedBindingManifestV0:
        raise TypeError('invalid routing manifest')
    if type(ledger) is not EventReservationStateV0:
        raise TypeError('invalid reservation state')
    if not (
        architecture.profile_id == storage.profile_id == manifest.profile_id
        == ledger.profile_id
        and storage.epoch_id == manifest.epoch_id == ledger.epoch_id
    ):
        raise ValueError('profile or epoch mismatch')

    pes = {p.pe_id: p for p in architecture.pes}
    if len(pes) != len(architecture.pes):
        raise ValueError('duplicate PE')
    # This also checks architectural output and routed event capacity.
    routed_storage_usage_v0(architecture, storage)

    expected = {route.route_request_id: route.occurrence for route in manifest.routes}
    for event in storage.pending_output + storage.admitted_events:
        if expected.get(event.event_id) != event:
            raise ValueError('unbound stored routed occurrence')
    if any(event_id not in expected for event_id in storage.consumed_ids):
        raise ValueError('unbound consumed route')

    pending = {event.event_id for event in storage.pending_output}
    reserved = {pe_id: 0 for pe_id in pes}
    for route_id in ledger.reserved_routes:
        route = expected.get(route_id)
        if route is None or route_id not in pending:
            raise ValueError('reservation without pending event')
        reserved[route.target_pe_id] += 1

    ext_by_id = {}
    for entry in ledger.ingress.arrivals:
        if type(entry) is not BoundExternalArrivalV0:
            raise TypeError('invalid external arrival entry')
        if (type(entry.input_index) is not int or entry.input_index < 0
                or entry.input_index in ext_by_id
                or entry.target_pe_id not in pes
                or type(entry.consume_request_id) is not int
                or entry.consume_request_id < 0
                or type(entry.arrival_boundary) is not int
                or entry.arrival_boundary < 0):
            raise ValueError('invalid external ingress identity')
        ext_by_id[entry.input_index] = entry
    if set(ext_by_id) != set(range(len(ext_by_id))):
        raise ValueError('noncanonical external indices')
    if (set(ledger.external_resident) | set(ledger.external_consumed)) - set(ext_by_id):
        raise ValueError('external occurrence not bound')

    actual = {pe_id: 0 for pe_id in pes}
    for event in storage.admitted_events:
        actual[event.target_pe_id] += 1
    external = {pe_id: 0 for pe_id in pes}
    for input_index in ledger.external_resident:
        external[ext_by_id[input_index].target_pe_id] += 1

    for pe_id, pe in pes.items():
        claims = actual[pe_id] + external[pe_id] + reserved[pe_id]
        if claims > pe.event_slots:
            raise ValueError('existing event claims exceed PE capacity')
    return pes, expected, ext_by_id, actual, external, reserved


def event_reservation_usage_v0(architecture, storage, manifest, ledger):
    pes, _, _, actual, external, reserved = _bound(
        architecture, storage, manifest, ledger,
    )
    return tuple(
        PEEventReservationUsageV0(
            pe_id, pe.event_slots, external[pe_id], actual[pe_id],
            reserved[pe_id], actual[pe_id] + external[pe_id] + reserved[pe_id],
            pe.event_slots - actual[pe_id] - external[pe_id] - reserved[pe_id],
        )
        for pe_id, pe in sorted(pes.items())
    )


def _claim(pe_id, pes, actual, external, reserved):
    claimed = actual[pe_id] + external[pe_id] + reserved[pe_id]
    if claimed >= pes[pe_id].event_slots:
        raise EventSlotUnavailableV0(pe_id, claimed, pes[pe_id].event_slots)


def reserve_routed_event_slot_v0(architecture, storage, manifest, ledger, route_id):
    pes, expected, _, actual, external, reserved = _bound(
        architecture, storage, manifest, ledger,
    )
    if type(route_id) is not int or route_id < 0:
        raise ValueError('invalid route identity')
    if route_id not in expected:
        raise ValueError('unknown routed occurrence')
    if route_id in ledger.reserved_routes:
        raise ValueError('duplicate route reservation')
    if not any(ev.event_id == route_id for ev in storage.pending_output):
        raise ValueError('route has no retained source output')
    target = expected[route_id].target_pe_id
    _claim(target, pes, actual, external, reserved)
    return replace(ledger, reserved_routes=tuple(sorted((*ledger.reserved_routes, route_id))))


def cancel_routed_event_slot_v0(architecture, storage, manifest, ledger, route_id):
    _bound(architecture, storage, manifest, ledger)
    if type(route_id) is not int or route_id not in ledger.reserved_routes:
        raise ValueError('no matching route reservation')
    # The event remains pending in its source PE; only the slot claim is freed.
    return replace(ledger, reserved_routes=tuple(i for i in ledger.reserved_routes if i != route_id))


def commit_routed_event_slot_v0(architecture, storage, manifest, ledger, route_id):
    _bound(architecture, storage, manifest, ledger)
    if type(route_id) is not int or route_id not in ledger.reserved_routes:
        raise ValueError('route delivery requires a reservation')
    # Pure atomic transaction: claimed free slot becomes a resident routed slot.
    # Source output is released by the existing provenance-bound transition.
    next_storage = admit_bound_routed_event_v0(
        architecture, storage, manifest, route_id,
    )
    next_ledger = replace(
        ledger, reserved_routes=tuple(i for i in ledger.reserved_routes if i != route_id),
    )
    _bound(architecture, next_storage, manifest, next_ledger)
    return next_storage, next_ledger


def arrive_external_event_slot_v0(architecture, storage, manifest, ledger, input_index):
    pes, _, ext_by_id, actual, external, reserved = _bound(
        architecture, storage, manifest, ledger,
    )
    if type(input_index) is not int or input_index not in ext_by_id:
        raise ValueError('unknown external occurrence')
    if input_index in ledger.external_resident or input_index in ledger.external_consumed:
        raise ValueError('external occurrence already accounted for')
    target = ext_by_id[input_index].target_pe_id
    _claim(target, pes, actual, external, reserved)
    return replace(
        ledger, external_resident=tuple(sorted((*ledger.external_resident, input_index))),
    )


def consume_external_event_slot_v0(
    architecture, storage, manifest, ledger, input_index, *, consume_request_id,
):
    _, _, ext_by_id, _, _, _ = _bound(architecture, storage, manifest, ledger)
    if type(input_index) is not int or input_index not in ledger.external_resident:
        raise ValueError('external event not resident')
    if (type(consume_request_id) is not int
            or consume_request_id != ext_by_id[input_index].consume_request_id):
        raise ValueError('wrong external consuming request')
    return replace(
        ledger,
        external_resident=tuple(i for i in ledger.external_resident if i != input_index),
        external_consumed=tuple(sorted((*ledger.external_consumed, input_index))),
    )


def consume_reserved_routed_event_v0(
    architecture, storage, manifest, ledger, route_id, *, consume_request_id,
):
    _bound(architecture, storage, manifest, ledger)
    if type(route_id) is not int or route_id in ledger.reserved_routes:
        raise ValueError('routed event still reserved or invalid')
    next_storage = consume_bound_routed_event_v0(
        architecture, storage, manifest, route_id,
        consume_request_id=consume_request_id,
    )
    _bound(architecture, next_storage, manifest, ledger)
    return next_storage
