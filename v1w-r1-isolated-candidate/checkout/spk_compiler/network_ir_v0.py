"""SPK Network IR v0: strict, versioned serialization."""

import json

from spk_core.ir_v0 import (
    build_core_ir_v0,
    parse_core_ir_v0,
)
from spk_network.model_v0 import (
    NetworkNodeV0,
    NetworkEdgeV0,
    NetworkV0,
)


NETWORK_IR_V0_SCHEMA = "spk-network-ir/v0"
NETWORK_IR_V0_VERSION = "0"


def _require_keys(data, expected, context):
    if type(data) is not dict:
        raise ValueError(f"{context} must be an object")

    actual = set(data)
    expected = set(expected)

    if actual != expected:
        raise ValueError(
            f"{context}: missing={sorted(expected - actual)}, "
            f"extra={sorted(actual - expected)}"
        )


def build_network_ir_v0(network: NetworkV0) -> dict:
    """Serialize an already validated NetworkV0."""

    if not isinstance(network, NetworkV0):
        raise TypeError("expected NetworkV0")

    return {
        "schema": NETWORK_IR_V0_SCHEMA,
        "network_version": NETWORK_IR_V0_VERSION,
        "nodes": [
            {
                "node_id": node.node_id,
                "initial_raw": node.initial_raw,
                "core_ir": build_core_ir_v0(
                    node.config,
                    node.program,
                ),
            }
            for node in network.nodes
        ],
        "edges": [
            {
                "source_node": edge.source_node,
                "source_channel": edge.source_channel,
                "target_node": edge.target_node,
                "target_channel": edge.target_channel,
                "delay_ticks": edge.delay_ticks,
            }
            for edge in network.edges
        ],
    }


def parse_network_ir_v0(data: dict) -> NetworkV0:
    """Reconstruct a validated network without rewriting it."""

    _require_keys(
        data,
        {"schema", "network_version", "nodes", "edges"},
        "Network IR",
    )

    if data["schema"] != NETWORK_IR_V0_SCHEMA:
        raise ValueError("unsupported Network IR schema")

    if data["network_version"] != NETWORK_IR_V0_VERSION:
        raise ValueError("unsupported Network IR version")

    if type(data["nodes"]) is not list:
        raise ValueError("nodes must be a list")

    if type(data["edges"]) is not list:
        raise ValueError("edges must be a list")

    nodes = []

    for item in data["nodes"]:
        _require_keys(
            item,
            {"node_id", "initial_raw", "core_ir"},
            "Network node",
        )

        config, program = parse_core_ir_v0(
            item["core_ir"]
        )

        nodes.append(
            NetworkNodeV0(
                node_id=item["node_id"],
                config=config,
                program=program,
                initial_raw=item["initial_raw"],
            )
        )

    edges = []

    for item in data["edges"]:
        _require_keys(
            item,
            {
                "source_node",
                "source_channel",
                "target_node",
                "target_channel",
                "delay_ticks",
            },
            "Network edge",
        )

        edges.append(NetworkEdgeV0(**item))

    return NetworkV0(
        nodes=tuple(nodes),
        edges=tuple(edges),
    )


def dumps_network_ir_v0(network: NetworkV0) -> str:
    """Deterministic JSON encoding for the same ordered network."""

    return json.dumps(
        build_network_ir_v0(network),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _unique_pairs(pairs):
    result = {}

    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value

    return result


def _reject_constant(value):
    raise ValueError(f"invalid JSON constant: {value}")


def loads_network_ir_v0(text: str) -> NetworkV0:
    """Reject duplicate keys and non-standard JSON constants."""

    if type(text) is not str:
        raise TypeError("Network IR text must be a string")

    data = json.loads(
        text,
        object_pairs_hook=_unique_pairs,
        parse_constant=_reject_constant,
    )

    return parse_network_ir_v0(data)
