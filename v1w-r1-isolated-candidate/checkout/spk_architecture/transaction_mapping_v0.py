"""SPK architectural transaction mapping v0.

Convert authorized logical intents into abstract
memory service requests, without scheduling them.
"""

from dataclasses import dataclass

from spk_architecture.access_v0 import (
    ActivityV0,
    AccessIntentKindV0,
    MemoryDomainV0,
)
from spk_architecture.memory_target_v0 import (
    MemoryTargetReferenceV0,
    resolve_memory_target_v0,
)
from spk_architecture.access_authorization_v0 import (
    AuthorizationContextV0,
    authorize_access_v0,
)


class MemoryAccessDeniedV0(ValueError):
    def __init__(self, reason):
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True, slots=True)
class TransactionCostRuleV0:
    kind: AccessIntentKindV0
    base_units: int
    per_item_units: int

    def __post_init__(self):
        if type(self.kind) is not AccessIntentKindV0:
            raise TypeError("invalid transaction kind")

        for name in ("base_units", "per_item_units"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"invalid {name}")

        if self.base_units + self.per_item_units == 0:
            raise ValueError("zero-cost rule not supported")


@dataclass(frozen=True, slots=True)
class TransactionCostProfileV0:
    profile_id: str
    rules: tuple[TransactionCostRuleV0, ...]

    def __post_init__(self):
        if (
            type(self.profile_id) is not str
            or not self.profile_id
            or self.profile_id.strip() != self.profile_id
        ):
            raise ValueError("invalid cost profile ID")

        if type(self.rules) is not tuple:
            raise TypeError("rules must be a tuple")

        if any(
            type(rule) is not TransactionCostRuleV0
            for rule in self.rules
        ):
            raise TypeError("invalid transaction cost rule")

        kinds = [rule.kind for rule in self.rules]

        if len(set(kinds)) != len(kinds):
            raise ValueError("duplicate transaction rule")

        if set(kinds) != set(AccessIntentKindV0):
            raise ValueError("incomplete transaction profile")

    def rule_for(self, kind):
        for rule in self.rules:
            if rule.kind is kind:
                return rule
        raise ValueError("unmapped transaction kind")


@dataclass(frozen=True, slots=True)
class MemoryServiceRequestV0:
    request_id: int
    principal_id: str
    activity: ActivityV0
    profile_id: str
    epoch_id: str
    requester_pe_id: str
    target_pe_id: str
    target_id: str
    domain: MemoryDomainV0
    kind: AccessIntentKindV0
    quantity: int
    service_units: int
    event_time: int | None


def map_memory_access_v0(
    reference: MemoryTargetReferenceV0,
    context: AuthorizationContextV0,
    profile: TransactionCostProfileV0,
) -> MemoryServiceRequestV0:
    """Authorize and map one logical memory access.

    No service-time assignment or memory mutation.
    """

    if type(reference) is not MemoryTargetReferenceV0:
        raise TypeError("invalid reference")

    if type(context) is not AuthorizationContextV0:
        raise TypeError("invalid context")

    if type(profile) is not TransactionCostProfileV0:
        raise TypeError("invalid cost profile")

    decision = authorize_access_v0(
        reference, context
    )

    if not decision.allowed:
        raise MemoryAccessDeniedV0(decision.reason)

    intent = reference.intent
    target = resolve_memory_target_v0(
        context.catalog, reference
    )

    rule = profile.rule_for(intent.kind)

    units = (
        rule.base_units
        + rule.per_item_units * intent.quantity
    )

    return MemoryServiceRequestV0(
        request_id=intent.request_id,
        principal_id=context.grant.principal_id,
        activity=context.grant.activity,
        profile_id=profile.profile_id,
        epoch_id=intent.epoch_id,
        requester_pe_id=intent.pe_id,
        target_pe_id=target.pe_id,
        target_id=target.target_id,
        domain=target.domain,
        kind=intent.kind,
        quantity=intent.quantity,
        service_units=units,
        event_time=intent.event_time,
    )
