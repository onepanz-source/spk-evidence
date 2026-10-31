from __future__ import annotations

import math
from itertools import product

from search.interaction_packed_core_v1 import (
    CoreConfig as PackedConfig,
    encode_history,
)
from search.packed_core_spk_bridge_v1 import (
    history_to_train,
)
from spk.operators import (
    Acc,
    Decay,
)
from spk.program import Program

from spk_core.compiler import (
    compile_spk_program,
)
from spk_core.isa import (
    CoreConfig,
)
from spk_core.runtime import (
    run_core_program,
)


PACKED = PackedConfig(
    channels=3,
    max_multiplicity=1,
    fractional_bits=24,
)


CORE_CONFIG = CoreConfig(
    state_bits=(
        PACKED.word_bits
    ),
    fractional_bits=(
        PACKED.fractional_bits
    ),
)


def source_program():
    k = PACKED.bits_per_tick

    tau = (
        1.0
        /
        (
            k
            * math.log(2.0)
        )
    )

    return Program(
        (
            Decay(
                tau=tau
            ),
            Acc(
                weight=1.0,
                channel=0,
            ),
            Acc(
                weight=2.0,
                channel=1,
            ),
            Acc(
                weight=4.0,
                channel=2,
            ),
        )
    )


def main() -> None:
    compilation = (
        compile_spk_program(
            source_program(),
            CORE_CONFIG,
        )
    )

    batches = tuple(
        product(
            (0, 1),
            repeat=3,
        )
    )

    tested = 0
    failures = 0

    for history in product(
        batches,
        repeat=4,
    ):
        train = history_to_train(
            PACKED,
            history,
        )

        result = run_core_program(
            compilation.config,
            compilation.program,
            train,
        )

        expected = encode_history(
            PACKED,
            history,
        )

        tested += 1

        if (
            result.final_raw
            != expected
        ):
            failures += 1

            print(
                "FIRST FAILURE"
            )

            print(
                "history:",
                history,
            )

            print(
                "core:",
                result.final_raw,
            )

            print(
                "expected:",
                expected,
            )

            break

    print(
        "SPK -> CORE COMPILER BRIDGE"
    )

    print(
        f"histories tested: "
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

    print()

    print(
        "LOWERING"
    )

    for note in (
        compilation.notes
    ):
        print(
            " ",
            note
        )

    print()

    print(
        "GENERATED CORE PROGRAM"
    )

    for pc, instruction in enumerate(
        compilation.program.instructions
    ):
        print(
            f"  {pc:02d}: "
            f"{instruction}"
        )


if __name__ == "__main__":
    main()
