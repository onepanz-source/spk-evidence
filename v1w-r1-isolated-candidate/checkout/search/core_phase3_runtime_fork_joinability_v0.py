from __future__ import annotations

from collections import Counter
from itertools import combinations
from itertools import product

from spk_core.isa import CoreProgram
from spk_core.rules import RuleLayer
from spk_core.semantic_canonicalize import (
    canonicalize_core_program_semantic_runtime,
)

from search.core_phase3_cycle_exact_provenance_v0 import (
    invoke_helper,
    runtime_helper_specs,
)
from search.core_rule_soundness_v0 import (
    CONFIG,
    PROGRAM_POOL,
)


MAX_DEPTH = 5


def programs():
    for depth in range(
        1,
        MAX_DEPTH + 1,
    ):
        for instructions in product(
            PROGRAM_POOL,
            repeat=depth,
        ):
            yield CoreProgram(
                tuple(instructions)
            )


def normalize(
    program: CoreProgram,
) -> CoreProgram:
    return (
        canonicalize_core_program_semantic_runtime(
            program,
            config=CONFIG,
        )
    )


def helper_label(
    spec,
) -> str:
    return (
        ",".join(
            spec.rule_ids
        )
        + ":"
        + spec.helper
    )


def one_step_targets(
    program: CoreProgram,
):
    #
    # Several helpers may produce the same candidate.  Keep that fact:
    # it is useful provenance, but it is not an ambiguity.
    #
    targets = {}

    for layer in (
        RuleLayer.CORE,
        RuleLayer.SEMANTIC,
    ):
        for spec in runtime_helper_specs(
            layer
        ):
            candidate = invoke_helper(
                spec,
                program,
            )

            if candidate == program:
                continue

            targets.setdefault(
                candidate,
                [],
            ).append(
                helper_label(
                    spec
                )
            )

    return {
        target: tuple(
            sorted(labels)
        )
        for target, labels in targets.items()
    }


def main():
    total = 0

    rewrite_sources = 0
    fork_sources = 0

    applicable_helper_edges = 0
    distinct_target_edges = 0
    fork_pairs = 0

    max_distinct_targets = 0

    target_nf_mismatches = 0
    fork_nf_mismatches = 0

    same_target_multi_helper = 0

    fork_arity = Counter()
    helper_pair_forks = Counter()

    first_target_mismatch = None
    first_fork_mismatch = None

    examples = []

    for program in programs():
        total += 1

        source_nf = normalize(
            program
        )

        targets = one_step_targets(
            program
        )

        if not targets:
            continue

        rewrite_sources += 1

        applicable_helper_edges += sum(
            len(labels)
            for labels in targets.values()
        )

        distinct_target_edges += len(
            targets
        )

        for labels in targets.values():
            if len(labels) > 1:
                same_target_multi_helper += 1

        target_nfs = {}

        for target, labels in targets.items():
            target_nf = normalize(
                target
            )

            target_nfs[
                target
            ] = target_nf

            if target_nf != source_nf:
                target_nf_mismatches += 1

                if first_target_mismatch is None:
                    first_target_mismatch = (
                        program,
                        labels,
                        target,
                        source_nf,
                        target_nf,
                    )

        if len(targets) < 2:
            continue

        fork_sources += 1

        fork_arity[
            len(targets)
        ] += 1

        max_distinct_targets = max(
            max_distinct_targets,
            len(targets),
        )

        target_items = tuple(
            targets.items()
        )

        if len(examples) < 10:
            examples.append(
                (
                    program,
                    source_nf,
                    target_items,
                )
            )

        for (
            target_a,
            labels_a,
        ), (
            target_b,
            labels_b,
        ) in combinations(
            target_items,
            2,
        ):
            fork_pairs += 1

            for label_a in labels_a:
                for label_b in labels_b:
                    helper_pair_forks[
                        tuple(
                            sorted(
                                (
                                    label_a,
                                    label_b,
                                )
                            )
                        )
                    ] += 1

            nf_a = target_nfs[
                target_a
            ]

            nf_b = target_nfs[
                target_b
            ]

            if nf_a != nf_b:
                fork_nf_mismatches += 1

                if first_fork_mismatch is None:
                    first_fork_mismatch = (
                        program,
                        labels_a,
                        target_a,
                        nf_a,
                        labels_b,
                        target_b,
                        nf_b,
                        source_nf,
                    )

    print(
        "SPK PHASE 3C RUNTIME "
        "HELPER-FORK JOINABILITY v0"
    )
    print()

    print(
        "max depth:",
        MAX_DEPTH,
    )
    print(
        "syntactic programs:",
        total,
    )

    print()

    print(
        "sources with >=1 runtime rewrite:",
        rewrite_sources,
    )
    print(
        "applicable helper edges:",
        applicable_helper_edges,
    )
    print(
        "distinct one-step target edges:",
        distinct_target_edges,
    )
    print(
        "same-target multi-helper cases:",
        same_target_multi_helper,
    )

    print()

    print(
        "fork sources:",
        fork_sources,
    )
    print(
        "fork target pairs:",
        fork_pairs,
    )
    print(
        "max distinct targets from one source:",
        max_distinct_targets,
    )
    print(
        "fork arity distribution:",
        dict(
            sorted(
                fork_arity.items()
            )
        ),
    )

    print()

    print(
        "target/source-NF mismatches:",
        target_nf_mismatches,
    )
    print(
        "fork joinability mismatches:",
        fork_nf_mismatches,
    )

    print()
    print(
        "MOST FREQUENT HELPER-PAIR FORKS:"
    )

    for (
        left,
        right,
    ), count in helper_pair_forks.most_common(
        20
    ):
        print(
            f"  {count:6}  "
            f"{left}"
        )
        print(
            f"          {right}"
        )

    if examples:
        print()
        print(
            "FIRST FORK EXAMPLES:"
        )

        for index, (
            source,
            source_nf,
            target_items,
        ) in enumerate(
            examples,
            start=1,
        ):
            print()
            print(
                f"[{index}] source:"
            )
            print(
                "   ",
                source,
            )

            for target_index, (
                target,
                labels,
            ) in enumerate(
                target_items,
                start=1,
            ):
                print(
                    f"    target "
                    f"{target_index}:"
                )
                print(
                    "      rules:",
                    labels,
                )
                print(
                    "      program:",
                    target,
                )
                print(
                    "      NF:",
                    normalize(
                        target
                    ),
                )

            print(
                "    source NF:",
                source_nf,
            )

    if first_target_mismatch is not None:
        print()
        print(
            "FIRST TARGET/SOURCE-NF MISMATCH:"
        )
        print(
            first_target_mismatch
        )

    if first_fork_mismatch is not None:
        print()
        print(
            "FIRST NON-JOINABLE FORK:"
        )
        print(
            first_fork_mismatch
        )

    if total != 19607:
        raise AssertionError(
            f"unexpected corpus size: "
            f"{total}"
        )

    if target_nf_mismatches:
        raise SystemExit(
            "PHASE 3C FAIL: a runtime rewrite "
            "reaches a different official NF"
        )

    if fork_nf_mismatches:
        raise SystemExit(
            "PHASE 3C FAIL: non-joinable "
            "runtime helper fork"
        )

    print()
    print(
        "finite claim:"
    )
    print(
        "  every distinct runtime helper target "
        "observed on the depth<=5 corpus"
    )
    print(
        "  normalizes to the same official runtime "
        "NF as its source"
    )

    print()
    print(
        "PHASE 3C RUNTIME HELPER-FORK "
        "JOINABILITY CHECKPOINT: PASS"
    )


if __name__ == "__main__":
    main()
