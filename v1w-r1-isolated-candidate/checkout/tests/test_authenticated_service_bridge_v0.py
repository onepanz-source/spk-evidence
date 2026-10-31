"""Single-boundary effect/quantum composition using native SPK laboratory APIs."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_simulator.authenticated_service_bridge_v0 import (
    AuthenticatedServiceBoundaryStateV0 as State,
    advance_authenticated_service_boundary_v0 as advance,
)
from spk_simulator.bounded_backpressure_driver_v0 import BackpressureServiceFrameV0 as Frame
from spk_simulator.causal_service_quantum_v0 import (
    ServiceQuantumStateV0 as Quantum, ServiceFinishedV0 as Finished,
    ServiceConfirmedV0,
)
from tests.test_service_effect_authority_v0 import setting, prior
from tests.test_release_aware_scheduler_v0 import graph


def context(t=0, finished=(), driver=None, deps=None, q=None):
    arch, manifest, admission, requests, initial = setting()
    if driver is None:
        driver = initial if t == 0 else prior(
            arch, manifest, admission, initial, *(Frame(i) for i in range(t))
        )
    service = q if q is not None else Quantum(
        next_service_tick=t,
        awaiting_confirmation=tuple(Finished(r,t) for r in sorted(finished)),
    )
    deps = graph(*((r.request_id,()) for r in requests)) if deps is None else deps
    return arch, manifest, admission, requests, deps, State(service,driver)


def invoke(c, frame, *, ingress=None):
    return advance(*c, frame, ingress=ingress)


def test_first_idle_boundary_no_fabricated_completion():
    out = invoke(context(), Frame(0))
    assert out.authority.confirmed_request_ids == ()
    assert out.quantum.confirmed_request_ids == ()
    assert out.state.service.next_service_tick == 1
    assert out.state.driver.boundary.arbiter.last_service_boundary == 0


def test_emission_effect_confirms_service_and_not_route():
    out = invoke(context(1,(2,)), Frame(1,new_ready_emission_ids=(2,)))
    assert out.authority.confirmed_request_ids == (2,)
    assert out.quantum.confirmed_request_ids == (2,)
    assert any(x.request_id==2 for x in out.state.service.confirmed)
    assert not any(x.request_id in (11,12) for x in out.state.service.confirmed)


def test_route_reservation_not_confirmed():
    out = invoke(context(1,(2,)), Frame(1,new_ready_emission_ids=(2,),new_ready_route_ids=(11,12)))
    assert out.authority.granted_route_request_ids == (11,12)
    assert out.quantum.confirmed_request_ids == (2,)
    assert all(x.request_id not in (11,12) for x in out.state.service.confirmed)
    assert all(x.request_id in (11,12) for x in out.quantum.slices if x.request_id in (11,12))


def test_route_submission_checked_for_missing_dependency():
    c=context(1,(2,))
    requests=c[3]
    pairs=tuple((r.request_id, (1,) if r.request_id==11 else ()) for r in requests)
    c=(*c[:4],graph(*pairs),c[-1])
    with pytest.raises(ValueError,match='premature route'):
        invoke(c,Frame(1,new_ready_emission_ids=(2,),new_ready_route_ids=(11,)))


def test_emission_confirmation_releases_route_in_same_boundary():
    c=context(1,(2,))
    pairs=tuple((r.request_id, (2,) if r.request_id==11 else ()) for r in c[3])
    c=(*c[:4],graph(*pairs),c[-1])
    out=invoke(c,Frame(1,new_ready_emission_ids=(2,),new_ready_route_ids=(11,)))
    assert 11 in out.quantum.frontier.ready_request_ids


def test_no_premature_completion_from_caller_claim():
    with pytest.raises(ValueError,match='finished service'):
        invoke(context(1),Frame(1,new_ready_emission_ids=(2,)))


def test_repeated_wrong_tick_rejected():
    with pytest.raises(ValueError,match='SERVICE_TIME mismatch'):
        invoke(context(1,(2,)),Frame(0,new_ready_emission_ids=(2,)))


def test_snapshot_mismatch_rejected_before_transition():
    c=context(1)
    with pytest.raises(ValueError,match='boundary mismatch'):
        State(Quantum(),c[-1].driver)


def test_unknown_graph_request_rejected():
    c=context(1,(2,))
    bad=graph((1,()),(2,()))
    with pytest.raises(ValueError,match='coverage'):
        invoke((*c[:4],bad,c[-1]),Frame(1,new_ready_emission_ids=(2,)))


def test_zero_external_arrivals_no_external_ingress_needed():
    out=invoke(context(),Frame(0))
    assert out.state.service.next_service_tick == 1


def test_immutable_state_and_result():
    out=invoke(context(),Frame(0))
    with pytest.raises((FrozenInstanceError,AttributeError)):
        out.state=out.state
    with pytest.raises((FrozenInstanceError,AttributeError)):
        out.state.driver=out.state.driver


def test_input_snapshot_unchanged_after_error():
    c=context(1)
    snapshot=repr(c)
    with pytest.raises(ValueError):
        invoke(c,Frame(1,route_commits=(11,)))
    assert repr(c)==snapshot


def test_invalid_state_type():
    c=context()
    with pytest.raises(TypeError,match='bridge state'):
        advance(*c[:5],None,Frame(0))


def test_invalid_graph_type():
    c=context()
    with pytest.raises(TypeError,match='dependency graph'):
        advance(*c[:4],None,c[-1],Frame(0))


def test_invalid_frame_type():
    c=context()
    with pytest.raises(TypeError,match='driver frame'):
        invoke(c,None)


def test_service_quantum_is_not_auto_confirmed_for_internal_ops():
    out=invoke(context(),Frame(0))
    assert not out.state.service.confirmed
    assert out.quantum.status in ('WAITING','PROGRESSED','IDLE')


def test_blocked_emission_stays_unconfirmed_in_quantum():
    out=invoke(context(1,(1,2)),Frame(1,new_ready_emission_ids=(1,2)))
    assert out.authority.confirmed_request_ids == (1,)
    assert out.state.driver.pending_emission_ids == (2,)
    assert 2 not in {x.request_id for x in out.state.service.confirmed}
    assert 2 in {x.request_id for x in out.state.service.awaiting_confirmation}


def test_route_cannot_be_claimed_before_source_publication():
    with pytest.raises(ValueError):
        invoke(context(),Frame(0,new_ready_route_ids=(11,)))


def test_external_ingress_requires_explicit_matching_release_binding():
    from spk_simulator.external_ingress_v0 import (
        ExternalIngressBindingV0, BoundExternalArrivalV0, BatchIngressReleaseV0,
    )
    c=context()
    binding=ExternalIngressBindingV0(
        (BoundExternalArrivalV0(0,2,'B',0,'PE1',0,50),),
        (BatchIngressReleaseV0(50,0,(0,)),),
    )
    driver=replace(c[-1].driver,boundary=replace(
        c[-1].driver.boundary,
        ledger=replace(c[-1].driver.boundary.ledger,ingress=binding),
    ))
    c=(*c[:-1],State(c[-1].service,driver))
    with pytest.raises(ValueError,match='explicit release binding'):
        invoke(c,Frame(0,external_arrivals=(0,)))
    with pytest.raises(ValueError,match='ingress binding mismatch'):
        invoke(c,Frame(0,external_arrivals=(0,)),
               ingress=ExternalIngressBindingV0((),()))


def test_duplicate_or_invalid_route_claim_rejected_without_mutation():
    c=context(1,(2,))
    before=repr(c)
    with pytest.raises(ValueError):
        invoke(c,Frame(1,new_ready_route_ids=(11,11)))
    assert repr(c)==before
