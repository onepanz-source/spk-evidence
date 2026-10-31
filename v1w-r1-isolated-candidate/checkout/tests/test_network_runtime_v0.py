from __future__ import annotations

import pytest

from spk_core.isa import (
    CoreAcc,
    CoreCmp,
    CoreConfig,
    CoreEmit,
    CoreProgram,
    CoreReset,
    ShiftDecay,
)
from spk_network.events_v0 import (
    NetworkEventV0,
)
from spk_network.model_v0 import (
    NetworkEdgeV0,
    NetworkNodeV0,
    NetworkV0,
)
from spk_network.runtime_v0 import (
    NetworkExecutionLimitV0,
    run_network_v0,
)


CONFIG = CoreConfig(
    state_bits=8,
    fractional_bits=0,
)


ACC_PROGRAM = CoreProgram(
    (
        CoreAcc(
            weight=1,
            channel=0,
        ),
    )
)


RELAY_PROGRAM = CoreProgram(
    (
        CoreAcc(
            weight=1,
            channel=0,
        ),
        CoreCmp(
            threshold_raw=1,
        ),
        CoreEmit(
            channel_out=7,
        ),
        CoreReset(
            value_raw=0,
        ),
    )
)


def node(
    node_id: str,
    program=ACC_PROGRAM,
    *,
    initial_raw: int = 0,
):
    return NetworkNodeV0(
        node_id=node_id,
        config=CONFIG,
        program=program,
        initial_raw=initial_raw,
    )


def state_map(
    result,
):
    return {
        state.node_id: state
        for state in result.states
    }


def test_empty_execution_preserves_initial_state():
    network = NetworkV0(
        nodes=(
            node(
                "a",
                initial_raw=17,
            ),
        ),
    )

    result = run_network_v0(
        network,
        (),
    )

    states = state_map(
        result
    )

    assert result.emissions == ()
    assert result.terminal_outputs == ()
    assert result.processed_batches == 0
    assert result.processed_events == 0

    assert states["a"].raw == 17
    assert (
        states["a"].last_timestamp
        == 0
    )


def test_node_state_persists_between_batches():
    network = NetworkV0(
        nodes=(
            node("a"),
        ),
    )

    result = run_network_v0(
        network,
        (
            NetworkEventV0(
                1,
                "a",
                0,
            ),
            NetworkEventV0(
                3,
                "a",
                0,
            ),
        ),
    )

    state = state_map(
        result
    )["a"]

    assert state.raw == 2
    assert state.last_timestamp == 3
    assert result.processed_batches == 2
    assert result.processed_events == 2


def test_batch_multiplicity_reaches_core_unchanged():
    network = NetworkV0(
        nodes=(
            node("a"),
        ),
    )

    result = run_network_v0(
        network,
        (
            NetworkEventV0(
                1,
                "a",
                0,
            ),
            NetworkEventV0(
                1,
                "a",
                0,
            ),
            NetworkEventV0(
                1,
                "a",
                0,
            ),
        ),
    )

    state = state_map(
        result
    )["a"]

    assert state.raw == 3
    assert result.processed_batches == 1
    assert result.processed_events == 3


def test_each_node_has_independent_time_history():
    decay = CoreProgram(
        (
            ShiftDecay(
                bits_per_tick=1,
            ),
        )
    )

    network = NetworkV0(
        nodes=(
            node(
                "a",
                decay,
                initial_raw=8,
            ),
            node(
                "b",
                decay,
                initial_raw=8,
            ),
        ),
    )

    result = run_network_v0(
        network,
        (
            NetworkEventV0(
                2,
                "a",
                0,
            ),
            NetworkEventV0(
                4,
                "b",
                0,
            ),
        ),
    )

    states = state_map(
        result
    )

    assert states["a"].raw == 2
    assert states["a"].last_timestamp == 2

    assert states["b"].raw == 0
    assert states["b"].last_timestamp == 4


def test_emit_is_routed_with_positive_edge_delay():
    network = NetworkV0(
        nodes=(
            node(
                "a",
                RELAY_PROGRAM,
            ),
            node(
                "b",
                ACC_PROGRAM,
            ),
        ),
        edges=(
            NetworkEdgeV0(
                source_node="a",
                source_channel=7,
                target_node="b",
                target_channel=0,
                delay_ticks=2,
            ),
        ),
    )

    result = run_network_v0(
        network,
        (
            NetworkEventV0(
                1,
                "a",
                0,
            ),
        ),
    )

    states = state_map(
        result
    )

    assert result.emissions == (
        NetworkEventV0(
            1,
            "a",
            7,
        ),
    )

    assert result.terminal_outputs == ()

    assert states["b"].raw == 1
    assert states["b"].last_timestamp == 3


def test_unrouted_emit_is_terminal_output():
    network = NetworkV0(
        nodes=(
            node(
                "a",
                RELAY_PROGRAM,
            ),
        ),
    )

    result = run_network_v0(
        network,
        (
            NetworkEventV0(
                5,
                "a",
                0,
            ),
        ),
    )

    event = NetworkEventV0(
        5,
        "a",
        7,
    )

    assert result.emissions == (
        event,
    )

    assert result.terminal_outputs == (
        event,
    )


def test_parallel_edges_preserve_routed_multiplicity():
    e = NetworkEdgeV0(
        source_node="a",
        source_channel=7,
        target_node="b",
        target_channel=0,
        delay_ticks=1,
    )

    network = NetworkV0(
        nodes=(
            node(
                "a",
                RELAY_PROGRAM,
            ),
            node(
                "b",
                ACC_PROGRAM,
            ),
        ),
        edges=(
            e,
            e,
        ),
    )

    result = run_network_v0(
        network,
        (
            NetworkEventV0(
                0,
                "a",
                0,
            ),
        ),
    )

    state = state_map(
        result
    )["b"]

    assert state.raw == 2
    assert state.last_timestamp == 1

    assert result.processed_batches == 2
    assert result.processed_events == 3


def test_input_order_does_not_change_result():
    network = NetworkV0(
        nodes=(
            node("a"),
            node("b"),
        ),
    )

    events = (
        NetworkEventV0(
            3,
            "a",
            0,
        ),
        NetworkEventV0(
            1,
            "b",
            0,
        ),
        NetworkEventV0(
            1,
            "a",
            0,
        ),
    )

    assert (
        run_network_v0(
            network,
            events,
        )
        ==
        run_network_v0(
            network,
            tuple(
                reversed(
                    events
                )
            ),
        )
    )


def test_positive_delay_cycle_is_bounded_by_event_limit():
    network = NetworkV0(
        nodes=(
            node(
                "a",
                RELAY_PROGRAM,
            ),
            node(
                "b",
                RELAY_PROGRAM,
            ),
        ),
        edges=(
            NetworkEdgeV0(
                source_node="a",
                source_channel=7,
                target_node="b",
                target_channel=0,
                delay_ticks=1,
            ),
            NetworkEdgeV0(
                source_node="b",
                source_channel=7,
                target_node="a",
                target_channel=0,
                delay_ticks=1,
            ),
        ),
    )

    with pytest.raises(
        NetworkExecutionLimitV0,
        match="max_events",
    ):
        run_network_v0(
            network,
            (
                NetworkEventV0(
                    0,
                    "a",
                    0,
                ),
            ),
            max_events=6,
        )


def test_batch_limit_is_enforced():
    network = NetworkV0(
        nodes=(
            node("a"),
        ),
    )

    with pytest.raises(
        NetworkExecutionLimitV0,
        match="max_batches",
    ):
        run_network_v0(
            network,
            (
                NetworkEventV0(
                    1,
                    "a",
                    0,
                ),
                NetworkEventV0(
                    2,
                    "a",
                    0,
                ),
            ),
            max_batches=1,
        )
