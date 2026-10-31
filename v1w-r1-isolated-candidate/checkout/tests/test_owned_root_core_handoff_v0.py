"""Physical root EVENT consumption -> witnessed, non-authoritative Core input."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_simulator.owned_root_core_handoff_v0 import (
    OwnedRootCoreHandoffStateV0 as State,
    advance_owned_root_core_handoff_v0 as tick,
    preview_witnessed_root_core_v0 as preview,
)
from spk_simulator.versioned_core_transition_v0 import initialize_neuron_image_v0
from tests.test_owned_root_batch_consumption_v0 import seeded


def initial(**kwargs):
    return State(seeded(**kwargs))


def consume(**kwargs):
    s = initial(**kwargs)
    a = tick(s)
    b = tick(a.state)
    return s, a, b


def neuron_image(state):
    registry = state.shared.dynamic.transit.registry
    return initialize_neuron_image_v0(
        registry.allocation_ledger.network, epoch_id=state.shared.seal.epoch_id,
    )


def test_new_state_is_empty():
    assert initial().witnesses == ()


def test_first_boundary_admits_and_serves_no_witness():
    s = initial()
    a = tick(s)
    assert a.newly_witnessed == ()
    assert a.state.witnesses == ()
    assert a.consume_step.newly_consumed_external_input_indices == ()


def test_second_boundary_creates_witness():
    _, a, b = consume()
    assert len(b.newly_witnessed) == 1
    w = b.newly_witnessed[0]
    assert (w.consume_request_id, w.node_id, w.event_time) == (2, 'C', 3)
    assert w.channels == (0,)
    assert w.external_input_indices == (0,)
    assert w.route_request_ids == ()
    assert w.service_boundary == b.service_tick == 5
    assert b.state.witnesses == (w,)


def test_witness_postdates_service_completion():
    _, a, b = consume()
    assert a.consume_step.work_finished_consume_request_ids == (2,)
    assert a.newly_witnessed == ()
    assert b.consume_step.confirmed_consume_request_ids == (2,)


def test_witness_is_in_physical_tombstone_set():
    _, _, b = consume()
    assert b.newly_witnessed[0].external_input_indices == b.state.shared.external_consumed_input_indices
    assert b.state.shared.external_resident_input_indices == ()


def test_channel_multiplicity_preserved():
    _, _, b = consume(arrivals=((4,3,0),(4,3,0)))
    assert b.newly_witnessed[0].channels == (0,0)
    assert b.newly_witnessed[0].external_input_indices == (0,1)


def test_channel_canonical_order_but_indices_not_lost():
    _, _, b = consume(arrivals=((4,3,3),(4,3,1)))
    assert b.newly_witnessed[0].channels == (1,3)
    assert b.newly_witnessed[0].external_input_indices == (0,1)


def test_three_channel_multiplicity():
    _, _, b = consume(arrivals=((4,3,0),(4,3,0),(4,3,1)))
    assert b.newly_witnessed[0].channels == (0,0,1)


def test_delayed_external_ingress_no_premature_witness():
    s = initial(arrivals=((4,3,0),(6,3,1)))
    for _ in range(3):
        a = tick(s)
        assert a.newly_witnessed == ()
        s = a.state
    fourth = tick(s)
    assert fourth.newly_witnessed[0].channels == (0,1)


def test_multicycle_service_no_early_witness():
    s = initial(units=4)
    for _ in range(10):
        a = tick(s)
        assert a.newly_witnessed == ()
        s = a.state
        if a.consume_step.work_finished_consume_request_ids:
            break
    else:
        pytest.fail('root BATCH_CONSUME never finished service')
    b = tick(s)
    assert len(b.newly_witnessed) == 1
    assert b.service_tick >= a.service_tick + 1


def test_event_time_not_derived_from_service_time():
    _, _, b = consume()
    assert b.newly_witnessed[0].event_time == 3
    assert b.newly_witnessed[0].service_boundary == 5


def test_preview_requires_real_consumption():
    s = initial()
    with pytest.raises(ValueError, match='physical EVENT consumption'):
        preview(s, neuron_image(s), consume_request_id=2)


def test_preview_denied_after_service_before_effect():
    a = tick(initial())
    with pytest.raises(ValueError, match='physical EVENT consumption'):
        preview(a.state, neuron_image(a.state), consume_request_id=2)


def test_preview_uses_actual_consumed_channels():
    _, _, b = consume()
    image = neuron_image(b.state)
    p = preview(b.state, image, consume_request_id=2)
    assert (p.node_id, p.event_time, p.channels, p.base_version) == ('C',3,(0,),0)


def test_preview_duplicate_channels_preserved():
    _, _, b = consume(arrivals=((4,3,0),(4,3,0)))
    p = preview(b.state, neuron_image(b.state), consume_request_id=2)
    assert p.channels == (0,0)


def test_preview_does_not_commit_state():
    _, _, b = consume()
    img = neuron_image(b.state)
    before = img
    preview(b.state, img, consume_request_id=2)
    assert img == before
    assert all(x.version == 0 for x in img.neurons)


def test_preview_does_not_publish_output():
    _, _, b = consume()
    before = b.state.shared.dynamic.transit.storage
    preview(b.state, neuron_image(b.state), consume_request_id=2)
    assert b.state.shared.dynamic.transit.storage == before


def test_preview_does_not_confirm_internal_reads():
    _, _, b = consume()
    before = b.state.shared.dynamic.transit.service
    preview(b.state, neuron_image(b.state), consume_request_id=2)
    assert b.state.shared.dynamic.transit.service == before


def test_preview_rejects_unknown_request():
    _, _, b = consume()
    with pytest.raises(ValueError, match='physical EVENT consumption'):
        preview(b.state, neuron_image(b.state), consume_request_id=999)


def test_preview_rejects_wrong_epoch_image():
    _, _, b = consume()
    image = neuron_image(b.state)
    with pytest.raises(ValueError, match='epoch mismatch'):
        preview(b.state, replace(image, epoch_id='BAD'), consume_request_id=2)


def test_preview_rejects_bad_image_type():
    _, _, b = consume()
    with pytest.raises(TypeError):
        preview(b.state, None, consume_request_id=2)


def test_preview_rejects_wrong_request_type():
    _, _, b = consume()
    with pytest.raises(ValueError, match='invalid consume'):
        preview(b.state, neuron_image(b.state), consume_request_id=True)


def test_handoff_rejects_wrong_state_type():
    with pytest.raises(TypeError):
        tick(None)


def test_handoff_state_rejects_wrong_shared_type():
    with pytest.raises(TypeError):
        State(None)


def test_handoff_state_rejects_wrong_witnesses_type():
    with pytest.raises(TypeError):
        State(initial().shared, witnesses=[])


def test_handoff_state_rejects_missing_historical_witness():
    _, _, b = consume()
    with pytest.raises(ValueError, match='coverage mismatch'):
        State(b.state.shared)


def test_handoff_state_rejects_duplicate_witness():
    _, _, b = consume()
    w = b.newly_witnessed[0]
    with pytest.raises(ValueError, match='noncanonical'):
        State(b.state.shared, (w,w))


@pytest.mark.parametrize('field,new', [
    ('event_time',5), ('node_id','A'), ('target_pe_id','PE1'),
    ('channels',(6,)), ('external_input_indices',(1,)),
    ('epoch_id','WRONG'), ('route_request_ids',(3,)),
    ('service_boundary',99), ('consume_request_id',1),
])
def test_handoff_state_rejects_modified_receipt(field,new):
    _, _, b = consume()
    fake = replace(b.newly_witnessed[0], **{field:new})
    with pytest.raises(ValueError):
        State(b.state.shared, (fake,))


def test_handoff_state_rejects_extra_tombstone_without_witness():
    _, _, b = consume(arrivals=((4,3,0),(4,3,1)))
    altered = replace(b.state.witnesses[0], external_input_indices=(0,))
    with pytest.raises(ValueError):
        State(b.state.shared,(altered,))


def test_handoff_original_state_unmodified():
    s = initial()
    saved = s
    tick(s)
    assert s == saved


def test_handoff_deterministic():
    s = initial()
    assert tick(s) == tick(s)


def test_handoff_result_immutable():
    result = tick(initial())
    with pytest.raises(FrozenInstanceError):
        result.service_tick = 999


def test_replayed_completion_not_silently_accepted():
    _, _, b = consume()
    with pytest.raises(ValueError,match='unowned'):
        tick(b.state)


def test_root_lifecycle_storage_unchanged_by_preview():
    _, _, b = consume()
    assert not b.state.shared.dynamic.transit.storage.pending_output
    assert not b.state.shared.dynamic.transit.storage.admitted_events
    assert b.newly_witnessed[0].route_request_ids == ()
