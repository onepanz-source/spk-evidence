from __future__ import annotations

from itertools import product

from search.core_synthesis_v1 import (
    CONFIG,
    INSTRUCTION_POOL,
    SAMPLES,
    render_program,
)

from spk.event import SpikeTrain

from spk_core.canonicalize import (
    canonicalize_core_program,
)
from spk_core.isa import (
    CoreProgram,
)
from spk_core.runtime import (
    run_core_program,
)


MAX_LENGTH = 4


EXTRA_SAMPLES = (
    (
        SpikeTrain.from_pairs(
            (
                (0, 1),
                (0, 1),
            )
        ),
        2,
    ),
    (
        SpikeTrain.from_pairs(
            (
                (0, 1),
                (0, 1),
            )
        ),
        0,
    ),
)


REFINED_SAMPLES = (
    tuple(SAMPLES)
    + EXTRA_SAMPLES
)


def observation(
    program: CoreProgram,
    sample,
):
    train, initial_raw = sample

    result = run_core_program(
        CONFIG,
        program,
        train,
        initial_raw=initial_raw,
    )

    return (
        result.output.as_pairs(),
        result.final_raw,
        result.final_guard,
    )


def signature(
    program: CoreProgram,
):
    return tuple(
        observation(
            program,
            sample,
        )
        for sample
        in REFINED_SAMPLES
    )


def main() -> None:
    syntactic = 0

    canonical_programs = set()

    source_behaviors = set()

    canonical_behaviors = set()

    violations = []

    for length in range(
        1,
        MAX_LENGTH + 1,
    ):
        for instructions in product(
            INSTRUCTION_POOL,
            repeat=length,
        ):
            source = CoreProgram(
                instructions
            )

            canonical = (
                canonicalize_core_program(
                    source,
                    config=CONFIG,
                )
            )

            source_signature = (
                signature(
                    source
                )
            )

            canonical_signature = (
                signature(
                    canonical
                )
            )

            syntactic += 1

            canonical_programs.add(
                canonical
            )

            source_behaviors.add(
                source_signature
            )

            canonical_behaviors.add(
                canonical_signature
            )

            if (
                source_signature
                != canonical_signature
            ):
                violations.append(
                    (
                        source,
                        canonical,
                    )
                )

                break

        if violations:
            break

    print(
        "SPK/CORE PRESERVATION v1"
    )

    print()

    print(
        f"refined samples: "
        f"{len(REFINED_SAMPLES)}"
    )

    print(
        f"syntactic programs: "
        f"{syntactic}"
    )

    print(
        f"canonical programs: "
        f"{len(canonical_programs)}"
    )

    print(
        f"source behavioral classes: "
        f"{len(source_behaviors)}"
    )

    print(
        f"canonical behavioral classes: "
        f"{len(canonical_behaviors)}"
    )

    print(
        f"semantic preservation violations: "
        f"{len(violations)}"
    )

    if not violations:
        print()

        print(
            "FINITE DOMAIN CHECKPOINT"
        )

        print(
            f"  {syntactic}"
            f" -> "
            f"{len(canonical_programs)}"
            f" -> "
            f"{len(canonical_behaviors)}"
        )

        print(
            "  canonical/behavior ratio: "
            f"{len(canonical_programs) / len(canonical_behaviors):.6f}"
        )

    else:
        source, canonical = (
            violations[0]
        )

        print()
        print(
            "FIRST PRESERVATION VIOLATION"
        )

        print()
        print(
            "SOURCE"
        )

        print(
            render_program(
                source
            )
        )

        print()
        print(
            "CANONICAL"
        )

        print(
            render_program(
                canonical
            )
        )


if __name__ == "__main__":
    main()
