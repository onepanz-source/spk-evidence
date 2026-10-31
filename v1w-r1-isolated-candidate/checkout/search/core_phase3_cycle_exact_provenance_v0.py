from __future__ import annotations

import inspect
from collections import Counter
from itertools import product

import spk_core.canonicalize as structural_module
import spk_core.semantic_canonicalize as semantic_module

from spk_core.canonicalize import (
    canonicalize_core_program,
)
from spk_core.isa import CoreProgram
from spk_core.rules import (
    CanonicalizationProfile,
    RuleLayer,
    RuleValidity,
    canonicalization_profile,
    rule_specs,
)
from spk_core.semantic_canonicalize import (
    abstract_normalize_program,
)

from search.core_rule_soundness_v0 import (
    CONFIG,
    PROGRAM_POOL,
)


MAX_DEPTH = 5
MAX_PASS_STEPS = 64


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


def structural(
    program: CoreProgram,
) -> CoreProgram:
    with canonicalization_profile(
        CanonicalizationProfile.RUNTIME
    ):
        return canonicalize_core_program(
            program,
            config=CONFIG,
        )


def semantic(
    program: CoreProgram,
) -> CoreProgram:
    with canonicalization_profile(
        CanonicalizationProfile.RUNTIME
    ):
        return abstract_normalize_program(
            CONFIG,
            program,
        )


def transition(
    state,
):
    program, phase = state

    if phase == "S":
        return (
            structural(program),
            "A",
        )

    if phase == "A":
        return (
            semantic(program),
            "S",
        )

    raise AssertionError(
        f"unknown phase: {phase!r}"
    )


def exact_cycle(
    start: CoreProgram,
):
    state = (
        start,
        "S",
    )

    seen = {
        state: 0
    }

    history = [
        state
    ]

    consecutive_noops = 0

    for _ in range(
        MAX_PASS_STEPS
    ):
        next_state = transition(
            state
        )

        if (
            next_state[0]
            == state[0]
        ):
            consecutive_noops += 1
        else:
            consecutive_noops = 0

        if consecutive_noops >= 2:
            return None

        previous = seen.get(
            next_state
        )

        if previous is not None:
            return tuple(
                history[
                    previous:
                ]
            )

        seen[
            next_state
        ] = len(
            history
        )

        history.append(
            next_state
        )

        state = next_state

    raise RuntimeError(
        "pass-step limit reached"
    )


def canonical_cycle_key(
    cycle,
):
    #
    # Cycles are currently length 2, but make rotation
    # canonical without assuming that fact.
    #
    rotations = tuple(
        cycle[index:]
        + cycle[:index]
        for index in range(
            len(cycle)
        )
    )

    return min(
        rotations,
        key=repr,
    )


def runtime_helper_specs(
    layer: RuleLayer,
):
    result = []
    seen = set()

    for spec in rule_specs(
        validity=RuleValidity.RUNTIME,
        layer=layer,
    ):
        if spec.helper in seen:
            continue

        seen.add(
            spec.helper
        )

        result.append(
            spec
        )

    return tuple(
        result
    )


def invoke_helper(
    spec,
    program: CoreProgram,
) -> CoreProgram:
    if spec.layer is RuleLayer.CORE:
        module = structural_module
    else:
        module = semantic_module

    helper = getattr(
        module,
        spec.helper,
    )

    parameters = tuple(
        inspect.signature(
            helper
        ).parameters
    )

    with canonicalization_profile(
        CanonicalizationProfile.RUNTIME
    ):
        if spec.layer is RuleLayer.CORE:
            if parameters == (
                "instructions",
            ):
                result = helper(
                    program.instructions
                )

            elif parameters == (
                "instructions",
                "config",
            ):
                result = helper(
                    program.instructions,
                    CONFIG,
                )

            elif parameters == (
                "config",
                "instructions",
            ):
                result = helper(
                    CONFIG,
                    program.instructions,
                )

            else:
                raise AssertionError(
                    f"unsupported CORE helper "
                    f"signature {spec.helper}: "
                    f"{parameters}"
                )

            return CoreProgram(
                tuple(result)
            )

        if parameters == (
            "program",
        ):
            return helper(
                program
            )

        if parameters == (
            "config",
            "program",
        ):
            return helper(
                CONFIG,
                program,
            )

        if parameters == (
            "program",
            "config",
        ):
            return helper(
                program,
                CONFIG,
            )

        raise AssertionError(
            f"unsupported SEMANTIC helper "
            f"signature {spec.helper}: "
            f"{parameters}"
        )


def probe_leg(
    source: CoreProgram,
    target: CoreProgram,
    phase: str,
):
    layer = (
        RuleLayer.CORE
        if phase == "S"
        else RuleLayer.SEMANTIC
    )

    exact = []
    changed = []

    for spec in runtime_helper_specs(
        layer
    ):
        candidate = invoke_helper(
            spec,
            source,
        )

        if candidate != source:
            changed.append(
                (
                    spec.rule_ids,
                    spec.helper,
                    candidate,
                )
            )

        if candidate == target:
            exact.append(
                (
                    spec.rule_ids,
                    spec.helper,
                )
            )

    return (
        tuple(exact),
        tuple(changed),
    )


def main():
    total = 0
    cycle_inputs = 0

    cycle_lengths = Counter()
    unique_cycles = {}

    for program in programs():
        total += 1

        cycle = exact_cycle(
            program
        )

        if cycle is None:
            continue

        cycle_inputs += 1

        cycle_lengths[
            len(cycle)
        ] += 1

        key = canonical_cycle_key(
            cycle
        )

        unique_cycles.setdefault(
            key,
            program,
        )

    print(
        "SPK PHASE 3B EXACT CYCLE PROVENANCE v0"
    )
    print()

    print(
        "syntactic programs:",
        total,
    )
    print(
        "cycle-producing inputs:",
        cycle_inputs,
    )
    print(
        "cycle lengths:",
        dict(
            sorted(
                cycle_lengths.items()
            )
        ),
    )
    print(
        "unique phase-aware cycles:",
        len(unique_cycles),
    )

    print()

    exact_leg_count = 0
    unexplained_legs = 0

    helper_hits = Counter()

    for cycle_index, (
        cycle,
        first_source,
    ) in enumerate(
        unique_cycles.items(),
        start=1,
    ):
        print(
            "=" * 100
        )
        print(
            f"CYCLE {cycle_index}"
        )
        print(
            "first corpus source:",
            first_source,
        )

        for leg_index in range(
            len(cycle)
        ):
            state = cycle[
                leg_index
            ]

            next_state = cycle[
                (
                    leg_index + 1
                )
                % len(cycle)
            ]

            source, phase = state
            target, next_phase = next_state

            print()
            print(
                f"LEG {leg_index + 1}: "
                f"{phase} -> {next_phase}"
            )
            print(
                "source:",
                source,
            )
            print(
                "target:",
                target,
            )

            exact, changed = probe_leg(
                source,
                target,
                phase,
            )

            print(
                "exact single-helper matches:",
                len(exact),
            )

            for (
                rule_ids,
                helper,
            ) in exact:
                print(
                    "  EXACT",
                    ",".join(
                        rule_ids
                    ),
                    helper,
                )

                helper_hits[
                    (
                        rule_ids,
                        helper,
                    )
                ] += 1

            if exact:
                exact_leg_count += 1
            else:
                unexplained_legs += 1

                print(
                    "  no single helper reproduces "
                    "the entire pass transition"
                )

                print(
                    "  helpers changing source:"
                )

                for (
                    rule_ids,
                    helper,
                    candidate,
                ) in changed:
                    print(
                        "   ",
                        ",".join(
                            rule_ids
                        ),
                        helper,
                    )
                    print(
                        "      ->",
                        candidate,
                    )

    print()
    print(
        "=" * 100
    )
    print(
        "SUMMARY"
    )
    print(
        "=" * 100
    )

    print(
        "exactly explained legs:",
        exact_leg_count,
    )
    print(
        "multi-step/unexplained legs:",
        unexplained_legs,
    )

    print()

    print(
        "exact helper hits:"
    )

    for (
        rule_ids,
        helper,
    ), count in sorted(
        helper_hits.items(),
        key=lambda item: (
            -item[1],
            item[0][1],
        ),
    ):
        print(
            f"  {','.join(rule_ids):20} "
            f"{helper:55} "
            f"{count}"
        )

    if total != 19607:
        raise AssertionError(
            f"unexpected corpus size: "
            f"{total}"
        )

    if cycle_inputs:
        raise SystemExit(
            "PHASE 3B EXACT PROVENANCE FAIL: "
            f"residual cycle-producing inputs: "
            f"{cycle_inputs}"
        )

    if cycle_lengths:
        raise SystemExit(
            "PHASE 3B EXACT PROVENANCE FAIL: "
            f"residual cycle lengths: "
            f"{dict(cycle_lengths)}"
        )

    if unique_cycles:
        raise SystemExit(
            "PHASE 3B EXACT PROVENANCE FAIL: "
            f"residual phase-aware cycles: "
            f"{len(unique_cycles)}"
        )

    print()
    print(
        "PHASE 3B EXACT CYCLE "
        "CHECKPOINT: PASS"
    )


if __name__ == "__main__":
    main()
