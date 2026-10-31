"""SPK S3.7d/3b2b2k/12: inspect computed route destinations without closing batches.

All destination groupings are OPEN: currently admitted EVENT occupants alone do not
prove there can be no further arrival at the same neuronal EVENT_TIME.
No request activation, service completion, consumption or Core evaluation occurs.
"""
from dataclasses import dataclass

from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_simulator.event_storage_v0 import (
    RoutedOccurrenceV0, RoutedStorageStateV0, routed_storage_usage_v0,
)
from spk_simulator.owned_dynamic_service_registration_v0 import (
    OwnedDynamicServiceRegistrationStateV0,
)


@dataclass(frozen=True, slots=True)
class ComputedDestinationRouteStatusV0:
    route_request_id: int
    target_channel: int
    stage: str   # STAGED / OUTPUT / EVENT / CONSUMED


@dataclass(frozen=True, slots=True)
class OpenComputedDestinationBatchV0:
    epoch_id: str
    target_node_id: str
    target_pe_id: str
    event_time: int
    routes: tuple[ComputedDestinationRouteStatusV0, ...]
    resident_channels: tuple[int, ...]
    # Not a completion certificate; there may be unregistered future emitters.
    closure_status: str = 'OPEN_UNPROVEN'

    @property
    def resident_route_request_ids(self) -> tuple[int, ...]:
        return tuple(x.route_request_id for x in self.routes if x.stage == 'EVENT')


@dataclass(frozen=True, slots=True)
class ComputedDestinationInventoryV0:
    profile_id: str
    epoch_id: str
    batches: tuple[OpenComputedDestinationBatchV0, ...]
    untracked_static_storage_ids: tuple[int, ...]
    terminal_candidate_count: int
    # Meaning: this is not yet a scheduler-ready BATCH_CONSUME manifest.
    supports_consume_admission: bool = False


def derive_dynamic_destination_inventory_v0(
    architecture: ArchitectureProfileV0,
    registry: OwnedDynamicServiceRegistrationStateV0,
    storage: RoutedStorageStateV0,
) -> ComputedDestinationInventoryV0:
    """Reconcile identity and presence using *provided* routed storage state.

    The caller must obtain storage from the authoritative controller. A
    hand-constructed RoutedStorageStateV0 is NOT independently authenticated.
    The output is observational only and never closes a destination batch.
    """
    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError('invalid architecture')
    if type(registry) is not OwnedDynamicServiceRegistrationStateV0:
        raise TypeError('invalid computed registration')
    if type(storage) is not RoutedStorageStateV0:
        raise TypeError('invalid routed storage')
    if architecture != registry.architecture or architecture.profile_id != storage.profile_id:
        raise ValueError('architecture/registry/storage profile mismatch')
    if storage.epoch_id != registry.allocation_ledger.epoch_id:
        raise ValueError('storage/registration epoch mismatch')
    routed_storage_usage_v0(architecture, storage)  # includes finite PE capacity checks

    expected: dict[int, RoutedOccurrenceV0] = {}
    terminal_count = 0
    for record in registry.registrations:
        topology = record.allocation.topology
        terminal_count += len(topology.terminal_outputs)
        for route in topology.routes:
            occurrence = route.occurrence
            if occurrence.event_id in expected:
                raise ValueError('duplicate computed route identity')
            expected[occurrence.event_id] = occurrence
    start = registry.allocation_ledger.first_dynamic_request_id
    # The dynamic request namespace also includes EMISSION_RECORD IDs, which
    # must never be materialized as routed occurrence identities.
    physical: dict[int, str] = {}
    static_ids = []
    for stage, values in (
        ('OUTPUT', storage.pending_output),
        ('EVENT', storage.admitted_events),
    ):
        for occurrence in values:
            rid = occurrence.event_id
            if rid < start:
                static_ids.append(rid)
                continue
            if rid not in expected:
                raise ValueError('unknown dynamic storage identity')
            if occurrence != expected[rid]:
                raise ValueError('computed route provenance mismatch')
            if rid in physical:
                raise ValueError('route identity appears in multiple storage stages')
            physical[rid] = stage
    for rid in storage.consumed_ids:
        if rid < start:
            static_ids.append(rid)
            continue
        if rid not in expected:
            raise ValueError('unknown dynamic consumed route identity')
        if rid in physical:
            raise ValueError('consumed route also occupies physical storage')
        physical[rid] = 'CONSUMED'

    groups: dict[tuple[str, str, str, int], list[ComputedDestinationRouteStatusV0]] = {}
    for rid, occurrence in expected.items():
        key = (occurrence.epoch_id, occurrence.target_node_id,
               occurrence.target_pe_id, occurrence.delivery_event_time)
        groups.setdefault(key, []).append(ComputedDestinationRouteStatusV0(
            rid, occurrence.target_channel, physical.get(rid, 'STAGED'),
        ))
    batches = []
    for (epoch, node, pe, time), statuses in sorted(groups.items()):
        entries = tuple(sorted(statuses, key=lambda x: x.route_request_id))
        # Preserve multiplicity, including parallel edges to the same channel.
        channels = tuple(sorted(s.target_channel for s in entries if s.stage == 'EVENT'))
        batches.append(OpenComputedDestinationBatchV0(
            epoch, node, pe, time, entries, channels,
        ))
    return ComputedDestinationInventoryV0(
        storage.profile_id, storage.epoch_id, tuple(batches),
        tuple(sorted(static_ids)), terminal_count,
    )
