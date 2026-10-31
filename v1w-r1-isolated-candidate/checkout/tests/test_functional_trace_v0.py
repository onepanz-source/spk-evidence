from dataclasses import FrozenInstanceError

import pytest

from spk_core.isa import (
    CoreAcc,
    CoreCmp,
    CoreConfig,
    CoreEmit,
    CoreProgram,
    CoreReset,
)
from spk_network.model_v0 import (
    NetworkNodeV0,
    NetworkEdgeV0,
    NetworkV0,
)
from spk_network.events_v0 import NetworkEventV0
from spk_network.runtime_v0 import run_network_v0

from spk_simulator.functional_trace_v0 import (
    run_network_observed_v0,
)


@pytest.fixture
def network():
    config = CoreConfig(
        state_bits=8,
        fractional_bits=0,
    )

    program = CoreProgram((
        CoreAcc(weight=1, channel=0),
        CoreCmp(threshold_raw=1),
        CoreEmit(channel_out=7),
        CoreReset(value_raw=0),
    ))

    return NetworkV0(
        nodes=(
            NetworkNodeV0("A", config, program),
            NetworkNodeV0("B", config, program),
        ),
        edges=(
            NetworkEdgeV0("A", 7, "B", 0, 2),
            NetworkEdgeV0("A", 7, "B", 0, 2),
            NetworkEdgeV0("A", 7, "B", 0, 3),
        ),
    )


def test_observation_does_not_change_result(network):
    events = (NetworkEventV0(2, "A", 0),)

    reference = run_network_v0(network, events)
    observed = run_network_observed_v0(network, events)

    assert observed.result == reference


def test_batch_trace_preserves_multiplicity(network):
    observed = run_network_observed_v0(
        network,
        (NetworkEventV0(2, "A", 0),),
    )

    assert len(observed.batches) == 3

    assert [
        (batch.timestamp, batch.node_id, batch.channels)
        for batch in observed.batches
    ] == [
        (2, "A", (0,)),
        (4, "B", (0, 0)),
        (5, "B", (0,)),
    ]


def test_route_trace_preserves_parallel_edges(network):
    observed = run_network_observed_v0(
        network,
        (NetworkEventV0(2, "A", 0),),
    )

    assert len(observed.routes) == 3

    assert sorted(
        route.delivery_timestamp
        for route in observed.routes
    ) == [4, 4, 5]

    assert all(
        route.delivery_timestamp
        == route.emission_timestamp + route.delay_ticks
        for route in observed.routes
    )


def test_empty_execution_trace(network):
    observed = run_network_observed_v0(network, ())

    assert observed.batches == ()
    assert observed.routes == ()
    assert observed.result == run_network_v0(network, ())


def test_observations_are_immutable(network):
    observed = run_network_observed_v0(
        network,
        (NetworkEventV0(2, "A", 0),),
    )

    with pytest.raises(FrozenInstanceError):
        observed.batches[0].final_raw = 100


def test_trace_is_deterministic(network):
    events = (NetworkEventV0(2, "A", 0),)

    first = run_network_observed_v0(network, events)
    second = run_network_observed_v0(network, events)

    assert first == second
