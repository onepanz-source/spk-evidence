"""Single SERVICE_TIME owner: physically admitted EVENT, real P/S and Core preparation.

Tests use actual frozen architecture and root fixtures on fwork. No preconfirmed P/S.
"""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_simulator.owned_root_single_clock_v0 import (
    OwnedRootSingleClockStateV0, RootPhysicalReadV0,
    initialize_owned_root_single_clock_v0 as init,
    advance_owned_root_single_clock_v0 as advance,
)
from tests.test_owned_root_batch_consumption_v0 import seeded


def fresh(**kw):
    return init(seeded(confirmed=(), **kw))


def to_prepared(state=None, limit=24):
    s = fresh() if state is None else state
    trail = []
    for _ in range(limit):
        step = advance(s)
        trail.append(step)
        s = step.state
        if s.prepared:
            return s, trail
    pytest.fail('single clock never produced actual P/S + consumed EVENT Core preparation')


def test_fresh_epoch_no_forged_ps_or_event_receipts():
    s = fresh()
    assert s.reads == s.witnesses == s.prepared == ()
    assert not s.shared.dynamic.transit.service.confirmed


def test_single_clock_physical_event_admission():
    step = advance(fresh())
    assert step.admitted_external_input_indices == (0,)
    assert step.state.shared.external_resident_input_indices == (0,)
    assert step.state.shared.external_consumed_input_indices == ()


def test_first_boundary_does_not_claim_instant_ps_reads():
    step = advance(fresh())
    assert step.newly_read_request_ids == ()
    assert step.state.reads == ()
    assert step.state.prepared == ()


def test_single_clock_spends_each_service_tick_once():
    s = fresh()
    for _ in range(7):
        before = s.shared.dynamic.transit.service.next_service_tick
        step = advance(s)
        assert step.service_tick == before
        assert step.state.shared.dynamic.transit.service.next_service_tick == before + 1
        assert all(x.service_tick == before for x in step.service_slices)
        s = step.state


def test_real_ps_service_both_confirmed():
    s, _ = to_prepared()
    assert {r.kind for r in s.reads} == {Kind.PROGRAM_REFERENCE, Kind.STATE_LOAD}
    assert {r.request_id for r in s.reads} == {0, 1}
    confirmed = {r.request_id for r in s.shared.dynamic.transit.service.confirmed}
    assert {0, 1, 2} <= confirmed


def test_root_batch_is_physically_consumed():
    s, _ = to_prepared()
    assert s.shared.external_resident_input_indices == ()
    assert s.shared.external_consumed_input_indices == (0,)
    assert s.witnesses[0].external_input_indices == (0,)
    assert s.witnesses[0].channels == (0,)


def test_core_prepare_uses_exact_physical_input():
    s, _ = to_prepared()
    p = s.prepared[0].transition
    assert p.channels == (0,)
    assert p.event_time == 3
    assert p.base_version == 0


def test_state_commit_is_not_preconfirmed_or_scheduled():
    s, trail = to_prepared()
    assert 3 not in {r.request_id for r in s.shared.dynamic.transit.service.confirmed}
    assert all(x.request_id != 3 for t in trail for x in t.service_slices)
    assert all(x.version == 0 for x in s.image.neurons)


def test_output_not_published():
    s, _ = to_prepared()
    assert s.shared.dynamic.transit.storage.pending_output == ()
    assert s.shared.dynamic.transit.storage.admitted_events == ()


def test_service_finish_needs_later_physical_effect():
    s = fresh()
    for _ in range(12):
        step = advance(s)
        if any(x.request_id == 2 for x in step.state.shared.dynamic.transit.service.awaiting_confirmation):
            assert 2 not in {x.request_id for x in step.state.shared.dynamic.transit.service.confirmed}
            assert step.state.shared.external_consumed_input_indices == ()
            later = advance(step.state)
            assert later.service_tick > step.service_tick
            assert later.consumed_external_input_indices == (0,)
            break
        s = step.state
    else:
        pytest.fail('BATCH_CONSUME did not finish')


def test_duplicate_channels_preserve_multiplicity():
    s, _ = to_prepared(fresh(arrivals=((4,3,0),(4,3,0))))
    assert s.witnesses[0].channels == (0,0)
    assert s.prepared[0].transition.channels == (0,0)


def test_distinct_channels_sorted():
    s, _ = to_prepared(fresh(arrivals=((4,3,3),(4,3,1))))
    assert s.witnesses[0].channels == (1,3)


def test_delayed_arrival_cannot_be_consumed_early():
    s = fresh(arrivals=((4,3,0),(6,3,1)))
    for _ in range(2):
        step = advance(s)
        assert step.state.shared.external_consumed_input_indices == ()
        s = step.state
    done, _ = to_prepared(s)
    assert done.shared.external_consumed_input_indices == (0,1)


def test_multicycle_consume_service():
    s, trail = to_prepared(fresh(units=7), limit=40)
    assert len([x for t in trail for x in t.service_slices if x.request_id == 2]) >= 2
    assert s.witnesses[0].external_input_indices == (0,)


def test_original_snapshot_immutable():
    s = fresh()
    original = s
    advance(s)
    assert s == original


def test_deterministic_successor():
    s = fresh()
    assert advance(s) == advance(s)


def test_wrong_initial_type_rejected():
    with pytest.raises(TypeError):
        init(None)


def test_wrong_step_type_rejected():
    with pytest.raises(TypeError):
        advance(None)


def test_preconfirmed_ps_fixture_rejected():
    with pytest.raises(ValueError, match='fresh, unconfirmed'):
        init(seeded())


def test_preconfirmed_consume_rejected():
    with pytest.raises(ValueError, match='fresh, unconfirmed'):
        init(seeded(confirmed=(2,)))


def test_forced_fabricated_read_without_service_rejected():
    s = fresh()
    fake = RootPhysicalReadV0(0, Kind.PROGRAM_REFERENCE, 'C', 3, 4, ('fake','fake'))
    with pytest.raises(ValueError, match='receipt without matching'):
        replace(s, reads=(fake,))


def test_dropped_witness_rejected_after_real_event_consume():
    s,_ = to_prepared()
    with pytest.raises(ValueError, match='coverage mismatch'):
        replace(s, witnesses=())


def test_modified_witness_rejected():
    s,_ = to_prepared()
    w = replace(s.witnesses[0], channels=(7,))
    with pytest.raises(ValueError):
        replace(s, witnesses=(w,))


def test_missing_ps_receipt_rejected_after_core_prepare():
    s,_ = to_prepared()
    with pytest.raises(ValueError,match='receipt coverage'):
        replace(s, reads=(s.reads[0],))


def test_mismatched_preparation_rejected():
    s,_ = to_prepared()
    fake = replace(s.prepared[0], transition=replace(s.prepared[0].transition, event_time=9))
    with pytest.raises(ValueError,match='differs from frozen'):
        replace(s, prepared=(fake,))


def test_read_value_tamper_rejected():
    s,_ = to_prepared()
    bad = replace(s.reads[0], value=('tamper',))
    with pytest.raises(ValueError):
        replace(s, reads=(bad,)+s.reads[1:])


def test_state_is_immutable():
    s = fresh()
    with pytest.raises(FrozenInstanceError):
        s.image = None


def test_nonroot_initialization_rejected():
    # Explicitly reject any root fixture where the supposed root has an inbound edge.
    from spk_network.model_v0 import NetworkEdgeV0
    s = seeded(confirmed=())
    registry = s.dynamic.transit.registry
    network = registry.allocation_ledger.network
    edge = NetworkEdgeV0('A', 7, 'C', 0, 2)
    altered = replace(network, edges=network.edges + (edge,))
    # This is intentionally a forged allocation owner, so fail closed at
    # either ledger consistency or the root-only guard.
    with pytest.raises((TypeError,ValueError)):
        replacement_ledger = replace(registry.allocation_ledger, network=altered)
        repl = replace(registry, allocation_ledger=replacement_ledger)
        transit = replace(s.dynamic.transit, registry=repl)
        invalid = replace(s, dynamic=replace(s.dynamic, transit=transit))
        init(invalid)


def test_external_overflow_fails_atomically():
    from spk_simulator.owned_shared_event_cycle_v0 import SharedExternalIngressOverflowV0
    s = fresh(arrivals=tuple((4,3,i) for i in range(20)))
    with pytest.raises(SharedExternalIngressOverflowV0):
        advance(s)
    assert s.shared.external_resident_input_indices == ()
    assert not s.shared.dynamic.transit.service.confirmed


def test_external_and_service_time_distinct():
    s,_ = to_prepared()
    assert s.witnesses[0].event_time == 3
    assert s.witnesses[0].service_boundary >= 5


def test_no_duplicate_consumption_after_prepare():
    s,_ = to_prepared()
    step = advance(s)
    assert step.consumed_external_input_indices == ()
    assert step.state.witnesses == s.witnesses
    assert step.state.shared.external_consumed_input_indices == (0,)


def test_confirmed_read_must_remain_in_receipt_history():
    s,_ = to_prepared()
    with pytest.raises(ValueError, match='receipt coverage'):
        replace(s, reads=())


def test_duplicate_read_receipt_rejected():
    s,_ = to_prepared()
    with pytest.raises(ValueError):
        replace(s, reads=(s.reads[0], s.reads[0], s.reads[1]))


def test_noncanonical_read_receipt_order_rejected():
    s,_ = to_prepared()
    with pytest.raises(ValueError, match='noncanonical'):
        replace(s, reads=tuple(reversed(s.reads)))


def test_duplicate_prepared_transition_rejected():
    s,_ = to_prepared()
    with pytest.raises(ValueError, match='duplicate Core preparation'):
        replace(s, prepared=s.prepared + s.prepared)
