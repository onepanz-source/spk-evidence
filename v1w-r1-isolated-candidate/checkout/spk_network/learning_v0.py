from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


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
class NetworkRouteObservationV0:
    """
    Immutable observation of one routed spike.

    This records causal provenance only.

    It deliberately defines no learning rule, reward,
    efficacy score or weight update.
    """

    emission_timestamp: int

    source_node: str
    source_channel: int

    delivery_timestamp: int

    target_node: str
    target_channel: int

    delay_ticks: int

    def __post_init__(
        self,
    ) -> None:
        _require_nonnegative_int(
            "emission_timestamp",
            self.emission_timestamp,
        )

        _require_nonnegative_int(
            "source_channel",
            self.source_channel,
        )

        _require_nonnegative_int(
            "delivery_timestamp",
            self.delivery_timestamp,
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

        if not self.source_node:
            raise ValueError(
                "source_node must not be empty"
            )

        if not self.target_node:
            raise ValueError(
                "target_node must not be empty"
            )

        if (
            self.delivery_timestamp
            != self.emission_timestamp
            + self.delay_ticks
        ):
            raise ValueError(
                "delivery timestamp must equal "
                "emission timestamp + delay"
            )


@dataclass(
    frozen=True,
    slots=True,
)
class NetworkBatchObservationV0:
    """
    Immutable observation of one completed node batch.

    channels preserves input multiplicity.

    output_channels preserves output multiplicity.

    No interpretation of the outcome as positive,
    negative or useful feedback is defined in v0.
    """

    timestamp: int
    node_id: str

    channels: tuple[
        int,
        ...,
    ]

    final_raw: int
    final_guard: bool

    output_channels: tuple[
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

        if not self.node_id:
            raise ValueError(
                "node_id must not be empty"
            )

        if not self.channels:
            raise ValueError(
                "batch observation requires "
                "at least one input event"
            )

        for channel in self.channels:
            _require_nonnegative_int(
                "channel",
                channel,
            )

        for channel in self.output_channels:
            _require_nonnegative_int(
                "output channel",
                channel,
            )

        if tuple(
            sorted(
                self.channels
            )
        ) != self.channels:
            raise ValueError(
                "input channels must be canonical"
            )

        if tuple(
            sorted(
                self.output_channels
            )
        ) != self.output_channels:
            raise ValueError(
                "output channels must be canonical"
            )

        _require_nonnegative_int(
            "final_raw",
            self.final_raw,
        )

        if type(
            self.final_guard
        ) is not bool:
            raise TypeError(
                "final_guard must be boolean"
            )


class NetworkLearningObserverV0(
    Protocol
):
    """
    Read-only learning/back-validation interface.

    Implementations may observe execution and derive external
    learning signals.

    Observer callbacks cannot alter Network v0 execution state.
    """

    def on_route(
        self,
        observation:
            NetworkRouteObservationV0,
    ) -> None:
        ...

    def on_batch(
        self,
        observation:
            NetworkBatchObservationV0,
    ) -> None:
        ...
