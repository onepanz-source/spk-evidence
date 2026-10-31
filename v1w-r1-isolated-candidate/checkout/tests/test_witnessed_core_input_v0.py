"""Witnessed Core input: real driver consumption -> canonical neuronal batch.

No caller-provided consumed IDs, input channels, service effect, or frame.
"""
from dataclasses import FrozenInstanceError, replace

import pytest

from spk_architecture.access_v0 import MemoryDomainV0 as Domain
from spk_core.isa import CoreConfig, CoreProgram, CoreAcc, CoreCmp, CoreEmit, CoreReset
from spk_network.model_v0 import NetworkV0, NetworkNodeV0
from spk_simulator.external_ingress_v0 import ExternalIngressBindingV0
from spk_simulator.witnessed_core_input_v0 import (
    advance_witnessed_core_input_tick_v0 as tick,
    WitnessedCoreInputBatchV0,
)
from tests.test_owned_service_autoframe_v0 import fixture


def network():
    cfg = CoreConfig(8, 0)
    program = CoreProgram((CoreAcc(weight=1, channel=0), CoreCmp(threshold_raw=1),
                           CoreEmit(channel_out=7), CoreReset(value_raw=0)))
    return NetworkV0(tuple(NetworkNodeV0(node_id, cfg, program)
                           for node_id in ('A', 'B', 'C')), ())


def scenario(*, ingress_tick=None, ext_time=4):
    arch, manifest, admission, requests, graph, state, ingress = fixture(ingress_tick=ingress_tick)
    times = {r.consume_request_id: r.occurrence.delivery_event_time for r in manifest.routes}
    updated = tuple(replace(r, event_time=times[r.request_id], quantity=(2 if r.request_id == 50 and ingress_tick is not None else 1))
                    if r.request_id in times else r for r in requests)
    if ingress is not None:
        ingress = replace(ingress, arrivals=tuple(replace(e, event_time=ext_time)
                                                  for e in ingress.arrivals))
        old_driver = state.boundary.driver
        old_boundary = old_driver.boundary
        next_boundary = replace(old_boundary,
                                ledger=replace(old_boundary.ledger, ingress=ingress))
        state = replace(state, boundary=replace(state.boundary,
                        driver=replace(old_driver, boundary=next_boundary)))
    return arch, network(), manifest, admission, updated, graph, state, ingress


def advance(c):
    return tick(*c[:7], ingress=c[7])


def trace(c, limit=24):
    collected = []
    for _ in range(limit):
        result = advance(c)
        collected.append(result)
        c = (*c[:6], result.owned_tick.result.state, c[7])
        if len(result.owned_tick.result.state.boundary.service.confirmed) == len(c[4]):
            break
    return tuple(collected)


def consumed(steps):
    return tuple(record for item in steps for record in item.consumed_batches)


def test_entire_route_execution_yields_three_witnessed_batches():
    result = consumed(trace(scenario()))
    assert tuple(x.consume_request_id for x in result) == (50, 51, 52)
    assert tuple(x.route_request_ids for x in result) == ((10,), (11,), (12,))
    assert all(x.external_input_indices == () for x in result)
    assert tuple(x.channels for x in result) == ((0,), (0,), (0,))


def test_event_time_comes_from_delivery_not_service_boundary():
    records = consumed(trace(scenario()))
    assert tuple(x.event_time for x in records) == (4, 5, 6)
    assert all(x.event_time == i for i, x in zip((4, 5, 6), records))


def test_target_identity_epoch_and_pe_are_derived():
    assert {(r.node_id,r.epoch_id,r.target_pe_id) for r in consumed(trace(scenario()))} == {('B','E0','PE1')}


def test_no_premature_witness_before_actual_consume():
    results = trace(scenario())
    assert results[0].consumed_batches == ()
    assert results[1].consumed_batches == ()
    assert results[2].consumed_batches == ()
    assert results[3].consumed_batches == ()
    assert results[4].consumed_batches[0].consume_request_id == 50


def test_boundary_consumption_and_proof_match():
    for item in trace(scenario()):
        effects = item.owned_tick.result.authenticated_effects.effects
        actual = {e.request_id for e in effects if e.kind.name == 'BATCH_CONSUME'}
        assert actual == {r.consume_request_id for r in item.consumed_batches}


def test_no_forged_input_arguments_accepted():
    c = scenario()
    with pytest.raises(TypeError):
        tick(*c[:7], ingress=c[7], channels=(999,))


def test_reordered_requests_dont_change_witnesses():
    c = scenario()
    reversed_ = (*c[:4], c[4][::-1], *c[5:])
    assert consumed(trace(c)) == consumed(trace(reversed_))


def test_same_snapshot_produces_identical_witnesses():
    c = scenario()
    assert trace(c) == trace(c)


def test_resume_produces_same_final_witnesses():
    c = scenario()
    full = trace(c)
    short = full[:3]
    resumed_ctx = (*c[:6], short[-1].owned_tick.result.state, c[7])
    assert consumed(short) + consumed(trace(resumed_ctx)) == consumed(full)


def test_external_and_routed_in_same_batch_preserve_multiplicity():
    c = scenario(ingress_tick=2, ext_time=4)
    records = consumed(trace(c))
    first = records[0]
    assert first.consume_request_id == 50
    assert first.route_request_ids == (10,)
    assert first.external_input_indices == (0,)
    assert first.channels == (0, 0)
    assert first.event_time == 4


def test_external_identity_zero_and_route_ten_not_conflated():
    first = consumed(trace(scenario(ingress_tick=2)))[0]
    assert first.external_input_indices == (0,)
    assert first.route_request_ids == (10,)


def test_external_ingress_future_release_is_respected():
    result = trace(scenario(ingress_tick=12), limit=32)
    first = next(x for x in consumed(result) if x.consume_request_id == 50)
    assert first.service_boundary >= 12
    assert first.event_time == 4


def test_external_event_time_must_match_routed_batch():
    c = scenario(ingress_tick=2, ext_time=2)
    with pytest.raises(ValueError, match='external arrival/request mismatch|EVENT_TIME'):
        trace(c)


def test_mismatched_consume_request_event_time_rejected():
    c = scenario()
    modified = tuple(replace(r, event_time=99) if r.request_id == 50 else r for r in c[4])
    with pytest.raises(ValueError, match='identity mismatch'):
        trace((*c[:4], modified, *c[5:]))


def test_mismatched_batch_quantity_rejected():
    c = scenario()
    changed = tuple(replace(r, quantity=2) if r.request_id == 50 else r for r in c[4])
    with pytest.raises(ValueError, match='quantity mismatch'):
        trace((*c[:4], changed, *c[5:]))


@pytest.mark.parametrize('modification', [
    {'target_id':'events:A'},
    {'target_pe_id':'PE0'},
    {'epoch_id':'WRONG'},
    {'domain':Domain.PROGRAM},
])
def test_invalid_declared_route_consumer_fails_closed(modification):
    c = scenario()
    changed = tuple(replace(r, **modification) if r.request_id == 50 else r for r in c[4])
    with pytest.raises(ValueError, match='invalid routed input binding'):
        advance((*c[:4], changed, *c[5:]))


def test_manifest_source_unknown_node_rejected():
    c = scenario()
    routes = (replace(c[2].routes[0], occurrence=replace(c[2].routes[0].occurrence,
                    source_node_id='UNKNOWN')),) + c[2].routes[1:]
    changed = replace(c[2], routes=routes)
    with pytest.raises(ValueError, match='invalid routed input binding'):
        advance((*c[:2], changed, *c[3:]))


def test_manifest_destination_unknown_node_rejected():
    c = scenario()
    route = c[2].routes[0]
    changed = replace(c[2], routes=(replace(route, occurrence=replace(route.occurrence,
                         target_node_id='UNKNOWN')),) + c[2].routes[1:])
    with pytest.raises(ValueError, match='invalid routed input binding'):
        advance((*c[:2], changed, *c[3:]))


def test_duplicate_route_manifest_id_rejected():
    c = scenario()
    with pytest.raises(ValueError, match='noncanonical bound route IDs'):
        replace(c[2], routes=c[2].routes + (c[2].routes[0],))


def test_missing_declared_routed_consumer_rejected():
    c = scenario()
    bad = tuple(r for r in c[4] if r.request_id != 50)
    with pytest.raises(ValueError, match='invalid routed input binding'):
        advance((*c[:4], bad, *c[5:]))


def test_ingress_binding_mismatch_rejected():
    c = scenario(ingress_tick=2)
    with pytest.raises(ValueError, match='external ingress mismatch'):
        tick(*c[:7], ingress=ExternalIngressBindingV0((),()))


def test_invalid_network_type_rejected():
    c = scenario()
    with pytest.raises(TypeError, match='invalid network'):
        advance((c[0],object(),*c[2:]))


def test_invalid_requests_type_rejected():
    c = scenario()
    with pytest.raises(TypeError, match='invalid requests'):
        advance((*c[:4], list(c[4]), *c[5:]))


def test_no_in_place_mutation():
    c = scenario()
    before = repr(c)
    advance(c)
    assert repr(c) == before


def test_receipt_is_immutable():
    record = consumed(trace(scenario()))[0]
    assert isinstance(record, WitnessedCoreInputBatchV0)
    with pytest.raises((FrozenInstanceError, AttributeError)):
        record.channels = (42,)


def test_storage_only_does_not_modify_neuron_state():
    c = scenario()
    image = repr(c[1])
    trace(c)
    assert repr(c[1]) == image


def test_distinguish_storage_completion_from_core_state_commit():
    from spk_simulator.versioned_core_transition_v0 import initialize_neuron_image_v0
    c = scenario()
    image = initialize_neuron_image_v0(c[1])
    records = consumed(trace(c))
    assert len(records) == 3
    assert all(s.version == 0 for s in image.neurons)


def stage_once(c, image=None):
    from spk_simulator.witnessed_core_input_v0 import advance_and_stage_witnessed_core_tick_v0
    from spk_simulator.versioned_core_transition_v0 import initialize_neuron_image_v0
    if image is None:
        image = initialize_neuron_image_v0(c[1])
    return advance_and_stage_witnessed_core_tick_v0(
        c[0], c[1], image, *c[2:7], ingress=c[7],
    )


def test_staged_core_is_empty_without_consumption():
    assert stage_once(scenario()).prepared_transitions == ()


def test_staged_core_uses_real_consumed_channel():
    c = scenario()
    state = c[6]
    for _ in range(4):
        state = advance((*c[:6], state, c[7])).owned_tick.result.state
    staged = stage_once((*c[:6], state, c[7]))
    assert len(staged.prepared_transitions) == 1
    proposal = staged.prepared_transitions[0]
    assert proposal.node_id == 'B'
    assert proposal.event_time == 4
    assert proposal.channels == (0,)
    assert proposal.candidate_outputs == ((4, 7),)
    assert proposal.base_version == 0


def test_core_is_computed_without_network_runtime_oracle():
    from unittest.mock import patch
    import spk_network.runtime_v0 as runtime
    c = scenario()
    state = c[6]
    for _ in range(4):
        state = advance((*c[:6], state, c[7])).owned_tick.result.state
    with patch.object(runtime, 'run_network_v0', side_effect=AssertionError('oracle call forbidden')):
        staged = stage_once((*c[:6], state, c[7]))
    assert staged.prepared_transitions[0].candidate_outputs == ((4, 7),)


def test_staging_does_not_modify_neuron_image():
    from spk_simulator.versioned_core_transition_v0 import initialize_neuron_image_v0
    c = scenario()
    image = initialize_neuron_image_v0(c[1])
    state = c[6]
    for _ in range(4):
        state = advance((*c[:6], state, c[7])).owned_tick.result.state
    staged = stage_once((*c[:6], state, c[7]), image)
    assert staged.prepared_transitions[0].after_timestamp == 4
    assert all(node.version == 0 for node in image.neurons)


def test_staging_refuses_other_epoch():
    from spk_simulator.versioned_core_transition_v0 import initialize_neuron_image_v0
    c = scenario()
    with pytest.raises(ValueError, match='epoch mismatch'):
        stage_once(c, initialize_neuron_image_v0(c[1], epoch_id='E1'))


def test_staged_core_preserves_duplicate_external_route_channels():
    c = scenario(ingress_tick=2)
    state = c[6]
    for _ in range(4):
        state = advance((*c[:6], state, c[7])).owned_tick.result.state
    staged = stage_once((*c[:6], state, c[7]))
    assert staged.prepared_transitions[0].channels == (0, 0)


def test_staging_rejects_invalid_image_type():
    c = scenario()
    with pytest.raises(TypeError, match='invalid versioned neuron image'):
        stage_once(c, object())
