from __future__ import annotations

from dataclasses import dataclass

from spk_core.isa import (
    CoreAcc,
    CoreCmp,
    CoreConfig,
    CoreEmit,
    CoreProgram,
    CoreReset,
    ShiftDecay,
)
from spk_core.runtime import run_core_batch


CONFIG = CoreConfig(
    state_bits=8,
    fractional_bits=0,
)


RAWS = range(
    CONFIG.max_raw + 1
)


DELTAS = range(
    0,
    9,
)


BATCHES = (
    (0,),
    (0, 0),
    (1,),
    (2,),
    (0, 1),
    (2, 2),
)


@dataclass(
    frozen=True,
    slots=True,
)
class Observation:
    status: str
    output_channels: tuple[int, ...] = ()
    final_raw: int | None = None
    final_guard: bool | None = None


@dataclass(
    frozen=True,
    slots=True,
)
class Candidate:
    name: str
    instruction: object
    expected_commutes: bool
    guard_contexts: tuple[str, ...] = (
        "false",
        "true",
    )


CANDIDATES = (
    Candidate(
        "shift2",
        ShiftDecay(2),
        True,
    ),

    Candidate(
        "acc0_ch0",
        CoreAcc(0, 0),
        True,
    ),

    Candidate(
        "acc1_ch0",
        CoreAcc(1, 0),
        False,
    ),

    Candidate(
        "acc1_all",
        CoreAcc(1, None),
        False,
    ),

    Candidate(
        "cmp0",
        CoreCmp(0),
        True,
    ),

    Candidate(
        "cmp1",
        CoreCmp(1),
        False,
    ),

    Candidate(
        "cmp128",
        CoreCmp(128),
        False,
    ),

    Candidate(
        "emit7",
        CoreEmit(7),
        True,
    ),

    Candidate(
        "reset0",
        CoreReset(0),
        True,
    ),

    Candidate(
        "reset1",
        CoreReset(1),
        False,
    ),
)


def prefix_for_context(
    context: str,
):
    if context == "false":
        #
        # Guard begins false at every batch.
        #
        return ()

    if context == "true":
        #
        # CMP(0) forces guard true without modifying raw.
        #
        return (
            CoreCmp(0),
        )

    raise ValueError(
        f"unknown guard context: "
        f"{context}"
    )


def observe(
    program: CoreProgram,
    *,
    raw: int,
    delta: int,
    channels: tuple[int, ...],
) -> Observation:
    try:
        result = run_core_batch(
            CONFIG,
            program,
            timestamp=delta,
            channels=channels,
            initial_raw=raw,
            previous_timestamp=0,
        )

    except OverflowError:
        return Observation(
            status="overflow"
        )

    return Observation(
        status="ok",
        output_channels=tuple(
            channel
            for _, channel
            in result.output.as_pairs()
        ),
        final_raw=result.final_raw,
        final_guard=result.final_guard,
    )


def programs_for(
    instruction,
    context: str,
):
    prefix = prefix_for_context(
        context
    )

    left = CoreProgram(
        (
            *prefix,
            ShiftDecay(1),
            instruction,
        )
    )

    right = CoreProgram(
        (
            *prefix,
            instruction,
            ShiftDecay(1),
        )
    )

    return (
        left,
        right,
    )


def audit_candidate(
    candidate: Candidate,
):
    checks = 0
    mismatches = 0

    first_mismatch = None

    for context in candidate.guard_contexts:
        (
            left,
            right,
        ) = programs_for(
            candidate.instruction,
            context,
        )

        for raw in RAWS:
            for delta in DELTAS:
                for channels in BATCHES:
                    left_obs = observe(
                        left,
                        raw=raw,
                        delta=delta,
                        channels=channels,
                    )

                    right_obs = observe(
                        right,
                        raw=raw,
                        delta=delta,
                        channels=channels,
                    )

                    checks += 1

                    if left_obs == right_obs:
                        continue

                    mismatches += 1

                    if first_mismatch is None:
                        first_mismatch = (
                            context,
                            raw,
                            delta,
                            channels,
                            left_obs,
                            right_obs,
                        )

    return (
        checks,
        mismatches,
        first_mismatch,
    )


def fusion_audit():
    """
    Independently check:

        ShiftDecay(1);
        ShiftDecay(2)

    against:

        ShiftDecay(3)

    under the shared batch delta.
    """

    checks = 0

    for context in (
        "false",
        "true",
    ):
        prefix = prefix_for_context(
            context
        )

        split = CoreProgram(
            (
                *prefix,
                ShiftDecay(1),
                ShiftDecay(2),
            )
        )

        fused = CoreProgram(
            (
                *prefix,
                ShiftDecay(3),
            )
        )

        for raw in RAWS:
            for delta in DELTAS:
                for channels in BATCHES:
                    left = observe(
                        split,
                        raw=raw,
                        delta=delta,
                        channels=channels,
                    )

                    right = observe(
                        fused,
                        raw=raw,
                        delta=delta,
                        channels=channels,
                    )

                    checks += 1

                    if left != right:
                        return (
                            checks,
                            (
                                context,
                                raw,
                                delta,
                                channels,
                                left,
                                right,
                            ),
                        )

    return (
        checks,
        None,
    )


def main() -> None:
    print(
        "SPK CORE TEMPORAL COMMUTATION v0"
    )

    print(
        "reference temporal action: "
        "ShiftDecay(1)"
    )

    print(
        "observation includes:"
    )

    print(
        "    termination/overflow"
    )

    print(
        "    emitted channels"
    )

    print(
        "    final raw"
    )

    print(
        "    final guard"
    )

    print(
        "guard contexts:"
    )

    print(
        "    false = batch initial guard"
    )

    print(
        "    true  = forced by CMP(0)"
    )

    total_checks = 0
    classification_errors = 0

    print()
    print(
        "=" * 88
    )
    print(
        "COMMUTATION MATRIX"
    )
    print(
        "=" * 88
    )

    for candidate in CANDIDATES:
        (
            checks,
            mismatches,
            first_mismatch,
        ) = audit_candidate(
            candidate
        )

        total_checks += checks

        supported = (
            mismatches == 0
        )

        classification_ok = (
            supported
            == candidate.expected_commutes
        )

        if not classification_ok:
            classification_errors += 1

        print()
        print(
            candidate.name
        )

        print(
            f"    cases checked: "
            f"{checks}"
        )

        print(
            f"    mismatches: "
            f"{mismatches}"
        )

        print(
            f"    commutation supported: "
            f"{supported}"
        )

        print(
            f"    expected: "
            f"{candidate.expected_commutes}"
        )

        print(
            f"    classification correct: "
            f"{classification_ok}"
        )

        if first_mismatch is not None:
            (
                context,
                raw,
                delta,
                channels,
                left,
                right,
            ) = first_mismatch

            print(
                "    first counterexample:"
            )

            print(
                f"        guard_context="
                f"{context}"
            )

            print(
                f"        raw="
                f"{raw}"
            )

            print(
                f"        delta="
                f"{delta}"
            )

            print(
                f"        channels="
                f"{channels}"
            )

            print(
                f"        SHIFT;P="
                f"{left}"
            )

            print(
                f"        P;SHIFT="
                f"{right}"
            )

    print()
    print(
        "=" * 88
    )
    print(
        "SHIFT FUSION"
    )
    print(
        "=" * 88
    )

    (
        fusion_checks,
        fusion_failure,
    ) = fusion_audit()

    total_checks += fusion_checks

    print(
        f"cases checked: "
        f"{fusion_checks}"
    )

    if fusion_failure is not None:
        print(
            f"first failure: "
            f"{fusion_failure}"
        )

        classification_errors += 1

    else:
        print(
            "Shift1;Shift2 == Shift3: "
            "SUPPORTED"
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
        f"total concrete cases: "
        f"{total_checks}"
    )

    print(
        f"classification errors: "
        f"{classification_errors}"
    )

    if classification_errors:
        raise SystemExit(1)

    print()
    print(
        "TEMPORAL COMMUTATION "
        "MATRIX CHECKPOINT: PASS"
    )

    print()
    print(
        "Expected general candidates:"
    )

    print(
        "    Shift <-> Shift      YES"
    )

    print(
        "    Shift <-> ACC(0)     YES"
    )

    print(
        "    Shift <-> ACC(w>0)   NO"
    )

    print(
        "    Shift <-> CMP(0)     YES"
    )

    print(
        "    Shift <-> CMP(t>0)   NO"
    )

    print(
        "    Shift <-> EMIT       YES"
    )

    print(
        "    Shift <-> RESET(0)   YES"
    )

    print(
        "    Shift <-> RESET(v>0) NO"
    )

    print()
    print(
        "Finite evidence only where a "
        "general proof is not separately given."
    )


if __name__ == "__main__":
    main()
