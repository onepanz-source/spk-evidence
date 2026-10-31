from __future__ import annotations

from collections import defaultdict
from itertools import chain, combinations, product

from search.core_synthesis_v1 import (
    CONFIG,
    INSTRUCTION_POOL,
    SAMPLES,
    program_signature,
    render_program,
)
from spk.event import SpikeTrain

from spk_core.canonicalize import (
    canonicalize_core_program,
)
from spk_core.isa import (
    CoreProgram,
)
from spk_core.runtime import (
    run_core_program,
)


MAX_LENGTH = 4

INITIAL_STATES = (
    0,
    1,
    2,
    3,
    4,
)


def train_from_batches(
    batches,
) -> SpikeTrain:
    pairs = []

    for timestamp, (
        ch0_count,
        ch1_count,
    ) in enumerate(
        batches
    ):
        pairs.extend(
            (
                timestamp,
                0,
            )
            for _ in range(
                ch0_count
            )
        )

        pairs.extend(
            (
                timestamp,
                1,
            )
            for _ in range(
                ch1_count
            )
        )

    return SpikeTrain.from_pairs(
        pairs
    )


NONEMPTY_BATCHES = tuple(
    batch
    for batch in product(
        range(4),
        repeat=2,
    )
    if batch != (
        0,
        0,
    )
)


CANDIDATE_TRAINS = tuple(
    dict.fromkeys(
        chain(
            (
                train_from_batches(
                    (batch,)
                )
                for batch
                in NONEMPTY_BATCHES
            ),
            (
                train_from_batches(
                    (
                        first,
                        second,
                    )
                )
                for first
                in NONEMPTY_BATCHES
                for second
                in NONEMPTY_BATCHES
            ),
        )
    )
)



CANDIDATE_SAMPLES = tuple(
    (
        train,
        initial_raw,
    )
    for train in CANDIDATE_TRAINS
    for initial_raw
    in INITIAL_STATES
)


def observation(
    program: CoreProgram,
    sample,
):
    train, initial_raw = sample

    result = run_core_program(
        CONFIG,
        program,
        train,
        initial_raw=initial_raw,
    )

    return (
        result.output.as_pairs(),
        result.final_raw,
        result.final_guard,
    )


def all_canonical_programs():
    programs = set()

    for length in range(
        1,
        MAX_LENGTH + 1,
    ):
        for instructions in product(
            INSTRUCTION_POOL,
            repeat=length,
        ):
            programs.add(
                canonicalize_core_program(
                    CoreProgram(
                        instructions
                    ),
                    config=CONFIG,
                )
            )

    return tuple(
        sorted(
            programs,
            key=lambda program: (
                len(
                    program.instructions
                ),
                repr(
                    program.instructions
                ),
            ),
        )
    )


def signature_on_samples(
    program,
    samples,
):
    return tuple(
        observation(
            program,
            sample,
        )
        for sample in samples
    )


def partition(
    programs,
    samples,
):
    classes = defaultdict(
        list
    )

    for program in programs:
        classes[
            signature_on_samples(
                program,
                samples,
            )
        ].append(
            program
        )

    return classes


def ambiguity_metrics(
    classes,
):
    ambiguous = [
        members
        for members in classes.values()
        if len(members) > 1
    ]

    excess = sum(
        len(members) - 1
        for members in ambiguous
    )

    unresolved_pairs = sum(
        len(members)
        * (
            len(members) - 1
        )
        // 2
        for members in ambiguous
    )

    return (
        ambiguous,
        excess,
        unresolved_pairs,
    )


def separating_gain(
    ambiguous,
    sample,
):
    gain = 0

    for members in ambiguous:
        buckets = defaultdict(
            int
        )

        for program in members:
            buckets[
                observation(
                    program,
                    sample,
                )
            ] += 1

        total_pairs = (
            len(members)
            * (
                len(members) - 1
            )
            // 2
        )

        surviving_pairs = sum(
            size
            * (
                size - 1
            )
            // 2
            for size in buckets.values()
        )

        gain += (
            total_pairs
            - surviving_pairs
        )

    return gain


def main() -> None:
    programs = (
        all_canonical_programs()
    )

    #
    # Preserve the existing synthesis corpus first.
    #
    active_samples = list(
        SAMPLES
    )

    candidate_samples = [
        sample
        for sample in CANDIDATE_SAMPLES
        if sample
        not in active_samples
    ]

    print(
        "SPK/CORE CEGAR v1"
    )

    print(
        f"canonical programs: "
        f"{len(programs)}"
    )

    print(
        f"initial samples: "
        f"{len(active_samples)}"
    )

    print(
        f"candidate samples: "
        f"{len(candidate_samples)}"
    )

    print()

    counterexamples = []

    round_index = 0

    while True:
        classes = partition(
            programs,
            active_samples,
        )

        (
            ambiguous,
            excess,
            unresolved_pairs,
        ) = ambiguity_metrics(
            classes
        )

        print(
            f"ROUND {round_index}"
        )

        print(
            f"  behavioral classes: "
            f"{len(classes)}"
        )

        print(
            f"  ambiguous classes: "
            f"{len(ambiguous)}"
        )

        print(
            f"  residual excess: "
            f"{excess}"
        )

        print(
            f"  unresolved pairs: "
            f"{unresolved_pairs}"
        )

        if not ambiguous:
            break

        best_sample = None
        best_gain = 0

        for sample in (
            candidate_samples
        ):
            gain = separating_gain(
                ambiguous,
                sample,
            )

            if gain > best_gain:
                best_gain = gain
                best_sample = sample

        if (
            best_sample is None
            or best_gain == 0
        ):
            print()
            print(
                "NO FURTHER COUNTEREXAMPLE "
                "IN CANDIDATE DOMAIN"
            )
            break

        train, initial_raw = (
            best_sample
        )

        print(
            f"  selected gain: "
            f"{best_gain}"
        )

        print(
            f"  initial_raw: "
            f"{initial_raw}"
        )

        print(
            f"  train: "
            f"{train.as_pairs()}"
        )

        counterexamples.append(
            best_sample
        )

        active_samples.append(
            best_sample
        )

        candidate_samples.remove(
            best_sample
        )

        round_index += 1

        print()

    #
    # Final residual analysis.
    #
    final_classes = partition(
        programs,
        active_samples,
    )

    (
        final_ambiguous,
        final_excess,
        final_pairs,
    ) = ambiguity_metrics(
        final_classes
    )

    print()
    print(
        "=" * 72
    )

    print(
        "FINAL"
    )

    print(
        f"counterexamples added: "
        f"{len(counterexamples)}"
    )

    print(
        f"corpus size: "
        f"{len(active_samples)}"
    )

    print(
        f"behavioral classes: "
        f"{len(final_classes)}"
    )

    print(
        f"ambiguous classes: "
        f"{len(final_ambiguous)}"
    )

    print(
        f"residual excess: "
        f"{final_excess}"
    )

    print(
        f"unresolved pairs: "
        f"{final_pairs}"
    )

    if counterexamples:
        print()
        print(
            "COUNTEREXAMPLES"
        )

        for index, (
            train,
            initial_raw,
        ) in enumerate(
            counterexamples,
            start=1,
        ):
            print(
                f"  {index:02d}: "
                f"x0={initial_raw} "
                f"events="
                f"{train.as_pairs()}"
            )

    if final_ambiguous:
        print()
        print(
            "ROBUST RESIDUAL CLASSES"
        )

        final_ambiguous.sort(
            key=lambda members: (
                -len(members),
                repr(members),
            )
        )

        for index, members in enumerate(
            final_ambiguous[:20],
            start=1,
        ):
            print()

            print(
                f"CLASS {index}: "
                f"{len(members)} forms"
            )

            for program in members:
                rendered = (
                    render_program(
                        program
                    )
                )

                if rendered:
                    for line in (
                        rendered.splitlines()
                    ):
                        print(
                            "  ",
                            line,
                        )
                else:
                    print(
                        "   <EMPTY>"
                    )


if __name__ == "__main__":
    main()
