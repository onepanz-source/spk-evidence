"""SPK Memory Access Authorization v0.

Default-deny architectural access policy.

Grants and contexts must be supplied by a trusted
machine controller, never constructed from requests.

No scheduling, priority or physical memory operations.
"""

from dataclasses import dataclass

from spk_architecture.access_v0 import (
    ActivityV0,
    AccessIntentKindV0 as Kind,
)
from spk_architecture.memory_target_v0 import (
    MemorySpaceV0 as Space,
    MemoryTargetCatalogV0,
    MemoryTargetReferenceV0,
    resolve_memory_target_v0,
)
from spk_compiler.pe_admission_v0 import (
    PEAdmissionManifestV0,
)


def _identifier(name, value):
    if (
        type(value) is not str
        or not value
        or value.strip() != value
    ):
        raise ValueError(f"invalid {name}")


def _epochs(name, values):
    if type(values) is not tuple:
        raise TypeError(f"{name} must be a tuple")
    for value in values:
        _identifier(name, value)
    if len(set(values)) != len(values):
        raise ValueError(f"duplicate {name}")


@dataclass(frozen=True, slots=True)
class AccessGrantV0:
    principal_id: str
    activity: ActivityV0
    pe_id: str
    node_id: str | None = None
    snapshot_epochs: tuple[str, ...] = ()
    candidate_epochs: tuple[str, ...] = ()

    def __post_init__(self):
        _identifier("principal_id", self.principal_id)
        _identifier("pe_id", self.pe_id)

        if type(self.activity) is not ActivityV0:
            raise TypeError("invalid grant activity")

        if self.node_id is not None:
            _identifier("node_id", self.node_id)

        if (
            self.activity is ActivityV0.EXECUTE
            and self.node_id is None
        ):
            raise ValueError(
                "EXECUTE grant requires a node"
            )

        _epochs("snapshot_epochs", self.snapshot_epochs)
        _epochs("candidate_epochs", self.candidate_epochs)


@dataclass(frozen=True, slots=True)
class AuthorizationPolicyV0:
    active_epoch_id: str
    snapshot_epochs: tuple[str, ...] = ()
    candidate_epochs: tuple[str, ...] = ()

    def __post_init__(self):
        _identifier("active_epoch_id", self.active_epoch_id)
        _epochs("snapshot_epochs", self.snapshot_epochs)
        _epochs("candidate_epochs", self.candidate_epochs)

        all_epochs = (
            (self.active_epoch_id,)
            + self.snapshot_epochs
            + self.candidate_epochs
        )
        if len(set(all_epochs)) != len(all_epochs):
            raise ValueError("overlapping epoch spaces")


@dataclass(frozen=True, slots=True)
class AuthorizationDecisionV0:
    allowed: bool
    reason: str


@dataclass(frozen=True, slots=True)
class AuthorizationContextV0:
    catalog: MemoryTargetCatalogV0
    placement: PEAdmissionManifestV0
    policy: AuthorizationPolicyV0
    grant: AccessGrantV0

    def __post_init__(self):
        if type(self.catalog) is not MemoryTargetCatalogV0:
            raise TypeError("invalid catalog")
        if type(self.placement) is not PEAdmissionManifestV0:
            raise TypeError("invalid placement")
        if type(self.policy) is not AuthorizationPolicyV0:
            raise TypeError("invalid policy")
        if type(self.grant) is not AccessGrantV0:
            raise TypeError("invalid grant")

        node_pe = {}
        pe_ids = set()

        for usage in self.placement.pe_usage:
            pe_ids.add(usage.pe_id)
            for node_id in usage.node_ids:
                if node_id in node_pe:
                    raise ValueError("duplicate placed node")
                node_pe[node_id] = usage.pe_id

        if self.grant.pe_id not in pe_ids:
            raise ValueError("grant references unknown PE")

        if self.grant.node_id is not None:
            if node_pe.get(self.grant.node_id) != self.grant.pe_id:
                raise ValueError("grant node/PE mismatch")

        for target in self.catalog.targets:
            if target.pe_id not in pe_ids:
                raise ValueError("target references unknown PE")

            if target.space is Space.ACTIVE:
                if target.epoch_id != self.policy.active_epoch_id:
                    raise ValueError("active target epoch mismatch")

                if target.owner_node_id is not None:
                    if (
                        node_pe.get(target.owner_node_id)
                        != target.pe_id
                    ):
                        raise ValueError(
                            "active target placement mismatch"
                        )


def authorize_access_v0(
    reference: MemoryTargetReferenceV0,
    context: AuthorizationContextV0,
) -> AuthorizationDecisionV0:
    """Return an explicit allow/deny decision.

    This authorizes a memory-domain access, not the
    semantic validity of a routed spike or operation.
    """

    if type(reference) is not MemoryTargetReferenceV0:
        raise TypeError("invalid reference")
    if type(context) is not AuthorizationContextV0:
        raise TypeError("invalid context")

    def deny(reason):
        return AuthorizationDecisionV0(False, reason)

    intent = reference.intent
    grant = context.grant
    policy = context.policy

    if intent.activity is not grant.activity:
        return deny("ACTIVITY_MISMATCH")
    if intent.pe_id != grant.pe_id:
        return deny("REQUESTER_PE_MISMATCH")

    try:
        target = resolve_memory_target_v0(
            context.catalog, reference
        )
    except KeyError:
        return deny("UNKNOWN_TARGET")
    except ValueError:
        return deny("DOMAIN_MISMATCH")

    active = (
        target.space is Space.ACTIVE
        and target.epoch_id == policy.active_epoch_id
        and intent.epoch_id == policy.active_epoch_id
    )

    if grant.activity is ActivityV0.EXECUTE:
        if intent.node_id != grant.node_id:
            return deny("NODE_OWNERSHIP")
        if not active:
            return deny("ACTIVE_EPOCH_REQUIRED")
        if target.pe_id != grant.pe_id:
            return deny("REMOTE_EXECUTION_ACCESS")
        if (
            target.owner_node_id is not None
            and target.owner_node_id != grant.node_id
        ):
            return deny("TARGET_OWNERSHIP")

        if intent.kind in (
            Kind.PROGRAM_REFERENCE,
            Kind.STATE_LOAD,
            Kind.STATE_COMMIT,
            Kind.BATCH_CONSUME,
            Kind.EMISSION_RECORD,
        ):
            return AuthorizationDecisionV0(
                True, "AUTHORIZED"
            )

    elif grant.activity is ActivityV0.ROUTER:
        if (
            active
            and intent.kind is Kind.ROUTE_ENQUEUE
        ):
            # node_id denotes the destination node.
            # Actual edge validity is not checked here.
            node_pe = {
                node: usage.pe_id
                for usage in context.placement.pe_usage
                for node in usage.node_ids
            }
            if node_pe.get(intent.node_id) != target.pe_id:
                return deny("DESTINATION_PLACEMENT")
            if (
                target.owner_node_id is not None
                and target.owner_node_id != intent.node_id
            ):
                return deny("TARGET_OWNERSHIP")
            return AuthorizationDecisionV0(
                True, "AUTHORIZED"
            )

    elif grant.activity is ActivityV0.OBSERVER:
        if (
            active
            and target.pe_id == grant.pe_id
            and intent.kind is Kind.OBSERVATION_RECORD
        ):
            return AuthorizationDecisionV0(
                True, "AUTHORIZED"
            )

    elif grant.activity is ActivityV0.LEARN:
        if (
            active
            and target.pe_id == grant.pe_id
            and intent.kind is Kind.OBSERVATION_READ
        ):
            return AuthorizationDecisionV0(
                True, "AUTHORIZED"
            )

    elif grant.activity is ActivityV0.VERIFY:
        if (
            intent.kind is Kind.SNAPSHOT_READ
            and target.space is Space.SNAPSHOT
            and intent.epoch_id == policy.active_epoch_id
            and target.epoch_id in policy.snapshot_epochs
            and target.epoch_id in grant.snapshot_epochs
        ):
            return AuthorizationDecisionV0(
                True, "AUTHORIZED"
            )

    elif grant.activity is ActivityV0.REMODEL:
        if (
            intent.kind is Kind.CANDIDATE_PROGRAM_WRITE
            and target.space is Space.CANDIDATE
            and intent.epoch_id == target.epoch_id
            and target.epoch_id in policy.candidate_epochs
            and target.epoch_id in grant.candidate_epochs
            and target.pe_id == grant.pe_id
        ):
            return AuthorizationDecisionV0(
                True, "AUTHORIZED"
            )

    return deny("POLICY_DENIED")
