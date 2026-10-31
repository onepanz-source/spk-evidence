from __future__ import annotations

import pytest

from spk_core.isa import (
    CoreAcc,
    CoreConfig,
    CoreProgram,
)
from spk_network.events_v0 import (
    NetworkBatchV0,
    NetworkEventV0,
    batch_network_events_v0,
)
from spk_network.model_v0 import (
    NetworkNodeV0,
    NetworkV0,
)


CONFIG = CoreConfig(
    state_bits=8,
    fractional_bits=0,
)

PROGRAM = CoreProgram(
    (
        CoreAcc(
            weight=1,
            channel=0,
        ),
    )
)


NETWORK = NetworkV0(
    nodes=(
        NetworkNodeV0(
            node_id="a",
            config=CONFIG,
            program=PROGRAM,
        ),
        NetworkNodeV0(
            node_id="b",
            config=CONFIG,
            program=PROGRAM,
        ),
    )
)


def test_event_accepts_timestamp_zero():
    event = NetworkEventV0(
        timestamp=0,
        node_id="a",
        channel=0,
    )

    assert event.timestamp == 0


@pytest.mark.parametrize(
    "field,value",
    (
        (
            "timestamp",
            -1,
        ),
        (
            "channel",
            -1,
        ),
    ),
)
def test_event_rejects_negative_integer_fields(
    field,
    value,
):
    kwargs = {
        "timestamp": 0,
        "node_id": "a",
        "channel": 0,
    }

    kwargs[
        field
    ] = value

    with pytest.raises(
        ValueError,
        match="non-negative integer",
    ):
        NetworkEventV0(
            **kwargs
        )


def test_empty_event_stream_produces_no_batches():
    assert (
        batch_network_events_v0(
            NETWORK,
            (),
        )
        == ()
    )


def test_same_timestamp_and_node_form_one_batch():
    batches = batch_network_events_v0(
        NETWORK,
        (
            NetworkEventV0(
                timestamp=3,
                node_id="a",
                channel=1,
            ),
            NetworkEventV0(
                timestamp=3,
                node_id="a",
                channel=0,
            ),
        ),
    )

    assert batches == (
        NetworkBatchV0(
            timestamp=3,
            node_id="a",
            channels=(
                0,
                1,
            ),
        ),
    )


def test_multiplicity_is_preserved():
    batches = batch_network_events_v0(
        NETWORK,
        (
            NetworkEventV0(
                timestamp=4,
                node_id="a",
                channel=1,
            ),
            NetworkEventV0(
                timestamp=4,
                node_id="a",
                channel=1,
            ),
            NetworkEventV0(
                timestamp=4,
                node_id="a",
                channel=1,
            ),
        ),
    )

    assert batches[
        0
    ].channels == (
        1,
        1,
        1,
    )


def test_same_timestamp_different_nodes_are_separate_batches():
    batches = batch_network_events_v0(
        NETWORK,
        (
            NetworkEventV0(
                timestamp=2,
                node_id="b",
                channel=0,
            ),
            NetworkEventV0(
                timestamp=2,
                node_id="a",
                channel=0,
            ),
        ),
    )

    assert batches == (
        NetworkBatchV0(
            timestamp=2,
            node_id="a",
            channels=(
                0,
            ),
        ),
        NetworkBatchV0(
            timestamp=2,
            node_id="b",
            channels=(
                0,
            ),
        ),
    )


def test_batches_are_sorted_by_timestamp_then_node():
    batches = batch_network_events_v0(
        NETWORK,
        (
            NetworkEventV0(
                timestamp=5,
                node_id="a",
                channel=0,
            ),
            NetworkEventV0(
                timestamp=1,
                node_id="b",
                channel=0,
            ),
            NetworkEventV0(
                timestamp=1,
                node_id="a",
                channel=0,
            ),
        ),
    )

    assert tuple(
        (
            batch.timestamp,
            batch.node_id,
        )
        for batch in batches
    ) == (
        (
            1,
            "a",
        ),
        (
            1,
            "b",
        ),
        (
            5,
            "a",
        ),
    )


def test_event_order_does_not_change_canonical_batches():
    events_a = (
        NetworkEventV0(
            timestamp=2,
            node_id="a",
            channel=1,
        ),
        NetworkEventV0(
            timestamp=1,
            node_id="b",
            channel=3,
        ),
        NetworkEventV0(
            timestamp=2,
            node_id="a",
            channel=0,
        ),
    )

    events_b = tuple(
        reversed(
            events_a
        )
    )

    assert (
        batch_network_events_v0(
            NETWORK,
            events_a,
        )
        ==
        batch_network_events_v0(
            NETWORK,
            events_b,
        )
    )


def test_total_event_multiplicity_is_preserved():
    events = (
        NetworkEventV0(
            timestamp=1,
            node_id="a",
            channel=0,
        ),
        NetworkEventV0(
            timestamp=1,
            node_id="a",
            channel=0,
        ),
        NetworkEventV0(
            timestamp=1,
            node_id="b",
            channel=2,
        ),
        NetworkEventV0(
            timestamp=2,
            node_id="a",
            channel=3,
        ),
    )

    batches = batch_network_events_v0(
        NETWORK,
        events,
    )

    assert sum(
        len(
            batch.channels
        )
        for batch in batches
    ) == len(
        events
    )


def test_unknown_target_node_is_rejected():
    with pytest.raises(
        ValueError,
        match="does not exist",
    ):
        batch_network_events_v0(
            NETWORK,
            (
                NetworkEventV0(
                    timestamp=0,
                    node_id="missing",
                    channel=0,
                ),
            ),
        )
