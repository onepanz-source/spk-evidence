from __future__ import annotations

import json

from .isa import (
    CoreAcc,
    CoreCmp,
    CoreConfig,
    CoreEmit,
    CoreProgram,
    CoreReset,
    ShiftDecay,
)
from .semantic_canonicalize import (
    canonicalize_core_program_semantic_runtime,
)


CORE_IR_V0_SCHEMA = "spk-core-ir/v0"
CORE_IR_V0_VERSION = "0"


def _instruction_to_ir(
    instruction,
) -> dict:
    if isinstance(
        instruction,
        ShiftDecay,
    ):
        return {
            "op": "DECAY",
            "bits_per_tick": (
                instruction.bits_per_tick
            ),
        }

    if isinstance(
        instruction,
        CoreAcc,
    ):
        return {
            "op": "ACC",
            "weight": instruction.weight,
            "channel": instruction.channel,
        }

    if isinstance(
        instruction,
        CoreCmp,
    ):
        return {
            "op": "CMP",
            "threshold_raw": (
                instruction.threshold_raw
            ),
        }

    if isinstance(
        instruction,
        CoreEmit,
    ):
        return {
            "op": "EMIT",
            "channel_out": (
                instruction.channel_out
            ),
        }

    if isinstance(
        instruction,
        CoreReset,
    ):
        return {
            "op": "RESET",
            "value_raw": (
                instruction.value_raw
            ),
        }

    raise TypeError(
        f"unsupported Core instruction: "
        f"{instruction!r}"
    )


def _instruction_from_ir(
    data: dict,
):
    if not isinstance(
        data,
        dict,
    ):
        raise ValueError(
            "IR instruction must be an object"
        )

    op = data.get(
        "op"
    )

    if op == "DECAY":
        return ShiftDecay(
            bits_per_tick=data[
                "bits_per_tick"
            ]
        )

    if op == "ACC":
        return CoreAcc(
            weight=data[
                "weight"
            ],
            channel=data[
                "channel"
            ],
        )

    if op == "CMP":
        return CoreCmp(
            threshold_raw=data[
                "threshold_raw"
            ]
        )

    if op == "EMIT":
        return CoreEmit(
            channel_out=data[
                "channel_out"
            ]
        )

    if op == "RESET":
        return CoreReset(
            value_raw=data[
                "value_raw"
            ]
        )

    raise ValueError(
        f"unknown Core IR opcode: "
        f"{op!r}"
    )


def build_core_ir_v0(
    config: CoreConfig,
    program: CoreProgram,
) -> dict:
    """
    Serialize one already-canonical SPK/Core v0 program.

    Core IR v0 is deliberately strict: it refuses non-normalized input.
    Canonicalization belongs to the compiler pipeline, not to the
    serialization layer.
    """

    normalized = (
        canonicalize_core_program_semantic_runtime(
            program,
            config=config,
        )
    )

    if normalized != program:
        raise ValueError(
            "Core IR v0 requires a runtime-normalized "
            "CoreProgram"
        )

    return {
        "schema": CORE_IR_V0_SCHEMA,
        "core_version": CORE_IR_V0_VERSION,
        "config": {
            "state_bits": (
                config.state_bits
            ),
            "fractional_bits": (
                config.fractional_bits
            ),
        },
        "instructions": [
            _instruction_to_ir(
                instruction
            )
            for instruction
            in program.instructions
        ],
    }


def parse_core_ir_v0(
    data: dict,
) -> tuple[
    CoreConfig,
    CoreProgram,
]:
    if not isinstance(
        data,
        dict,
    ):
        raise ValueError(
            "Core IR v0 document must be an object"
        )

    if (
        data.get("schema")
        != CORE_IR_V0_SCHEMA
    ):
        raise ValueError(
            "unsupported Core IR schema"
        )

    if (
        data.get("core_version")
        != CORE_IR_V0_VERSION
    ):
        raise ValueError(
            "unsupported Core version"
        )

    config_data = data.get(
        "config"
    )

    if not isinstance(
        config_data,
        dict,
    ):
        raise ValueError(
            "Core IR config must be an object"
        )

    instruction_data = data.get(
        "instructions"
    )

    if not isinstance(
        instruction_data,
        list,
    ):
        raise ValueError(
            "Core IR instructions must be a list"
        )

    config = CoreConfig(
        state_bits=config_data[
            "state_bits"
        ],
        fractional_bits=config_data[
            "fractional_bits"
        ],
    )

    program = CoreProgram(
        tuple(
            _instruction_from_ir(
                item
            )
            for item
            in instruction_data
        )
    )

    normalized = (
        canonicalize_core_program_semantic_runtime(
            program,
            config=config,
        )
    )

    if normalized != program:
        raise ValueError(
            "Core IR v0 contains a non-normalized "
            "CoreProgram"
        )

    return (
        config,
        program,
    )


def dumps_core_ir_v0(
    config: CoreConfig,
    program: CoreProgram,
) -> str:
    """
    Deterministic JSON representation suitable for hashing,
    caching and compiler artifacts.
    """

    return json.dumps(
        build_core_ir_v0(
            config,
            program,
        ),
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        ensure_ascii=True,
    )


def loads_core_ir_v0(
    text: str,
) -> tuple[
    CoreConfig,
    CoreProgram,
]:
    try:
        data = json.loads(
            text
        )
    except json.JSONDecodeError as exc:
        raise ValueError(
            "invalid Core IR v0 JSON"
        ) from exc

    return parse_core_ir_v0(
        data
    )
