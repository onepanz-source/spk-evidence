from collections import Counter

from search.canonicalize import canonicalize
from search.corpus_decay_v1 import CORPUS_DECAY_V1
from search.enumerate import enumerate_programs
from search.equivalence import signature
from spk.operators import (
    Acc,
    Compare,
    Decay,
    Emit,
    Reset,
)


OPERATORS = (
    Acc(weight=0.0, channel=0),
    Acc(weight=1.0, channel=0),
    Acc(weight=2.0, channel=0),

    Decay(tau=1.0),
    Decay(tau=2.0),

    Compare(threshold=1.0),
    Compare(threshold=2.0),

    Emit(channel_out=0),
    Reset(value=0.0),
)


def main() -> None:
    programs = tuple(
        enumerate_programs(
            OPERATORS,
            min_length=0,
            max_length=4,
        )
    )

    canonical_map = {}
    violations = []

    for program in programs:
        canonical = canonicalize(program)

        canonical_map[program] = canonical

        original_signature = signature(
            program,
            CORPUS_DECAY_V1,
        )

        canonical_signature = signature(
            canonical,
            CORPUS_DECAY_V1,
        )

        if original_signature != canonical_signature:
            violations.append(
                (
                    program,
                    canonical,
                )
            )

    canonical_programs = set(
        canonical_map.values()
    )

    behavioral_signatures = {
        signature(
            program,
            CORPUS_DECAY_V1,
        )
        for program in canonical_programs
    }

    original_lengths = Counter(
        len(program)
        for program in programs
    )

    canonical_lengths = Counter(
        len(program)
        for program in canonical_programs
    )

    print(
        f"corpus samples: {len(CORPUS_DECAY_V1)}"
    )

    print(
        f"operators: {len(OPERATORS)}"
    )

    print(
        f"syntactic programs: {len(programs)}"
    )

    print(
        f"canonical forms: {len(canonical_programs)}"
    )

    print(
        "syntactic/canonical ratio: "
        f"{len(programs) / len(canonical_programs):.3f}"
    )

    print(
        "empirical classes after canonicalization: "
        f"{len(behavioral_signatures)}"
    )

    print(
        "canonical/behavior ratio: "
        f"{len(canonical_programs) / len(behavioral_signatures):.3f}"
    )

    print(
        "semantic preservation violations: "
        f"{len(violations)}"
    )

    print()
    print("Original program length distribution:")

    for length in sorted(original_lengths):
        print(
            f"  L={length}: "
            f"{original_lengths[length]}"
        )

    print()
    print("Canonical form length distribution:")

    for length in sorted(canonical_lengths):
        print(
            f"  L={length}: "
            f"{canonical_lengths[length]}"
        )

    if violations:
        print()
        print("FIRST VIOLATIONS:")

        for original, canonical in violations[:10]:
            print()
            print(
                "original: ",
                original,
            )
            print(
                "canonical:",
                canonical,
            )


if __name__ == "__main__":
    main()
