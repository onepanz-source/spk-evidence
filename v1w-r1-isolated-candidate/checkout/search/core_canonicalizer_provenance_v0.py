from __future__ import annotations

from functools import wraps

import spk_core.canonicalize as canon

from search.core_temporal_normalize_v0 import (
    BATCHES,
    DELTAS,
    RAWS,
    observe,
    programs,
)


HELPERS = (
    "_remove_zero_acc",
    "_remove_false_guard_prefix",
    "_remove_dead_compares",
    "_move_emit_left",
    "_collapse_adjacent_resets",
    "_commute_zero_reset_across_shift",
    "_remove_shift_between_cmp1_and_reset0",
    "_remove_shift_when_state_known_zero",
    "_remove_pre_acc_shift_under_cmp1_reset0",
    "_sink_known_false_compare_across_shift",
    "_cap_shift_before_zero_reset_from_compare_bound",
    "_normalize_shift_decay_runs",
    "_normalize_acc_runs",
    "_sort_emit_runs",
    "_remove_redundant_repeated_compares",
    "_normalize_false_compare_after_reset",
    "_remove_shadowed_resets",
    "_pull_saturated_acc_across_compare",
    "_cap_saturated_acc_before_guarded_reset",
    "_strip_state_before_lsb_annihilator",
)


TRACE = []


def as_instruction_tuple(value):
    if isinstance(
        value,
        (list, tuple),
    ):
        return tuple(value)

    return None


def install_tracing():
    originals = {}

    for name in HELPERS:
        original = getattr(
            canon,
            name,
        )

        originals[
            name
        ] = original

        @wraps(original)
        def wrapper(
            *args,
            __name=name,
            __original=original,
            **kwargs,
        ):
            before = (
                as_instruction_tuple(
                    args[0]
                )
                if args
                else None
            )

            result = __original(
                *args,
                **kwargs,
            )

            after = (
                as_instruction_tuple(
                    result
                )
            )

            if (
                before is not None
                and after is not None
                and before != after
            ):
                TRACE.append(
                    (
                        __name,
                        before,
                        after,
                    )
                )

            return result

        setattr(
            canon,
            name,
            wrapper,
        )

    return originals


def restore_tracing(
    originals,
):
    for name, original in (
        originals.items()
    ):
        setattr(
            canon,
            name,
            original,
        )


def semantic_mismatch(
    source,
    target,
):
    first = None
    count = 0

    for raw in RAWS:
        for delta in DELTAS:
            for channels in BATCHES:
                left = observe(
                    source,
                    raw=raw,
                    delta=delta,
                    channels=channels,
                )

                right = observe(
                    target,
                    raw=raw,
                    delta=delta,
                    channels=channels,
                )

                if left == right:
                    continue

                count += 1

                if first is None:
                    first = (
                        raw,
                        delta,
                        channels,
                        left,
                        right,
                    )

    return (
        count,
        first,
    )


def find_affected_programs():
    affected = []

    for source in programs():
        target = (
            canon.canonicalize_core_program(
                source
            )
        )

        (
            mismatch_count,
            first,
        ) = semantic_mismatch(
            source,
            target,
        )

        if mismatch_count:
            affected.append(
                (
                    source,
                    target,
                    mismatch_count,
                    first,
                )
            )

    return affected


def trace_program(
    source,
):
    TRACE.clear()

    target = (
        canon.canonicalize_core_program(
            source
        )
    )

    return (
        target,
        tuple(TRACE),
    )


def main():
    print(
        "SPK CORE CANONICALIZER "
        "RULE PROVENANCE v0"
    )

    #
    # First find the exact finite set of programs whose Core
    # canonicalization changes observable runtime behavior.
    #
    affected = (
        find_affected_programs()
    )

    print()
    print(
        "=" * 88
    )
    print(
        "AFFECTED PROGRAMS"
    )
    print(
        "=" * 88
    )

    print(
        f"affected programs: "
        f"{len(affected)}"
    )

    print(
        f"total mismatches: "
        f"{sum(x[2] for x in affected)}"
    )

    #
    # Now instrument every helper used by the canonicalizer.
    #
    originals = install_tracing()

    try:
        helper_hits = {}

        for index, (
            source,
            expected_target,
            mismatch_count,
            first,
        ) in enumerate(
            affected,
            start=1,
        ):
            (
                traced_target,
                trace,
            ) = trace_program(
                source
            )

            if (
                traced_target.instructions
                != expected_target.instructions
            ):
                raise AssertionError(
                    "instrumentation changed "
                    "canonicalization"
                )

            print()
            print(
                "-" * 88
            )

            print(
                f"program {index}"
            )

            print(
                f"source:"
            )

            print(
                f"    "
                f"{source.instructions}"
            )

            print(
                f"target:"
            )

            print(
                f"    "
                f"{traced_target.instructions}"
            )

            print(
                f"semantic mismatches: "
                f"{mismatch_count}"
            )

            print(
                f"first witness:"
            )

            print(
                f"    {first}"
            )

            print(
                "rewrite trace:"
            )

            for step, (
                helper,
                before,
                after,
            ) in enumerate(
                trace,
                start=1,
            ):
                print(
                    f"    {step}. "
                    f"{helper}"
                )

                print(
                    f"       before="
                    f"{before}"
                )

                print(
                    f"       after ="
                    f"{after}"
                )

                helper_hits[
                    helper
                ] = (
                    helper_hits.get(
                        helper,
                        0,
                    )
                    + 1
                )

        print()
        print(
            "=" * 88
        )
        print(
            "HELPER ATTRIBUTION"
        )
        print(
            "=" * 88
        )

        for helper, count in sorted(
            helper_hits.items(),
            key=lambda item: (
                -item[1],
                item[0],
            ),
        ):
            print(
                f"{count:3d}  "
                f"{helper}"
            )

        print()
        print(
            "=" * 88
        )
        print(
            "CHECKPOINT"
        )
        print(
            "=" * 88
        )

        print(
            f"affected programs: "
            f"{len(affected)}"
        )

        print(
            f"helpers participating: "
            f"{len(helper_hits)}"
        )

        print()
        print(
            "RULE PROVENANCE CENSUS: PASS"
        )

    finally:
        restore_tracing(
            originals
        )


if __name__ == "__main__":
    main()
