from __future__ import annotations

from collections import Counter
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


def main():
    total = 0
    normal_forms = set()

    for program in programs():
        total += 1

        normal_forms.add(
            normalize(
                program
            )
        )

    residual_edges = 0
    residual_normal_forms = set()
    residual_targets = set()

    helper_hits = Counter()

    first_residual = None

    for normal_form in normal_forms:
        #
        # First retain the already-established orchestrator property.
        #
        if normalize(
            normal_form
        ) != normal_form:
            raise SystemExit(
                "PHASE 3D FAIL: official runtime "
                "normal form is not idempotent"
            )

        for layer in (
            RuleLayer.CORE,
            RuleLayer.SEMANTIC,
        ):
            for spec in runtime_helper_specs(
                layer
            ):
                candidate = invoke_helper(
                    spec,
                    normal_form,
                )

                if candidate == normal_form:
                    continue

                residual_edges += 1

                residual_normal_forms.add(
                    normal_form
                )

                residual_targets.add(
                    candidate
                )

                label = helper_label(
                    spec
                )

                helper_hits[
                    label
                ] += 1

                if first_residual is None:
                    first_residual = (
                        normal_form,
                        label,
                        candidate,
                        normalize(
                            candidate
                        ),
                    )

    print(
        "SPK PHASE 3D RUNTIME "
        "IRREDUCIBLE-NF GATE v0"
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
    print(
        "distinct official runtime NFs:",
        len(normal_forms),
    )

    print()

    print(
        "residual helper edges:",
        residual_edges,
    )
    print(
        "reducible official NFs:",
        len(
            residual_normal_forms
        ),
    )
    print(
        "distinct residual targets:",
        len(
            residual_targets
        ),
    )

    if helper_hits:
        print()
        print(
            "RESIDUAL HELPER HITS:"
        )

        for label, count in (
            helper_hits.most_common()
        ):
            print(
                f"  {count:6}  {label}"
            )

    if first_residual is not None:
        print()
        print(
            "FIRST RESIDUAL REDUCTION:"
        )

        (
            normal_form,
            label,
            candidate,
            candidate_nf,
        ) = first_residual

        print(
            "  NF:",
            normal_form,
        )
        print(
            "  helper:",
            label,
        )
        print(
            "  candidate:",
            candidate,
        )
        print(
            "  candidate official NF:",
            candidate_nf,
        )

    if total != 19607:
        raise AssertionError(
            f"unexpected corpus size: "
            f"{total}"
        )

    if len(normal_forms) != 2499:
        raise SystemExit(
            "PHASE 3D FAIL: runtime NF "
            f"baseline changed: "
            f"{len(normal_forms)} != 2499"
        )

    if residual_edges:
        raise SystemExit(
            "PHASE 3D FAIL: official runtime "
            "normal forms remain reducible"
        )

    print()
    print(
        "finite claim:"
    )
    print(
        "  every official runtime NF reached "
        "from the depth<=5 corpus"
    )
    print(
        "  is a fixed point of every individual "
        "RUNTIME helper"
    )

    print()
    print(
        "PHASE 3D RUNTIME IRREDUCIBLE-NF "
        "CHECKPOINT: PASS"
    )


if __name__ == "__main__":
    main()
