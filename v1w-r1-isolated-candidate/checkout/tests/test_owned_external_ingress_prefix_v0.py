"""Closed finite external input prefix, witnessed by real boundary ownership."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_simulator.owned_external_ingress_prefix_v0 import (
    ExternalPrefixQueryV0 as Q,
    seal_finite_external_ingress_v0 as seal,
    analyze_owned_external_prefix_v0 as assess,
)
from tests.test_backpressure_boundary_v0 import (
    fixture, advance, next_ctx,
)
from tests.test_dynamic_destination_inventory_v0 import context


def setup(*, external=True, capacity=2):
    ctx=fixture(count=0, external=external, capacity=capacity)
    net=context()[1].allocation_ledger.network
    a,m,b=ctx
    root=seal(a,net,b.ledger.ingress)
    return ctx,root,net


def run(ctx,root, *items):
    a,m,b=ctx
    return assess(a,root,m,b,queries=tuple(Q(n,t) for n,t in items))


def row(ctx,root,node='A',t=2):
    return run(ctx,root,(node,t)).evidences[0]


def extended(ctx, *, extra_time=2, extra_boundary=2, channel=2):
    a,m,b=ctx
    old=b.ledger.ingress
    extra=replace(old.arrivals[0],input_index=1,event_time=extra_time,
                  arrival_boundary=extra_boundary,channel=channel)
    releases=(replace(old.batch_releases[0], input_indices=(0,1),
                      ready_boundary=max(0,extra_boundary)),)
    binding=replace(old,arrivals=(old.arrivals[0],extra),batch_releases=releases)
    return (a,m,replace(b,ledger=replace(b.ledger,ingress=binding)))


def test_initial_nonempty_input_is_pending():
    ctx,s,_=setup()
    z=row(ctx,s)
    assert z.status=='PENDING_EXTERNAL_INPUT'
    assert z.pending_input_indices==(0,)
    assert not z.supports_consume_admission


def test_boundary_owned_arrival_settles_prefix():
    ctx,s,_=setup()
    after=advance(ctx,0,external_arrivals=(0,))
    z=row(next_ctx(ctx,after),s)
    assert z.status=='ACCOUNTED_SEALED_PREFIX'
    assert z.sealed_prefix_accounted
    assert z.resident_input_indices==(0,)
    assert z.pending_input_indices==()
    assert not z.supports_consume_admission


def test_consume_tombstone_preserves_prefix_evidence():
    ctx,s,_=setup()
    one=advance(ctx,0,external_arrivals=(0,))
    two=advance(next_ctx(ctx,one),1,external_consumptions=(0,))
    z=row(next_ctx(ctx,two),s)
    assert z.consumed_input_indices==(0,)
    assert z.resident_input_indices==()
    assert z.sealed_prefix_accounted


def test_empty_sealed_input_is_vacuously_accounted():
    ctx,s,_=setup(external=False)
    z=row(ctx,s,'A',2000)
    assert z.known_input_indices==()
    assert z.sealed_prefix_accounted
    assert not z.supports_consume_admission


def test_earlier_time_excludes_later_external_event():
    ctx,s,_=setup()
    z=row(ctx,s,'A',1)
    assert z.known_input_indices==()
    assert z.sealed_prefix_accounted


def test_other_node_independent():
    ctx,s,_=setup()
    assert row(ctx,s,'B',999).sealed_prefix_accounted
    assert not row(ctx,s,'A',2).sealed_prefix_accounted


def test_input_can_arrive_later_in_service_time_without_shifting_event_time():
    ctx,s,_=setup()
    a,m,b=ctx
    old=b.ledger.ingress
    shifted=replace(old,arrivals=(replace(old.arrivals[0],arrival_boundary=3),),
                    batch_releases=(replace(old.batch_releases[0],ready_boundary=3),))
    ctx=(a,m,replace(b,ledger=replace(b.ledger,ingress=shifted)))
    s=seal(a,context()[1].allocation_ledger.network,shifted)
    assert not row(ctx,s).sealed_prefix_accounted
    before=advance(ctx,0)
    assert not row(next_ctx(ctx,before),s).sealed_prefix_accounted
    at_three=advance(next_ctx(ctx,before),3,external_arrivals=(0,))
    assert row(next_ctx(ctx,at_three),s).sealed_prefix_accounted
    assert row(next_ctx(ctx,at_three),s).settled_through_event_time==2


def test_multiple_input_multiplicity_requires_every_occurrence():
    ctx,_,net=setup()
    ctx=extended(ctx,extra_time=2,extra_boundary=2)
    a,m,b=ctx
    s=seal(a,net,b.ledger.ingress)
    one=advance(ctx,0,external_arrivals=(0,))
    z=row(next_ctx(ctx,one),s)
    assert z.known_input_indices==(0,1)
    assert z.resident_input_indices==(0,)
    assert z.pending_input_indices==(1,)
    assert not z.sealed_prefix_accounted
    two=advance(next_ctx(ctx,one),2,external_arrivals=(1,))
    assert row(next_ctx(ctx,two),s).sealed_prefix_accounted


def test_future_logical_input_does_not_block_earlier_prefix():
    ctx,_,net=setup()
    ctx=extended(ctx,extra_time=9,extra_boundary=2)
    a,m,b=ctx
    s=seal(a,net,b.ledger.ingress)
    one=advance(ctx,0,external_arrivals=(0,))
    r=next_ctx(ctx,one)
    assert row(r,s,t=2).sealed_prefix_accounted
    assert not row(r,s,t=9).sealed_prefix_accounted


def test_boundary_after_future_arrival_maintains_past_prefix():
    ctx,_,net=setup()
    ctx=extended(ctx,extra_time=9,extra_boundary=2)
    a,m,b=ctx
    s=seal(a,net,b.ledger.ingress)
    one=advance(ctx,0,external_arrivals=(0,))
    two=advance(next_ctx(ctx,one),2,external_arrivals=(1,))
    assert row(next_ctx(ctx,two),s,t=2).known_input_indices==(0,)


def test_queries_sorted_deterministically():
    ctx,s,_=setup()
    assert run(ctx,s,('B',5),('A',2))==run(ctx,s,('A',2),('B',5))


def test_empty_queries_do_not_authorize_anything():
    ctx,s,_=setup()
    x=run(ctx,s)
    assert x.evidences==()
    assert not x.supports_consume_admission


def test_result_always_refuses_batch_admission():
    ctx,s,_=setup()
    one=advance(ctx,0,external_arrivals=(0,))
    z=run(next_ctx(ctx,one),s,('A',2))
    assert z.evidences[0].sealed_prefix_accounted
    assert not z.supports_consume_admission
    assert not z.evidences[0].supports_consume_admission


def test_preexisting_snapshot_unchanged_by_assessment():
    ctx,s,_=setup()
    before=(ctx,s)
    run(ctx,s,('A',2))
    assert (ctx,s)==before


def test_stale_seal_rejected_when_ingress_changes():
    ctx,s,_=setup()
    altered=extended(ctx)
    with pytest.raises(ValueError,match='seal modified'):
        run(altered,s,('A',2))


def test_accounted_before_service_boundary_rejected():
    ctx,s,_=setup()
    a,m,b=ctx
    bad=replace(b,ledger=replace(b.ledger,external_resident=(0,)))
    with pytest.raises(ValueError,match='before its SERVICE_TIME'):
        run((a,m,bad),s,('A',2))


def test_fabricated_consumed_before_service_boundary_rejected():
    ctx,s,_=setup()
    a,m,b=ctx
    bad=replace(b,ledger=replace(b.ledger,external_consumed=(0,)))
    with pytest.raises(ValueError,match='before its SERVICE_TIME'):
        run((a,m,bad),s,('A',2))


def test_missing_due_ingress_rejected_even_if_query_is_earlier():
    ctx,s,_=setup()
    a,m,b=ctx
    bad=replace(b,arbiter=replace(b.arbiter,last_service_boundary=0))
    with pytest.raises(ValueError,match='due external'):
        run((a,m,bad),s,('A',1))


def test_unknown_external_identity_rejected_by_capacity_audit():
    ctx,s,_=setup()
    a,m,b=ctx
    bad=replace(b,ledger=replace(b.ledger,external_resident=(999,)))
    with pytest.raises(ValueError,match='external occurrence not bound'):
        run((a,m,bad),s,('A',2))


def test_wrong_epoch_rejected():
    ctx,s,_=setup()
    with pytest.raises(ValueError,match='epoch'):
        run(ctx,replace(s,epoch_id='OTHER'),('A',2))


def test_wrong_profile_rejected():
    ctx,s,_=setup()
    with pytest.raises(ValueError,match='profile'):
        run(ctx,replace(s,profile_id='OTHER'),('A',2))


def test_unknown_query_node_rejected():
    ctx,s,_=setup()
    with pytest.raises(ValueError,match='unknown node'):
        run(ctx,s,('MISSING',2))


def test_duplicate_query_rejected():
    ctx,s,_=setup()
    with pytest.raises(ValueError,match='duplicate prefix'):
        run(ctx,s,('A',2),('A',2))


@pytest.mark.parametrize('bad',[-1,True,2.5,'2',None])
def test_query_invalid_event_time_rejected(bad):
    with pytest.raises(ValueError,match='EVENT_TIME'):
        Q('A',bad)


@pytest.mark.parametrize('bad',['',' A','A ',None,4])
def test_query_invalid_node_rejected(bad):
    with pytest.raises(ValueError,match='target'):
        Q(bad,2)


def test_invalid_query_collection_rejected():
    ctx,s,_=setup()
    with pytest.raises(TypeError,match='queries'):
        assess(ctx[0],s,ctx[1],ctx[2],queries=[Q('A',2)])


def test_invalid_query_item_rejected():
    ctx,s,_=setup()
    with pytest.raises(TypeError,match='queries'):
        assess(ctx[0],s,ctx[1],ctx[2],queries=('A',))


def test_noncanonical_external_schedule_rejected_at_seal():
    ctx,s,n=setup()
    a,m,b=ctx
    arrival=b.ledger.ingress.arrivals[0]
    altered=replace(b.ledger.ingress,arrivals=(replace(arrival,input_index=1),))
    with pytest.raises(ValueError,match='noncanonical sealed'):
        seal(a,n,altered)


def test_wrong_network_target_rejected_at_seal():
    ctx,s,n=setup()
    a,m,b=ctx
    altered=replace(b.ledger.ingress,arrivals=(replace(b.ledger.ingress.arrivals[0],node_id='UNKNOWN'),))
    with pytest.raises(ValueError,match='invalid sealed arrival'):
        seal(a,n,altered)


def test_negative_service_release_rejected_at_seal():
    ctx,s,n=setup()
    a,m,b=ctx
    altered=replace(b.ledger.ingress,
                    batch_releases=(replace(b.ledger.ingress.batch_releases[0],ready_boundary=-1),))
    with pytest.raises(ValueError,match='invalid sealed batch release'):
        seal(a,n,altered)


def test_wrong_batch_consuming_request_rejected_at_seal():
    ctx,s,n=setup()
    a,m,b=ctx
    altered=replace(b.ledger.ingress,
                    batch_releases=(replace(b.ledger.ingress.batch_releases[0],consume_request_id=501),))
    with pytest.raises(ValueError,match='inconsistent sealed'):
        seal(a,n,altered)


def test_uncovered_input_rejected_at_seal():
    ctx,s,n=setup()
    a,m,b=ctx
    altered=replace(b.ledger.ingress,batch_releases=())
    with pytest.raises(ValueError,match='does not cover all'):
        seal(a,n,altered)


def test_immutable_evidence_and_seal():
    ctx,s,_=setup()
    with pytest.raises((AttributeError,FrozenInstanceError)):
        s.epoch_id='MODIFIED'
    with pytest.raises((AttributeError,FrozenInstanceError)):
        row(ctx,s).status='CLOSED'


def test_bad_root_type_rejected():
    ctx,s,_=setup()
    with pytest.raises(TypeError,match='seal'):
        assess(ctx[0],None,ctx[1],ctx[2],queries=(Q('A',2),))


def test_bad_snapshot_type_rejected():
    ctx,s,_=setup()
    with pytest.raises(TypeError,match='boundary'):
        assess(ctx[0],s,ctx[1],None,queries=(Q('A',2),))


def test_outside_epoch_cannot_be_inferred_from_this_seal():
    ctx,s,_=setup()
    assert s.epoch_id=='E0'
    assert row(ctx,s,'B',100).sealed_prefix_accounted
    assert not row(ctx,s,'B',100).supports_consume_admission
