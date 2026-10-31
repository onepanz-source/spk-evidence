from __future__ import annotations

from itertools import product

from search.core_synthesis_v1 import (
    CONFIG,
    render_program,
)

from search.core_temporal_cegar_v2 import (
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


MAX_LENGTH = 4


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
            )
        ),
        3,
    ),
    (
        SpikeTrain.from_pairs(
            (
                (1, 1),
            )
        ),
        14,
    ),
)


REFINED_SAMPLES = tuple(
    dict.fromkeys(
        tuple(
            INITIAL_SAMPLES
        )
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
        for sample
        in REFINED_SAMPLES
    )


def all_source_programs():
    programs = []

    for length in range(
        1,
        MAX_LENGTH + 1,
    ):
        for instructions in product(
            TEMPORAL_POOL,
            repeat=length,
        ):
            programs.append(
                CoreProgram(
                    instructions
                )
            )

    return tuple(
        programs
    )


def main() -> None:
    sources = (
        all_source_programs()
    )

    canonical_for = {}

    canonical_programs = set()

    for source in sources:
        canonical = (
            canonicalize_core_program(
                source,
                config=CONFIG,
            )
        )

        canonical_for[
            source
        ] = canonical

        canonical_programs.add(
            canonical
        )

    #
    # Cache every distinct program signature.  Otherwise humans would
    # make the CPU rediscover the same 576 facts thousands of times,
    # which is apparently how civilization normally operates.
    #
    signature_cache = {}

    def cached_signature(
        program,
    ):
        if program not in signature_cache:
            signature_cache[
                program
            ] = signature(
                program
            )

        return signature_cache[
            program
        ]

    source_behaviors = set()

    canonical_behaviors = set()

    violations = []

    first_bad_sample = None

    for source in sources:
        canonical = (
            canonical_for[
                source
            ]
        )

        source_signature = (
            cached_signature(
                source
            )
        )

        canonical_signature = (
            cached_signature(
                canonical
            )
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

            for index, (
                source_observation,
                canonical_observation,
            ) in enumerate(
                zip(
                    source_signature,
                    canonical_signature,
                )
            ):
                if (
                    source_observation
                    != canonical_observation
                ):
                    first_bad_sample = (
                        REFINED_SAMPLES[
                            index
                        ],
                        source_observation,
                        canonical_observation,
                    )
                    break

            break

    print(
        "SPK/CORE TEMPORAL PRESERVATION v1"
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
        f"syntactic programs: "
        f"{len(sources)}"
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
            "TEMPORAL FINITE-DOMAIN STATUS"
        )

        print(
            f"  {len(sources)}"
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

        if (
            first_bad_sample
            is not None
        ):
            (
                sample,
                source_observation,
                canonical_observation,
            ) = first_bad_sample

            train, initial_raw = sample

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
