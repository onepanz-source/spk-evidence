from search.core_synthesis_v1 import (
    TARGET_PROGRAM,
    program_signature,
    synthesize_target,
)


def test_target_is_not_synthesizable_below_length_four():
    result = synthesize_target()

    assert result.minimum_length == 4


def test_synthesized_program_matches_target_exactly():
    result = synthesize_target()

    assert (
        program_signature(
            result.representative
        )
        ==
        program_signature(
            TARGET_PROGRAM
        )
    )


def test_at_least_one_minimal_program_exists():
    result = synthesize_target()

    assert (
        len(
            result.minimal_programs
        )
        >= 1
    )

    assert all(
        len(
            program.instructions
        )
        == 4
        for program in (
            result.minimal_programs
        )
    )
