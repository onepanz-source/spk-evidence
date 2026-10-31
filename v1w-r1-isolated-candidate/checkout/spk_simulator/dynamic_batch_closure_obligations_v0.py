"""SPK S3.7d/3b2b2k/13: necessary, NOT sufficient, batch closure obligations.

This is a *read-only* structural proof-obligation analyzer. A claimed event-time
frontier is not a certificate. This module NEVER authorizes BATCH_CONSUME.
"""
from dataclasses import dataclass

from spk_architecture.profile_v0 import ArchitectureProfileV0
from spk_network.model_v0 import NetworkV0
from spk_simulator.event_storage_v0 import RoutedStorageStateV0
from spk_simulator.owned_dynamic_service_registration_v0 import (
    OwnedDynamicServiceRegistrationStateV0,
)
from spk_simulator.dynamic_destination_inventory_v0 import (
    derive_dynamic_destination_inventory_v0,
)


@dataclass(frozen=True, slots=True)
class EventTimeClaimV0:
    """A non-authoritative claim: event times <= settled_through cannot recur.

    `kind` is SOURCE_EMISSION or EXTERNAL_INGRESS. An authoritative single-owner
    scheduler is still required to establish these claims from its own state.
    """
    kind: str
    node_id: str
    settled_through: int

    def __post_init__(self):
        if self.kind not in ('SOURCE_EMISSION', 'EXTERNAL_INGRESS'):
            raise ValueError('invalid frontier claim kind')
        if type(self.node_id) is not str or not self.node_id or self.node_id.strip() != self.node_id:
            raise ValueError('invalid frontier claim node')
        if type(self.settled_through) is not int or self.settled_through < -1:
            raise ValueError('invalid frontier claim time')


@dataclass(frozen=True, slots=True)
class InboundEdgeClosureObligationV0:
    edge_index: int
    source_node_id: str
    source_channel: int
    target_channel: int
    delay_ticks: int
    # A source may still generate an emission at e = target_event_time-delay.
    # Negative values are vacuous because EVENT_TIME is nonnegative.
    required_source_settled_through: int
    claimed_source_settled_through: int | None
    claim_covers_requirement: bool


@dataclass(frozen=True, slots=True)
class DestinationClosureObligationsV0:
    epoch_id: str
    target_node_id: str
    target_pe_id: str
    event_time: int
    edge_obligations: tuple[InboundEdgeClosureObligationV0, ...]
    required_external_settled_through: int
    claimed_external_settled_through: int | None
    route_request_ids: tuple[int, ...]
    resident_route_request_ids: tuple[int, ...]
    blocking_route_request_ids: tuple[int, ...]
    already_consumed_route_request_ids: tuple[int, ...]
    source_requirements_claimed: bool
    ingress_requirement_claimed: bool
    all_registered_routes_resident: bool
    # Even when True, these are merely caller-supplied frontier *claims*.
    declared_preconditions_met: bool
    status: str = 'OPEN_UNPROVEN'
    supports_consume_admission: bool = False


@dataclass(frozen=True, slots=True)
class DynamicBatchClosureAnalysisV0:
    profile_id: str
    epoch_id: str
    batches: tuple[DestinationClosureObligationsV0, ...]
    supports_consume_admission: bool = False


def analyze_dynamic_batch_closure_v0(
    architecture: ArchitectureProfileV0,
    registry: OwnedDynamicServiceRegistrationStateV0,
    storage: RoutedStorageStateV0,
    *,
    frontier_claims: tuple[EventTimeClaimV0, ...] = (),
) -> DynamicBatchClosureAnalysisV0:
    """Analyze causal obstacles WITHOUT minting a closure or consume certificate.

    For a destination event at t and an incoming edge of delay d, an
    authentic SOURCE_EMISSION watermark >= t-d would exclude any *new*
    route along that edge delivering at t. EXTERNAL_INGRESS separately needs
    an authentic per-destination watermark >= t. Here watermarks are only
    *claims*: no ownership, liveness, or admission evidence is established.
    """
    if type(architecture) is not ArchitectureProfileV0:
        raise TypeError('invalid architecture')
    if type(registry) is not OwnedDynamicServiceRegistrationStateV0:
        raise TypeError('invalid registration')
    if type(storage) is not RoutedStorageStateV0:
        raise TypeError('invalid storage')
    if type(frontier_claims) is not tuple or any(type(c) is not EventTimeClaimV0 for c in frontier_claims):
        raise TypeError('invalid frontier claims')
    # Re-derive rather than trusting an inventory supplied by the caller.
    inventory = derive_dynamic_destination_inventory_v0(architecture, registry, storage)
    network = registry.allocation_ledger.network
    if type(network) is not NetworkV0:
        raise TypeError('invalid frozen network')
    node_ids = {n.node_id for n in network.nodes}
    if len(node_ids) != len(network.nodes):
        raise ValueError('duplicate network node ID')
    # Do not assume a mocked or externally constructed NetworkV0 validated its edges.
    for edge in network.edges:
        if (edge.source_node not in node_ids or edge.target_node not in node_ids or
                type(edge.delay_ticks) is not int or edge.delay_ticks < 1):
            raise ValueError('invalid incoming topology edge')
        if (type(edge.source_channel) is not int or edge.source_channel < 0 or
                type(edge.target_channel) is not int or edge.target_channel < 0):
            raise ValueError('invalid topology channel')
    claims = {}
    for claim in frontier_claims:
        key = (claim.kind, claim.node_id)
        if claim.node_id not in node_ids:
            raise ValueError('unknown frontier claim node')
        if key in claims:
            raise ValueError('duplicate frontier claim')
        claims[key] = claim.settled_through

    batches = []
    for candidate in inventory.batches:
        t = candidate.event_time
        obligations = []
        for index, edge in enumerate(network.edges):
            if edge.target_node != candidate.target_node_id:
                continue
            threshold = t - edge.delay_ticks
            claimed = claims.get(('SOURCE_EMISSION', edge.source_node))
            # EVENT_TIME never negative; future emitters cannot emit at negative times.
            covered = threshold < 0 or (claimed is not None and claimed >= threshold)
            obligations.append(InboundEdgeClosureObligationV0(
                index, edge.source_node, edge.source_channel, edge.target_channel,
                edge.delay_ticks, threshold, claimed, covered,
            ))
        ext = claims.get(('EXTERNAL_INGRESS', candidate.target_node_id))
        route_ids = tuple(x.route_request_id for x in candidate.routes)
        resident_ids = tuple(x.route_request_id for x in candidate.routes if x.stage == 'EVENT')
        pending_ids = tuple(x.route_request_id for x in candidate.routes if x.stage in ('STAGED', 'OUTPUT'))
        consumed_ids = tuple(x.route_request_id for x in candidate.routes if x.stage == 'CONSUMED')
        if any(x.stage not in ('STAGED', 'OUTPUT', 'EVENT', 'CONSUMED') for x in candidate.routes):
            raise ValueError('unknown routed storage stage')
        all_resident = len(resident_ids) == len(route_ids)
        sources_cover = all(x.claim_covers_requirement for x in obligations)
        ingress_cover = ext is not None and ext >= t
        # Historical consumptions cannot be readmitted as a fresh batch.
        declared = sources_cover and ingress_cover and all_resident and not consumed_ids
        batches.append(DestinationClosureObligationsV0(
            candidate.epoch_id, candidate.target_node_id, candidate.target_pe_id,
            t, tuple(obligations), t, ext, route_ids, resident_ids, pending_ids,
            consumed_ids, sources_cover, ingress_cover, all_resident, declared,
        ))
    return DynamicBatchClosureAnalysisV0(
        inventory.profile_id, inventory.epoch_id, tuple(batches),
    )
