from __future__ import annotations

import pytest

from spk_core.isa import (
    CoreAcc,
    CoreCmp,
    CoreConfig,
    CoreProgram,
)
from spk_network.model_v0 import (
    NetworkEdgeV0,
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


def node(
    node_id: str,
) -> NetworkNodeV0:
    return NetworkNodeV0(
        node_id=node_id,
        config=CONFIG,
        program=PROGRAM,
    )


def edge(
    source: str = "a",
    target: str = "b",
    *,
    delay: int = 1,
) -> NetworkEdgeV0:
    return NetworkEdgeV0(
        source_node=source,
        source_channel=7,
        target_node=target,
        target_channel=0,
        delay_ticks=delay,
    )


def test_single_node_network_is_valid():
    network = NetworkV0(
        nodes=(
            node("a"),
        ),
    )

    assert len(
        network.nodes
    ) == 1

    assert network.edges == ()


def test_directed_edge_is_valid():
    network = NetworkV0(
        nodes=(
            node("a"),
            node("b"),
        ),
        edges=(
            edge(),
        ),
    )

    assert len(
        network.edges
    ) == 1


def test_parallel_edges_preserve_multiplicity():
    e = edge()

    network = NetworkV0(
        nodes=(
            node("a"),
            node("b"),
        ),
        edges=(
            e,
            e,
        ),
    )

    assert network.edges == (
        e,
        e,
    )


def test_structural_cycle_is_allowed():
    network = NetworkV0(
        nodes=(
            node("a"),
            node("b"),
        ),
        edges=(
            edge(
                "a",
                "b",
            ),
            edge(
                "b",
                "a",
            ),
        ),
    )

    assert len(
        network.edges
    ) == 2


def test_duplicate_node_ids_are_rejected():
    with pytest.raises(
        ValueError,
        match="unique",
    ):
        NetworkV0(
            nodes=(
                node("a"),
                node("a"),
            ),
        )


def test_missing_source_is_rejected():
    with pytest.raises(
        ValueError,
        match="source node",
    ):
        NetworkV0(
            nodes=(
                node("b"),
            ),
            edges=(
                edge(
                    "a",
                    "b",
                ),
            ),
        )


def test_missing_target_is_rejected():
    with pytest.raises(
        ValueError,
        match="target node",
    ):
        NetworkV0(
            nodes=(
                node("a"),
            ),
            edges=(
                edge(
                    "a",
                    "b",
                ),
            ),
        )


@pytest.mark.parametrize(
    "delay",
    (
        0,
        -1,
    ),
)
def test_delay_must_be_positive(
    delay,
):
    with pytest.raises(
        ValueError,
        match="positive integer",
    ):
        edge(
            delay=delay,
        )


def test_non_normalized_core_program_is_rejected():
    non_normal = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
        )
    )

    with pytest.raises(
        ValueError,
        match="runtime-normalized",
    ):
        NetworkNodeV0(
            node_id="a",
            config=CONFIG,
            program=non_normal,
        )


def test_node_accepts_nonzero_initial_raw():
    n = NetworkNodeV0(
        node_id="a",
        config=CONFIG,
        program=PROGRAM,
        initial_raw=17,
    )

    assert n.initial_raw == 17


def test_node_rejects_out_of_range_initial_raw():
    with pytest.raises(
        ValueError,
        match="initial_raw",
    ):
        NetworkNodeV0(
            node_id="a",
            config=CONFIG,
            program=PROGRAM,
            initial_raw=(
                CONFIG.max_raw
                + 1
            ),
        )
