from dataclasses import replace

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
    authorize_access_v0,
)
from spk_compiler.pe_admission_v0 import (
    PEUsageV0,
    PEAdmissionManifestV0,
)


@pytest.fixture
def environment():
    targets = (
        MemoryTargetV0(
            "state-A", Space.ACTIVE, "E0",
            "PE0", Domain.STATE, "A",
        ),
        MemoryTargetV0(
            "state-B", Space.ACTIVE, "E0",
            "PE1", Domain.STATE, "B",
        ),
        MemoryTargetV0(
            "program-A", Space.ACTIVE, "E0",
            "PE0", Domain.PROGRAM, "A",
        ),
        MemoryTargetV0(
            "events-B", Space.ACTIVE, "E0",
            "PE1", Domain.EVENT,
        ),
        MemoryTargetV0(
            "observations", Space.ACTIVE, "E0",
            "PE0", Domain.OBSERVATION,
        ),
        MemoryTargetV0(
            "snapshot-B", Space.SNAPSHOT, "Eold",
            "PE1", Domain.STATE, "B",
        ),
        MemoryTargetV0(
            "candidate", Space.CANDIDATE, "Enew",
            "PE0", Domain.PROGRAM,
        ),
    )

    def usage(pe, node):
        return PEUsageV0(
            pe_id=pe,
            node_ids=(node,),
            program_used=4,
            program_capacity=16,
            state_used=1,
            state_capacity=4,
            event_capacity=8,
            output_capacity=8,
            observation_capacity=8,
            accesses_per_service_tick=2,
        )

    placement = PEAdmissionManifestV0(
        profile_id="test",
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

    return (
        MemoryTargetCatalogV0(targets),
        placement,
        AuthorizationPolicyV0(
            active_epoch_id="E0",
            snapshot_epochs=("Eold",),
            candidate_epochs=("Enew",),
        ),
    )


def check(
    environment,
    activity,
    kind,
    target_id,
    *,
    node_id="A",
    pe_id="PE0",
    request_epoch="E0",
    snapshot_epochs=(),
    candidate_epochs=(),
):
    catalog, placement, policy = environment

    grant = AccessGrantV0(
        principal_id="trusted-principal",
        activity=activity,
        pe_id=pe_id,
        node_id=node_id if activity is Activity.EXECUTE
        else None,
        snapshot_epochs=snapshot_epochs,
        candidate_epochs=candidate_epochs,
    )

    context = AuthorizationContextV0(
        catalog, placement, policy, grant
    )

    intent = MemoryAccessIntentV0(
        request_id=1,
        epoch_id=request_epoch,
        pe_id=pe_id,
        activity=activity,
        kind=kind,
        node_id=node_id,
    )

    reference = MemoryTargetReferenceV0(
        intent, target_id
    )

    return authorize_access_v0(reference, context)


def test_execution_owns_state(environment):
    assert check(
        environment, Activity.EXECUTE,
        Kind.STATE_LOAD, "state-A",
    ).allowed


def test_execution_cannot_access_foreign_state(environment):
    assert not check(
        environment, Activity.EXECUTE,
        Kind.STATE_LOAD, "state-B",
    ).allowed


def test_program_read(environment):
    assert check(
        environment, Activity.EXECUTE,
        Kind.PROGRAM_REFERENCE, "program-A",
    ).allowed


def test_router_remote_delivery(environment):
    assert check(
        environment, Activity.ROUTER,
        Kind.ROUTE_ENQUEUE, "events-B",
        node_id="B",
    ).allowed


def test_router_rejects_wrong_destination(environment):
    assert not check(
        environment, Activity.ROUTER,
        Kind.ROUTE_ENQUEUE, "events-B",
        node_id="A",
    ).allowed


def test_observer_writes_observations(environment):
    assert check(
        environment, Activity.OBSERVER,
        Kind.OBSERVATION_RECORD, "observations",
    ).allowed


def test_learning_reads_observations(environment):
    assert check(
        environment, Activity.LEARN,
        Kind.OBSERVATION_READ, "observations",
    ).allowed


def test_learning_cannot_write_observations(environment):
    assert not check(
        environment, Activity.LEARN,
        Kind.OBSERVATION_RECORD, "observations",
    ).allowed


def test_snapshot_requires_explicit_grant(environment):
    assert not check(
        environment, Activity.VERIFY,
        Kind.SNAPSHOT_READ, "snapshot-B",
    ).allowed

    assert check(
        environment, Activity.VERIFY,
        Kind.SNAPSHOT_READ, "snapshot-B",
        snapshot_epochs=("Eold",),
    ).allowed


def test_candidate_requires_explicit_grant(environment):
    assert not check(
        environment, Activity.REMODEL,
        Kind.CANDIDATE_PROGRAM_WRITE, "candidate",
        request_epoch="Enew",
    ).allowed

    assert check(
        environment, Activity.REMODEL,
        Kind.CANDIDATE_PROGRAM_WRITE, "candidate",
        request_epoch="Enew",
        candidate_epochs=("Enew",),
    ).allowed


def test_candidate_cannot_modify_active_program(environment):
    assert not check(
        environment, Activity.REMODEL,
        Kind.CANDIDATE_PROGRAM_WRITE, "program-A",
        request_epoch="Enew",
        candidate_epochs=("Enew",),
    ).allowed


def test_active_execution_rejects_wrong_epoch(environment):
    assert not check(
        environment, Activity.EXECUTE,
        Kind.STATE_LOAD, "state-A",
        request_epoch="Eold",
    ).allowed


def test_domain_mismatch_denied(environment):
    decision = check(
        environment, Activity.EXECUTE,
        Kind.PROGRAM_REFERENCE, "state-A",
    )
    assert not decision.allowed
    assert decision.reason == "DOMAIN_MISMATCH"


def test_invalid_active_target_binding(environment):
    catalog, placement, policy = environment
    target = replace(
        catalog.get("state-A"),
        pe_id="PE1",
    )

    with pytest.raises(ValueError):
        AuthorizationContextV0(
            MemoryTargetCatalogV0((target,)),
            placement,
            policy,
            AccessGrantV0(
                "executor", Activity.EXECUTE,
                "PE0", node_id="A",
            ),
        )


def test_caller_cannot_claim_different_role(environment):
    catalog, placement, policy = environment
    grant = AccessGrantV0(
        "executor", Activity.EXECUTE,
        "PE0", node_id="A",
    )
    context = AuthorizationContextV0(
        catalog, placement, policy, grant
    )

    intent = MemoryAccessIntentV0(
        request_id=0,
        epoch_id="E0",
        pe_id="PE0",
        activity=Activity.OBSERVER,
        kind=Kind.OBSERVATION_RECORD,
    )

    decision = authorize_access_v0(
        MemoryTargetReferenceV0(
            intent, "observations"
        ),
        context,
    )
    assert not decision.allowed
    assert decision.reason == "ACTIVITY_MISMATCH"


def test_unknown_target_denied(environment):
    assert not check(
        environment, Activity.EXECUTE,
        Kind.STATE_LOAD, "unknown",
    ).allowed


def test_grant_requires_execution_owner():
    with pytest.raises(ValueError):
        AccessGrantV0(
            "executor", Activity.EXECUTE, "PE0",
        )


def test_observation_read_domain():
    intent = MemoryAccessIntentV0(
        request_id=0,
        epoch_id="E0",
        pe_id="PE0",
        activity=Activity.LEARN,
        kind=Kind.OBSERVATION_READ,
    )
    assert intent.domain is Domain.OBSERVATION
