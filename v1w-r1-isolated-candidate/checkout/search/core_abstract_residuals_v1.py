from __future__ import annotations

from collections import defaultdict

from search.core_synthesis_v1 import (
    CONFIG,
    render_program,
)

from search.core_temporal_depth5_cegar_v2 import (
    INITIAL_SAMPLES,
    all_canonical_programs,
    observation,
)

from spk.event import SpikeTrain

from spk_core.abstract import (
    analyze_program,
    equivalent_threshold_interval,
)
from spk_core.isa import (
    CoreCmp,
)


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
        for sample
        in REFINED_SAMPLES
    )


def interesting_facts(
    program,
):
    facts = []

    for step in analyze_program(
        CONFIG,
        program,
    ):
        raw = step.after.merged

        if raw is None:
            continue

        if raw.is_exact:
            facts.append(
                (
                    step.index,
                    f"exact={raw.exact_value}",
                )
            )

        elif raw.modulus > 1:
            facts.append(
                (
                    step.index,
                    (
                        f"raw in "
                        f"[{raw.lower},{raw.upper}] "
                        f"mod {raw.modulus} "
                        f"= {raw.residue}"
                    ),
                )
            )

        if (
            step.after.guard_status
            != "UNKNOWN"
        ):
            facts.append(
                (
                    step.index,
                    (
                        "guard="
                        + step.after.guard_status
                    ),
                )
            )

        if isinstance(
            step.instruction,
            CoreCmp,
        ):
            before_raw = (
                step.before.merged
            )

            if before_raw is not None:
                low, high = (
                    equivalent_threshold_interval(
                        before_raw,
                        step.instruction.threshold_raw,
                    )
                )

                if low != high:
                    facts.append(
                        (
                            step.index,
                            (
                                "CMP threshold "
                                f"{step.instruction.threshold_raw} "
                                "equivalent over abstract state to "
                                f"[{low},{high}]"
                            ),
                        )
                    )

    return tuple(
        facts
    )


def main() -> None:
    (
        syntactic,
        programs,
    ) = all_canonical_programs()

    classes = defaultdict(
        list
    )

    for program in programs:
        classes[
            signature(
                program
            )
        ].append(
            program
        )

    residuals = [
        members
        for members in classes.values()
        if len(members) > 1
    ]

    residuals.sort(
        key=lambda members: (
            -len(members),
            repr(members),
        )
    )

    excess = sum(
        len(members) - 1
        for members in residuals
    )

    print(
        "SPK/CORE ABSTRACT RESIDUAL "
        "ANALYSIS v1"
    )

    print()

    print(
        f"syntactic programs: "
        f"{syntactic}"
    )

    print(
        f"canonical programs: "
        f"{len(programs)}"
    )

    print(
        f"behavioral classes: "
        f"{len(classes)}"
    )

    print(
        f"residual classes: "
        f"{len(residuals)}"
    )

    print(
        f"residual excess: "
        f"{excess}"
    )

    print()

    for number, members in enumerate(
        residuals,
        start=1,
    ):
        print(
            "=" * 72
        )

        print(
            f"CLASS {number}: "
            f"{len(members)} forms"
        )

        for member_index, program in enumerate(
            members,
            start=1,
        ):
            print()
            print(
                f"FORM {member_index}"
            )

            rendered = (
                render_program(
                    program
                )
            )

            if rendered:
                print(
                    rendered
                )
            else:
                print(
                    "<EMPTY>"
                )

            facts = (
                interesting_facts(
                    program
                )
            )

            if facts:
                print(
                    "  ABSTRACT FACTS"
                )

                for index, fact in facts:
                    print(
                        f"    @{index}: "
                        f"{fact}"
                    )

            else:
                print(
                    "  ABSTRACT FACTS: none"
                )


if __name__ == "__main__":
    main()
