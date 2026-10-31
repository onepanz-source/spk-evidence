from __future__ import annotations

from collections import defaultdict
from itertools import combinations, product

from search.core_synthesis_v1 import (
    CONFIG,
    INSTRUCTION_POOL,
    SAMPLES,
    render_program,
)

from spk.event import SpikeTrain

from spk_core.canonicalize import (
    canonicalize_core_program,
)
from spk_core.isa import (
    CoreProgram,
    ShiftDecay,
)
from spk_core.runtime import (
    run_core_program,
)


MAX_LENGTH = 5


TEMPORAL_POOL = (
    (
        ShiftDecay(
            bits_per_tick=1
        ),
    )
    + INSTRUCTION_POOL
)


CEGAR_BASE_EXTRA = (
    (
        SpikeTrain.from_pairs(
            (
                (0, 1),
                (0, 1),
            )
        ),
        2,
    ),
    (
        SpikeTrain.from_pairs(
            (
                (0, 1),
                (0, 1),
            )
        ),
        0,
    ),
)


INITIAL_SAMPLES = tuple(
    SAMPLES
) + CEGAR_BASE_EXTRA


#
# Include all raw-state boundaries relevant to <=4 SHIFT_DECAY(1)
# instructions.  In particular x0=8 and x0=16 expose distinctions
# hidden by the original 0..7 domain.
#
#
# Depth 5 reaches the next binary boundary at 2**5 = 32.
#
INITIAL_STATES = tuple(
    range(33)
)


TIMESTAMPS = tuple(
    range(5)
)


NONEMPTY_BATCHES = tuple(
    batch
    for batch in product(
        range(3),
        repeat=2,
    )
    if batch != (
        0,
        0,
    )
)


def make_train(
    timed_batches,
) -> SpikeTrain:
    pairs = []

    for timestamp, (
        ch0_count,
        ch1_count,
    ) in timed_batches:
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


def candidate_trains():
    result = {}

    #
    # One nonempty batch, including leading temporal gaps.
    #
    for timestamp in TIMESTAMPS:
        for batch in NONEMPTY_BATCHES:
            train = make_train(
                (
                    (
                        timestamp,
                        batch,
                    ),
                )
            )

            result[
                train.as_pairs()
            ] = train

    #
    # Two nonempty batches with arbitrary gap.
    #
    for left, right in combinations(
        TIMESTAMPS,
        2,
    ):
        for first in NONEMPTY_BATCHES:
            for second in NONEMPTY_BATCHES:
                train = make_train(
                    (
                        (
                            left,
                            first,
                        ),
                        (
                            right,
                            second,
                        ),
                    )
                )

                result[
                    train.as_pairs()
                ] = train

    return tuple(
        result.values()
    )


BASE_CANDIDATE_TRAINS = (
    candidate_trains()
)


def extra_probe_trains():
    """
    Strengthen observability with an unhandled channel (ch2).

    This exposes temporal evolution even when ACC(ch0/ch1) receives
    no event, and adds simple three-batch histories for persistent
    state/control interactions.
    """

    trains = {}

    timestamps = tuple(
        range(6)
    )

    #
    # One-event histories on the unhandled channel.
    #
    for timestamp in timestamps:
        train = SpikeTrain.from_pairs(
            (
                (
                    timestamp,
                    2,
                ),
            )
        )

        trains[
            train.as_pairs()
        ] = train

    #
    # Two batches, one event per batch, channels 0/1/2.
    #
    for left, right in combinations(
        timestamps,
        2,
    ):
        for first_channel in range(3):
            for second_channel in range(3):
                train = SpikeTrain.from_pairs(
                    (
                        (
                            left,
                            first_channel,
                        ),
                        (
                            right,
                            second_channel,
                        ),
                    )
                )

                trains[
                    train.as_pairs()
                ] = train

    #
    # Three batches, one event per batch.
    #
    for first, second, third in combinations(
        timestamps,
        3,
    ):
        for first_channel in range(3):
            for second_channel in range(3):
                for third_channel in range(3):
                    train = SpikeTrain.from_pairs(
                        (
                            (
                                first,
                                first_channel,
                            ),
                            (
                                second,
                                second_channel,
                            ),
                            (
                                third,
                                third_channel,
                            ),
                        )
                    )

                    trains[
                        train.as_pairs()
                    ] = train

    return tuple(
        trains.values()
    )


EXTRA_PROBE_TRAINS = (
    extra_probe_trains()
)


_all_candidate_trains = {}

for train in (
    BASE_CANDIDATE_TRAINS
    + EXTRA_PROBE_TRAINS
):
    _all_candidate_trains[
        train.as_pairs()
    ] = train


CANDIDATE_TRAINS = tuple(
    _all_candidate_trains.values()
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
    program,
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
    result = set()

    syntactic = 0

    for length in range(
        1,
        MAX_LENGTH + 1,
    ):
        for instructions in product(
            TEMPORAL_POOL,
            repeat=length,
        ):
            syntactic += 1

            result.add(
                canonicalize_core_program(
                    CoreProgram(
                        instructions
                    ),
                    config=CONFIG,
                )
            )

    return (
        syntactic,
        tuple(
            sorted(
                result,
                key=lambda program: (
                    len(
                        program.instructions
                    ),
                    repr(
                        program.instructions
                    ),
                ),
            )
        ),
    )


def partition(
    programs,
    samples,
):
    classes = defaultdict(
        list
    )

    for program in programs:
        signature = tuple(
            observation(
                program,
                sample,
            )
            for sample in samples
        )

        classes[
            signature
        ].append(
            program
        )

    return classes


def ambiguity(
    classes,
):
    ambiguous = [
        members
        for members
        in classes.values()
        if len(members) > 1
    ]

    excess = sum(
        len(members) - 1
        for members
        in ambiguous
    )

    pairs = sum(
        len(members)
        * (
            len(members) - 1
        )
        // 2
        for members
        in ambiguous
    )

    return (
        ambiguous,
        excess,
        pairs,
    )


def gain_for_sample(
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

        old_pairs = (
            len(members)
            * (
                len(members) - 1
            )
            // 2
        )

        new_pairs = sum(
            size
            * (
                size - 1
            )
            // 2
            for size
            in buckets.values()
        )

        gain += (
            old_pairs
            - new_pairs
        )

    return gain


def main() -> None:
    (
        syntactic,
        programs,
    ) = all_canonical_programs()

    active = list(
        INITIAL_SAMPLES
    )

    candidates = [
        sample
        for sample in CANDIDATE_SAMPLES
        if sample not in active
    ]

    print(
        "SPK/CORE TEMPORAL DEPTH-5 CEGAR v2"
    )

    print()

    print(
        f"instruction pool: "
        f"{len(TEMPORAL_POOL)}"
    )

    print(
        f"syntactic programs: "
        f"{syntactic}"
    )

    print(
        f"canonical programs: "
        f"{len(programs)}"
    )

    print(
        f"initial samples: "
        f"{len(active)}"
    )

    print(
        f"candidate trains: "
        f"{len(CANDIDATE_TRAINS)}"
    )

    print(
        f"candidate samples: "
        f"{len(candidates)}"
    )

    print()

    counterexamples = []

    round_index = 0

    while True:
        classes = partition(
            programs,
            active,
        )

        (
            ambiguous,
            excess,
            unresolved,
        ) = ambiguity(
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
            f"{unresolved}"
        )

        if not ambiguous:
            break

        best_sample = None
        best_gain = 0

        for sample in candidates:
            gain = gain_for_sample(
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
                "IN TEMPORAL CANDIDATE DOMAIN"
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

        active.append(
            best_sample
        )

        candidates.remove(
            best_sample
        )

        counterexamples.append(
            best_sample
        )

        round_index += 1

        print()

    final_classes = partition(
        programs,
        active,
    )

    (
        final_ambiguous,
        final_excess,
        final_pairs,
    ) = ambiguity(
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
        f"{len(active)}"
    )

    print(
        f"canonical programs: "
        f"{len(programs)}"
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
            "TEMPORAL COUNTEREXAMPLES"
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
            "ROBUST TEMPORAL RESIDUALS"
        )

        final_ambiguous.sort(
            key=lambda members: (
                -len(members),
                repr(members),
            )
        )

        for number, members in enumerate(
            final_ambiguous[:20],
            start=1,
        ):
            print()

            print(
                f"CLASS {number}: "
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
