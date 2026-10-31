from dataclasses import replace

import pytest

from spk_architecture.access_v0 import (
    AccessIntentKindV0 as Kind, ActivityV0 as Activity,
    MemoryDomainV0 as Domain, MemoryAccessIntentV0,
)
from spk_architecture.memory_target_v0 import (
    MemorySpaceV0 as Space, MemoryTargetV0, MemoryTargetCatalogV0,
    MemoryTargetReferenceV0,
)
from spk_architecture.transaction_mapping_v0 import MemoryServiceRequestV0
from spk_simulator.logical_access_v0 import LogicalAccessPlanV0
from spk_simulator.causal_service_quantum_v0 import (
    ServiceQuantumStateV0, ServiceWorkV0, ServiceFinishedV0,
    ServiceConfirmedV0,
)
from spk_simulator.internal_effect_obligations_v0 import (
    bind_internal_effect_obligations_v0,
)


def fixture(kind=Kind.PROGRAM_REFERENCE, *, rid=5):
    domain_name = {
        Kind.PROGRAM_REFERENCE: 'PROGRAM', Kind.STATE_LOAD: 'STATE',
        Kind.STATE_COMMIT: 'STATE', Kind.OBSERVATION_RECORD: 'OBSERVATION',
        Kind.OBSERVATION_READ: 'OBSERVATION', Kind.SNAPSHOT_READ: 'STATE',
        Kind.CANDIDATE_PROGRAM_WRITE: 'PROGRAM',
    }[kind]
    space_name = ('CANDIDATE' if kind is Kind.CANDIDATE_PROGRAM_WRITE else
                  'SNAPSHOT' if kind is Kind.SNAPSHOT_READ else 'ACTIVE')
    domain = getattr(Domain, domain_name)
    target = MemoryTargetV0('T:A', getattr(Space, space_name), 'E0', 'PE0', domain, 'A')
    intent = MemoryAccessIntentV0(
        request_id=rid, epoch_id='E0', pe_id='PE0', activity=Activity.EXECUTE,
        kind=kind, node_id='A', event_time=42, quantity=1,
    )
    ref = MemoryTargetReferenceV0(intent, 'T:A')
    plan = LogicalAccessPlanV0('E0', MemoryTargetCatalogV0((target,)), (ref,))
    req = MemoryServiceRequestV0(
        request_id=rid, principal_id='p', activity=Activity.EXECUTE,
        profile_id='profile', epoch_id='E0', requester_pe_id='PE0',
        target_pe_id='PE0', target_id='T:A', domain=domain, kind=kind,
        quantity=1, service_units=3, event_time=42,
    )
    return plan, (req,), ServiceQuantumStateV0()


def apply(ctx):
    return bind_internal_effect_obligations_v0(*ctx)


@pytest.mark.parametrize('kind', (
    Kind.PROGRAM_REFERENCE, Kind.STATE_LOAD, Kind.STATE_COMMIT,
))
def test_active_program_and_state_produce_obligation_not_confirmation(kind):
    result = apply(fixture(kind))
    assert len(result.obligations) == 1
    assert result.obligations[0].kind is kind
    assert result.obligations[0].lifecycle == 'NOT_STARTED'
    assert not result.awaiting_effect_request_ids
    assert not result.unverified_confirmed_request_ids


@pytest.mark.parametrize('kind, witness', (
    (Kind.OBSERVATION_RECORD, 'OBSERVATION_APPEND'),
    (Kind.OBSERVATION_READ, 'OBSERVATION_READ'),
    (Kind.SNAPSHOT_READ, 'SNAPSHOT_READ'),
    (Kind.CANDIDATE_PROGRAM_WRITE, 'CANDIDATE_PROGRAM_WRITE'),
))
def test_future_kinds_require_explicit_evidence(kind, witness):
    # Do not fabricate a synthetic activity/target that the upstream v0
    # contract might reject for non-execution epochs.
    from spk_simulator.internal_effect_obligations_v0 import _REQUIREMENTS
    assert _REQUIREMENTS[kind][2] == witness


def test_finished_service_is_obligation_not_confirmation():
    p, r, _ = fixture(Kind.STATE_COMMIT)
    s = ServiceQuantumStateV0(next_service_tick=7,
                             awaiting_confirmation=(ServiceFinishedV0(5, 6),))
    result = apply((p, r, s))
    assert result.awaiting_effect_request_ids == (5,)
    assert result.obligations[0].required_evidence == 'STATE_WRITE_WITH_TRANSITION'


def test_partial_work_stays_partial():
    p, r, _ = fixture()
    result = apply((p, r, ServiceQuantumStateV0(
        next_service_tick=1, partial=(ServiceWorkV0(5, 2),),
    )))
    assert result.obligations[0].lifecycle == 'PARTIAL'


def test_preexisting_confirmation_is_marked_unverified():
    p, r, _ = fixture()
    result = apply((p, r, ServiceQuantumStateV0(
        next_service_tick=2, confirmed=(ServiceConfirmedV0(5, 1),),
    )))
    assert result.unverified_confirmed_request_ids == (5,)


def test_request_epoch_mismatch_rejected():
    p, r, s = fixture()
    with pytest.raises(ValueError, match='epoch'):
        apply((p, (replace(r[0], epoch_id='E1'),), s))


def test_request_activity_mismatch_rejected():
    p, r, s = fixture()
    with pytest.raises(ValueError, match='logical reference'):
        apply((p, (replace(r[0], activity=next(a for a in Activity if a is not Activity.EXECUTE)),), s))


def test_wrong_request_target_id_rejected():
    p, r, s = fixture()
    with pytest.raises(ValueError, match='logical reference'):
        apply((p, (replace(r[0], target_id='unknown'),), s))


def test_wrong_request_target_pe_rejected():
    p, r, s = fixture()
    with pytest.raises(ValueError, match='target ownership'):
        apply((p, (replace(r[0], target_pe_id='PE1'),), s))


def test_wrong_requester_pe_rejected():
    p, r, s = fixture()
    with pytest.raises(ValueError, match='logical reference'):
        apply((p, (replace(r[0], requester_pe_id='PE1'),), s))


def test_wrong_event_time_rejected():
    p, r, s = fixture()
    with pytest.raises(ValueError, match='logical reference'):
        apply((p, (replace(r[0], event_time=43),), s))


def test_wrong_quantity_rejected():
    p, r, s = fixture()
    with pytest.raises(ValueError, match='logical reference'):
        apply((p, (replace(r[0], quantity=2),), s))


def test_wrong_target_space_rejected():
    p, r, s = fixture()
    old = p.catalog.targets[0]
    p = replace(p, catalog=MemoryTargetCatalogV0((replace(old, space=Space.SNAPSHOT),)))
    with pytest.raises(ValueError, match='space'):
        apply((p, r, s))


def test_wrong_domain_for_kind_rejected():
    p, r, s = fixture()
    t = p.catalog.targets[0]
    altered = replace(t, domain=Domain.EVENT)
    p = replace(p, catalog=MemoryTargetCatalogV0((altered,)))
    r = (replace(r[0], domain=Domain.EVENT),)
    with pytest.raises(ValueError, match='domain'):
        apply((p, r, s))


def test_target_owner_node_mismatch_rejected():
    p, r, s = fixture()
    t = p.catalog.targets[0]
    p = replace(p, catalog=MemoryTargetCatalogV0((replace(t, owner_node_id='B'),)))
    with pytest.raises(ValueError, match='ownership'):
        apply((p, r, s))


def test_missing_reference_rejected():
    p, r, s = fixture()
    p = replace(p, references=())
    with pytest.raises(ValueError, match='unbound'):
        apply((p, r, s))


def test_duplicate_requests_rejected():
    p, r, s = fixture()
    with pytest.raises(ValueError, match='duplicate'):
        apply((p, r + r, s))


def test_unknown_service_state_identity_rejected():
    p, r, _ = fixture()
    s = ServiceQuantumStateV0(next_service_tick=1,
                             awaiting_confirmation=(ServiceFinishedV0(99, 1),))
    with pytest.raises(ValueError, match='unknown'):
        apply((p, r, s))


def test_deterministic_order_by_request_id():
    p1, r1, _ = fixture(rid=9)
    p2, r2, _ = fixture(Kind.STATE_LOAD, rid=2)
    t2 = replace(p2.catalog.targets[0], target_id='T:B')
    ref2 = replace(p2.references[0], target_id='T:B')
    req2 = replace(r2[0], target_id='T:B')
    p = LogicalAccessPlanV0('E0', MemoryTargetCatalogV0((p1.catalog.targets[0], t2)),
                            (ref2, p1.references[0]))
    first = apply((p, (r1[0], req2), ServiceQuantumStateV0()))
    second = apply((p, (req2, r1[0]), ServiceQuantumStateV0()))
    assert first == second
    assert tuple(x.request_id for x in first.obligations) == (2, 9)


def test_wrong_plan_type_rejected():
    p, r, s = fixture()
    with pytest.raises(TypeError, match='plan'):
        apply((None, r, s))


def test_wrong_service_state_type_rejected():
    p, r, s = fixture()
    with pytest.raises(TypeError, match='service state'):
        apply((p, r, None))
