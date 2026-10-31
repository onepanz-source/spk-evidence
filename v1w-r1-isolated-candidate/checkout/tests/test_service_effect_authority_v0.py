"""Storage completion must be witnessed by real driver transitions."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_simulator.bounded_backpressure_driver_v0 import (
    BackpressureServiceFrameV0 as Frame,
    advance_bounded_backpressure_v0,
)
from spk_simulator.causal_service_quantum_v0 import (
    ServiceQuantumStateV0 as Quantum, ServiceFinishedV0 as Finished,
    ServiceWorkV0,
)
from spk_simulator.service_effect_authority_v0 import (
    authenticate_service_storage_effects_v0 as authenticate,
)
from spk_simulator.atomic_emission_admission_v0 import AtomicEmissionGroupV0
from spk_simulator.external_ingress_v0 import (
    ExternalIngressBindingV0, BoundExternalArrivalV0,
    BatchIngressReleaseV0,
)
from tests.test_bounded_backpressure_driver_v0 import ctx
from tests.test_release_aware_scheduler_v0 import req


def setting():
    a, m, admission, driver = ctx()
    # All identity bindings exist in the real service-request set.
    requests = tuple(sorted((
        req(1, kind=Kind.EMISSION_RECORD, pe='PE0'),
        req(2, kind=Kind.EMISSION_RECORD, pe='PE0'),
        *tuple(req(i, kind=Kind.ROUTE_ENQUEUE, pe='PE1') for i in (10, 11, 12)),
        *tuple(req(i, kind=Kind.BATCH_CONSUME, pe='PE1') for i in (50, 51, 52)),
    ), key=lambda r: r.request_id))
    return a, m, admission, requests, driver


def prior(a, m, adm, driver, *frames):
    for frame in frames:
        driver, _ = advance_bounded_backpressure_v0(a, m, adm, driver, frame)
    return driver


def q(t, *ids):
    return Quantum(next_service_tick=t, awaiting_confirmation=tuple(Finished(x,t) for x in sorted(ids)))


def call(setting_, service, frame):
    a, m, adm, reqs, driver = setting_
    return authenticate(a, m, adm, reqs, service, driver, frame)


def prepared():
    a,m,adm,reqs,driver = setting()
    driver = prior(a,m,adm,driver, Frame(0))
    return a,m,adm,reqs,driver


def delivered():
    a,m,adm,reqs,driver = prepared()
    first = call((a,m,adm,reqs,driver), q(1,2), Frame(1,new_ready_emission_ids=(2,)))
    driver = first.driver_state
    next_ = call((a,m,adm,reqs,driver), q(2), Frame(2,new_ready_route_ids=(11,12)))
    driver = next_.driver_state
    final = call((a,m,adm,reqs,driver), q(3,11,12), Frame(3,route_commits=(11,12)))
    return (a,m,adm,reqs,final.driver_state), final


def test_idle_boundary_no_spurious_confirmation():
    x = call(setting(), Quantum(), Frame(0))
    assert x.confirmed_request_ids == ()
    assert x.granted_route_request_ids == ()
    assert x.driver_step.service_boundary == 0


def test_emission_publication_is_authenticated():
    x = call(prepared(), q(1,2), Frame(1,new_ready_emission_ids=(2,)))
    assert x.confirmed_request_ids == (2,)
    assert x.effects[0].route_request_ids == (11,12)
    assert {ev.event_id for ev in x.driver_state.boundary.storage.pending_output} == {11,12}


def test_blocked_emission_is_not_confirmed():
    a,m,adm,reqs,driver = prepared()
    out = call((a,m,adm,reqs,driver),q(1,1,2),Frame(1,new_ready_emission_ids=(1,2)))
    assert out.confirmed_request_ids == (1,)
    assert out.driver_state.pending_emission_ids == (2,)


def test_auto_retry_witness_confirms_later_boundary():
    a,m,adm,reqs,driver = prepared()
    first = call((a,m,adm,reqs,driver),q(1,1,2),Frame(1,new_ready_emission_ids=(1,2),new_ready_route_ids=(10,)))
    second = call((a,m,adm,reqs,first.driver_state),q(2,2,10),Frame(2,route_commits=(10,)))
    assert second.confirmed_request_ids == (10,)
    third = call((a,m,adm,reqs,second.driver_state),q(3,2),Frame(3))
    assert third.confirmed_request_ids == (2,)


def test_route_grant_is_not_service_completion():
    a,m,adm,reqs,driver = prepared()
    first = call((a,m,adm,reqs,driver),q(1,2),Frame(1,new_ready_emission_ids=(2,),new_ready_route_ids=(11,12)))
    assert first.confirmed_request_ids == (2,)
    assert first.granted_route_request_ids == (11,12)
    assert 11 not in first.confirmed_request_ids


def test_route_commit_requires_completed_work_and_real_reservation():
    x, out = delivered()
    assert out.confirmed_request_ids == (11,12)
    assert tuple(item.route_request_ids for item in out.effects) == ((11,),(12,))
    assert {event.event_id for event in x[-1].boundary.storage.admitted_events} == {11,12}


def test_complete_route_consumption_can_confirm_own_batch():
    x, _ = delivered()
    out = call(x,q(4,51,52),Frame(4,route_consumptions=(11,12)))
    assert out.confirmed_request_ids == (51,52)
    assert out.driver_state.boundary.storage.consumed_ids == (11,12)


def test_no_confirmation_for_missing_work():
    with pytest.raises(ValueError,match='finished service'):
        call(prepared(), q(1), Frame(1,new_ready_emission_ids=(2,)))


def test_no_premature_confirmation():
    a,m,adm,reqs,driver = prepared()
    # Snapshot constructor must itself reject a future finish.
    with pytest.raises(ValueError,match='future'):
        Quantum(next_service_tick=1,awaiting_confirmation=(Finished(2,2),))


def test_boundary_tick_mismatch_rejected():
    with pytest.raises(ValueError,match='boundary/state'):
        call(prepared(),q(2,2),Frame(1,new_ready_emission_ids=(2,)))


def test_route_commit_cannot_come_before_finished_service():
    a,m,adm,reqs,driver = prepared()
    first = call((a,m,adm,reqs,driver),q(1,2),Frame(1,new_ready_emission_ids=(2,),new_ready_route_ids=(11,12)))
    with pytest.raises(ValueError,match='finished service'):
        call((a,m,adm,reqs,first.driver_state),q(2),Frame(2,route_commits=(11,)))


def test_batch_consume_cannot_come_before_finished_service():
    x, _ = delivered()
    with pytest.raises(ValueError,match='finished service'):
        call(x,q(4),Frame(4,route_consumptions=(11,)))


def test_unbound_consumption_rejected():
    x,_ = delivered()
    with pytest.raises(ValueError,match='unbound'):
        call(x,q(4,51),Frame(4,route_consumptions=(999,)))


def test_partial_batch_is_rejected_before_driver():
    x,_ = delivered()
    a,m,adm,reqs,driver = x
    altered_routes = tuple(replace(route,consume_request_id=51) if route.route_request_id==12 else route for route in m.routes)
    altered = replace(m, routes=altered_routes)
    with pytest.raises(ValueError,match='partial batch'):
        call((a,altered,adm,reqs,driver),q(4,51),Frame(4,route_consumptions=(11,)))


def test_unfinished_emission_rejected_before_mutation():
    ctx_ = prepared()
    original = repr(ctx_)
    with pytest.raises(ValueError):
        call(ctx_, q(1), Frame(1,new_ready_emission_ids=(1,)))
    assert repr(ctx_) == original


def test_invalid_request_kind_rejected():
    a,m,adm,reqs,driver = prepared()
    changed = tuple(replace(r,kind=Kind.BATCH_CONSUME) if r.request_id==2 else r for r in reqs)
    with pytest.raises(ValueError,match='emission request'):
        call((a,m,adm,changed,driver),q(1,2),Frame(1,new_ready_emission_ids=(2,)))


def test_mismatched_route_pe_rejected():
    a,m,adm,reqs,driver = prepared()
    changed = tuple(replace(r,target_pe_id='PE0') if r.request_id==11 else r for r in reqs)
    with pytest.raises(ValueError,match='route request'):
        call((a,m,adm,changed,driver),q(1,2),Frame(1,new_ready_emission_ids=(2,)))


def test_empty_fanout_emission_can_confirm_without_offer():
    a,m,adm,reqs,driver = prepared()
    empty = AtomicEmissionGroupV0(3,'PE1','D',6,(),0,2)
    adm = replace(adm,groups=adm.groups+(empty,),zero_fanout_emission_count=1)
    reqs = tuple(sorted(reqs+(req(3,kind=Kind.EMISSION_RECORD,pe='PE1'),),key=lambda r:r.request_id))
    out=call((a,m,adm,reqs,driver),q(1,3),Frame(1,new_ready_emission_ids=(3,)))
    assert out.confirmed_request_ids==(3,)
    assert not out.effects[0].route_request_ids


def test_epoch_mismatch_rejected():
    a,m,adm,reqs,driver=prepared()
    with pytest.raises(ValueError,match='epoch'):
        call((a,replace(m,epoch_id='E1'),adm,reqs,driver),q(1),Frame(1))


def test_profile_mismatch_rejected():
    a,m,adm,reqs,driver=prepared()
    with pytest.raises(ValueError,match='profile'):
        call((replace(a,profile_id='different'),m,adm,reqs,driver),q(1),Frame(1))


def test_storage_result_is_immutable():
    out=call(setting(),Quantum(),Frame(0))
    with pytest.raises((FrozenInstanceError,AttributeError)):
        out.confirmed_request_ids=()


def test_duplicate_requests_rejected():
    a,m,adm,reqs,driver=prepared()
    with pytest.raises(ValueError,match='duplicate'):
        call((a,m,adm,reqs+(reqs[0],),driver),q(1),Frame(1))


def test_invalid_service_state_type_rejected():
    a,m,adm,reqs,driver=prepared()
    with pytest.raises(TypeError,match='service state'):
        call((a,m,adm,reqs,driver),None,Frame(1))


def test_invalid_frame_type_rejected():
    a,m,adm,reqs,driver=prepared()
    with pytest.raises(TypeError,match='driver frame'):
        call((a,m,adm,reqs,driver),q(1),None)


def test_repeat_same_boundary_rejected():
    a,m,adm,reqs,driver=prepared()
    with pytest.raises(ValueError,match='boundary/state'):
        call((a,m,adm,reqs,driver),q(1),Frame(0))


def test_external_arrival_is_not_a_consumption_confirmation():
    a,m,adm,reqs,driver=setting()
    incoming = ExternalIngressBindingV0(
        (BoundExternalArrivalV0(0, 2, 'B', 0, 'PE1', 0, 500),),
        (BatchIngressReleaseV0(500, 0, (0,)),),
    )
    driver = replace(driver,boundary=replace(driver.boundary,
                 ledger=replace(driver.boundary.ledger,ingress=incoming)))
    reqs=tuple(sorted(reqs+(req(500,kind=Kind.BATCH_CONSUME,pe='PE1'),), key=lambda x:x.request_id))
    first=call((a,m,adm,reqs,driver),q(0),Frame(0,external_arrivals=(0,)))
    assert first.confirmed_request_ids == ()
    assert first.driver_state.boundary.ledger.external_resident==(0,)
    second=call((a,m,adm,reqs,first.driver_state),q(1,500),Frame(1,external_consumptions=(0,)))
    assert second.confirmed_request_ids==(500,)
    assert second.driver_state.boundary.ledger.external_consumed==(0,)


def test_route_and_external_must_be_consumed_together_for_one_batch():
    a,m,adm,reqs,driver=setting()
    incoming = ExternalIngressBindingV0(
        (BoundExternalArrivalV0(0,2,'B',0,'PE1',0,51),),
        (BatchIngressReleaseV0(51,0,(0,)),),
    )
    driver = replace(driver,boundary=replace(driver.boundary,
                 ledger=replace(driver.boundary.ledger,ingress=incoming)))
    driver = prior(a,m,adm,driver,Frame(0,external_arrivals=(0,)))
    first=call((a,m,adm,reqs,driver),q(1,2),Frame(1,new_ready_emission_ids=(2,)))
    second=call((a,m,adm,reqs,first.driver_state),q(2),Frame(2,new_ready_route_ids=(11,12)))
    third=call((a,m,adm,reqs,second.driver_state),q(3,11,12),Frame(3,route_commits=(11,12)))
    snapshot=(a,m,adm,reqs,third.driver_state)
    with pytest.raises(ValueError,match='partial batch'):
        call(snapshot,q(4,51),Frame(4,route_consumptions=(11,)))
    with pytest.raises(ValueError,match='partial batch'):
        call(snapshot,q(4,51),Frame(4,external_consumptions=(0,)))
    out=call(snapshot,q(4,51),Frame(4,route_consumptions=(11,),external_consumptions=(0,)))
    assert out.confirmed_request_ids==(51,)
    assert out.effects[0].route_request_ids==(11,)
    assert out.effects[0].external_input_indices==(0,)


def test_quantum_service_finish_then_authentic_storage_effect():
    from spk_simulator.causal_service_quantum_v0 import advance_service_quantum_v0
    from tests.test_release_aware_scheduler_v0 import graph
    a,m,adm,reqs,driver=setting()
    # Caller grant is still a claim; the purpose here is to exercise the
    # native state produced by Service Quantum, not authenticate its grants.
    dag=graph(*((r.request_id,()) for r in reqs))
    quantum_step=advance_service_quantum_v0(
        a, reqs, dag, Quantum(), granted_memory_request_ids=(2,)
    )
    assert any(x.request_id==2 for x in quantum_step.state.awaiting_confirmation)
    driver=prior(a,m,adm,driver,Frame(0))
    out=call((a,m,adm,reqs,driver),quantum_step.state,Frame(1,new_ready_emission_ids=(2,)))
    assert out.confirmed_request_ids==(2,)
