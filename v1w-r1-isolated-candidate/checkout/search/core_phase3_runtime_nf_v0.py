from __future__ import annotations

from contextlib import contextmanager
from itertools import product
import signal

from spk_core.isa import CoreProgram

from spk_core.semantic_canonicalize import (
    canonicalize_core_program_semantic,
    canonicalize_core_program_semantic_runtime,
)

from search.core_rule_soundness_v0 import (
    CONFIG,
    PROGRAM_POOL,
)


MAX_DEPTH = 5
PER_NORMALIZATION_TIMEOUT = 0.25


class NormalizationTimeout(RuntimeError):
    pass


def _timeout_handler(
    signum,
    frame,
):
    raise NormalizationTimeout(
        "normalization did not terminate "
        f"within {PER_NORMALIZATION_TIMEOUT}s"
    )


@contextmanager
def normalization_timeout():
    previous = signal.signal(
        signal.SIGALRM,
        _timeout_handler,
    )

    signal.setitimer(
        signal.ITIMER_REAL,
        PER_NORMALIZATION_TIMEOUT,
    )

    try:
        yield
    finally:
        signal.setitimer(
            signal.ITIMER_REAL,
            0,
        )

        signal.signal(
            signal.SIGALRM,
            previous,
        )


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


def normalize_runtime(
    program: CoreProgram,
) -> CoreProgram:
    with normalization_timeout():
        return (
            canonicalize_core_program_semantic_runtime(
                program,
                config=CONFIG,
            )
        )


def normalize_default(
    program: CoreProgram,
) -> CoreProgram:
    with normalization_timeout():
        return canonicalize_core_program_semantic(
            program,
            config=CONFIG,
        )


def main():
    total = 0
    changed = 0

    idempotence_failures = 0
    default_runtime_mismatches = 0
    termination_failures = 0

    first_idempotence = None
    first_default_runtime = None
    first_termination = None

    normal_forms = set()

    for program in programs():
        total += 1

        try:
            normalized = normalize_runtime(
                program
            )

            normalized_twice = (
                normalize_runtime(
                    normalized
                )
            )

            default_normalized = (
                normalize_default(
                    program
                )
            )

        except NormalizationTimeout as exc:
            termination_failures += 1

            if first_termination is None:
                first_termination = (
                    program,
                    str(exc),
                )

            continue

        if normalized != program:
            changed += 1

        normal_forms.add(
            normalized
        )

        if normalized_twice != normalized:
            idempotence_failures += 1

            if first_idempotence is None:
                first_idempotence = (
                    program,
                    normalized,
                    normalized_twice,
                )

        if default_normalized != normalized:
            default_runtime_mismatches += 1

            if first_default_runtime is None:
                first_default_runtime = (
                    program,
                    normalized,
                    default_normalized,
                )

    print(
        "SPK PHASE 3A RUNTIME NORMAL-FORM GATE v0"
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
        "changed programs:",
        changed,
    )
    print(
        "distinct runtime normal forms:",
        len(normal_forms),
    )

    print()

    print(
        "termination failures:",
        termination_failures,
    )
    print(
        "idempotence failures:",
        idempotence_failures,
    )
    print(
        "default/runtime mismatches:",
        default_runtime_mismatches,
    )

    if first_termination is not None:
        print()
        print(
            "FIRST TERMINATION FAILURE:"
        )
        print(
            first_termination
        )

    if first_idempotence is not None:
        print()
        print(
            "FIRST IDEMPOTENCE FAILURE:"
        )
        print(
            first_idempotence
        )

    if first_default_runtime is not None:
        print()
        print(
            "FIRST DEFAULT/RUNTIME MISMATCH:"
        )
        print(
            first_default_runtime
        )

    if termination_failures:
        raise SystemExit(
            "PHASE 3A FAIL: termination"
        )

    if idempotence_failures:
        raise SystemExit(
            "PHASE 3A FAIL: idempotence"
        )

    if default_runtime_mismatches:
        raise SystemExit(
            "PHASE 3A FAIL: default/runtime divergence"
        )

    if total != 19607:
        raise AssertionError(
            f"unexpected depth<=5 corpus size: "
            f"{total}"
        )

    print()
    print(
        "PHASE 3A RUNTIME NORMAL-FORM "
        "CHECKPOINT: PASS"
    )


if __name__ == "__main__":
    main()
