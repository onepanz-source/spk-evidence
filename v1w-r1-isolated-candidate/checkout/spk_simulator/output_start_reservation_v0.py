"""SPK S3.7d/3b2b2g: finite OUTPUT reservations before emission service.

Pure serialized admission. Not yet a scheduler, hardware lock, or attestation of
past execution. Reservation identities are metadata, not extra spike storage.
"""
from dataclasses import dataclass, replace

from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_simulator.atomic_emission_admission_v0 import AtomicEmissionAdmissionV0
from spk_simulator.event_storage_v0 import RoutedStorageStateV0, routed_storage_usage_v0


def _canonical_ids(label, ids):
    if (type(ids) is not tuple or any(type(x) is not int or x < 0 for x in ids)
            or ids != tuple(sorted(set(ids)))):
        raise ValueError(f'noncanonical {label}')


@dataclass(frozen=True, slots=True)
class OutputStartReservationV0:
    emission_request_id: int
    source_pe_id: str
    slots: int

    def __post_init__(self):
        if type(self.emission_request_id) is not int or self.emission_request_id < 0:
            raise ValueError('invalid emission request ID')
        if type(self.source_pe_id) is not str or not self.source_pe_id:
            raise ValueError('invalid source PE')
        if type(self.slots) is not int or self.slots < 0:
            raise ValueError('invalid reservation size')


@dataclass(frozen=True, slots=True)
class OutputStartLedgerV0:
    profile_id: str
    epoch_id: str
    active: tuple[OutputStartReservationV0, ...] = ()
    completed_emission_ids: tuple[int, ...] = ()

    def __post_init__(self):
        if type(self.profile_id) is not str or not self.profile_id:
            raise ValueError('invalid profile')
        if type(self.epoch_id) is not str or not self.epoch_id:
            raise ValueError('invalid epoch')
        if type(self.active) is not tuple or any(type(x) is not OutputStartReservationV0 for x in self.active):
            raise TypeError('invalid active reservation tuple')
        active_ids = tuple(x.emission_request_id for x in self.active)
        _canonical_ids('active emission reservations', active_ids)
        _canonical_ids('completed emissions', self.completed_emission_ids)
        if set(active_ids) & set(self.completed_emission_ids):
            raise ValueError('emission active and completed')


@dataclass(frozen=True, slots=True)
class OutputStartUsageV0:
    pe_id: str
    capacity: int
    occupied: int
    reserved: int
    free: int


@dataclass(frozen=True, slots=True)
class OutputStartDecisionV0:
    ledger: OutputStartLedgerV0
    granted_emission_ids: tuple[int, ...]
    blocked_emission_ids: tuple[int, ...]


def _validate(arch, admission, storage, ledger):
    if type(arch) is not ArchitectureProfileV0:
        raise TypeError('invalid architecture')
    if type(admission) is not AtomicEmissionAdmissionV0:
        raise TypeError('invalid atomic emission admission')
    if type(storage) is not RoutedStorageStateV0:
        raise TypeError('invalid storage')
    if type(ledger) is not OutputStartLedgerV0:
        raise TypeError('invalid OUTPUT start ledger')
    if not (arch.profile_id == admission.profile_id == storage.profile_id == ledger.profile_id):
        raise ValueError('profile mismatch')
    if not (admission.epoch_id == storage.epoch_id == ledger.epoch_id):
        raise ValueError('epoch mismatch')
    pes = {pe.pe_id: pe for pe in arch.pes}
    groups = {g.emission_request_id: g for g in admission.groups}
    if len(groups) != len(admission.groups):
        raise ValueError('duplicate emission group')
    expected_routes = set()
    for group in admission.groups:
        if (group.source_pe_id not in pes or
                group.output_capacity != pes[group.source_pe_id].output_slots or
                group.required_output_slots != len(group.route_request_ids) or
                group.required_output_slots > group.output_capacity or
                group.route_request_ids != tuple(sorted(set(group.route_request_ids))) or
                expected_routes.intersection(group.route_request_ids)):
            raise ValueError('invalid emission group/capacity/route identity')
        expected_routes.update(group.route_request_ids)
    if len(expected_routes) != admission.routed_occurrence_count:
        raise ValueError('invalid route count in admission')
    if sum(not g.route_request_ids for g in admission.groups) != admission.zero_fanout_emission_count:
        raise ValueError('invalid zero-fanout count')
    active = {x.emission_request_id: x for x in ledger.active}
    for emission_id, entry in active.items():
        group = groups.get(emission_id)
        if group is None or entry.source_pe_id != group.source_pe_id or entry.slots != group.required_output_slots:
            raise ValueError('reservation/group mismatch')
    if set(ledger.completed_emission_ids) - groups.keys():
        raise ValueError('completed unknown emission')
    # All event identities from previously published atomic groups must remain
    # accounted, in OUTPUT, EVENT, or consumed identity tombstones.
    stored = {e.event_id for e in storage.pending_output + storage.admitted_events} | set(storage.consumed_ids)
    for emission_id in ledger.completed_emission_ids:
        if not set(groups[emission_id].route_request_ids) <= stored:
            raise ValueError('completed emission lacks routed occurrence evidence')
    for emission_id, entry in active.items():
        if set(groups[emission_id].route_request_ids) & stored:
            raise ValueError('active reservation already physically published')
    existing = {x.pe_id: x for x in routed_storage_usage_v0(arch, storage)}
    reserved = {pe: 0 for pe in pes}
    for entry in ledger.active:
        reserved[entry.source_pe_id] += entry.slots
    usage = []
    for pe_id in sorted(pes):
        occupied = existing[pe_id].pending_output
        capacity = pes[pe_id].output_slots
        if occupied + reserved[pe_id] > capacity:
            raise ValueError('OUTPUT reservations exceed capacity')
        usage.append(OutputStartUsageV0(pe_id, capacity, occupied, reserved[pe_id],
                                        capacity - occupied - reserved[pe_id]))
    return groups, tuple(usage)


def output_start_usage_v0(architecture, admission, storage, ledger):
    """Validate every current claim; return finite OUTPUT occupancy and grants."""
    return _validate(architecture, admission, storage, ledger)[1]


def reserve_output_starts_v0(architecture, admission, storage, ledger, ready_emission_ids):
    """Deterministically reserve complete bundles, or return explicit blocked IDs.

    No partial bundle. Reservations consume *capacity claims* during service;
    no routed spike is materialized by this function. Input order is immaterial.
    """
    groups, usage = _validate(architecture, admission, storage, ledger)
    if (type(ready_emission_ids) is not tuple or
            any(type(i) is not int or i < 0 for i in ready_emission_ids) or
            len(set(ready_emission_ids)) != len(ready_emission_ids)):
        raise ValueError('invalid ready emission IDs')
    ready = tuple(sorted(ready_emission_ids))
    if set(ready) - groups.keys():
        raise ValueError('unknown emission')
    replay = set(ready) & (
        {x.emission_request_id for x in ledger.active} | set(ledger.completed_emission_ids)
    )
    if replay:
        raise ValueError('emission already reserved or published')
    # A prior uncontrolled offer cannot become a legitimate first start grant.
    present = {e.event_id for e in storage.pending_output + storage.admitted_events} | set(storage.consumed_ids)
    for emission_id in ready:
        if set(groups[emission_id].route_request_ids) & present:
            raise ValueError('emission already partially or fully published')
    free = {x.pe_id: x.free for x in usage}
    active = list(ledger.active)
    granted, denied = [], []
    for emission_id in ready:
        group = groups[emission_id]
        if free[group.source_pe_id] < group.required_output_slots:
            denied.append(emission_id)
            continue
        free[group.source_pe_id] -= group.required_output_slots
        active.append(OutputStartReservationV0(emission_id, group.source_pe_id,
                                                group.required_output_slots))
        granted.append(emission_id)
    return OutputStartDecisionV0(
        replace(ledger, active=tuple(sorted(active, key=lambda x: x.emission_request_id))),
        tuple(granted), tuple(denied),
    )


def cancel_output_start_v0(architecture, admission, storage, ledger, emission_request_id):
    """Withdraw an uncompleted start grant without publishing any spike."""
    groups, _ = _validate(architecture, admission, storage, ledger)
    if type(emission_request_id) is not int or emission_request_id not in groups:
        raise ValueError('unknown emission')
    if emission_request_id not in {x.emission_request_id for x in ledger.active}:
        raise ValueError('emission has no active reservation')
    result = replace(ledger, active=tuple(x for x in ledger.active
                                          if x.emission_request_id != emission_request_id))
    _validate(architecture, admission, storage, result)
    return result


def confirm_output_publications_v0(architecture, admission, storage_before, storage_after,
                                   ledger, emission_request_ids):
    """Atomically settle a set of start grants after witnessed OUTPUT offers.

    *Does not* itself authenticate the caller's storage transition. The future
    single-owner scheduler must feed storage_after from the bounded controller
    and check the authenticated service-effect receipts. At this level we
    independently require that every grouped route identity appeared and
    that no new routed identity outside those groups was introduced.
    """
    _validate(architecture, admission, storage_before, ledger)
    groups = {x.emission_request_id: x for x in admission.groups}
    if (type(emission_request_ids) is not tuple or
            any(type(x) is not int or x < 0 for x in emission_request_ids) or
            len(emission_request_ids) != len(set(emission_request_ids))):
        raise ValueError('invalid confirmation IDs')
    ids = tuple(sorted(emission_request_ids))
    if not ids:
        if storage_before != storage_after:
            raise ValueError('unexpected storage change without emission confirmations')
        return ledger
    active = {x.emission_request_id for x in ledger.active}
    if set(ids) - active:
        raise ValueError('confirmation lacks start grant')
    allowed = set().union(*(set(groups[i].route_request_ids) for i in ids))
    before = {e.event_id for e in storage_before.pending_output + storage_before.admitted_events} | set(storage_before.consumed_ids)
    after = {e.event_id for e in storage_after.pending_output + storage_after.admitted_events} | set(storage_after.consumed_ids)
    if (after - before) != allowed:
        raise ValueError('publication identity mismatch or incomplete bundle')
    if before - after:
        raise ValueError('stored spike identity disappeared')
    # An atomic publication creates occupants in OUTPUT. Merely inserting an
    # identity in EVENT or a consumed tombstone is not an OFFER operation.
    new_pending = {e.event_id for e in storage_after.pending_output} - before
    if new_pending != allowed:
        raise ValueError('newly published routes must occupy OUTPUT')
    owner = {route: groups[eid].source_pe_id
             for eid in ids for route in groups[eid].route_request_ids}
    for occurrence in storage_after.pending_output:
        if occurrence.event_id in allowed and occurrence.source_pe_id != owner[occurrence.event_id]:
            raise ValueError('new OUTPUT occurrence has wrong source PE')
    # A post-transition snapshot may include route deliveries/consumptions
    # of existing occurrences at the same boundary. Only identities matter.
    result = replace(
        ledger,
        active=tuple(x for x in ledger.active if x.emission_request_id not in ids),
        completed_emission_ids=tuple(sorted(ledger.completed_emission_ids + ids)),
    )
    _validate(architecture, admission, storage_after, result)
    return result
