from __future__ import annotations

from dataclasses import dataclass

from spk_core.ir_v0 import (
    build_core_ir_v0,
)
from spk_core.isa import (
    CoreConfig,
    CoreProgram,
)


NETWORK_V0_VERSION = "0"


def _require_nonnegative_int(
    name: str,
    value: int,
) -> None:
    if (
        type(value) is not int
        or value < 0
    ):
        raise ValueError(
            f"{name} must be a "
            "non-negative integer"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class NetworkNodeV0:
    node_id: str
    config: CoreConfig
    program: CoreProgram
    initial_raw: int = 0

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.node_id,
                str,
            )
            or not self.node_id
        ):
            raise ValueError(
                "node_id must be a "
                "non-empty string"
            )

        if (
            type(self.initial_raw) is not int
            or not (
                0
                <= self.initial_raw
                <= self.config.max_raw
            )
        ):
            raise ValueError(
                "initial_raw must be an integer "
                f"in [0,{self.config.max_raw}]"
            )

        #
        # Network v0 accepts only frozen Core v0
        # runtime-normalized programs.
        #
        build_core_ir_v0(
            self.config,
            self.program,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class NetworkEdgeV0:
    source_node: str
    source_channel: int
    target_node: str
    target_channel: int
    delay_ticks: int

    def __post_init__(
        self,
    ) -> None:
        if (
            not isinstance(
                self.source_node,
                str,
            )
            or not self.source_node
        ):
            raise ValueError(
                "source_node must be a "
                "non-empty string"
            )

        if (
            not isinstance(
                self.target_node,
                str,
            )
            or not self.target_node
        ):
            raise ValueError(
                "target_node must be a "
                "non-empty string"
            )

        _require_nonnegative_int(
            "source_channel",
            self.source_channel,
        )

        _require_nonnegative_int(
            "target_channel",
            self.target_channel,
        )

        if (
            type(self.delay_ticks)
            is not int
            or self.delay_ticks <= 0
        ):
            raise ValueError(
                "delay_ticks must be a "
                "positive integer"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class NetworkV0:
    nodes: tuple[
        NetworkNodeV0,
        ...,
    ]
    edges: tuple[
        NetworkEdgeV0,
        ...,
    ] = ()

    def __post_init__(
        self,
    ) -> None:
        if not self.nodes:
            raise ValueError(
                "Network v0 requires "
                "at least one node"
            )

        node_ids = tuple(
            node.node_id
            for node in self.nodes
        )

        if (
            len(set(node_ids))
            != len(node_ids)
        ):
            raise ValueError(
                "Network v0 node IDs "
                "must be unique"
            )

        known_nodes = set(
            node_ids
        )

        for edge in self.edges:
            if (
                edge.source_node
                not in known_nodes
            ):
                raise ValueError(
                    "edge source node "
                    f"{edge.source_node!r} "
                    "does not exist"
                )

            if (
                edge.target_node
                not in known_nodes
            ):
                raise ValueError(
                    "edge target node "
                    f"{edge.target_node!r} "
                    "does not exist"
                )
