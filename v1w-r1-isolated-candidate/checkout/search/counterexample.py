from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from search.equivalence import (
    Observation,
    Sample,
    observe,
    to_signature_observation,
)
from spk.program import Program


@dataclass(frozen=True, slots=True)
class Counterexample:
    """
    One sample that empirically distinguishes two programs.

    Raw observations are retained for diagnostics, but the decision
    whether they differ uses the same normalized numerical policy as
    empirical signatures.
    """

    sample: Sample
    left: Observation
    right: Observation


def find_counterexample(
    left: Program,
    right: Program,
    corpus: Iterable[Sample],
) -> Counterexample | None:
    """
    Return the first empirical counterexample in the supplied corpus.

    Floating-point state is compared through the normalized signature
    policy. Output events and guard remain exact.

    None means only that no counterexample was found in this finite
    search domain.
    """

    if not isinstance(left, Program):
        raise TypeError(
            "left must be a Program"
        )

    if not isinstance(right, Program):
        raise TypeError(
            "right must be a Program"
        )

    for sample in corpus:
        if not isinstance(sample, Sample):
            raise TypeError(
                "corpus must contain only Sample instances"
            )

        left_observation = observe(
            left,
            sample,
        )

        right_observation = observe(
            right,
            sample,
        )

        if (
            to_signature_observation(
                left_observation
            )
            !=
            to_signature_observation(
                right_observation
            )
        ):
            return Counterexample(
                sample=sample,
                left=left_observation,
                right=right_observation,
            )

    return None
