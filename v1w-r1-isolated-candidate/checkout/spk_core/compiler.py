from __future__ import annotations

import math
from dataclasses import dataclass, fields, is_dataclass

from spk.operators import (
    Acc,
    Compare,
    Decay,
    Emit,
    Reset,
)
from spk.program import Program

from .isa import (
    CoreAcc,
    CoreCmp,
    CoreConfig,
    CoreEmit,
    CoreProgram,
    CoreReset,
    ShiftDecay,
)


class CoreCompileError(ValueError):
    pass


@dataclass(
    frozen=True,
    slots=True,
)
class CoreCompilation:
    config: CoreConfig
    program: CoreProgram

    #
    # Means every source instruction has an exact structural lowering.
    # It does NOT claim that arbitrary real-valued SPK executions are
    # bit-exact with finite fixed-point execution.
    #
    structurally_exact: bool

    notes: tuple[str, ...]


def _source_instructions(
    program: Program,
) -> tuple:
    #
    # Keep this tolerant of the current Program container naming.
    #
    for name in (
        "operators",
        "instructions",
        "steps",
        "ops",
    ):
        value = getattr(
            program,
            name,
            None,
        )

        if isinstance(
            value,
            tuple,
        ):
            return value

    if is_dataclass(
        program
    ):
        for field in fields(
            program
        ):
            value = getattr(
                program,
                field.name,
            )

            if isinstance(
                value,
                tuple,
            ):
                return value

    try:
        return tuple(
            program
        )
    except TypeError as exc:
        raise CoreCompileError(
            "cannot extract instructions "
            "from SPK Program"
        ) from exc


def _nearest_exact_int(
    value: float,
    *,
    label: str,
    tolerance: float = 1e-12,
) -> int:
    if not math.isfinite(
        value
    ):
        raise CoreCompileError(
            f"{label} must be finite"
        )

    nearest = round(
        value
    )

    if not math.isclose(
        value,
        nearest,
        rel_tol=0.0,
        abs_tol=tolerance,
    ):
        raise CoreCompileError(
            f"{label} is not exactly "
            f"representable: {value!r}"
        )

    return int(
        nearest
    )


def _fixed_raw(
    value: float,
    config: CoreConfig,
    *,
    label: str,
) -> int:
    return _nearest_exact_int(
        float(value)
        * config.scale,
        label=label,
    )


def _compile_decay(
    operator: Decay,
):
    tau = float(
        operator.tau
    )

    if (
        not math.isfinite(tau)
        or tau <= 0.0
    ):
        raise CoreCompileError(
            f"invalid DECAY tau: {tau!r}"
        )

    #
    # Want:
    #
    #   exp(-dt/tau) == 2^(-k*dt)
    #
    # therefore:
    #
    #   k = 1 / (tau ln 2)
    #
    k_float = (
        1.0
        /
        (
            tau
            * math.log(2.0)
        )
    )

    k = _nearest_exact_int(
        k_float,
        label="DECAY shift rate",
    )

    if k < 1:
        raise CoreCompileError(
            "Core v0 requires DECAY "
            "with positive integer "
            "bits_per_tick"
        )

    return ShiftDecay(
        bits_per_tick=k
    )


def compile_spk_program(
    program: Program,
    config: CoreConfig,
) -> CoreCompilation:
    output = []

    notes = []

    for pc, operator in enumerate(
        _source_instructions(
            program
        )
    ):
        if isinstance(
            operator,
            Decay,
        ):
            core = _compile_decay(
                operator
            )

            output.append(
                core
            )

            notes.append(
                f"{pc}: DECAY -> "
                f"SHIFT_DECAY("
                f"{core.bits_per_tick})"
            )

        elif isinstance(
            operator,
            Acc,
        ):
            weight = (
                _nearest_exact_int(
                    float(
                        operator.weight
                    ),
                    label=(
                        f"ACC weight at "
                        f"pc={pc}"
                    ),
                )
            )

            if weight < 0:
                raise CoreCompileError(
                    "Core v0 unsigned state "
                    "does not support "
                    "negative ACC weights"
                )

            output.append(
                CoreAcc(
                    weight=weight,
                    channel=(
                        operator.channel
                    ),
                )
            )

            notes.append(
                f"{pc}: ACC exact integer "
                f"weight"
            )

        elif isinstance(
            operator,
            Compare,
        ):
            raw = _fixed_raw(
                operator.threshold,
                config,
                label=(
                    f"CMP threshold at "
                    f"pc={pc}"
                ),
            )

            output.append(
                CoreCmp(
                    threshold_raw=raw
                )
            )

            notes.append(
                f"{pc}: CMP exact "
                f"fixed-point threshold"
            )

        elif isinstance(
            operator,
            Emit,
        ):
            output.append(
                CoreEmit(
                    channel_out=(
                        operator.channel_out
                    )
                )
            )

            notes.append(
                f"{pc}: EMIT exact"
            )

        elif isinstance(
            operator,
            Reset,
        ):
            raw = _fixed_raw(
                operator.value,
                config,
                label=(
                    f"RESET value at "
                    f"pc={pc}"
                ),
            )

            if not (
                0
                <= raw
                <= config.max_raw
            ):
                raise CoreCompileError(
                    f"RESET at pc={pc} "
                    "outside unsigned "
                    "Core state range"
                )

            output.append(
                CoreReset(
                    value_raw=raw
                )
            )

            notes.append(
                f"{pc}: RESET exact "
                f"fixed-point value"
            )

        else:
            raise CoreCompileError(
                f"unsupported SPK operator "
                f"at pc={pc}: "
                f"{operator!r}"
            )

    return CoreCompilation(
        config=config,
        program=CoreProgram(
            tuple(output)
        ),
        structurally_exact=True,
        notes=tuple(notes),
    )
