from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from spk.event import SpikeTrain
from spk.operators import (
    Acc,
    Compare,
    Emit,
    Reset,
)
from spk.program import Program
from spk.runner import run_program

from spk_core.compiler import (
    compile_spk_program,
)
from spk_core.isa import (
    CoreConfig,
)
from spk_core.runtime import (
    run_core_program,
)


CONFIG = CoreConfig(
    state_bits=24,
    fractional_bits=8,
)


@dataclass(
    frozen=True,
    slots=True,
)
class ControlCase:
    name: str
    program: Program


CASES = (
    ControlCase(
        name="threshold_emit_reset",
        program=Program(
            (
                Acc(
                    weight=1.0,
                    channel=0,
                ),
                Compare(
                    threshold=1.0,
                ),
                Emit(
                    channel_out=7,
                ),
                Reset(
                    value=0.0,
                ),
            )
        ),
    ),

    ControlCase(
        name="persistent_threshold",
        program=Program(
            (
                Acc(
                    weight=1.0,
                    channel=0,
                ),
                Compare(
                    threshold=2.0,
                ),
                Emit(
                    channel_out=7,
                ),
            )
        ),
    ),

    ControlCase(
        name="weighted_two_channel",
        program=Program(
            (
                Acc(
                    weight=1.0,
                    channel=0,
                ),
                Acc(
                    weight=2.0,
                    channel=1,
                ),
                Compare(
                    threshold=3.0,
                ),
                Emit(
                    channel_out=9,
                ),
                Reset(
                    value=0.0,
                ),
            )
        ),
    ),

    ControlCase(
        name="reset_then_recompare",
        program=Program(
            (
                Acc(
                    weight=1.0,
                    channel=0,
                ),
                Compare(
                    threshold=2.0,
                ),
                Reset(
                    value=0.0,
                ),
                Compare(
                    threshold=1.0,
                ),
                Emit(
                    channel_out=8,
                ),
            )
        ),
    ),

    ControlCase(
        name="two_compare_two_emit",
        program=Program(
            (
                Acc(
                    weight=1.0,
                    channel=0,
                ),
                Compare(
                    threshold=1.0,
                ),
                Emit(
                    channel_out=7,
                ),
                Compare(
                    threshold=2.0,
                ),
                Emit(
                    channel_out=8,
                ),
            )
        ),
    ),
)


INITIAL_STATES = (
    0.0,
    1.0,
    2.0,
)


def history_to_train(
    history,
) -> SpikeTrain:
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

    return SpikeTrain.from_pairs(
        pairs
    )


def compare_execution(
    case: ControlCase,
    history,
    initial_x: float,
):
    compilation = compile_spk_program(
        case.program,
        CONFIG,
    )

    train = history_to_train(
        history
    )

    source = run_program(
        case.program,
        train,
        initial_x=initial_x,
    )

    initial_raw = int(
        initial_x
        * CONFIG.scale
    )

    core = run_core_program(
        CONFIG,
        compilation.program,
        train,
        initial_raw=initial_raw,
    )

    source_x, source_guard = (
        source.final_state
    )

    return (
        source.output.as_pairs(),
        source_x,
        source_guard,
        core.output.as_pairs(),
        core.final_value(
            CONFIG
        ),
        core.final_guard,
    )


def main() -> None:
    #
    # Two input channels.
    #
    # Each channel may contribute 0, 1 or 2 coincident events
    # per timestamp.
    #
    possible_batches = tuple(
        product(
            range(3),
            repeat=2,
        )
    )

    tested = 0
    failures = 0

    first_failure = None

    for case in CASES:
        compilation = (
            compile_spk_program(
                case.program,
                CONFIG,
            )
        )

        print(
            "=" * 72
        )

        print(
            case.name
        )

        print(
            "source instructions:",
            len(
                case.program.operators
                if hasattr(
                    case.program,
                    "operators",
                )
                else compilation.program.instructions
            ),
        )

        print(
            "core instructions:",
            len(
                compilation.program.instructions
            ),
        )

        case_tested = 0

        for history in product(
            possible_batches,
            repeat=3,
        ):
            for initial_x in (
                INITIAL_STATES
            ):
                (
                    source_output,
                    source_x,
                    source_guard,
                    core_output,
                    core_x,
                    core_guard,
                ) = compare_execution(
                    case,
                    history,
                    initial_x,
                )

                tested += 1
                case_tested += 1

                if (
                    source_output
                    != core_output
                    or source_x
                    != core_x
                    or source_guard
                    != core_guard
                ):
                    failures += 1

                    if (
                        first_failure
                        is None
                    ):
                        first_failure = (
                            case.name,
                            history,
                            initial_x,
                            source_output,
                            source_x,
                            source_guard,
                            core_output,
                            core_x,
                            core_guard,
                        )

        print(
            f"executions tested: "
            f"{case_tested}"
        )

        print(
            "exact agreement: ",
            failures == 0,
        )

        print()

    print(
        "=" * 72
    )

    print(
        "SPK/CORE CONTROL BRIDGE"
    )

    print(
        f"programs: "
        f"{len(CASES)}"
    )

    print(
        f"total executions: "
        f"{tested}"
    )

    print(
        f"failures: "
        f"{failures}"
    )

    print(
        f"exact agreement: "
        f"{failures == 0}"
    )

    if first_failure is not None:
        (
            name,
            history,
            initial_x,
            source_output,
            source_x,
            source_guard,
            core_output,
            core_x,
            core_guard,
        ) = first_failure

        print()
        print(
            "FIRST FAILURE"
        )

        print(
            "program:",
            name,
        )

        print(
            "history:",
            history,
        )

        print(
            "initial_x:",
            initial_x,
        )

        print(
            "source:",
            (
                source_output,
                source_x,
                source_guard,
            ),
        )

        print(
            "core:",
            (
                core_output,
                core_x,
                core_guard,
            ),
        )


if __name__ == "__main__":
    main()
