from __future__ import annotations

from itertools import product

from search.core_synthesis_v1 import (
    CONFIG,
    render_program,
)

from search.core_temporal_depth5_cegar_v2 import (
    TEMPORAL_POOL,
    observation,
)

from search.core_temporal_depth5_preservation_v1 import (
    REFINED_SAMPLES,
)

from spk_core.isa import (
    CoreProgram,
)

from spk_core.semantic_canonicalize import (
    canonicalize_core_program_semantic,
)


MAX_LENGTH = 5


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

    semantic_canonical = set()

    canonical_signature_cache = {}

    violations = []

    rewritten = 0

    for length in range(
        1,
        MAX_LENGTH + 1,
    ):
        for instructions in product(
            TEMPORAL_POOL,
            repeat=length,
        ):
            syntactic += 1

            source = CoreProgram(
                instructions
            )

            canonical = (
                canonicalize_core_program_semantic(
                    source,
                    config=CONFIG,
                )
            )

            semantic_canonical.add(
                canonical
            )

            if source == canonical:
                continue

            rewritten += 1

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

    print(
        "SPK/CORE SEMANTIC DEPTH-5 "
        "PRESERVATION v1"
    )

    print()

    print(
        f"refined samples: "
        f"{len(REFINED_SAMPLES)}"
    )

    print(
        f"syntactic programs checked: "
        f"{syntactic}"
    )

    print(
        f"programs rewritten: "
        f"{rewritten}"
    )

    print(
        f"semantic canonical programs: "
        f"{len(semantic_canonical)}"
    )

    print(
        f"semantic preservation violations: "
        f"{len(violations)}"
    )

    if not violations:
        print()

        print(
            "SEMANTIC DEPTH-5 "
            "PRESERVATION CHECKPOINT"
        )

        print(
            f"  {syntactic}"
            f" -> "
            f"{len(semantic_canonical)}"
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
            "FIRST SEMANTIC "
            "PRESERVATION VIOLATION"
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
            "SEMANTIC CANONICAL"
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
