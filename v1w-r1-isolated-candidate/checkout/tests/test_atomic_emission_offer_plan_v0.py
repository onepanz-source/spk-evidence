"""Atomic source OUTPUT admission. Uses repository-native storage and routing fixtures."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_simulator.atomic_emission_admission_v0 import (
    AtomicEmissionAdmissionV0, AtomicEmissionGroupV0,
)
from spk_simulator.atomic_emission_offer_plan_v0 import (
    AtomicEmissionOfferPlanV0, plan_atomic_emission_offers_v0,
)
from spk_simulator.backpressure_boundary_v0 import (
    BackpressureBoundaryStateV0, BackpressureBoundaryActionsV0,
    advance_backpressure_boundary_v0,
)
from tests.test_backpressure_arbiter_v0 import setup


def fixture(*, output_slots=2, count=0, two_groups=True):
    arch, manifest, storage, ledger, arbiter = setup(capacity=3, count=count)
    arch = replace(arch, pes=tuple(replace(p, output_slots=output_slots) for p in arch.pes))
    ledger = replace(ledger, ingress=replace(ledger.ingress, arrivals=(), batch_releases=()))
    if two_groups:
        routes = tuple(
            replace(r, occurrence=replace(r.occurrence,
                emission_event_time=3, source_node_id='C')) if i else r
            for i, r in enumerate(manifest.routes)
        )
        manifest = replace(manifest, routes=routes)
        groups = (
            AtomicEmissionGroupV0(1, 'PE0', 'A', 2, (10,), 1, output_slots),
            AtomicEmissionGroupV0(2, 'PE0', 'C', 3, (11, 12), 2, output_slots),
        )
    else:
        groups = (AtomicEmissionGroupV0(1, 'PE0', 'A', 2, (10, 11, 12), 3, output_slots),)
    admission = AtomicEmissionAdmissionV0(
        manifest.profile_id, manifest.epoch_id, groups, 3, 0,
    )
    state = BackpressureBoundaryStateV0(storage, ledger, arbiter)
    return arch, manifest, admission, state


def plan(ctx, **kwargs):
    return plan_atomic_emission_offers_v0(*ctx, **kwargs)


def test_no_ready_emission_is_noop():
    ctx = fixture()
    out = plan(ctx)
    assert out.admitted_emission_ids == ()
    assert out.routed_offers == ()
    assert out.pe_free_after == (('PE0', 2), ('PE1', 2))


def test_atomic_group_fits_and_keeps_duplicates_distinct():
    out = plan(fixture(), ready_emission_ids=(2,))
    assert out.admitted_emission_ids == (2,)
    assert out.routed_offers == (11, 12)
    assert out.blocked == ()


def test_two_groups_do_not_overcommit_shared_pe():
    out = plan(fixture(), ready_emission_ids=(2, 1))
    assert out.admitted_emission_ids == (1,)
    assert out.routed_offers == (10,)
    assert [(b.emission_request_id, b.required_output_slots, b.free_output_slots)
            for b in out.blocked] == [(2, 2, 1)]
    assert dict(out.pe_free_after)['PE0'] == 1


def test_existing_source_occupant_blocks_later_atomic_emission():
    out = plan(fixture(count=1), ready_emission_ids=(2,))
    assert out.admitted_emission_ids == ()
    assert out.blocked[0].free_output_slots == 1


def test_after_source_slot_release_blocked_group_can_retry():
    ctx = fixture(count=1)
    first = plan(ctx, ready_emission_ids=(2,))
    assert len(first.blocked) == 1
    state = ctx[3]
    released = replace(state, storage=replace(
        state.storage, pending_output=(), consumed_ids=(10,),
    ))
    second = plan(ctx[:3] + (released,), ready_emission_ids=(2,))
    assert second.routed_offers == (11, 12)


def test_plan_does_not_mutate_caller_state():
    ctx = fixture()
    before = repr(ctx)
    plan(ctx, ready_emission_ids=(1, 2))
    assert repr(ctx) == before


def test_plan_determinism_and_input_order_independence():
    ctx = fixture()
    assert plan(ctx, ready_emission_ids=(1, 2)) == plan(ctx, ready_emission_ids=(2, 1))


def test_selected_offers_integrate_with_boundary_controller():
    ctx = fixture()
    offer = plan(ctx, ready_emission_ids=(2,))
    result = advance_backpressure_boundary_v0(
        ctx[0], ctx[1], ctx[3], service_boundary=0,
        actions=BackpressureBoundaryActionsV0(routed_offers=offer.routed_offers),
    )
    assert tuple(e.event_id for e in result.state.storage.pending_output) == (11, 12)
    assert result.pe_usage[0].pending_output == 2


def test_no_partial_publication_when_output_insufficient():
    ctx = fixture(count=1)
    offer = plan(ctx, ready_emission_ids=(2,))
    result = advance_backpressure_boundary_v0(
        ctx[0], ctx[1], ctx[3], service_boundary=0,
        actions=BackpressureBoundaryActionsV0(routed_offers=offer.routed_offers),
    )
    assert tuple(e.event_id for e in result.state.storage.pending_output) == (10,)


def test_reoffer_existing_complete_group_rejected():
    ctx = fixture(count=1)
    with pytest.raises(ValueError, match='published'):
        plan(ctx, ready_emission_ids=(1,))


def test_reoffer_partially_published_group_rejected():
    ctx = fixture(output_slots=3, count=1, two_groups=False)
    with pytest.raises(ValueError, match='partially'):
        plan(ctx, ready_emission_ids=(1,))


def test_full_atomic_group_permitted_at_exact_capacity():
    out = plan(fixture(output_slots=3, two_groups=False), ready_emission_ids=(1,))
    assert out.routed_offers == (10, 11, 12)
    assert dict(out.pe_free_after)['PE0'] == 0


def test_empty_group_accepted_without_output_capacity():
    ctx = fixture()
    extra = AtomicEmissionGroupV0(3, 'PE1', 'D', 6, (), 0, 2)
    adm = replace(ctx[2], groups=ctx[2].groups + (extra,), zero_fanout_emission_count=1)
    out = plan((ctx[0], ctx[1], adm, ctx[3]), ready_emission_ids=(3,))
    assert out.admitted_emission_ids == (3,)
    assert out.routed_offers == ()


@pytest.mark.parametrize('bad', [None, [], (1, 1), (True,), (-1,), ('1',)])
def test_invalid_ready_id_containers_rejected(bad):
    with pytest.raises(ValueError):
        plan(fixture(), ready_emission_ids=bad)


def test_unknown_ready_emission_rejected():
    with pytest.raises(ValueError, match='unknown'):
        plan(fixture(), ready_emission_ids=(999,))


def test_manifest_route_coverage_rejected():
    ctx = fixture()
    with pytest.raises(ValueError, match='coverage'):
        plan((ctx[0], replace(ctx[1], routes=ctx[1].routes[:2]), ctx[2], ctx[3]))


def test_corrupted_group_route_identity_rejected():
    ctx = fixture()
    g = replace(ctx[2].groups[1], source_pe_id='PE1')
    with pytest.raises(ValueError, match='mismatch'):
        plan((ctx[0], ctx[1], replace(ctx[2], groups=(ctx[2].groups[0], g)), ctx[3]))


def test_duplicate_logical_emission_group_rejected():
    ctx = fixture()
    g = replace(ctx[2].groups[1], emission_event_time=2, source_node_id='A')
    with pytest.raises(ValueError, match='duplicate logical'):
        plan((ctx[0], ctx[1], replace(ctx[2], groups=(ctx[2].groups[0], g)), ctx[3]))


def test_wrong_epoch_rejected():
    ctx = fixture()
    with pytest.raises(ValueError, match='epoch'):
        plan((ctx[0], ctx[1], replace(ctx[2], epoch_id='E1'), ctx[3]))


def test_wrong_architecture_type_rejected():
    ctx = fixture()
    with pytest.raises(TypeError):
        plan((None,) + ctx[1:])


def test_frozen_result():
    out = plan(fixture(), ready_emission_ids=(1,))
    with pytest.raises((FrozenInstanceError, AttributeError)):
        out.blocked = ()


def test_no_event_time_mutation():
    ctx = fixture()
    old = tuple(r.occurrence.emission_event_time for r in ctx[1].routes)
    plan(ctx, ready_emission_ids=(1, 2))
    assert old == tuple(r.occurrence.emission_event_time for r in ctx[1].routes)


def test_independent_pe_may_publish_while_another_is_full():
    arch, manifest, adm, state = fixture(output_slots=1)
    routes = list(manifest.routes)
    routes[2] = replace(routes[2], occurrence=replace(
        routes[2].occurrence, source_pe_id='PE1', source_node_id='D',
        emission_event_time=4,
    ))
    manifest = replace(manifest, routes=tuple(routes))
    groups = (
        AtomicEmissionGroupV0(1, 'PE0', 'A', 2, (10,), 1, 1),
        AtomicEmissionGroupV0(2, 'PE0', 'C', 3, (11,), 1, 1),
        AtomicEmissionGroupV0(3, 'PE1', 'D', 4, (12,), 1, 1),
    )
    adm = replace(adm, groups=groups)
    out = plan((arch, manifest, adm, state), ready_emission_ids=(3, 2, 1))
    assert out.admitted_emission_ids == (1, 3)
    assert out.routed_offers == (10, 12)
    assert [b.emission_request_id for b in out.blocked] == [2]
    assert dict(out.pe_free_after) == {'PE0': 0, 'PE1': 0}


def test_corrupted_waiting_route_without_source_owner_rejected():
    ctx = fixture()
    state = replace(ctx[3], arbiter=replace(
        ctx[3].arbiter, last_service_boundary=0, waiting_route_ids=(10,),
    ))
    with pytest.raises(ValueError, match='waiting route ownership'):
        plan(ctx[:3] + (state,))


def test_incorrect_output_capacity_in_group_rejected():
    ctx = fixture()
    bad_group = replace(ctx[2].groups[1], output_capacity=99)
    with pytest.raises(ValueError, match='capacity'):
        plan((ctx[0], ctx[1], replace(ctx[2], groups=(ctx[2].groups[0], bad_group)), ctx[3]))
