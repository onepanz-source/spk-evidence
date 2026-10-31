from __future__ import annotations

import math
from itertools import product

from search.interaction_packed_core_v1 import (
    CoreConfig,
    encode_history,
)
from spk.event import SpikeTrain
from spk.operators import (
    Acc,
    Decay,
)
from spk.program import Program
from spk.runner import run_program


CONFIG = CoreConfig(
    channels=3,
    max_multiplicity=1,
    fractional_bits=24,
)


def spk_tau(
    config: CoreConfig,
) -> float:
    #
    # exp(-delta/tau)
    #
    # with:
    #
    #   tau = 1/(k ln 2)
    #
    # gives:
    #
    #   2^(-k delta)
    #
    k = config.bits_per_tick

    return (
        1.0
        /
        (
            k
            * math.log(2.0)
        )
    )


def spk_program(
    config: CoreConfig,
) -> Program:
    operators = [
        Decay(
            tau=spk_tau(
                config
            )
        )
    ]

    for channel in range(
        config.channels
    ):
        weight = float(
            1
            << (
                channel
                * config.bits_per_channel
            )
        )

        operators.append(
            Acc(
                weight=weight,
                channel=channel,
            )
        )

    return Program(
        tuple(
            operators
        )
    )


def history_to_train(
    config: CoreConfig,
    history,
) -> SpikeTrain:
    """
    Convert a fixed-horizon history to an event-driven SpikeTrain.

    SPK/v0 materializes temporal evolution only when a batch is
    processed. Therefore a trailing empty tick would otherwise be
    invisible.

    A sentinel event on channel == config.channels is inserted at the
    final timestamp. No ACC operator listens to that channel, so it
    affects only temporal materialization through DECAY.
    """

    if not history:
        return SpikeTrain()

    pairs = []

    for timestamp, batch in enumerate(
        history
    ):
        for channel, count in enumerate(
            batch
        ):
            pairs.extend(
                (
                    timestamp,
                    channel,
                )
                for _ in range(
                    count
                )
            )

    #
    # Explicit observation horizon.
    #
    pairs.append(
        (
            len(history) - 1,
            config.channels,
        )
    )

    return SpikeTrain.from_pairs(
        pairs
    )

def packed_as_real(
    config: CoreConfig,
    history,
) -> float:
    packed = encode_history(
        config,
        history,
    )

    return (
        packed
        /
        float(
            1
            << config.fractional_bits
        )
    )


def compare_history(
    config: CoreConfig,
    history,
):
    train = history_to_train(
        config,
        history,
    )

    result = run_program(
        spk_program(
            config
        ),
        train,
        initial_x=0.0,
    )

    spk_value = (
        result.final_state[0]
    )

    packed_value = (
        packed_as_real(
            config,
            history,
        )
    )

    return (
        spk_value,
        packed_value,
    )


def main() -> None:
    config = CONFIG

    print(
        "PACKED CORE <-> SPK BRIDGE"
    )

    print(
        f"channels: "
        f"{config.channels}"
    )

    print(
        f"bits/channel: "
        f"{config.bits_per_channel}"
    )

    print(
        f"bits/tick: "
        f"{config.bits_per_tick}"
    )

    print(
        f"tau: "
        f"{spk_tau(config)!r}"
    )

    print()

    possible_batches = tuple(
        product(
            range(
                config.max_multiplicity
                + 1
            ),
            repeat=config.channels,
        )
    )

    tested = 0

    max_abs_error = 0.0

    first_failure = None

    #
    # Four ticks are enough for an exhaustive bridge test:
    #
    #     8^4 = 4096 histories
    #
    for history in product(
        possible_batches,
        repeat=4,
    ):
        #
        # Empty complete history has no batches in run_program and
        # therefore no temporal endpoint. Skip it here.
        #
        if not any(
            any(batch)
            for batch in history
        ):
            continue

        spk_value, packed_value = (
            compare_history(
                config,
                history,
            )
        )

        error = abs(
            spk_value
            - packed_value
        )

        max_abs_error = max(
            max_abs_error,
            error,
        )

        tested += 1

        if (
            not math.isclose(
                spk_value,
                packed_value,
                rel_tol=1e-12,
                abs_tol=1e-12,
            )
            and first_failure is None
        ):
            first_failure = (
                history,
                spk_value,
                packed_value,
                error,
            )

    print(
        f"histories tested: "
        f"{tested}"
    )

    print(
        f"max absolute IEEE error: "
        f"{max_abs_error:.17g}"
    )

    print(
        "algebraic-model agreement "
        "within 1e-12: "
        f"{first_failure is None}"
    )

    if first_failure is not None:
        (
            history,
            spk_value,
            packed_value,
            error,
        ) = first_failure

        print()
        print(
            "FIRST FAILURE"
        )

        print(
            "history:",
            history,
        )

        print(
            "SPK:",
            repr(
                spk_value
            ),
        )

        print(
            "packed:",
            repr(
                packed_value
            ),
        )

        print(
            "error:",
            repr(
                error
            ),
        )


if __name__ == "__main__":
    main()
