from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from spk.event import SpikeTrain
from spk.program import Program
from spk.runner import run_program


#
# Numerical policy for empirical signatures.
#
# This is NOT part of the mathematical SPK semantics.
#
# It only prevents IEEE-754 rounding noise from creating artificial
# empirical equivalence classes.
#
SIGNATURE_SIGNIFICANT_DIGITS = 12
SIGNATURE_ZERO_TOLERANCE = 1e-12


@dataclass(frozen=True, slots=True)
class Sample:
    """
    One empirical equivalence sample.

    train:
        Input spike train.

    initial_x:
        Initial persistent scalar state.
    """

    train: SpikeTrain
    initial_x: float = 0.0


@dataclass(frozen=True, slots=True)
class Observation:
    """
    Raw execution observation.

    Raw floating-point state is preserved for diagnostics and
    counterexample reporting.
    """

    output: tuple[tuple[int, int], ...]
    final_state: tuple[float, bool]


@dataclass(frozen=True, slots=True)
class SignatureObservation:
    """
    Hashable empirical observation used for equivalence clustering.

    Output and guard remain exact.

    final_x is deterministically normalized to suppress irrelevant
    IEEE-754 rounding differences.
    """

    output: tuple[tuple[int, int], ...]
    final_x: float
    final_guard: bool


Signature = tuple[SignatureObservation, ...]


def normalize_signature_x(
    value: float,
) -> float:
    """
    Deterministic projection of floating-point state for empirical
    signatures.

    This deliberately defines a coarser numerical observation than
    raw IEEE-754 equality.

    It must NOT be interpreted as mathematical equality over R.
    """

    value = float(value)

    if abs(value) <= SIGNATURE_ZERO_TOLERANCE:
        return 0.0

    return float(
        format(
            value,
            f".{SIGNATURE_SIGNIFICANT_DIGITS}g",
        )
    )


def observe(
    program: Program,
    sample: Sample,
) -> Observation:
    """
    Execute one program on one sample and preserve the raw result.
    """

    result = run_program(
        program,
        sample.train,
        initial_x=sample.initial_x,
    )

    return Observation(
        output=result.output.as_pairs(),
        final_state=result.final_state,
    )


def to_signature_observation(
    observation: Observation,
) -> SignatureObservation:
    """
    Convert a raw observation into its empirical-signature form.
    """

    final_x, final_guard = (
        observation.final_state
    )

    return SignatureObservation(
        output=observation.output,
        final_x=normalize_signature_x(
            final_x
        ),
        final_guard=final_guard,
    )


def signature(
    program: Program,
    corpus: Iterable[Sample],
) -> Signature:
    """
    Compute the empirical signature Sig_D(P).

    Numerical state is normalized according to the explicit
    signature policy.

    Output spike trains and guards remain exact.

    Identical signatures therefore mean empirical equivalence under:

        corpus D
        +
        numerical signature policy

    This is not a proof of mathematical equivalence.
    """

    if not isinstance(program, Program):
        raise TypeError(
            "signature requires a Program"
        )

    samples = tuple(corpus)

    if not all(
        isinstance(sample, Sample)
        for sample in samples
    ):
        raise TypeError(
            "corpus must contain only Sample instances"
        )

    return tuple(
        to_signature_observation(
            observe(
                program,
                sample,
            )
        )
        for sample in samples
    )


def empirically_equivalent(
    left: Program,
    right: Program,
    corpus: Iterable[Sample],
) -> bool:
    """
    Return True iff both programs have identical normalized empirical
    signatures on the supplied corpus.

    This is NOT a proof of strong equivalence.
    """

    samples = tuple(corpus)

    return (
        signature(left, samples)
        ==
        signature(right, samples)
    )


def cluster_by_signature(
    programs: Iterable[Program],
    corpus: Iterable[Sample],
) -> dict[Signature, tuple[Program, ...]]:
    """
    Group programs into empirical equivalence classes.
    """

    samples = tuple(corpus)

    groups: dict[
        Signature,
        list[Program],
    ] = defaultdict(list)

    for program in programs:
        groups[
            signature(
                program,
                samples,
            )
        ].append(program)

    return {
        sig: tuple(members)
        for sig, members in groups.items()
    }
