from search.core_synthesis_spec_v2 import (
    specification_signature,
    synthesize_from_specification,
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


EXPECTED_A = CoreProgram(
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


EXPECTED_B = CoreProgram(
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


def test_specification_has_minimum_length_four():
    result = (
        synthesize_from_specification()
    )

    assert (
        result.minimum_length
        == 4
    )


def test_exactly_two_minimal_solutions():
    result = (
        synthesize_from_specification()
    )

    assert (
        len(
            result.minimal_programs
        )
        == 2
    )


def test_expected_equivalent_programs_are_discovered():
    result = (
        synthesize_from_specification()
    )

    assert set(
        result.minimal_programs
    ) == {
        EXPECTED_A,
        EXPECTED_B,
    }


def test_every_solution_satisfies_declarative_spec():
    result = (
        synthesize_from_specification()
    )

    desired = (
        specification_signature()
    )

    assert all(
        program_signature(
            program
        ) == desired
        for program
        in result.minimal_programs
    )
