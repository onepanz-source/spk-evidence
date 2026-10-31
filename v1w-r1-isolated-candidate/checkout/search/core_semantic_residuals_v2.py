from __future__ import annotations

from collections import (
    Counter,
    defaultdict,
)
from itertools import product

from search.core_synthesis_v1 import (
    CONFIG,
    render_program,
)

from search.core_temporal_depth5_cegar_v2 import (
    TEMPORAL_POOL,
    observation,
)

from search.core_semantic_depth5_preservation_v1 import (
    REFINED_SAMPLES,
)

from search.core_abstract_residuals_v1 import (
    interesting_facts,
)

from spk_core.canonicalize import (
    canonicalize_core_program,
)

from spk_core.semantic_canonicalize import (
    canonicalize_core_program_semantic,
)

from spk_core.isa import (
    CoreAcc,
    CoreCmp,
    CoreEmit,
    CoreProgram,
    CoreReset,
    ShiftDecay,
)


MAX_LENGTH = 5


def signature(program):
    return tuple(
        observation(
            program,
            sample,
        )
        for sample
        in REFINED_SAMPLES
    )


def program_tags(program):
    instructions = (
        program.instructions
    )

    acc_channels = [
        instruction.channel
        for instruction in instructions
        if isinstance(
            instruction,
            CoreAcc,
        )
    ]

    counts = Counter(
        acc_channels
    )

    tags = []

    if any(
        count >= 2
        for count in counts.values()
    ):
        tags.append(
            "REPEATED_SAME_CHANNEL_ACC"
        )

    if any(
        isinstance(
            instruction,
            ShiftDecay,
        )
        for instruction
        in instructions
    ):
        tags.append(
            "TEMPORAL"
        )

    if sum(
        isinstance(
            instruction,
            ShiftDecay,
        )
        for instruction
        in instructions
    ) >= 2:
        tags.append(
            "MULTI_SHIFT"
        )

    if (
        not any(
            isinstance(
                instruction,
                (
                    CoreAcc,
                    ShiftDecay,
                ),
            )
            for instruction
            in instructions
        )
    ):
        tags.append(
            "CONTROL_ONLY"
        )

    if sum(
        isinstance(
            instruction,
            CoreCmp,
        )
        for instruction
        in instructions
    ) >= 2:
        tags.append(
            "MULTI_CMP"
        )

    if any(
        isinstance(
            instruction,
            CoreEmit,
        )
        for instruction
        in instructions
    ):
        tags.append(
            "EMIT"
        )

    if any(
        isinstance(
            instruction,
            CoreReset,
        )
        for instruction
        in instructions
    ):
        tags.append(
            "RESET"
        )

    return tuple(
        tags
    )


def main():
    syntactic = 0

    structural = set()

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

            structural.add(
                canonicalize_core_program(
                    source,
                    config=CONFIG,
                )
            )

    semantic_map = {}

    semantic = set()

    changed_structural = []

    for program in structural:
        normalized = (
            canonicalize_core_program_semantic(
                program,
                config=CONFIG,
            )
        )

        semantic_map[
            program
        ] = normalized

        semantic.add(
            normalized
        )

        if normalized != program:
            changed_structural.append(
                (
                    program,
                    normalized,
                )
            )

    #
    # Which structural forms collapse onto one semantic form?
    #
    collapse_groups = defaultdict(
        list
    )

    for source, target in (
        semantic_map.items()
    ):
        collapse_groups[
            target
        ].append(
            source
        )

    real_collapses = [
        (
            target,
            members,
        )
        for target, members
        in collapse_groups.items()
        if len(members) > 1
    ]

    real_collapses.sort(
        key=lambda item: (
            -len(item[1]),
            repr(item[0]),
        )
    )

    #
    # Behavioral partition after semantic normalization.
    #
    classes = defaultdict(
        list
    )

    for program in semantic:
        classes[
            signature(
                program
            )
        ].append(
            program
        )

    residuals = [
        members
        for members
        in classes.values()
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
        for members
        in residuals
    )

    print(
        "SPK/CORE SEMANTIC RESIDUAL "
        "CENSUS v2"
    )

    print()

    print(
        f"syntactic programs: "
        f"{syntactic}"
    )

    print(
        f"structural canonical: "
        f"{len(structural)}"
    )

    print(
        f"semantic canonical: "
        f"{len(semantic)}"
    )

    print(
        f"structural forms changed "
        f"by semantic pass: "
        f"{len(changed_structural)}"
    )

    print(
        f"semantic collapse groups: "
        f"{len(real_collapses)}"
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

    print(
        "=" * 72
    )

    print(
        "SEMANTIC COLLAPSES"
    )

    for number, (
        target,
        members,
    ) in enumerate(
        real_collapses,
        start=1,
    ):
        print()

        print(
            f"COLLAPSE {number}: "
            f"{len(members)} -> 1"
        )

        for member_index, member in enumerate(
            members,
            start=1,
        ):
            print()

            print(
                f"  SOURCE {member_index}"
            )

            rendered = (
                render_program(
                    member
                )
            )

            print(
                rendered
                if rendered
                else "<EMPTY>"
            )

        print()

        print(
            "  TARGET"
        )

        rendered = (
            render_program(
                target
            )
        )

        print(
            rendered
            if rendered
            else "<EMPTY>"
        )

    print()

    print(
        "=" * 72
    )

    print(
        "REMAINING SEMANTIC RESIDUALS"
    )

    tag_summary = Counter()

    for number, members in enumerate(
        residuals,
        start=1,
    ):
        print()

        print(
            "-" * 72
        )

        print(
            f"CLASS {number}: "
            f"{len(members)} forms"
        )

        class_tags = set()

        for form_number, program in enumerate(
            members,
            start=1,
        ):
            tags = (
                program_tags(
                    program
                )
            )

            class_tags.update(
                tags
            )

            print()

            print(
                f"FORM {form_number}"
            )

            print(
                render_program(
                    program
                )
            )

            print(
                "  TAGS: "
                + (
                    ", ".join(tags)
                    if tags
                    else "NONE"
                )
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

        for tag in class_tags:
            tag_summary[
                tag
            ] += 1

    print()

    print(
        "=" * 72
    )

    print(
        "RESIDUAL FEATURE SUMMARY"
    )

    for tag, count in (
        tag_summary.most_common()
    ):
        print(
            f"  {tag}: "
            f"{count} classes"
        )


if __name__ == "__main__":
    main()
