import math

import pytest

from search.interaction_packed_core_v1 import (
    CoreConfig as PackedConfig,
)
from spk.operators import (
    Acc,
    Compare,
    Decay,
    Reset,
)
from spk.program import Program

from spk_core.compiler import (
    CoreCompileError,
    compile_spk_program,
)
from spk_core.isa import (
    CoreCmp,
    CoreConfig,
    CoreReset,
)
from spk_core.packed import (
    lower_packed_core,
)


PACKED = PackedConfig(
    channels=3,
    max_multiplicity=1,
    fractional_bits=24,
)


CONFIG, EXPECTED = (
    lower_packed_core(
        PACKED
    )
)


def packed_spk_program():
    k = PACKED.bits_per_tick

    tau = (
        1.0
        /
        (
            k
            * math.log(2.0)
        )
    )

    return Program(
        (
            Decay(
                tau=tau
            ),
            Acc(
                weight=1.0,
                channel=0,
            ),
            Acc(
                weight=2.0,
                channel=1,
            ),
            Acc(
                weight=4.0,
                channel=2,
            ),
        )
    )


def test_compiler_reconstructs_packed_microcode():
    compiled = compile_spk_program(
        packed_spk_program(),
        CONFIG,
    )

    assert (
        compiled.program
        == EXPECTED
    )

    assert (
        compiled.structurally_exact
        is True
    )


def test_general_exponential_decay_is_rejected():
    program = Program(
        (
            Decay(
                tau=1.0
            ),
        )
    )

    with pytest.raises(
        CoreCompileError
    ):
        compile_spk_program(
            program,
            CONFIG,
        )


def test_fractional_acc_weight_is_rejected():
    program = Program(
        (
            Acc(
                weight=0.5,
                channel=0,
            ),
        )
    )

    with pytest.raises(
        CoreCompileError
    ):
        compile_spk_program(
            program,
            CONFIG,
        )


def test_dyadic_compare_is_compiled_exactly():
    config = CoreConfig(
        state_bits=16,
        fractional_bits=8,
    )

    program = Program(
        (
            Compare(
                threshold=0.5
            ),
        )
    )

    compiled = compile_spk_program(
        program,
        config,
    )

    assert (
        compiled.program.instructions
        == (
            CoreCmp(
                threshold_raw=128
            ),
        )
    )


def test_dyadic_reset_is_compiled_exactly():
    config = CoreConfig(
        state_bits=16,
        fractional_bits=8,
    )

    program = Program(
        (
            Reset(
                value=0.25
            ),
        )
    )

    compiled = compile_spk_program(
        program,
        config,
    )

    assert (
        compiled.program.instructions
        == (
            CoreReset(
                value_raw=64
            ),
        )
    )


def test_nonrepresentable_reset_is_rejected():
    config = CoreConfig(
        state_bits=16,
        fractional_bits=8,
    )

    program = Program(
        (
            Reset(
                value=0.1
            ),
        )
    )

    with pytest.raises(
        CoreCompileError
    ):
        compile_spk_program(
            program,
            config,
        )
