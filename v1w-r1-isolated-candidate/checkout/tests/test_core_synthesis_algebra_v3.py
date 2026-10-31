from search.core_synthesis_algebra_v3 import (
    canonicalize_core_program,
    synthesize_algebra_guided,
)
from search.core_synthesis_v1 import (
    program_signature,
)

from spk_core.isa import (
    CoreAcc,
    CoreCmp,
    CoreEmit,
    CoreProgram,
    CoreReset,
)


CANONICAL = CoreProgram(
    (
        CoreAcc(
            weight=1,
            channel=0,
        ),
        CoreCmp(
            threshold_raw=2,
        ),
        CoreEmit(
            channel_out=7,
        ),
        CoreReset(
            value_raw=0,
        ),
    )
)


ALTERNATIVE = CoreProgram(
    (
        CoreAcc(
            weight=1,
            channel=0,
        ),
        CoreCmp(
            threshold_raw=2,
        ),
        CoreReset(
            value_raw=0,
        ),
        CoreEmit(
            channel_out=7,
        ),
    )
)


def test_emit_reset_form_is_already_canonical():
    assert (
        canonicalize_core_program(
            CANONICAL
        )
        == CANONICAL
    )


def test_reset_emit_is_canonicalized():
    assert (
        canonicalize_core_program(
            ALTERNATIVE
        )
        == CANONICAL
    )


def test_control_rewrite_preserves_behavior():
    assert (
        program_signature(
            ALTERNATIVE
        )
        ==
        program_signature(
            canonicalize_core_program(
                ALTERNATIVE
            )
        )
    )


def test_algebra_guided_synthesis_has_one_canonical_solution():
    result = (
        synthesize_algebra_guided()
    )

    assert (
        result.minimum_length
        == 4
    )

    assert (
        result.solutions
        == (
            CANONICAL,
        )
    )
