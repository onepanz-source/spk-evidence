"""SPK S3.7d/3b2b0: admission for atomic source emission bundles.

An EMISSION_RECORD is one indivisible logical production boundary in v0.
Its observed ROUTE_ENQUEUE occurrences are offered together by the boundary
controller. Without a streaming-emission cursor, a bundle that exceeds the
source PE's finite OUTPUT storage cannot be made schedulable by waiting.

This module classifies this *policy-specific* impossibility. It neither
schedules services nor claims that all admissible bundles can run.
"""
from dataclasses import dataclass

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_simulator.logical_access_v0 import LogicalAccessPlanV0
from spk_simulator.routing_binding_v0 import RoutedBindingManifestV0


class AtomicEmissionCapacityV0(RuntimeError):
    code = 'ATOMIC_EMISSION_FANOUT_EXCEEDS_OUTPUT'

    def __init__(self, emission_request_id: int, pe_id: str, required: int, capacity: int):
        self.emission_request_id = emission_request_id
        self.pe_id = pe_id
        self.required = required
        self.capacity = capacity
        super().__init__(
            f'{self.code}: emission={emission_request_id}, PE={pe_id}, '
            f'required={required}, output_slots={capacity}'
        )


@dataclass(frozen=True, slots=True)
class AtomicEmissionGroupV0:
    emission_request_id: int
    source_pe_id: str
    source_node_id: str
    emission_event_time: int
    route_request_ids: tuple[int, ...]
    required_output_slots: int
    output_capacity: int


@dataclass(frozen=True, slots=True)
class AtomicEmissionAdmissionV0:
    profile_id: str
    epoch_id: str
    groups: tuple[AtomicEmissionGroupV0, ...]
    routed_occurrence_count: int
    zero_fanout_emission_count: int


def admit_atomic_emissions_v0(
    architecture: ArchitectureProfileV0,
    manifest: RoutedBindingManifestV0,
    plan: LogicalAccessPlanV0,
    requests: tuple[MemoryServiceRequestV0, ...],
) -> AtomicEmissionAdmissionV0:
    """Check complete observed fan-out against the atomic-emission v0 policy.

    Fail closed for missing/mismatched routing provenance, emission mapping,
    service requests, or intrinsically unpublishable *atomic* fan-out. PE
    runtime occupancy, ingress, dependency readiness, and deadlock are not
    proved here. Nothing in Network v0 is mutated or reinterpreted.
    """
    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError('invalid architecture')
    if type(manifest) is not RoutedBindingManifestV0:
        raise TypeError('invalid binding manifest')
    if type(plan) is not LogicalAccessPlanV0:
        raise TypeError('invalid logical access plan')
    if type(requests) is not tuple or any(type(req) is not MemoryServiceRequestV0 for req in requests):
        raise TypeError('invalid memory requests')
    if architecture.profile_id != manifest.profile_id or plan.epoch_id != manifest.epoch_id:
        raise ValueError('profile or epoch mismatch')
    pes = {pe.pe_id: pe for pe in architecture.pes}
    refs = {ref.intent.request_id: ref for ref in plan.references}
    reqs = {req.request_id: req for req in requests}
    if (len(refs) != len(plan.references) or len(reqs) != len(requests)
            or set(refs) != set(reqs)):
        raise ValueError('request/reference coverage mismatch')
    for rid, ref in refs.items():
        req = reqs[rid]
        intent = ref.intent
        if (req.kind is not intent.kind or req.activity is not intent.activity
                or req.requester_pe_id != intent.pe_id
                or req.event_time != intent.event_time
                or req.epoch_id != plan.epoch_id
                or intent.epoch_id != plan.epoch_id
                or req.target_id != ref.target_id):
            raise ValueError('request/reference identity mismatch')

    emit = {}
    for ref in plan.references:
        intent = ref.intent
        if intent.kind is Kind.EMISSION_RECORD:
            key = (intent.node_id, intent.event_time)
            if key in emit:
                raise ValueError('duplicate emission record')
            if intent.pe_id not in pes:
                raise ValueError('emission from unknown PE')
            emit[key] = ref

    route_ids = {route.route_request_id for route in manifest.routes}
    declared = {ref.intent.request_id for ref in plan.references
                if ref.intent.kind is Kind.ROUTE_ENQUEUE}
    if route_ids != declared:
        raise ValueError('routing manifest / plan coverage mismatch')
    by_emission = {key: [] for key in emit}
    for route in manifest.routes:
        oc = route.occurrence
        key = (oc.source_node_id, oc.emission_event_time)
        source = emit.get(key)
        route_ref = refs.get(route.route_request_id)
        consume_ref = refs.get(route.consume_request_id)
        if (source is None or route_ref is None or consume_ref is None
                or source.intent.pe_id != oc.source_pe_id
                or route_ref.intent.kind is not Kind.ROUTE_ENQUEUE
                or route_ref.intent.pe_id != oc.source_pe_id
                or route_ref.intent.node_id != oc.target_node_id
                or route_ref.intent.event_time != oc.emission_event_time
                or consume_ref.intent.kind is not Kind.BATCH_CONSUME
                or consume_ref.intent.node_id != oc.target_node_id
                or consume_ref.intent.pe_id != oc.target_pe_id
                or consume_ref.intent.event_time != oc.delivery_event_time
                or reqs[route.route_request_id].target_pe_id != oc.target_pe_id):
            raise ValueError('inconsistent route emission/consumption identity')
        by_emission[key].append(route.route_request_id)

    groups = []
    for key, ref in sorted(emit.items(), key=lambda kv: kv[1].intent.request_id):
        intent = ref.intent
        route_ids_for_emission = tuple(sorted(by_emission[key]))
        required = len(route_ids_for_emission)
        capacity = pes[intent.pe_id].output_slots
        if required > capacity:
            raise AtomicEmissionCapacityV0(intent.request_id, intent.pe_id, required, capacity)
        groups.append(AtomicEmissionGroupV0(
            intent.request_id, intent.pe_id, intent.node_id, intent.event_time,
            route_ids_for_emission, required, capacity,
        ))

    return AtomicEmissionAdmissionV0(
        manifest.profile_id, manifest.epoch_id, tuple(groups),
        len(manifest.routes), sum(not x.route_request_ids for x in groups),
    )
