import pytest

from spk_core.isa import (
    CoreAcc,
    CoreCmp,
    CoreConfig,
    CoreEmit,
    CoreProgram,
    CoreReset,
)
from spk_core.network import (
    CoreNetwork,
    NetworkEdge,
    NetworkEvent,
    NetworkExecutionLimit,
    NetworkNode,
    run_core_network,
)


CONFIG = CoreConfig(
    state_bits=8,
    fractional_bits=0,
)


def relay_program(
    *,
    input_channel=0,
    output_channel=7,
):
    return CoreProgram(
        (
            CoreAcc(
                1,
                input_channel,
            ),
            CoreCmp(1),
            CoreEmit(
                output_channel
            ),
            CoreReset(0),
        )
    )


def test_single_node_terminal_emission():
    network = CoreNetwork(
        nodes=(
            NetworkNode(
                "a",
                CONFIG,
                relay_program(),
            ),
        ),
        edges=(),
    )

    result = run_core_network(
        network,
        (
            NetworkEvent(
                3,
                "a",
                0,
            ),
        ),
    )

    expected = (
        NetworkEvent(
            3,
            "a",
            7,
        ),
    )

    assert result.emissions == expected
    assert result.terminal_outputs == expected

    assert result.processed_batches == 1
    assert result.processed_events == 1

    assert result.states[0].node == "a"
    assert result.states[0].raw == 0
    assert result.states[0].last_timestamp == 3


def test_edge_routes_with_positive_delay():
    network = CoreNetwork(
        nodes=(
            NetworkNode(
                "a",
                CONFIG,
                relay_program(
                    output_channel=7,
                ),
            ),
            NetworkNode(
                "b",
                CONFIG,
                relay_program(
                    input_channel=0,
                    output_channel=9,
                ),
            ),
        ),
        edges=(
            NetworkEdge(
                source="a",
                source_channel=7,
                target="b",
                target_channel=0,
                delay=2,
            ),
        ),
    )

    result = run_core_network(
        network,
        (
            NetworkEvent(
                1,
                "a",
                0,
            ),
        ),
    )

    assert result.emissions == (
        NetworkEvent(
            1,
            "a",
            7,
        ),
        NetworkEvent(
            3,
            "b",
            9,
        ),
    )

    assert result.terminal_outputs == (
        NetworkEvent(
            3,
            "b",
            9,
        ),
    )

    assert result.processed_batches == 2
    assert result.processed_events == 2


def test_same_timestamp_same_node_is_one_batch():
    #
    # a and c both emit toward b at t=1.
    #
    # B receives multiplicity two in ONE batch.
    #
    # With CMP(1), one shared batch emits once.
    # If B were incorrectly executed once per event it would emit twice.
    #
    network = CoreNetwork(
        nodes=(
            NetworkNode(
                "a",
                CONFIG,
                relay_program(),
            ),
            NetworkNode(
                "b",
                CONFIG,
                relay_program(
                    input_channel=0,
                    output_channel=9,
                ),
            ),
            NetworkNode(
                "c",
                CONFIG,
                relay_program(),
            ),
        ),
        edges=(
            NetworkEdge(
                "a",
                7,
                "b",
                0,
                1,
            ),
            NetworkEdge(
                "c",
                7,
                "b",
                0,
                1,
            ),
        ),
    )

    result = run_core_network(
        network,
        (
            NetworkEvent(
                0,
                "a",
                0,
            ),
            NetworkEvent(
                0,
                "c",
                0,
            ),
        ),
    )

    b_outputs = tuple(
        event
        for event in result.emissions
        if event.node == "b"
    )

    assert b_outputs == (
        NetworkEvent(
            1,
            "b",
            9,
        ),
    )

    assert result.processed_batches == 3

    #
    # Two external events + two routed events.
    #
    assert result.processed_events == 4


def test_parallel_edges_preserve_multiplicity():
    network = CoreNetwork(
        nodes=(
            NetworkNode(
                "a",
                CONFIG,
                relay_program(),
            ),
            NetworkNode(
                "b",
                CONFIG,
                CoreProgram(
                    (
                        CoreAcc(1, 0),
                    )
                ),
            ),
        ),
        edges=(
            NetworkEdge(
                "a",
                7,
                "b",
                0,
                1,
            ),
            NetworkEdge(
                "a",
                7,
                "b",
                0,
                1,
            ),
        ),
    )

    result = run_core_network(
        network,
        (
            NetworkEvent(
                0,
                "a",
                0,
            ),
        ),
    )

    state_b = next(
        state
        for state in result.states
        if state.node == "b"
    )

    assert state_b.raw == 2

    assert result.processed_events == 3


def test_node_construction_order_is_irrelevant():
    a = NetworkNode(
        "a",
        CONFIG,
        relay_program(),
    )

    b = NetworkNode(
        "b",
        CONFIG,
        relay_program(
            output_channel=9,
        ),
    )

    edge = NetworkEdge(
        "a",
        7,
        "b",
        0,
        2,
    )

    first = CoreNetwork(
        nodes=(
            a,
            b,
        ),
        edges=(
            edge,
        ),
    )

    second = CoreNetwork(
        nodes=(
            b,
            a,
        ),
        edges=(
            edge,
        ),
    )

    events_a = (
        NetworkEvent(
            0,
            "a",
            0,
        ),
        NetworkEvent(
            4,
            "a",
            0,
        ),
    )

    events_b = tuple(
        reversed(
            events_a
        )
    )

    result_a = run_core_network(
        first,
        events_a,
    )

    result_b = run_core_network(
        second,
        events_b,
    )

    assert result_a == result_b


def test_zero_delay_edge_is_rejected():
    with pytest.raises(
        ValueError,
        match="delay >= 1",
    ):
        NetworkEdge(
            "a",
            7,
            "b",
            0,
            0,
        )


def test_unknown_edge_endpoint_is_rejected():
    with pytest.raises(
        ValueError,
        match="unknown edge target",
    ):
        CoreNetwork(
            nodes=(
                NetworkNode(
                    "a",
                    CONFIG,
                    relay_program(),
                ),
            ),
            edges=(
                NetworkEdge(
                    "a",
                    7,
                    "missing",
                    0,
                    1,
                ),
            ),
        )


def test_event_for_unknown_node_is_rejected():
    network = CoreNetwork(
        nodes=(
            NetworkNode(
                "a",
                CONFIG,
                relay_program(),
            ),
        ),
        edges=(),
    )

    with pytest.raises(
        ValueError,
        match="unknown node",
    ):
        run_core_network(
            network,
            (
                NetworkEvent(
                    0,
                    "missing",
                    0,
                ),
            ),
        )


def test_positive_delay_cycle_hits_execution_limit():
    network = CoreNetwork(
        nodes=(
            NetworkNode(
                "a",
                CONFIG,
                relay_program(),
            ),
        ),
        edges=(
            NetworkEdge(
                "a",
                7,
                "a",
                0,
                1,
            ),
        ),
    )

    with pytest.raises(
        NetworkExecutionLimit,
        match="max_batches",
    ):
        run_core_network(
            network,
            (
                NetworkEvent(
                    0,
                    "a",
                    0,
                ),
            ),
            max_batches=5,
        )


def test_empty_network_execution_preserves_initial_states():
    network = CoreNetwork(
        nodes=(
            NetworkNode(
                "a",
                CONFIG,
                relay_program(),
                initial_raw=17,
            ),
        ),
        edges=(),
    )

    result = run_core_network(
        network,
        (),
    )

    assert result.emissions == ()
    assert result.terminal_outputs == ()
    assert result.processed_batches == 0
    assert result.processed_events == 0

    assert result.states[0].raw == 17
    assert result.states[0].last_timestamp == 0
