from __future__ import annotations

from collections import defaultdict
from itertools import product

from search.core_synthesis_v1 import (
    CONFIG,
)

from search.core_temporal_depth5_cegar_v2 import (
    INITIAL_SAMPLES,
    TEMPORAL_POOL,
    observation,
)

from spk.event import SpikeTrain

from spk_core.isa import (
    CoreProgram,
)

from spk_core.semantic_canonicalize import (
    canonicalize_core_program_semantic,
)


MAX_LENGTH = 5


CEGAR_REFINEMENTS = (
    (
        SpikeTrain.from_pairs(
            (
                (1, 0),
                (1, 0),
                (1, 1),
            )
        ),
        4,
    ),
    (
        SpikeTrain.from_pairs(
            (
                (1, 1),
                (1, 1),
            )
        ),
        2,
    ),
    (
        SpikeTrain.from_pairs(
            (
                (0, 1),
                (1, 0),
                (1, 0),
                (1, 1),
                (1, 1),
            )
        ),
        11,
    ),
    (
        SpikeTrain.from_pairs(
            (
                (1, 0),
            )
        ),
        30,
    ),
    (
        SpikeTrain.from_pairs(
            (
                (1, 0),
            )
        ),
        2,
    ),
    (
        SpikeTrain.from_pairs(
            (
                (1, 1),
            )
        ),
        12,
    ),
    (
        SpikeTrain.from_pairs(
            (
                (1, 2),
            )
        ),
        1,
    ),
    (
        SpikeTrain.from_pairs(
            (
                (0, 0),
            )
        ),
        2,
    ),
)


REFINED_SAMPLES = tuple(
    dict.fromkeys(
        tuple(INITIAL_SAMPLES)
        + CEGAR_REFINEMENTS
    )
)


def signature(
    program,
):
    return tuple(
        observation(
            program,
            sample,
        )
        for sample in REFINED_SAMPLES
    )


def main():
    syntactic = 0

    canonical = set()

    for length in range(
        1,
        MAX_LENGTH + 1,
    ):
        for instructions in product(
            TEMPORAL_POOL,
            repeat=length,
        ):
            syntactic += 1

            program = CoreProgram(
                instructions
            )

            canonical.add(
                canonicalize_core_program_semantic(
                    program,
                    config=CONFIG,
                )
            )

    classes = defaultdict(
        list
    )

    for program in canonical:
        classes[
            signature(
                program
            )
        ].append(
            program
        )

    ambiguous = [
        members
        for members in classes.values()
        if len(members) > 1
    ]

    excess = sum(
        len(members) - 1
        for members in ambiguous
    )

    print(
        "SPK/CORE SEMANTIC CANONICALIZATION "
        "DEPTH-5 v1"
    )

    print()

    print(
        f"syntactic programs: "
        f"{syntactic}"
    )

    print(
        f"semantic canonical programs: "
        f"{len(canonical)}"
    )

    print(
        f"behavioral classes: "
        f"{len(classes)}"
    )

    print(
        f"ambiguous classes: "
        f"{len(ambiguous)}"
    )

    print(
        f"residual excess: "
        f"{excess}"
    )

    print()

    print(
        "CHECKPOINT"
    )

    print(
        f"  {syntactic}"
        f" -> "
        f"{len(canonical)}"
        f" -> "
        f"{len(classes)}"
    )


if __name__ == "__main__":
    main()
