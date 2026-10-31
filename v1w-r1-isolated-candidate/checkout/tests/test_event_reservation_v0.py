"""S3.7d/1: finite, provenance-bound event-slot claims."""
from dataclasses import FrozenInstanceError, replace

import pytest

from spk_network.events_v0 import NetworkEventV0
from spk_simulator.event_storage_v0 import RoutedStorageStateV0
from spk_simulator.external_ingress_v0 import (
    ExternalArrivalV0, ExternalIngressPlanV0, ExternalIngressBindingV0,
    BoundExternalArrivalV0, bind_external_ingress_v0,
)
from spk_simulator.routing_binding_v0 import offer_bound_routed_event_v0
from spk_simulator.event_reservation_v0 import (
    EventSlotUnavailableV0, EventReservationStateV0,
    event_reservation_usage_v0, reserve_routed_event_slot_v0,
    cancel_routed_event_slot_v0, commit_routed_event_slot_v0,
    arrive_external_event_slot_v0, consume_external_event_slot_v0,
    consume_reserved_routed_event_v0,
)
from tests.test_routing_binding_v0 import setup_case


def case(*, capacity=3, target_external=False, same_pe=False):
    initial = (NetworkEventV0(2, 'A', 0),)
    # Share event_slots with a genuine initial A occurrence on PE0.
    if target_external:
        same_pe = True
    args, binding, storage = setup_case(
        events=capacity, output=4, initial=initial, same_pe=same_pe,
    )
    network, observed, placement, plan, provenance, initial, architecture = args
    ingress = bind_external_ingress_v0(
        plan, provenance, initial,
        ExternalIngressPlanV0(tuple(ExternalArrivalV0(i, i * 2) for i in range(len(initial)))),
    )
    ledger = EventReservationStateV0(architecture.profile_id, binding.epoch_id, ingress)
    return architecture, binding, storage, ledger


def route(case_tuple, i=0):
    _, binding, _, _ = case_tuple
    return binding.routes[i].route_request_id


def offered(c, *indices):
    architecture, binding, storage, ledger = c
    for index in indices:
        storage = offer_bound_routed_event_v0(
            architecture, storage, binding, route(c, index),
        )
    return architecture, binding, storage, ledger


def usage(c, pe_id='PE1'):
    a,b,s,l=c
    return next(x for x in event_reservation_usage_v0(a,s,b,l) if x.pe_id == pe_id)


def reserve(c, i=0):
    a,b,s,l=c
    return a,b,s,reserve_routed_event_slot_v0(a,s,b,l,route(c,i))


def commit(c, i=0):
    a,b,s,l=c
    next_storage, next_ledger=commit_routed_event_slot_v0(a,s,b,l,route(c,i))
    return a,b,next_storage,next_ledger


def consume(c, i=0):
    a,b,s,l=c
    rid=route(c,i)
    return a,b,consume_reserved_routed_event_v0(
        a,s,b,l,rid,consume_request_id=b.get(rid).consume_request_id,
    ),l


def test_empty_claims():
    c=case()
    assert usage(c).claimed == 0
    assert usage(c).free == 3


def test_reservation_retains_output_and_claims_destination():
    c=offered(case(),0)
    r=reserve(c)
    assert r[2] == c[2]
    assert len(r[2].pending_output) == 1
    assert usage(r).reserved == 1
    assert usage(r).routed_admitted == 0


def test_commit_transfers_atomically():
    c=commit(reserve(offered(case(),0)))
    assert len(c[2].pending_output) == 0
    assert len(c[2].admitted_events) == 1
    assert usage(c).reserved == 0
    assert usage(c).routed_admitted == 1
    assert usage(c).claimed == 1


def test_consume_frees_slot_and_retains_tombstone():
    c=consume(commit(reserve(offered(case(),0))))
    assert usage(c).free == 3
    assert c[2].consumed_ids == (route(c),)


def test_cancel_preserves_owned_spike():
    c=reserve(offered(case(),0))
    a,b,s,l=c
    cancelled=cancel_routed_event_slot_v0(a,s,b,l,route(c))
    assert cancelled.reserved_routes == ()
    assert s.pending_output
    assert usage((a,b,s,cancelled)).claimed == 0


def test_cancel_missing_reservation_rejected():
    c=offered(case(),0)
    a,b,s,l=c
    with pytest.raises(ValueError,match='no matching'):
        cancel_routed_event_slot_v0(a,s,b,l,route(c))


def test_reservation_requires_source_output():
    c=case()
    a,b,s,l=c
    with pytest.raises(ValueError,match='retained source'):
        reserve_routed_event_slot_v0(a,s,b,l,route(c))


def test_duplicate_reservation_rejected():
    c=reserve(offered(case(),0))
    a,b,s,l=c
    with pytest.raises(ValueError,match='duplicate'):
        reserve_routed_event_slot_v0(a,s,b,l,route(c))


def test_unknown_route_rejected():
    a,b,s,l=case()
    with pytest.raises(ValueError,match='unknown routed'):
        reserve_routed_event_slot_v0(a,s,b,l,99999)


def test_bool_route_identity_rejected():
    a,b,s,l=case()
    with pytest.raises(ValueError,match='invalid route'):
        reserve_routed_event_slot_v0(a,s,b,l,True)


def test_unreserved_delivery_rejected():
    c=offered(case(),0)
    a,b,s,l=c
    with pytest.raises(ValueError,match='requires a reservation'):
        commit_routed_event_slot_v0(a,s,b,l,route(c))
    assert s.pending_output and not s.admitted_events


def test_two_producers_cannot_reserve_one_slot():
    c=offered(case(capacity=1),0,1)
    c=reserve(c,0)
    a,b,s,l=c
    with pytest.raises(EventSlotUnavailableV0) as ex:
        reserve_routed_event_slot_v0(a,s,b,l,route(c,1))
    assert (ex.value.pe_id,ex.value.occupied,ex.value.capacity)==('PE1',1,1)
    assert len(s.pending_output)==2 and l.reserved_routes==(route(c,0),)


def test_routed_residency_blocks_further_reservation():
    c=commit(reserve(offered(case(capacity=1),0,1)))
    a,b,s,l=c
    with pytest.raises(EventSlotUnavailableV0):
        reserve_routed_event_slot_v0(a,s,b,l,route(c,1))
    assert len(s.pending_output) == 1


def test_after_consume_second_reservation_succeeds():
    c=consume(commit(reserve(offered(case(capacity=1),0,1))))
    assert usage(reserve(c,1)).claimed == 1


def test_reserved_capacity_blocks_external_arrival():
    c=reserve(offered(case(capacity=1,target_external=True),0))
    a,b,s,l=c
    with pytest.raises(EventSlotUnavailableV0):
        arrive_external_event_slot_v0(a,s,b,l,0)
    assert l.external_resident == ()


def test_external_residency_blocks_route_reservation():
    c=offered(case(capacity=1,target_external=True),0)
    a,b,s,l=c
    l=arrive_external_event_slot_v0(a,s,b,l,0)
    with pytest.raises(EventSlotUnavailableV0):
        reserve_routed_event_slot_v0(a,s,b,l,route(c))
    assert len(s.pending_output)==1


def test_external_consume_releases_capacity():
    c=offered(case(capacity=1,target_external=True),0)
    a,b,s,l=c
    l=arrive_external_event_slot_v0(a,s,b,l,0)
    external=next(e for e in l.ingress.arrivals if e.input_index==0)
    l=consume_external_event_slot_v0(a,s,b,l,0,consume_request_id=external.consume_request_id)
    assert l.external_consumed == (0,)
    assert usage((a,b,s,l),'PE0').free == 1
    assert reserve_routed_event_slot_v0(a,s,b,l,route(c)).reserved_routes == (route(c),)


def test_duplicate_external_arrival_rejected():
    a,b,s,l=case(target_external=True)
    l=arrive_external_event_slot_v0(a,s,b,l,0)
    with pytest.raises(ValueError,match='already accounted'):
        arrive_external_event_slot_v0(a,s,b,l,0)


def test_consumed_external_cannot_reenter():
    a,b,s,l=case(target_external=True)
    l=arrive_external_event_slot_v0(a,s,b,l,0)
    consume_id=next(e.consume_request_id for e in l.ingress.arrivals if e.input_index==0)
    l=consume_external_event_slot_v0(a,s,b,l,0,consume_request_id=consume_id)
    with pytest.raises(ValueError,match='already accounted'):
        arrive_external_event_slot_v0(a,s,b,l,0)


def test_wrong_external_consumer_rejected():
    a,b,s,l=case(target_external=True)
    l=arrive_external_event_slot_v0(a,s,b,l,0)
    with pytest.raises(ValueError,match='wrong external'):
        consume_external_event_slot_v0(a,s,b,l,0,consume_request_id=9999)


def test_consume_nonresident_external_rejected():
    a,b,s,l=case(target_external=True)
    with pytest.raises(ValueError,match='not resident'):
        consume_external_event_slot_v0(a,s,b,l,0,consume_request_id=0)


def test_unknown_external_rejected():
    a,b,s,l=case()
    with pytest.raises(ValueError,match='unknown external'):
        arrive_external_event_slot_v0(a,s,b,l,999)


def test_cross_epoch_ledger_rejected():
    a,b,s,l=case()
    with pytest.raises(ValueError,match='profile or epoch'):
        event_reservation_usage_v0(a,s,b,replace(l,epoch_id='E1'))


def test_forged_stored_event_rejected():
    a,b,s,l=offered(case(),0)
    forged=replace(s.pending_output[0],target_channel=9)
    with pytest.raises(ValueError,match='unbound stored'):
        event_reservation_usage_v0(a,replace(s,pending_output=(forged,)),b,l)


def test_tampered_reservation_overbooking_rejected():
    a,b,s,l=offered(case(capacity=1),0,1)
    with pytest.raises(ValueError,match='existing event claims'):
        event_reservation_usage_v0(a,s,b,replace(l,reserved_routes=tuple(sorted((route((a,b,s,l),0),route((a,b,s,l),1))))))


def test_frozen_state():
    a,b,s,l=case()
    with pytest.raises(FrozenInstanceError):
        l.epoch_id='changed'


def test_deterministic_claims_and_canonical_order():
    c=offered(case(),0,1)
    c1=reserve(reserve(c,1),0)
    c2=reserve(reserve(c,0),1)
    assert c1[3] == c2[3]
    assert c1[3].reserved_routes == tuple(sorted(c1[3].reserved_routes))


def test_invalid_external_binding_duplicate_rejected():
    a,b,s,l=case()
    bad=replace(l,ingress=ExternalIngressBindingV0(l.ingress.arrivals*2,l.ingress.batch_releases))
    with pytest.raises(ValueError,match='invalid external ingress identity'):
        event_reservation_usage_v0(a,s,b,bad)


def test_invalid_external_pe_rejected():
    a,b,s,l=case()
    first=replace(l.ingress.arrivals[0],target_pe_id='UNKNOWN')
    bad=replace(l,ingress=ExternalIngressBindingV0((first,),l.ingress.batch_releases))
    with pytest.raises(ValueError,match='invalid external ingress identity'):
        event_reservation_usage_v0(a,s,b,bad)


def test_distinct_pe_claims_do_not_block_each_other():
    c=reserve(offered(case(capacity=1),0))
    a,b,s,l=c
    l2=arrive_external_event_slot_v0(a,s,b,l,0)
    assert usage((a,b,s,l2),'PE0').claimed == 1
    assert usage((a,b,s,l2),'PE1').claimed == 1


def test_same_pe_can_reserve_when_finite_space_available():
    c=offered(case(capacity=2,same_pe=True),0)
    c=reserve(c)
    assert usage(c,'PE0').reserved==1
    assert len(c[2].pending_output)==1


def test_external_and_routed_share_two_slots():
    c=offered(case(capacity=2,target_external=True),0)
    a,b,s,l=c
    l=arrive_external_event_slot_v0(a,s,b,l,0)
    c=(a,b,s,l)
    c=reserve(c)
    assert usage(c,'PE0').claimed==2 and usage(c,'PE0').free==0
    c=commit(c)
    assert usage(c,'PE0').claimed==2 and usage(c,'PE0').routed_admitted==1


def test_reservation_missing_pending_during_validation_rejected():
    c=reserve(offered(case(),0))
    a,b,s,l=c
    with pytest.raises(ValueError,match='reservation without pending'):
        event_reservation_usage_v0(a,replace(s,pending_output=()),b,l)


def test_preexisting_claim_conflict_rejected():
    c=reserve(offered(case(capacity=1,target_external=True),0))
    a,b,s,l=c
    # Tampered immutable snapshot claims the sole slot twice.
    bad=replace(l,external_resident=(0,))
    with pytest.raises(ValueError, match='existing event claims'):
        event_reservation_usage_v0(a,s,b,bad)
