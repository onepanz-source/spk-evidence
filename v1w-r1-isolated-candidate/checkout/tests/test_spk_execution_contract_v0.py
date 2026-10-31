from collections import Counter

import pytest

from spk_core.runtime import SpikeTrain
from spk_network.model_v0 import NetworkEdgeV0


def test_spike_train_preserves_timestamps_and_multiplicity():
    pairs = [
        (3, 1),
        (3, 1),
        (7, 2),
    ]

    train = SpikeTrain.from_pairs(pairs)

    assert Counter(train.as_pairs()) == Counter(pairs)


@pytest.mark.parametrize("delay", [0, -1])
def test_network_rejects_nonpositive_edge_delay(delay):
    with pytest.raises(ValueError):
        NetworkEdgeV0(
            source_node="A",
            source_channel=0,
            target_node="B",
            target_channel=0,
            delay_ticks=delay,
        )
