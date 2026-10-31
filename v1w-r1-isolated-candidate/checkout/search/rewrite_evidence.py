from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class AlgebraicStatus(str, Enum):
    PROVEN = "PROVEN"
    TESTED = "TESTED"
    CONJECTURED = "CONJECTURED"


class RuntimeStatus(str, Enum):
    IEEE_SAFE = "IEEE_SAFE"
    NOT_IEEE_SAFE = "NOT_IEEE_SAFE"
    NOT_CLASSIFIED = "NOT_CLASSIFIED"


@dataclass(
    frozen=True,
    slots=True,
)
class RewriteEvidence:
    name: str
    algebraic_status: AlgebraicStatus
    runtime_status: RuntimeStatus
    rationale: str


DECAY_RUN_FUSION = RewriteEvidence(
    name="DECAY_RUN_FUSION",
    algebraic_status=AlgebraicStatus.PROVEN,
    runtime_status=RuntimeStatus.NOT_IEEE_SAFE,
    rationale=(
        "Consecutive exponential decays compose exactly over the reals "
        "by addition of lambda=1/tau. IEEE-754 evaluation order may "
        "differ by one or more ULPs, and CMP can make that difference "
        "observationally visible at a threshold."
    ),
)


REWRITE_EVIDENCE = {
    DECAY_RUN_FUSION.name: (
        DECAY_RUN_FUSION
    ),
}


DISCRETE_TIME_FALSE_COMPARE_SINK = RewriteEvidence(
    name="DISCRETE_TIME_FALSE_COMPARE_SINK",
    algebraic_status=AlgebraicStatus.PROVEN,
    runtime_status=RuntimeStatus.IEEE_SAFE,
    rationale=(
        "For integer delta ticks, a positive state upper bound U and "
        "accumulated decay rate lambda can prove CMP(theta) false for "
        "all delta>=1 when U*exp(-lambda)<theta. At delta=0 DECAY is "
        "identity, so moving the comparison across another DECAY "
        "preserves its result. The sink itself changes no floating-"
        "point arithmetic order; subsequent DECAY fusion remains "
        "separately classified as NOT_IEEE_SAFE."
    ),
)

REWRITE_EVIDENCE[
    DISCRETE_TIME_FALSE_COMPARE_SINK.name
] = DISCRETE_TIME_FALSE_COMPARE_SINK
