from __future__ import annotations

from itertools import product

from search.interaction_packed_core_v1 import (
    CoreConfig as PackedConfig,
    encode_history,
)
from search.packed_core_spk_bridge_v1 import (
    history_to_train,
)
from spk_core.packed import (
    lower_packed_core,
)
from spk_core.runtime import (
    run_core_program,
)


PACKED = PackedConfig(
    channels=3,
    max_multiplicity=1,
    fractional_bits=24,
)


def main() -> None:
    config, program = (
        lower_packed_core(
            PACKED
        )
    )

    batches = tuple(
        product(
            (0, 1),
            repeat=3,
        )
    )

    tested = 0

    failures = []

    for history in product(
        batches,
        repeat=4,
    ):
        train = history_to_train(
            PACKED,
            history,
        )

        result = run_core_program(
            config,
            program,
            train,
        )

        expected = (
            encode_history(
                PACKED,
                history,
            )
        )

        tested += 1

        if (
            result.final_raw
            != expected
        ):
            failures.append(
                (
                    history,
                    result.final_raw,
                    expected,
                )
            )

            break

    print(
        "SPK/CORE MICRO-ISA BRIDGE"
    )

    print(
        f"histories tested: "
        f"{tested}"
    )

    print(
        f"exact integer matches: "
        f"{tested - len(failures)}"
    )

    print(
        f"failures: "
        f"{len(failures)}"
    )

    print(
        f"exact agreement: "
        f"{not failures}"
    )

    print()

    print(
        "CORE PROGRAM"
    )

    for pc, instruction in enumerate(
        program.instructions
    ):
        print(
            f"  {pc:02d}: "
            f"{instruction}"
        )

    if failures:
        print()
        print(
            "FIRST FAILURE"
        )

        print(
            failures[0]
        )


if __name__ == "__main__":
    main()
