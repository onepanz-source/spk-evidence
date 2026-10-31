from __future__ import annotations

import json

import pytest

from spk_core.ir_v0 import (
    CORE_IR_V0_SCHEMA,
    CORE_IR_V0_VERSION,
    build_core_ir_v0,
    dumps_core_ir_v0,
    loads_core_ir_v0,
    parse_core_ir_v0,
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


PROGRAM = CoreProgram(
    (
        ShiftDecay(
            bits_per_tick=1,
        ),
        CoreAcc(
            weight=2,
            channel=0,
        ),
        CoreCmp(
            threshold_raw=3,
        ),
        CoreEmit(
            channel_out=7,
        ),
        CoreReset(
            value_raw=0,
        ),
    )
)


def test_core_ir_v0_roundtrip():
    document = build_core_ir_v0(
        CONFIG,
        PROGRAM,
    )

    (
        config,
        program,
    ) = parse_core_ir_v0(
        document
    )

    assert config == CONFIG
    assert program == PROGRAM


def test_core_ir_v0_identity():
    document = build_core_ir_v0(
        CONFIG,
        PROGRAM,
    )

    assert (
        document["schema"]
        == CORE_IR_V0_SCHEMA
        == "spk-core-ir/v0"
    )

    assert (
        document["core_version"]
        == CORE_IR_V0_VERSION
        == "0"
    )


def test_core_ir_v0_instruction_encoding():
    document = build_core_ir_v0(
        CONFIG,
        PROGRAM,
    )

    assert document[
        "instructions"
    ] == [
        {
            "op": "DECAY",
            "bits_per_tick": 1,
        },
        {
            "op": "ACC",
            "weight": 2,
            "channel": 0,
        },
        {
            "op": "CMP",
            "threshold_raw": 3,
        },
        {
            "op": "EMIT",
            "channel_out": 7,
        },
        {
            "op": "RESET",
            "value_raw": 0,
        },
    ]


def test_core_ir_v0_json_is_deterministic():
    first = dumps_core_ir_v0(
        CONFIG,
        PROGRAM,
    )

    second = dumps_core_ir_v0(
        CONFIG,
        PROGRAM,
    )

    assert first == second

    assert json.loads(
        first
    ) == build_core_ir_v0(
        CONFIG,
        PROGRAM,
    )


def test_core_ir_v0_json_roundtrip():
    serialized = dumps_core_ir_v0(
        CONFIG,
        PROGRAM,
    )

    (
        config,
        program,
    ) = loads_core_ir_v0(
        serialized
    )

    assert config == CONFIG
    assert program == PROGRAM


def test_core_ir_v0_rejects_non_normalized_program():
    program = CoreProgram(
        (
            CoreCmp(
                threshold_raw=1,
            ),
            CoreCmp(
                threshold_raw=1,
            ),
        )
    )

    with pytest.raises(
        ValueError,
        match="runtime-normalized",
    ):
        build_core_ir_v0(
            CONFIG,
            program,
        )


def test_core_ir_v0_parser_rejects_non_normalized_program():
    document = {
        "schema": CORE_IR_V0_SCHEMA,
        "core_version": CORE_IR_V0_VERSION,
        "config": {
            "state_bits": 8,
            "fractional_bits": 0,
        },
        "instructions": [
            {
                "op": "CMP",
                "threshold_raw": 1,
            },
            {
                "op": "CMP",
                "threshold_raw": 1,
            },
        ],
    }

    with pytest.raises(
        ValueError,
        match="non-normalized",
    ):
        parse_core_ir_v0(
            document
        )


def test_core_ir_v0_rejects_unknown_opcode():
    document = {
        "schema": CORE_IR_V0_SCHEMA,
        "core_version": CORE_IR_V0_VERSION,
        "config": {
            "state_bits": 8,
            "fractional_bits": 0,
        },
        "instructions": [
            {
                "op": "TELEPORT",
            },
        ],
    }

    with pytest.raises(
        ValueError,
        match="unknown Core IR opcode",
    ):
        parse_core_ir_v0(
            document
        )


def test_core_ir_v0_rejects_wrong_schema():
    document = build_core_ir_v0(
        CONFIG,
        PROGRAM,
    )

    document[
        "schema"
    ] = "spk-core-ir/v999"

    with pytest.raises(
        ValueError,
        match="unsupported Core IR schema",
    ):
        parse_core_ir_v0(
            document
        )
