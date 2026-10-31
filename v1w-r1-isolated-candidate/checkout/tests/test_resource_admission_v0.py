from dataclasses import replace

import pytest

from spk_core.isa import (
    CoreAcc,
    CoreCmp,
    CoreConfig,
    CoreEmit,
    CoreProgram,
    CoreReset,
)
from spk_network.events_v0 import NetworkEventV0
from spk_network.model_v0 import (
    NetworkEdgeV0,
    NetworkNodeV0,
    NetworkV0,
)
from spk_network.runtime_v0 import run_network_v0

from spk_compiler.resource_admission_v0 import (
    AdmissionRejectedV0,
    ResourceProfileV0,
    admit_network_v0,
)


@pytest.fixture
def sample():
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

    network = NetworkV0(
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

    events = (
        NetworkEventV0(2, "A", 0),
    )

    return network, events


def test_admission_success(sample):
    network, events = sample

    manifest = admit_network_v0(
        network,
        events,
        ResourceProfileV0(),
    )

    assert manifest.node_count == 2
    assert manifest.edge_count == 3
    assert manifest.instruction_count == 8
    assert manifest.max_node_emits == 1
    assert manifest.max_channel_fanout == 3
    assert manifest.conservative_emission_bound == 5000


@pytest.mark.parametrize(
    "limit, value, metric",
    [
        ("max_instructions_per_node", 3,
         "instructions_per_node"),
        ("max_nodes", 1, "nodes"),
        ("max_edges", 2, "edges"),
        ("max_fanout_per_channel", 2,
         "fanout_per_channel"),
        ("max_emissions", 4999,
         "conservative_emissions"),
    ],
)
def test_admission_rejects_resource_limits(
    sample, limit, value, metric
):
    network, events = sample

    profile = replace(
        ResourceProfileV0(),
        **{limit: value},
    )

    with pytest.raises(AdmissionRejectedV0) as error:
        admit_network_v0(network, events, profile)

    assert error.value.code == "ADMISSION_REJECTED"
    assert error.value.metric == metric


def test_initial_event_limit(sample):
    network, events = sample

    repeated = events + events

    profile = replace(
        ResourceProfileV0(),
        max_initial_events=1,
    )

    with pytest.raises(AdmissionRejectedV0) as error:
        admit_network_v0(network, repeated, profile)

    assert error.value.metric == "initial_events"


def test_admission_does_not_change_execution(sample):
    network, events = sample

    before = run_network_v0(network, events)

    manifest = admit_network_v0(
        network,
        events,
        ResourceProfileV0(),
    )

    after = run_network_v0(
        network,
        events,
        max_batches=manifest.runtime_max_batches,
        max_events=manifest.runtime_max_events,
    )

    assert before == after


def test_invalid_resource_profile():
    with pytest.raises(ValueError):
        ResourceProfileV0(max_nodes=True)


def test_invalid_profile_capacity():
    with pytest.raises(ValueError):
        ResourceProfileV0(
            max_initial_events=100,
            max_scheduled_events=50,
        )
