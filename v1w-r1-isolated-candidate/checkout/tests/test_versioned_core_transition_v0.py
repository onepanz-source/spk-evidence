"""Independent frozen Core transitions + versioned memory write tests."""
from dataclasses import replace
from unittest.mock import patch

import pytest

from spk_core.isa import (
    CoreAcc, CoreCmp, CoreConfig, CoreEmit, CoreProgram, CoreReset,
)
from spk_network.model_v0 import NetworkNodeV0, NetworkV0
from spk_network.events_v0 import NetworkEventV0
from spk_network.runtime_v0 import run_network_v0
from spk_simulator.versioned_core_transition_v0 import (
    VersionedNeuronImageV0, NeuronVersionV0,
    initialize_neuron_image_v0, prepare_core_transition_v0,
    commit_core_transition_v0,
)


def case(*, b_initial=0):
    cfg = CoreConfig(8, 0)
    program = CoreProgram((
        CoreAcc(weight=1, channel=0), CoreCmp(threshold_raw=1),
        CoreEmit(channel_out=7), CoreReset(value_raw=0),
    ))
    # Reverse the node insertion order to exercise canonical memory ordering.
    return NetworkV0((
        NetworkNodeV0('B', cfg, program, initial_raw=b_initial),
        NetworkNodeV0('A', cfg, program),
    ), ())


def stage(network, image, node='A', timestamp=2, channels=(0,)):
    return prepare_core_transition_v0(
        network, image, node_id=node, timestamp=timestamp, channels=channels,
    )


def apply(network, image, node='A', timestamp=2, channels=(0,)):
    return commit_core_transition_v0(
        network, image, stage(network, image, node, timestamp, channels)
    )


def test_image_canonical_even_if_network_inverted():
    img = initialize_neuron_image_v0(case())
    assert tuple(n.node_id for n in img.neurons) == ('A', 'B')
    assert all(n.version == 0 and n.last_timestamp == 0 for n in img.neurons)


def test_prepare_is_read_only():
    network = case()
    before = initialize_neuron_image_v0(network)
    prepared = stage(network, before)
    assert before == initialize_neuron_image_v0(network)
    assert prepared.base_version == 0 and prepared.before_timestamp == 0


def test_single_batch_matches_frozen_network_oracle():
    network = case()
    initial = initialize_neuron_image_v0(network)
    step = apply(network, initial)
    oracle = run_network_v0(network, (NetworkEventV0(2, 'A', 0),))
    assert step.state.neurons[0].raw == next(s.raw for s in oracle.states if s.node_id == 'A')
    assert step.state.neurons[0].last_timestamp == next(s.last_timestamp for s in oracle.states if s.node_id == 'A')
    assert step.receipt.candidate_outputs == tuple(
        (e.timestamp, e.channel) for e in oracle.emissions
    )
    assert initial.neurons[0].version == 0


def test_neighbour_state_is_not_changed():
    network = case(b_initial=2)
    img = initialize_neuron_image_v0(network)
    updated = apply(network, img).state
    assert updated.neurons[1] == img.neurons[1]
    assert updated.neurons[0].version == 1


def test_two_batches_sequential_match_oracle():
    network = case()
    img = initialize_neuron_image_v0(network)
    emissions = []
    for t in (2, 5):
        tick = apply(network, img, timestamp=t)
        img = tick.state
        emissions.extend(tick.receipt.candidate_outputs)
    oracle = run_network_v0(network, (
        NetworkEventV0(2, 'A', 0), NetworkEventV0(5, 'A', 0),
    ))
    assert img.neurons[0].raw == next(s.raw for s in oracle.states if s.node_id == 'A')
    assert img.neurons[0].version == 2
    assert tuple(emissions) == tuple((e.timestamp, e.channel) for e in oracle.emissions)


def test_two_neurons_independently_match_oracle():
    network = case()
    img = initialize_neuron_image_v0(network)
    x = apply(network, img, 'A', 3)
    y = apply(network, x.state, 'B', 2)
    oracle = run_network_v0(network, (
        NetworkEventV0(3, 'A', 0), NetworkEventV0(2, 'B', 0),
    ))
    assert {n.node_id: (n.raw, n.last_timestamp) for n in y.state.neurons} == {
        n.node_id: (n.raw, n.last_timestamp) for n in oracle.states
    }
    assert sorted(x.receipt.candidate_outputs + y.receipt.candidate_outputs) == sorted(
        (e.timestamp, e.channel) for e in oracle.emissions
    )


def test_channel_multiplicity_preserved():
    network = case()
    img = initialize_neuron_image_v0(network)
    transition = stage(network, img, channels=(0, 0, 0))
    oracle = run_network_v0(network, tuple(NetworkEventV0(2, 'A', 0) for _ in range(3)))
    assert transition.channels == (0, 0, 0)
    assert transition.after_raw == next(s.raw for s in oracle.states if s.node_id == 'A')


def test_version_increment_receipt():
    network = case()
    step = apply(network, initialize_neuron_image_v0(network))
    assert (step.receipt.old_version, step.receipt.new_version) == (0, 1)
    assert (step.receipt.old_timestamp, step.receipt.new_timestamp) == (0, 2)
    assert step.receipt.epoch_id == 'E0'


def test_separate_epoch_binding():
    network = case()
    img = initialize_neuron_image_v0(network, epoch_id='E6')
    assert apply(network, img).receipt.epoch_id == 'E6'


def test_stale_prepared_cannot_be_replayed():
    network = case()
    img = initialize_neuron_image_v0(network)
    p = stage(network, img)
    latest = commit_core_transition_v0(network, img, p).state
    with pytest.raises(ValueError):
        commit_core_transition_v0(network, latest, p)


def test_two_concurrent_preparations_conflict():
    network = case()
    img = initialize_neuron_image_v0(network)
    p1 = stage(network, img, timestamp=2)
    p2 = stage(network, img, timestamp=3)
    latest = commit_core_transition_v0(network, img, p1).state
    with pytest.raises(ValueError):
        commit_core_transition_v0(network, latest, p2)


@pytest.mark.parametrize('field,new_value', [
    ('after_raw', 3),
    ('after_timestamp', 999),
    ('candidate_outputs', ((2, 127),)),
    ('final_guard', 'false'),
    ('before_raw', 7),
    ('before_timestamp', 99),
    ('base_version', 8),
    ('event_time', 9),
])
def test_forged_transition_rejected(field, new_value):
    network = case()
    image = initialize_neuron_image_v0(network)
    forged = replace(stage(network, image), **{field: new_value})
    with pytest.raises((TypeError, ValueError)):
        commit_core_transition_v0(network, image, forged)


@pytest.mark.parametrize('channels', [(), (1, 0), [-1], (-1,), (False,), (0, True)])
def test_malformed_channels_rejected(channels):
    network = case()
    with pytest.raises((TypeError, ValueError)):
        stage(network, initialize_neuron_image_v0(network), channels=channels)


@pytest.mark.parametrize('timestamp', [-1, 1.5, True])
def test_invalid_timestamp_rejected(timestamp):
    network = case()
    with pytest.raises(ValueError):
        stage(network, initialize_neuron_image_v0(network), timestamp=timestamp)


def test_initial_timestamp_zero_allowed_once():
    network = case()
    image = initialize_neuron_image_v0(network)
    fresh = apply(network, image, timestamp=0).state
    with pytest.raises(ValueError):
        stage(network, fresh, timestamp=0)


def test_same_timestamp_rejected_after_first_commit():
    network = case()
    image = apply(network, initialize_neuron_image_v0(network)).state
    with pytest.raises(ValueError):
        stage(network, image, timestamp=2)


def test_out_of_order_timestamp_rejected():
    network = case()
    image = apply(network, initialize_neuron_image_v0(network), timestamp=5).state
    with pytest.raises(ValueError):
        stage(network, image, timestamp=4)


def test_unknown_node_rejected():
    network = case()
    with pytest.raises(ValueError):
        stage(network, initialize_neuron_image_v0(network), node='X')


def test_cross_epoch_rejected():
    network = case()
    one = initialize_neuron_image_v0(network, epoch_id='E1')
    two = initialize_neuron_image_v0(network, epoch_id='E2')
    with pytest.raises(ValueError):
        commit_core_transition_v0(network, two, stage(network, one))


def test_other_network_rejected():
    network = case()
    image = initialize_neuron_image_v0(network)
    with pytest.raises(ValueError):
        stage(case(b_initial=4), image)


@pytest.mark.parametrize('epoch', ['', ' bad', 'bad ', None])
def test_invalid_epoch_rejected(epoch):
    with pytest.raises(ValueError):
        initialize_neuron_image_v0(case(), epoch_id=epoch)


@pytest.mark.parametrize('neurons', [
    (),
    (NeuronVersionV0('A', 0, 0, 0),),
    (NeuronVersionV0('B', 0, 0, 0), NeuronVersionV0('A', 0, 0, 0)),
    (NeuronVersionV0('A', 0, 0, 0), NeuronVersionV0('A', 0, 0, 0)),
    (NeuronVersionV0('A', 9999, 0, 1), NeuronVersionV0('B', 0, 0, 0)),
    (NeuronVersionV0('A', 0, 1, 0), NeuronVersionV0('B', 0, 0, 0)),
    (NeuronVersionV0('A', 0, 0, -1), NeuronVersionV0('B', 0, 0, 0)),
])
def test_malformed_memory_image_rejected(neurons):
    network = case()
    invalid = VersionedNeuronImageV0(network, 'E0', neurons)
    with pytest.raises((TypeError, ValueError)):
        stage(network, invalid)


def test_runtime_oracle_is_not_invoked_by_transition_module():
    import spk_network.runtime_v0 as runtime
    network = case()
    image = initialize_neuron_image_v0(network)
    with patch.object(runtime, 'run_network_v0', side_effect=AssertionError('forbidden')):
        result = apply(network, image)
    assert result.state.neurons[0].version == 1


def test_channels_require_independent_ingress_evidence():
    # This adapter verifies computation, NOT provenance of input events.
    # A malicious caller may change channels while preserving the same Core
    # result. The future storage owner must authenticate the consumed batch.
    network = case()
    image = initialize_neuron_image_v0(network)
    candidate = replace(stage(network, image), channels=(0, 0))
    assert commit_core_transition_v0(network, image, candidate).receipt.new_version == 1
