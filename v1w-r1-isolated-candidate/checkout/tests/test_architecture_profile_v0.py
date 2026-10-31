from dataclasses import FrozenInstanceError, replace

import pytest

from spk_architecture.profile_v0 import (
    ProcessingElementV0,
    ArchitectureProfileV0,
)


@pytest.fixture
def pe():
    return ProcessingElementV0(
        pe_id="PE0",
        program_slots=64,
        state_slots=16,
        event_slots=32,
        output_slots=32,
        observation_slots=16,
        accesses_per_service_tick=2,
    )


def test_valid_profile(pe):
    other = replace(pe, pe_id="PE1")

    profile = ArchitectureProfileV0(
        profile_id="spk-test-v0",
        pes=(pe, other),
    )

    assert len(profile.pes) == 2
    assert profile.pes[0].state_slots == 16


def test_profile_immutable(pe):
    with pytest.raises(FrozenInstanceError):
        pe.program_slots = 100


def test_empty_profile_rejected():
    with pytest.raises(ValueError):
        ArchitectureProfileV0("empty", ())


def test_duplicate_pe_rejected(pe):
    with pytest.raises(ValueError):
        ArchitectureProfileV0(
            "duplicate",
            (pe, pe),
        )


def test_heterogeneous_pe_rejected(pe):
    other = replace(
        pe,
        pe_id="PE1",
        state_slots=8,
    )

    with pytest.raises(ValueError):
        ArchitectureProfileV0(
            "heterogeneous",
            (pe, other),
        )


@pytest.mark.parametrize(
    "field,value",
    [
        ("program_slots", -1),
        ("state_slots", True),
        ("event_slots", -1),
        ("accesses_per_service_tick", 0),
    ],
)
def test_invalid_capacities_rejected(pe, field, value):
    with pytest.raises(ValueError):
        replace(pe, **{field: value})


def test_invalid_pe_id(pe):
    with pytest.raises(ValueError):
        replace(pe, pe_id=" ")


def test_invalid_profile_id(pe):
    with pytest.raises(ValueError):
        ArchitectureProfileV0("", (pe,))
