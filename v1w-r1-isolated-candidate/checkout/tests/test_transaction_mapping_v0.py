from dataclasses import FrozenInstanceError, replace

import pytest

from spk_architecture.access_v0 import (
    ActivityV0 as Activity,
    AccessIntentKindV0 as Kind,
    MemoryAccessIntentV0,
    MemoryDomainV0 as Domain,
)
from spk_architecture.memory_target_v0 import (
    MemorySpaceV0 as Space,
    MemoryTargetV0,
    MemoryTargetCatalogV0,
    MemoryTargetReferenceV0,
)
from spk_architecture.access_authorization_v0 import (
    AccessGrantV0,
    AuthorizationPolicyV0,
    AuthorizationContextV0,
)
from spk_architecture.transaction_mapping_v0 import (
    TransactionCostRuleV0,
    TransactionCostProfileV0,
    MemoryAccessDeniedV0,
    map_memory_access_v0,
)
from spk_compiler.pe_admission_v0 import (
    PEUsageV0,
    PEAdmissionManifestV0,
)


@pytest.fixture
def profile():
    rules = tuple(
        TransactionCostRuleV0(
            kind,
            base_units=(
                0 if kind in (
                    Kind.BATCH_CONSUME,
                    Kind.ROUTE_ENQUEUE,
                ) else 1
            ),
            per_item_units=(
                1 if kind in (
                    Kind.BATCH_CONSUME,
                    Kind.ROUTE_ENQUEUE,
                ) else 0
            ),
        )
        for kind in Kind
    )
    return TransactionCostProfileV0("reference-v0", rules)


@pytest.fixture
def environment():
    catalog = MemoryTargetCatalogV0((
        MemoryTargetV0(
            "state-A", Space.ACTIVE, "E0",
            "PE0", Domain.STATE, "A",
        ),
        MemoryTargetV0(
            "events-B", Space.ACTIVE, "E0",
            "PE1", Domain.EVENT,
        ),
    ))

    def usage(pe, node):
        return PEUsageV0(
            pe_id=pe,
            node_ids=(node,),
            program_used=4,
            program_capacity=8,
            state_used=1,
            state_capacity=2,
            event_capacity=8,
            output_capacity=8,
            observation_capacity=4,
            accesses_per_service_tick=2,
        )

    placement = PEAdmissionManifestV0(
        profile_id="machine-v0",
        node_count=2,
        pe_count=2,
        total_program_slots=8,
        total_state_slots=2,
        cross_pe_edges=1,
        pe_usage=(
            usage("PE0", "A"),
            usage("PE1", "B"),
        ),
    )

    return catalog, placement


def make_request(
    environment, kind, target_id,
    *,
    activity=Activity.EXECUTE,
    node_id="A",
    quantity=1,
):
    catalog, placement = environment

    grant = AccessGrantV0(
        principal_id="trusted",
        activity=activity,
        pe_id="PE0",
        node_id="A" if activity is Activity.EXECUTE
        else None,
    )

    context = AuthorizationContextV0(
        catalog,
        placement,
        AuthorizationPolicyV0("E0"),
        grant,
    )

    intent = MemoryAccessIntentV0(
        request_id=7,
        epoch_id="E0",
        pe_id="PE0",
        activity=activity,
        kind=kind,
        node_id=node_id,
        event_time=3,
        quantity=quantity,
    )

    return (
        MemoryTargetReferenceV0(intent, target_id),
        context,
    )


def test_fixed_service_cost(environment, profile):
    reference, context = make_request(
        environment, Kind.STATE_LOAD, "state-A"
    )
    request = map_memory_access_v0(
        reference, context, profile
    )

    assert request.service_units == 1
    assert request.domain is Domain.STATE
    assert request.target_pe_id == "PE0"


def test_event_multiplicity_cost(environment, profile):
    reference, context = make_request(
        environment,
        Kind.ROUTE_ENQUEUE,
        "events-B",
        activity=Activity.ROUTER,
        node_id="B",
        quantity=3,
    )

    request = map_memory_access_v0(
        reference, context, profile
    )

    assert request.quantity == 3
    assert request.service_units == 3
    assert request.requester_pe_id == "PE0"
    assert request.target_pe_id == "PE1"


def test_unauthorized_access_rejected(environment, profile):
    reference, context = make_request(
        environment, Kind.STATE_LOAD, "events-B"
    )

    with pytest.raises(MemoryAccessDeniedV0):
        map_memory_access_v0(
            reference, context, profile
        )


def test_mapping_is_deterministic(environment, profile):
    reference, context = make_request(
        environment, Kind.STATE_LOAD, "state-A"
    )

    first = map_memory_access_v0(
        reference, context, profile
    )
    second = map_memory_access_v0(
        reference, context, profile
    )

    assert first == second


def test_event_time_preserved(environment, profile):
    reference, context = make_request(
        environment, Kind.STATE_LOAD, "state-A"
    )

    request = map_memory_access_v0(
        reference, context, profile
    )

    assert request.event_time == 3
    assert not hasattr(request, "service_time")


def test_service_request_immutable(environment, profile):
    reference, context = make_request(
        environment, Kind.STATE_LOAD, "state-A"
    )

    request = map_memory_access_v0(
        reference, context, profile
    )

    with pytest.raises(FrozenInstanceError):
        request.service_units = 100


def test_missing_cost_rule_rejected(profile):
    with pytest.raises(ValueError):
        TransactionCostProfileV0(
            "incomplete", profile.rules[:-1]
        )


def test_duplicate_cost_rule_rejected(profile):
    with pytest.raises(ValueError):
        TransactionCostProfileV0(
            "duplicate",
            profile.rules + (profile.rules[0],),
        )


@pytest.mark.parametrize("base,per_item", [
    (-1, 1),
    (1, -1),
    (True, 0),
    (0, 0),
])
def test_invalid_cost_rule(base, per_item):
    with pytest.raises(ValueError):
        TransactionCostRuleV0(
            Kind.STATE_LOAD, base, per_item
        )


def test_invalid_cost_profile_id(profile):
    with pytest.raises(ValueError):
        replace(profile, profile_id="")


def test_cannot_fake_authorization_result(
    environment, profile
):
    reference, context = make_request(
        environment, Kind.STATE_COMMIT, "events-B"
    )

    with pytest.raises(MemoryAccessDeniedV0):
        map_memory_access_v0(
            reference, context, profile
        )


@pytest.mark.parametrize(
    "kind,target_id,activity,node_id",
    [
        (
            Kind.STATE_LOAD,
            "state-A",
            Activity.EXECUTE,
            "A",
        ),
        (
            Kind.ROUTE_ENQUEUE,
            "events-B",
            Activity.ROUTER,
            "B",
        ),
    ],
)
def test_transaction_retains_authorized_activity(
    environment, profile,
    kind, target_id, activity, node_id,
):
    reference, context = make_request(
        environment,
        kind,
        target_id,
        activity=activity,
        node_id=node_id,
    )

    request = map_memory_access_v0(
        reference, context, profile
    )

    assert request.activity is context.grant.activity

    # Priority is assigned later by the arbiter,
    # not supplied by the access request.
    assert not hasattr(request, "priority_class")
