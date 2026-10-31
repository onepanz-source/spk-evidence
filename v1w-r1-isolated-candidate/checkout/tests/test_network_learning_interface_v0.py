from __future__ import annotations

from dataclasses import dataclass, field

from spk_core.isa import (
    CoreAcc,
    CoreCmp,
    CoreConfig,
    CoreEmit,
    CoreProgram,
    CoreReset,
)
from spk_network.events_v0 import (
    NetworkEventV0,
)
from spk_network.learning_v0 import (
    NetworkBatchObservationV0,
    NetworkRouteObservationV0,
)
from spk_network.model_v0 import (
    NetworkEdgeV0,
    NetworkNodeV0,
    NetworkV0,
)
from spk_network.runtime_v0 import (
    run_network_v0,
)


CONFIG = CoreConfig(
    state_bits=8,
    fractional_bits=0,
)


RELAY = CoreProgram(
    (
        CoreAcc(1, 0),
        CoreCmp(1),
        CoreEmit(7),
        CoreReset(0),
    )
)


ACC = CoreProgram(
    (
        CoreAcc(1, 0),
    )
)


@dataclass
class Recorder:
    routes: list = field(
        default_factory=list
    )

    batches: list = field(
        default_factory=list
    )

    def on_route(
        self,
        observation,
    ):
        self.routes.append(
            observation
        )

    def on_batch(
        self,
        observation,
    ):
        self.batches.append(
            observation
        )


def network(
    *,
    parallel=False,
):
    edge = NetworkEdgeV0(
        source_node="a",
        source_channel=7,
        target_node="b",
        target_channel=0,
        delay_ticks=2,
    )

    return NetworkV0(
        nodes=(
            NetworkNodeV0(
                "a",
                CONFIG,
                RELAY,
            ),
            NetworkNodeV0(
                "b",
                CONFIG,
                ACC,
            ),
        ),
        edges=(
            (
                edge,
                edge,
            )
            if parallel
            else (
                edge,
            )
        ),
    )


def test_observer_does_not_change_runtime_result():
    n = network()

    events = (
        NetworkEventV0(
            1,
            "a",
            0,
        ),
    )

    recorder = Recorder()

    observed = run_network_v0(
        n,
        events,
        learning_observer=recorder,
    )

    unobserved = run_network_v0(
        n,
        events,
    )

    assert observed == unobserved


def test_route_observation_preserves_causal_provenance():
    recorder = Recorder()

    run_network_v0(
        network(),
        (
            NetworkEventV0(
                1,
                "a",
                0,
            ),
        ),
        learning_observer=recorder,
    )

    assert recorder.routes == [
        NetworkRouteObservationV0(
            emission_timestamp=1,
            source_node="a",
            source_channel=7,
            delivery_timestamp=3,
            target_node="b",
            target_channel=0,
            delay_ticks=2,
        )
    ]


def test_batch_observation_exposes_recipient_outcome():
    recorder = Recorder()

    run_network_v0(
        network(),
        (
            NetworkEventV0(
                1,
                "a",
                0,
            ),
        ),
        learning_observer=recorder,
    )

    assert recorder.batches == [
        NetworkBatchObservationV0(
            timestamp=1,
            node_id="a",
            channels=(0,),
            final_raw=0,
            final_guard=True,
            output_channels=(7,),
        ),
        NetworkBatchObservationV0(
            timestamp=3,
            node_id="b",
            channels=(0,),
            final_raw=1,
            final_guard=False,
            output_channels=(),
        ),
    ]


def test_parallel_edges_preserve_learning_observation_multiplicity():
    recorder = Recorder()

    run_network_v0(
        network(
            parallel=True,
        ),
        (
            NetworkEventV0(
                0,
                "a",
                0,
            ),
        ),
        learning_observer=recorder,
    )

    assert len(
        recorder.routes
    ) == 2

    assert (
        recorder.routes[0]
        == recorder.routes[1]
    )

    assert (
        recorder.batches[-1].channels
        == (
            0,
            0,
        )
    )


def test_input_batch_multiplicity_is_visible_to_observer():
    recorder = Recorder()

    isolated = NetworkV0(
        nodes=(
            NetworkNodeV0(
                "a",
                CONFIG,
                ACC,
            ),
        ),
    )

    run_network_v0(
        isolated,
        (
            NetworkEventV0(
                4,
                "a",
                0,
            ),
            NetworkEventV0(
                4,
                "a",
                0,
            ),
            NetworkEventV0(
                4,
                "a",
                0,
            ),
        ),
        learning_observer=recorder,
    )

    assert (
        recorder.batches[0].channels
        == (
            0,
            0,
            0,
        )
    )

    assert (
        recorder.batches[0].final_raw
        == 3
    )
