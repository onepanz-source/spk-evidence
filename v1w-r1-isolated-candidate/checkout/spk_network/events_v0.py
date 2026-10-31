from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from .model_v0 import NetworkV0


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
    order=True,
)
class NetworkEventV0:
    timestamp: int
    node_id: str
    channel: int

    def __post_init__(
        self,
    ) -> None:
        _require_nonnegative_int(
            "timestamp",
            self.timestamp,
        )

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

        _require_nonnegative_int(
            "channel",
            self.channel,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class NetworkBatchV0:
    timestamp: int
    node_id: str
    channels: tuple[
        int,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        _require_nonnegative_int(
            "timestamp",
            self.timestamp,
        )

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

        if not self.channels:
            raise ValueError(
                "network batch must contain "
                "at least one event"
            )

        for channel in self.channels:
            _require_nonnegative_int(
                "channel",
                channel,
            )

        if tuple(
            sorted(
                self.channels
            )
        ) != self.channels:
            raise ValueError(
                "network batch channels "
                "must be canonicalized"
            )


def validate_network_events_v0(
    network: NetworkV0,
    events: tuple[
        NetworkEventV0,
        ...,
    ],
) -> None:
    known_nodes = {
        node.node_id
        for node in network.nodes
    }

    for event in events:
        if (
            event.node_id
            not in known_nodes
        ):
            raise ValueError(
                "event target node "
                f"{event.node_id!r} "
                "does not exist"
            )


def batch_network_events_v0(
    network: NetworkV0,
    events: tuple[
        NetworkEventV0,
        ...,
    ],
) -> tuple[
    NetworkBatchV0,
    ...,
]:
    """
    Canonical network event batching.

    Events are grouped by (timestamp, node_id).

    Multiplicity is preserved exactly.  Channel sorting is
    representational only and gives deterministic batches.
    """

    validate_network_events_v0(
        network,
        events,
    )

    grouped = defaultdict(
        list
    )

    for event in events:
        grouped[
            (
                event.timestamp,
                event.node_id,
            )
        ].append(
            event.channel
        )

    batches = []

    for (
        timestamp,
        node_id,
    ) in sorted(
        grouped
    ):
        batches.append(
            NetworkBatchV0(
                timestamp=timestamp,
                node_id=node_id,
                channels=tuple(
                    sorted(
                        grouped[
                            (
                                timestamp,
                                node_id,
                            )
                        ]
                    )
                ),
            )
        )

    return tuple(
        batches
    )
