"""Output start grants are finite claims, not memory effects or real scheduler cycles."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_simulator.atomic_emission_admission_v0 import AtomicEmissionGroupV0
from spk_simulator.output_start_reservation_v0 import (
    OutputStartLedgerV0 as Ledger, OutputStartReservationV0 as Reservation,
    reserve_output_starts_v0 as reserve, cancel_output_start_v0 as cancel,
    confirm_output_publications_v0 as confirm, output_start_usage_v0 as usage,
)
from spk_simulator.backpressure_boundary_v0 import (
    BackpressureBoundaryActionsV0, advance_backpressure_boundary_v0,
)
from tests.test_atomic_emission_offer_plan_v0 import fixture


def ctx(*, slots=2, count=0):
    a, m, adm, boundary = fixture(output_slots=slots, count=count)
    return a, m, adm, boundary, Ledger(a.profile_id, adm.epoch_id)


def grant(c, ids):
    a,m,adm,boundary,ledger = c
    return reserve(a,adm,boundary.storage,ledger,ids)


def offered(c, ids):
    a,m,adm,boundary,_=c
    groups={g.emission_request_id:g for g in adm.groups}
    route_ids=tuple(sorted(i for rid in ids for i in groups[rid].route_request_ids))
    return advance_backpressure_boundary_v0(
        a,m,boundary,service_boundary=0,
        actions=BackpressureBoundaryActionsV0(routed_offers=route_ids),
    ).state.storage


def test_empty_snapshot_has_full_free_capacity():
    a,m,adm,b,ledger=ctx()
    assert [(x.pe_id,x.occupied,x.reserved,x.free) for x in usage(a,adm,b.storage,ledger)] == [
        ('PE0',0,0,2),('PE1',0,0,2)]


def test_reserve_single_emission_accounts_slots():
    c=ctx()
    out=grant(c,(1,))
    assert out.granted_emission_ids==(1,)
    assert out.blocked_emission_ids==()
    assert [(x.pe_id,x.free) for x in usage(c[0],c[2],c[3].storage,out.ledger)]==[
        ('PE0',1),('PE1',2)]


def test_no_physical_spike_is_created_at_service_start():
    c=ctx()
    old=c[3].storage
    result=grant(c,(1,2))
    assert old==c[3].storage
    assert result.ledger.active==(Reservation(1,'PE0',1),)
    assert result.blocked_emission_ids==(2,)


def test_multiple_competing_emissions_grant_only_one():
    assert grant(ctx(),(1,2)).granted_emission_ids==(1,)
    assert grant(ctx(),(1,2)).blocked_emission_ids==(2,)


def test_input_order_does_not_change_priority():
    c=ctx()
    assert grant(c,(2,1))==grant(c,(1,2))


def test_exact_capacity_for_two_slot_fanout():
    c=ctx()
    out=grant(c,(2,))
    assert out.granted_emission_ids==(2,)
    assert usage(c[0],c[2],c[3].storage,out.ledger)[0].free==0


def test_independent_pe_reservations_do_not_contend():
    c=ctx()
    a,m,adm,b,ledger=c
    other=AtomicEmissionGroupV0(3,'PE1','X',4,(),0,2)
    adm=replace(adm,groups=adm.groups+(other,),zero_fanout_emission_count=1)
    res=reserve(a,adm,b.storage,ledger,(2,3))
    assert res.granted_emission_ids==(2,3)


def test_zero_fanout_emission_needs_no_slots():
    c=ctx()
    a,m,adm,b,ledger=c
    other=AtomicEmissionGroupV0(3,'PE0','X',4,(),0,2)
    adm=replace(adm,groups=adm.groups+(other,),zero_fanout_emission_count=1)
    res=reserve(a,adm,b.storage,ledger,(2,3))
    assert res.granted_emission_ids==(2,3)
    assert usage(a,adm,b.storage,res.ledger)[0].reserved==2


def test_duplicate_start_rejected():
    c=ctx()
    led=grant(c,(1,)).ledger
    with pytest.raises(ValueError,match='already reserved'):
        reserve(c[0],c[2],c[3].storage,led,(1,))


def test_unknown_start_rejected():
    with pytest.raises(ValueError,match='unknown'):
        grant(ctx(),(999,))

@pytest.mark.parametrize('ids', [None,[],(-1,),(True,),(1,1),('1',)])
def test_bad_ready_ids_fail_closed(ids):
    with pytest.raises(ValueError):
        grant(ctx(),ids)


def test_cancel_frees_output_capacity():
    c=ctx()
    led=grant(c,(1,)).ledger
    free=cancel(c[0],c[2],c[3].storage,led,1)
    assert grant((*c[:4],free),(2,)).granted_emission_ids==(2,)


def test_double_cancel_is_invalid():
    c=ctx()
    led=grant(c,(1,)).ledger
    cleared=cancel(c[0],c[2],c[3].storage,led,1)
    with pytest.raises(ValueError,match='no active'):
        cancel(c[0],c[2],c[3].storage,cleared,1)


def test_cannot_cancel_after_storage_already_published():
    c=ctx()
    led=grant(c,(1,)).ledger
    after=offered(c,(1,))
    with pytest.raises(ValueError,match='physically published'):
        cancel(c[0],c[2],after,led,1)


def test_confirm_requires_exact_route_occurrences():
    c=ctx()
    led=grant(c,(2,)).ledger
    after=offered(c,(2,))
    committed=confirm(c[0],c[2],c[3].storage,after,led,(2,))
    assert committed.active==()
    assert committed.completed_emission_ids==(2,)
    assert usage(c[0],c[2],after,committed)[0].occupied==2


def test_can_replay_committed_emission_as_completed_but_not_new_start():
    c=ctx()
    led=grant(c,(1,)).ledger
    after=offered(c,(1,))
    done=confirm(c[0],c[2],c[3].storage,after,led,(1,))
    with pytest.raises(ValueError,match='already reserved'):
        reserve(c[0],c[2],after,done,(1,))


def test_partial_bundle_rejected():
    c=ctx()
    led=grant(c,(2,)).ledger
    after=replace(c[3].storage,pending_output=(c[1].routes[1].occurrence,))
    with pytest.raises(ValueError,match='incomplete'):
        confirm(c[0],c[2],c[3].storage,after,led,(2,))


def test_confirm_without_start_grant_rejected():
    c=ctx()
    with pytest.raises(ValueError,match='lacks start'):
        confirm(c[0],c[2],c[3].storage,offered(c,(1,)),c[4],(1,))


def test_unsolicited_new_route_rejected():
    c=ctx(slots=3)
    led=grant(c,(1,)).ledger
    with pytest.raises(ValueError,match='mismatch'):
        confirm(c[0],c[2],c[3].storage,offered(c,(1,2)),led,(1,))


def test_no_commit_ids_cannot_change_storage():
    c=ctx()
    with pytest.raises(ValueError,match='unexpected'):
        confirm(c[0],c[2],c[3].storage,offered(c,(1,)),c[4],())


def test_can_reserve_followup_after_consumption_of_prior_group():
    c=ctx(slots=2)
    a,m,adm,b,led=c
    first=grant(c,(2,)).ledger
    after=offered(c,(2,))
    done=confirm(a,adm,b.storage,after,first,(2,))
    # Cannot start another group while output has no free space.
    assert reserve(a,adm,after,done,(1,)).blocked_emission_ids==(1,)
    moved=replace(after,pending_output=(),admitted_events=after.pending_output)
    assert reserve(a,adm,moved,done,(1,)).granted_emission_ids==(1,)


def test_corrupted_reservation_exceeds_capacity_rejected():
    c=ctx()
    bad=Ledger(c[0].profile_id,c[2].epoch_id,(
        Reservation(1,'PE0',1),Reservation(2,'PE0',2),
    ))
    with pytest.raises(ValueError,match='exceed capacity'):
        usage(c[0],c[2],c[3].storage,bad)


def test_wrong_profile_or_epoch_rejected():
    c=ctx()
    with pytest.raises(ValueError,match='profile mismatch'):
        usage(c[0],c[2],c[3].storage,Ledger('other',c[2].epoch_id))
    with pytest.raises(ValueError,match='epoch mismatch'):
        usage(c[0],c[2],c[3].storage,Ledger(c[0].profile_id,'other'))


def test_malformed_group_capacity_rejected():
    c=ctx()
    adm=replace(c[2],groups=(replace(c[2].groups[0],output_capacity=777),c[2].groups[1]))
    with pytest.raises(ValueError,match='group'):
        usage(c[0],adm,c[3].storage,c[4])


def test_duplicate_ledger_identity_rejected():
    with pytest.raises(ValueError,match='noncanonical'):
        Ledger('p','e',(Reservation(1,'PE0',1),Reservation(1,'PE0',1)))


def test_released_original_snapshot_is_immutable():
    c=ctx()
    led=grant(c,(1,)).ledger
    with pytest.raises((FrozenInstanceError,AttributeError)):
        led.profile_id='hack'
    assert c[4].active==()


def test_invalid_input_does_not_mutate_ledger():
    c=ctx()
    led=grant(c,(1,)).ledger
    before=repr(led)
    with pytest.raises(ValueError):
        reserve(c[0],c[2],c[3].storage,led,(999,))
    assert repr(led)==before


def test_new_identity_in_tombstone_does_not_prove_output_publication():
    c=ctx()
    led=grant(c,(1,)).ledger
    forged=replace(c[3].storage,consumed_ids=(10,))
    with pytest.raises(ValueError,match='occupy OUTPUT'):
        confirm(c[0],c[2],c[3].storage,forged,led,(1,))


def test_new_identity_in_destination_does_not_prove_output_publication():
    c=ctx()
    led=grant(c,(1,)).ledger
    forged=replace(c[3].storage,admitted_events=(c[1].routes[0].occurrence,))
    with pytest.raises(ValueError,match='occupy OUTPUT'):
        confirm(c[0],c[2],c[3].storage,forged,led,(1,))


def test_new_output_from_wrong_source_rejected():
    c=ctx()
    led=grant(c,(1,)).ledger
    forged_occ=replace(c[1].routes[0].occurrence,source_pe_id='PE1')
    forged=replace(c[3].storage,pending_output=(forged_occ,))
    with pytest.raises(ValueError,match='wrong source'):
        confirm(c[0],c[2],c[3].storage,forged,led,(1,))
