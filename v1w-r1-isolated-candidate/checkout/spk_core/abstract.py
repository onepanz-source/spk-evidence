from __future__ import annotations

from dataclasses import dataclass
from math import gcd

from .isa import (
    CoreAcc,
    CoreCmp,
    CoreConfig,
    CoreEmit,
    CoreProgram,
    CoreReset,
    ShiftDecay,
)


@dataclass(
    frozen=True,
    slots=True,
)
class RawSet:
    """
    Conservative set of unsigned raw states.

    Values satisfy:

        lower <= x <= upper
        x % modulus == residue

    The interval may be an over-approximation.
    """

    lower: int
    upper: int
    modulus: int = 1
    residue: int = 0

    def __post_init__(self):
        if self.lower < 0:
            raise ValueError(
                "lower must be nonnegative"
            )

        if self.upper < self.lower:
            raise ValueError(
                "upper must be >= lower"
            )

        if self.modulus <= 0:
            raise ValueError(
                "modulus must be positive"
            )

        object.__setattr__(
            self,
            "residue",
            self.residue
            % self.modulus,
        )

    @classmethod
    def top(
        cls,
        config: CoreConfig,
    ):
        return cls(
            lower=0,
            upper=config.max_raw,
        )

    @classmethod
    def exact(
        cls,
        value: int,
    ):
        return cls(
            lower=value,
            upper=value,
        )

    @property
    def is_exact(self):
        return (
            self.lower
            == self.upper
        )

    @property
    def exact_value(self):
        if not self.is_exact:
            return None

        return self.lower

    def _first_at_or_above(
        self,
        value,
    ):
        remainder = (
            value
            - self.residue
        ) % self.modulus

        if remainder == 0:
            return value

        return (
            value
            + self.modulus
            - remainder
        )

    def _last_at_or_below(
        self,
        value,
    ):
        remainder = (
            value
            - self.residue
        ) % self.modulus

        return (
            value
            - remainder
        )

    @property
    def minimum_reachable(self):
        value = self._first_at_or_above(
            self.lower
        )

        if value > self.upper:
            return None

        return value

    @property
    def maximum_reachable(self):
        value = self._last_at_or_below(
            self.upper
        )

        if value < self.lower:
            return None

        return value

    def refine(
        self,
        *,
        lower=None,
        upper=None,
    ):
        lo = (
            self.lower
            if lower is None
            else max(
                self.lower,
                lower,
            )
        )

        hi = (
            self.upper
            if upper is None
            else min(
                self.upper,
                upper,
            )
        )

        if hi < lo:
            return None

        first = self._first_at_or_above(
            lo
        )

        last = self._last_at_or_below(
            hi
        )

        if (
            first > hi
            or last < lo
        ):
            return None

        return RawSet(
            lower=first,
            upper=last,
            modulus=self.modulus,
            residue=self.residue,
        )

    def add_unknown_multiple(
        self,
        step: int,
        max_raw: int,
    ):
        """
        Abstract:

            x' = x + n * step
            n >= 0

        For an exact starting state v, the result preserves the full
        congruence:

            x' == v (mod step)

        For a non-singleton congruence class

            x == r (mod m),

        adding arbitrary multiples of step gives

            x' == r (mod gcd(m, step)).

        The exact-state case must be handled separately because our
        singleton representation uses modulus=1; blindly computing

            gcd(1, step)

        would discard newly-created modular information.
        """

        if step < 0:
            raise ValueError(
                "step must be nonnegative"
            )

        if step == 0:
            return self

        if self.is_exact:
            modulus = step
            residue = (
                self.lower
                % modulus
            )

            result = RawSet(
                lower=self.lower,
                upper=max_raw,
                modulus=modulus,
                residue=residue,
            )

            return result.refine()

        new_modulus = gcd(
            self.modulus,
            step,
        )

        result = RawSet(
            lower=self.lower,
            upper=max_raw,
            modulus=new_modulus,
            residue=(
                self.residue
                % new_modulus
            ),
        )

        return result.refine()


    def shift_unknown_delta(
        self,
        bits_per_tick: int,
    ):
        if bits_per_tick == 0:
            return self

        if (
            self.is_exact
            and self.lower == 0
        ):
            return self

        #
        # delta may be zero, therefore upper cannot decrease
        # universally.  Positive delta may destroy congruence
        # information and can drive the state to zero.
        #
        return RawSet(
            lower=0,
            upper=self.upper,
        )


def join_raw(
    left: RawSet | None,
    right: RawSet | None,
):
    """
    Conservative join preserving congruence information where possible.

    Singleton sets need special treatment because RawSet.exact(v) uses
    modulus=1 as a representation detail.  Semantically, an exact value
    is much more precise than "all values modulo 1".

    Examples:

        {0} U {0,2,4,...}
            -> mod 2 == 0

        {2} U {0,4,8,...}
            -> mod 2 == 0

        {0} U {2}
            -> [0,2] mod 2 == 0
    """

    if left is None:
        return right

    if right is None:
        return left

    if left == right:
        return left

    #
    # Two exact values.
    #
    if (
        left.is_exact
        and right.is_exact
    ):
        left_value = (
            left.exact_value
        )

        right_value = (
            right.exact_value
        )

        if (
            left_value
            == right_value
        ):
            return RawSet.exact(
                left_value
            )

        modulus = abs(
            left_value
            - right_value
        )

        lower = min(
            left_value,
            right_value,
        )

        upper = max(
            left_value,
            right_value,
        )

        return RawSet(
            lower=lower,
            upper=upper,
            modulus=modulus,
            residue=(
                lower
                % modulus
            ),
        )

    #
    # Exact left, congruent right.
    #
    if left.is_exact:
        value = (
            left.exact_value
        )

        modulus = gcd(
            right.modulus,
            abs(
                value
                - right.residue
            ),
        )

        if modulus == 0:
            modulus = (
                right.modulus
            )

        return RawSet(
            lower=min(
                value,
                right.lower,
            ),
            upper=max(
                value,
                right.upper,
            ),
            modulus=modulus,
            residue=(
                value
                % modulus
            ),
        )

    #
    # Congruent left, exact right.
    #
    if right.is_exact:
        value = (
            right.exact_value
        )

        modulus = gcd(
            left.modulus,
            abs(
                value
                - left.residue
            ),
        )

        if modulus == 0:
            modulus = (
                left.modulus
            )

        return RawSet(
            lower=min(
                left.lower,
                value,
            ),
            upper=max(
                left.upper,
                value,
            ),
            modulus=modulus,
            residue=(
                value
                % modulus
            ),
        )

    #
    # General congruence join.
    #
    modulus = gcd(
        left.modulus,
        right.modulus,
        abs(
            left.residue
            - right.residue
        ),
    )

    if modulus == 0:
        modulus = 1

    return RawSet(
        lower=min(
            left.lower,
            right.lower,
        ),
        upper=max(
            left.upper,
            right.upper,
        ),
        modulus=modulus,
        residue=(
            left.residue
            % modulus
        ),
    )



@dataclass(
    frozen=True,
    slots=True,
)
class GuardPartition:
    """
    Raw-state abstraction conditioned on the current guard.

    true:
        states reachable when guard == True

    false:
        states reachable when guard == False
    """

    true: RawSet | None
    false: RawSet | None

    @property
    def merged(self):
        return join_raw(
            self.true,
            self.false,
        )

    @property
    def guard_status(self):
        if self.true is None:
            return "FALSE"

        if self.false is None:
            return "TRUE"

        return "UNKNOWN"


@dataclass(
    frozen=True,
    slots=True,
)
class AnalysisStep:
    index: int
    instruction: object
    before: GuardPartition
    after: GuardPartition


def _map_partition(
    partition,
    function,
):
    return GuardPartition(
        true=(
            None
            if partition.true is None
            else function(
                partition.true
            )
        ),
        false=(
            None
            if partition.false is None
            else function(
                partition.false
            )
        ),
    )


def transfer(
    config: CoreConfig,
    partition: GuardPartition,
    instruction,
):
    if isinstance(
        instruction,
        CoreAcc,
    ):
        step = (
            instruction.weight
            * config.scale
        )

        return _map_partition(
            partition,
            lambda raw: (
                raw.add_unknown_multiple(
                    step,
                    config.max_raw,
                )
            ),
        )

    if isinstance(
        instruction,
        ShiftDecay,
    ):
        return _map_partition(
            partition,
            lambda raw: (
                raw.shift_unknown_delta(
                    instruction.bits_per_tick
                )
            ),
        )

    if isinstance(
        instruction,
        CoreCmp,
    ):
        raw = partition.merged

        if raw is None:
            return GuardPartition(
                true=None,
                false=None,
            )

        return GuardPartition(
            true=raw.refine(
                lower=(
                    instruction.threshold_raw
                )
            ),
            false=raw.refine(
                upper=(
                    instruction.threshold_raw
                    - 1
                )
            ),
        )

    if isinstance(
        instruction,
        CoreEmit,
    ):
        return partition

    if isinstance(
        instruction,
        CoreReset,
    ):
        return GuardPartition(
            true=(
                None
                if partition.true is None
                else RawSet.exact(
                    instruction.value_raw
                )
            ),
            false=partition.false,
        )

    raise TypeError(
        f"unsupported instruction: "
        f"{instruction!r}"
    )


def analyze_program(
    config: CoreConfig,
    program: CoreProgram,
):
    #
    # Runtime guard is False at batch entry.
    #
    partition = GuardPartition(
        true=None,
        false=RawSet.top(
            config
        ),
    )

    steps = []

    for index, instruction in enumerate(
        program.instructions
    ):
        before = partition

        partition = transfer(
            config,
            partition,
            instruction,
        )

        steps.append(
            AnalysisStep(
                index=index,
                instruction=instruction,
                before=before,
                after=partition,
            )
        )

    return tuple(
        steps
    )


def equivalent_threshold_interval(
    raw: RawSet,
    threshold: int,
):
    """
    Return the inclusive interval of thresholds that induce the same
    true/false partition over this abstract raw-state set.

    This is conservative: if abstraction has forgotten information,
    the interval may be smaller than the real equivalence class.
    """

    false_part = raw.refine(
        upper=threshold - 1
    )

    true_part = raw.refine(
        lower=threshold
    )

    if false_part is None:
        lower_threshold = 0
    else:
        lower_threshold = (
            false_part.maximum_reachable
            + 1
        )

    if true_part is None:
        upper_threshold = (
            raw.maximum_reachable
            + 1
        )
    else:
        upper_threshold = (
            true_part.minimum_reachable
        )

    return (
        lower_threshold,
        upper_threshold,
    )
