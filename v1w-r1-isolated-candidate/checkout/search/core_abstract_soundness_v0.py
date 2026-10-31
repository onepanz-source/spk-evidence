from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from spk_core.abstract import (
    GuardPartition,
    RawSet,
    analyze_program,
)
from spk_core.isa import (
    CoreAcc,
    CoreCmp,
    CoreConfig,
    CoreEmit,
    CoreProgram,
    CoreReset,
    ShiftDecay,
)


CONFIG = CoreConfig(
    state_bits=8,
    fractional_bits=0,
)

CHANNELS = (
    0,
    1,
    2,
)


@dataclass(frozen=True)
class ConcreteState:
    raw: int
    guard: bool


@dataclass(frozen=True)
class Domain:
    initial_raws: tuple[int, ...]
    counts: tuple[int, ...]
    deltas: tuple[int, ...]


@dataclass
class Stats:
    executions: int = 0
    instruction_checks: int = 0
    overflow_skips: int = 0

    def add(
        self,
        other: "Stats",
    ) -> None:
        self.executions += (
            other.executions
        )
        self.instruction_checks += (
            other.instruction_checks
        )
        self.overflow_skips += (
            other.overflow_skips
        )


def raw_contains(
    abstract_raw: RawSet | None,
    raw: int,
) -> bool:
    if abstract_raw is None:
        return False

    if not (
        abstract_raw.lower
        <= raw
        <= abstract_raw.upper
    ):
        return False

    if abstract_raw.modulus <= 0:
        raise AssertionError(
            "invalid abstract modulus: "
            f"{abstract_raw.modulus}"
        )

    return (
        raw - abstract_raw.residue
    ) % abstract_raw.modulus == 0


def partition_contains(
    partition: GuardPartition,
    state: ConcreteState,
) -> bool:
    branch = (
        partition.true
        if state.guard
        else partition.false
    )

    return raw_contains(
        branch,
        state.raw,
    )


def concrete_step(
    state: ConcreteState,
    instruction,
    *,
    delta: int,
    counts: dict[int, int],
) -> ConcreteState:
    raw = state.raw
    guard = state.guard

    if isinstance(
        instruction,
        ShiftDecay,
    ):
        raw >>= (
            instruction.bits_per_tick
            * delta
        )

    elif isinstance(
        instruction,
        CoreAcc,
    ):
        if instruction.channel is None:
            count = sum(
                counts.values()
            )
        else:
            count = counts.get(
                instruction.channel,
                0,
            )

        raw += (
            count
            * instruction.weight
            * CONFIG.scale
        )

        if not (
            0 <= raw <= CONFIG.max_raw
        ):
            raise OverflowError

    elif isinstance(
        instruction,
        CoreCmp,
    ):
        guard = (
            raw
            >= instruction.threshold_raw
        )

    elif isinstance(
        instruction,
        CoreEmit,
    ):
        pass

    elif isinstance(
        instruction,
        CoreReset,
    ):
        if guard:
            raw = (
                instruction.value_raw
            )

            if not (
                0 <= raw
                <= CONFIG.max_raw
            ):
                raise OverflowError

    else:
        raise TypeError(
            f"unknown instruction: "
            f"{instruction!r}"
        )

    return ConcreteState(
        raw=raw,
        guard=guard,
    )


def configurations(
    domain: Domain,
):
    for (
        initial_raw,
        n0,
        n1,
        n2,
        delta,
    ) in product(
        domain.initial_raws,
        domain.counts,
        domain.counts,
        domain.counts,
        domain.deltas,
    ):
        yield (
            initial_raw,
            {
                0: n0,
                1: n1,
                2: n2,
            },
            delta,
        )


def check_program(
    program: CoreProgram,
    domain: Domain,
) -> Stats:
    analysis = analyze_program(
        CONFIG,
        program,
    )

    if len(analysis) != len(
        program.instructions
    ):
        raise AssertionError(
            "analysis length mismatch: "
            f"{len(analysis)} != "
            f"{len(program.instructions)}"
        )

    stats = Stats()

    for (
        initial_raw,
        counts,
        delta,
    ) in configurations(
        domain
    ):
        stats.executions += 1

        state = ConcreteState(
            raw=initial_raw,
            guard=False,
        )

        if analysis:
            if not partition_contains(
                analysis[0].before,
                state,
            ):
                raise AssertionError(
                    "\n".join(
                        (
                            "ABSTRACT INITIAL SOUNDNESS FAILURE",
                            f"program={program}",
                            f"initial_raw={initial_raw}",
                            f"counts={counts}",
                            f"delta={delta}",
                            f"abstract={analysis[0].before}",
                        )
                    )
                )

        for step in analysis:
            if not partition_contains(
                step.before,
                state,
            ):
                raise AssertionError(
                    "\n".join(
                        (
                            "ABSTRACT BEFORE SOUNDNESS FAILURE",
                            f"program={program}",
                            f"index={step.index}",
                            f"instruction={step.instruction}",
                            f"state={state}",
                            f"counts={counts}",
                            f"delta={delta}",
                            f"abstract={step.before}",
                        )
                    )
                )

            try:
                state = concrete_step(
                    state,
                    step.instruction,
                    delta=delta,
                    counts=counts,
                )
            except OverflowError:
                stats.overflow_skips += 1
                break

            if not partition_contains(
                step.after,
                state,
            ):
                raise AssertionError(
                    "\n".join(
                        (
                            "ABSTRACT AFTER SOUNDNESS FAILURE",
                            f"program={program}",
                            f"index={step.index}",
                            f"instruction={step.instruction}",
                            f"state={state}",
                            f"counts={counts}",
                            f"delta={delta}",
                            f"abstract={step.after}",
                        )
                    )
                )

            stats.instruction_checks += 1

    return stats


WIDE_DOMAIN = Domain(
    initial_raws=tuple(
        range(65)
    ),
    counts=tuple(
        range(4)
    ),
    deltas=tuple(
        range(7)
    ),
)


WIDE_PROGRAMS = (
    CoreProgram(
        (
            CoreAcc(1, 0),
        )
    ),
    CoreProgram(
        (
            ShiftDecay(1),
        )
    ),
    CoreProgram(
        (
            CoreCmp(1),
        )
    ),
    CoreProgram(
        (
            CoreCmp(2),
            CoreReset(0),
        )
    ),
    CoreProgram(
        (
            CoreAcc(2, 0),
            CoreCmp(2),
            CoreReset(0),
        )
    ),
    CoreProgram(
        (
            CoreAcc(1, 0),
            ShiftDecay(1),
            CoreAcc(1, 0),
            CoreCmp(1),
            CoreReset(0),
        )
    ),
    CoreProgram(
        (
            CoreAcc(1, 0),
            CoreAcc(2, 1),
            CoreCmp(2),
            CoreEmit(7),
            CoreReset(0),
        )
    ),
)


SYSTEMATIC_POOL = (
    ShiftDecay(1),
    ShiftDecay(2),
    CoreAcc(1, 0),
    CoreAcc(2, 0),
    CoreAcc(1, 1),
    CoreAcc(1, None),
    CoreCmp(1),
    CoreCmp(2),
    CoreEmit(7),
    CoreReset(0),
    CoreReset(1),
)


SYSTEMATIC_DOMAIN = Domain(
    initial_raws=tuple(
        range(33)
    ),
    counts=tuple(
        range(3)
    ),
    deltas=tuple(
        range(5)
    ),
)


BOUNDARY_DOMAIN = Domain(
    initial_raws=tuple(
        range(
            CONFIG.max_raw - 15,
            CONFIG.max_raw + 1,
        )
    ),
    counts=(
        0,
        1,
    ),
    deltas=(
        0,
        1,
        2,
    ),
)


def generated_programs(
    max_depth: int,
):
    for depth in range(
        1,
        max_depth + 1,
    ):
        for instructions in product(
            SYSTEMATIC_POOL,
            repeat=depth,
        ):
            yield CoreProgram(
                tuple(instructions)
            )


def run_tier(
    name: str,
    programs,
    domain: Domain,
    *,
    progress_every: int = 0,
) -> tuple[int, Stats]:
    print()
    print(
        "=" * 88
    )
    print(name)
    print(
        "=" * 88
    )

    total = Stats()
    program_count = 0

    for program_count, program in enumerate(
        programs,
        start=1,
    ):
        stats = check_program(
            program,
            domain,
        )

        total.add(
            stats
        )

        if (
            progress_every
            and program_count
            % progress_every == 0
        ):
            print(
                f"programs={program_count} "
                f"executions={total.executions} "
                f"checks={total.instruction_checks} "
                f"overflow_skips={total.overflow_skips}"
            )

    print(
        f"programs checked: "
        f"{program_count}"
    )
    print(
        f"concrete executions: "
        f"{total.executions}"
    )
    print(
        f"instruction states checked: "
        f"{total.instruction_checks}"
    )
    print(
        f"overflowing executions skipped: "
        f"{total.overflow_skips}"
    )

    return (
        program_count,
        total,
    )


def main() -> None:
    print(
        "SPK/CORE ABSTRACT SOUNDNESS v0"
    )
    print(
        f"config: "
        f"state_bits={CONFIG.state_bits} "
        f"fractional_bits={CONFIG.fractional_bits} "
        f"max_raw={CONFIG.max_raw}"
    )

    grand = Stats()
    grand_programs = 0

    count, stats = run_tier(
        "TIER 1 — WIDE MANUAL PROBES",
        WIDE_PROGRAMS,
        WIDE_DOMAIN,
    )

    grand_programs += count
    grand.add(stats)

    count, stats = run_tier(
        "TIER 2 — SYSTEMATIC PROGRAMS DEPTH <= 3",
        generated_programs(3),
        SYSTEMATIC_DOMAIN,
        progress_every=200,
    )

    grand_programs += count
    grand.add(stats)

    #
    # Boundary values deserve their own pass because interval and
    # congruence abstractions often fail at domain edges.
    #
    count, stats = run_tier(
        "TIER 3 — MAX_RAW BOUNDARY DEPTH <= 2",
        generated_programs(2),
        BOUNDARY_DOMAIN,
    )

    grand_programs += count
    grand.add(stats)

    print()
    print(
        "=" * 88
    )
    print(
        "FINAL CHECKPOINT"
    )
    print(
        "=" * 88
    )

    print(
        f"program instances checked: "
        f"{grand_programs}"
    )
    print(
        f"concrete executions: "
        f"{grand.executions}"
    )
    print(
        f"concrete instruction states checked: "
        f"{grand.instruction_checks}"
    )
    print(
        f"overflowing executions skipped: "
        f"{grand.overflow_skips}"
    )
    print()
    print(
        "ABSTRACT SOUNDNESS CHECKPOINT: PASS"
    )


if __name__ == "__main__":
    main()
