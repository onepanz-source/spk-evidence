from __future__ import annotations

from itertools import product

from search.core_synthesis_v1 import (
    CONFIG,
    render_program,
)

from search.core_temporal_depth5_cegar_v2 import (
    INITIAL_SAMPLES,
    TEMPORAL_POOL,
    observation,
)

from spk.event import SpikeTrain

from spk_core.canonicalize import (
    canonicalize_core_program,
)
from spk_core.isa import (
    CoreProgram,
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
    program: CoreProgram,
):
    return tuple(
        observation(
            program,
            sample,
        )
        for sample in REFINED_SAMPLES
    )


def main() -> None:
    syntactic = 0

    canonical_programs = set()

    canonical_signature_cache = {}

    violations = []

    count_by_length = {}

    for length in range(
        1,
        MAX_LENGTH + 1,
    ):
        depth_count = 0

        for instructions in product(
            TEMPORAL_POOL,
            repeat=length,
        ):
            syntactic += 1
            depth_count += 1

            source = CoreProgram(
                instructions
            )

            canonical = (
                canonicalize_core_program(
                    source,
                    config=CONFIG,
                )
            )

            canonical_programs.add(
                canonical
            )

            #
            # Syntactically canonical programs trivially preserve
            # themselves.
            #
            if source == canonical:
                continue

            canonical_signature = (
                canonical_signature_cache.get(
                    canonical
                )
            )

            if canonical_signature is None:
                canonical_signature = (
                    signature(
                        canonical
                    )
                )

                canonical_signature_cache[
                    canonical
                ] = (
                    canonical_signature
                )

            source_signature = (
                signature(
                    source
                )
            )

            if (
                source_signature
                != canonical_signature
            ):
                bad_index = next(
                    index
                    for index, (
                        source_observation,
                        canonical_observation,
                    )
                    in enumerate(
                        zip(
                            source_signature,
                            canonical_signature,
                        )
                    )
                    if (
                        source_observation
                        != canonical_observation
                    )
                )

                violations.append(
                    (
                        source,
                        canonical,
                        bad_index,
                        source_signature[
                            bad_index
                        ],
                        canonical_signature[
                            bad_index
                        ],
                    )
                )

                break

        count_by_length[
            length
        ] = depth_count

        if violations:
            break

    print(
        "SPK/CORE TEMPORAL DEPTH-5 "
        "PRESERVATION v1"
    )

    print()

    print(
        f"instruction pool: "
        f"{len(TEMPORAL_POOL)}"
    )

    print(
        f"max length: "
        f"{MAX_LENGTH}"
    )

    print(
        f"refined samples: "
        f"{len(REFINED_SAMPLES)}"
    )

    print(
        f"syntactic programs checked: "
        f"{syntactic}"
    )

    print(
        f"canonical programs: "
        f"{len(canonical_programs)}"
    )

    print(
        f"semantic preservation violations: "
        f"{len(violations)}"
    )

    print()

    print(
        "PROGRAMS BY DEPTH"
    )

    for length in sorted(
        count_by_length
    ):
        print(
            f"  depth={length}: "
            f"{count_by_length[length]}"
        )

    if not violations:
        print()
        print(
            "DEPTH-5 PRESERVATION CHECKPOINT"
        )

        print(
            f"  {syntactic}"
            f" -> "
            f"{len(canonical_programs)}"
        )

        print(
            "  preservation = EXACT "
            "ON REFINED CORPUS"
        )

    else:
        (
            source,
            canonical,
            bad_index,
            source_observation,
            canonical_observation,
        ) = violations[0]

        train, initial_raw = (
            REFINED_SAMPLES[
                bad_index
            ]
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

        print()
        print(
            "SEPARATING SAMPLE"
        )

        print(
            f"  x0="
            f"{initial_raw}"
        )

        print(
            f"  events="
            f"{train.as_pairs()}"
        )

        print(
            f"  source="
            f"{source_observation}"
        )

        print(
            f"  canonical="
            f"{canonical_observation}"
        )


if __name__ == "__main__":
    main()
