import json

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

from spk_compiler.network_ir_v0 import (
    NETWORK_IR_V0_SCHEMA,
    NETWORK_IR_V0_VERSION,
    build_network_ir_v0,
    parse_network_ir_v0,
    dumps_network_ir_v0,
    loads_network_ir_v0,
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
            NetworkNodeV0("B", config, program),
            NetworkNodeV0("A", config, program),
        ),
        edges=(
            NetworkEdgeV0("A", 7, "B", 0, 3),
            NetworkEdgeV0("A", 7, "B", 0, 2),
            NetworkEdgeV0("A", 7, "B", 0, 2),
        ),
    )


def test_network_ir_identity(network):
    document = build_network_ir_v0(network)

    assert document["schema"] == NETWORK_IR_V0_SCHEMA
    assert document["network_version"] == NETWORK_IR_V0_VERSION
    assert document["nodes"][0]["core_ir"]["schema"] == (
        "spk-core-ir/v0"
    )


def test_network_ir_roundtrip(network):
    restored = parse_network_ir_v0(
        build_network_ir_v0(network)
    )

    assert restored == network
    assert restored.nodes == network.nodes
    assert restored.edges == network.edges


def test_network_ir_preserves_parallel_edges(network):
    restored = loads_network_ir_v0(
        dumps_network_ir_v0(network)
    )

    assert len(restored.edges) == 3
    assert restored.edges[1] == restored.edges[2]
    assert restored.edges[0].delay_ticks == 3


def test_network_ir_deterministic_serialization(network):
    text1 = dumps_network_ir_v0(network)
    text2 = dumps_network_ir_v0(network)
    restored = loads_network_ir_v0(text1)

    assert text1 == text2
    assert dumps_network_ir_v0(restored) == text1


def test_network_ir_execution_equivalence(network):
    events = (
        NetworkEventV0(
            timestamp=2,
            node_id="A",
            channel=0,
        ),
    )

    restored = loads_network_ir_v0(
        dumps_network_ir_v0(network)
    )

    before = run_network_v0(network, events)
    after = run_network_v0(restored, events)

    assert before == after

    assert before.processed_events == 4
    assert before.processed_batches == 3

    assert before.terminal_outputs == (
        NetworkEventV0(4, "B", 7),
        NetworkEventV0(5, "B", 7),
    )


@pytest.mark.parametrize("mutation", [
    "schema",
    "version",
    "extra",
    "missing",
    "empty_nodes",
    "nodes_type",
    "edges_type",
    "duplicate_node",
    "bad_delay",
    "unknown_target",
    "bad_core_op",
])
def test_network_ir_rejects_invalid_documents(
    network,
    mutation,
):
    document = build_network_ir_v0(network)

    if mutation == "schema":
        document["schema"] = "unknown"

    elif mutation == "version":
        document["network_version"] = "999"

    elif mutation == "extra":
        document["unexpected"] = True

    elif mutation == "missing":
        del document["edges"]

    elif mutation == "empty_nodes":
        document["nodes"] = []

    elif mutation == "nodes_type":
        document["nodes"] = {}

    elif mutation == "edges_type":
        document["edges"] = {}

    elif mutation == "duplicate_node":
        document["nodes"].append(
            document["nodes"][0].copy()
        )

    elif mutation == "bad_delay":
        document["edges"][0]["delay_ticks"] = 0

    elif mutation == "unknown_target":
        document["edges"][0]["target_node"] = "UNKNOWN"

    elif mutation == "bad_core_op":
        document["nodes"][0]["core_ir"][
            "instructions"
        ][0]["op"] = "UNKNOWN"

    with pytest.raises((ValueError, TypeError, KeyError)):
        parse_network_ir_v0(document)


@pytest.mark.parametrize("text", [
    '{"schema":"x","schema":"y"}',
    '{"value":NaN}',
    '{"value":Infinity}',
])
def test_network_ir_rejects_invalid_json(text):
    with pytest.raises(ValueError):
        loads_network_ir_v0(text)


def test_network_ir_json_is_valid(network):
    text = dumps_network_ir_v0(network)
    parsed = json.loads(text)

    assert parsed["schema"] == "spk-network-ir/v0"
