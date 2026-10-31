"""S3.7a: bounded source-output and destination-event ownership."""

from dataclasses import FrozenInstanceError, replace

import pytest

from spk_architecture.profile_v0 import ArchitectureProfileV0, ProcessingElementV0
from spk_simulator.event_storage_v0 import (
    RoutedOccurrenceV0,
    RoutedStorageStateV0,
    RoutedStorageBlockedV0,
    offer_routed_output_v0,
    admit_routed_event_v0,
    consume_routed_event_v0,
    routed_storage_usage_v0,
)


def machine(output=2, events=2):
    pe0 = ProcessingElementV0(
        pe_id="PE0", program_slots=8, state_slots=4,
        event_slots=events, output_slots=output,
        observation_slots=4, accesses_per_service_tick=2,
    )
    pe1 = replace(pe0, pe_id="PE1")
    return ArchitectureProfileV0("lab-v0", (pe0, pe1))


def empty():
    return RoutedStorageStateV0("lab-v0", "E0")


def spike(event_id=1, **overrides):
    return replace(
        RoutedOccurrenceV0(
            event_id=event_id, epoch_id="E0",
            source_node_id="A", source_pe_id="PE0", source_channel=7,
            target_node_id="B", target_pe_id="PE1", target_channel=0,
            emission_event_time=2, delivery_event_time=4,
        ),
        **overrides,
    )


def test_complete_lifecycle_and_conservation():
    arch, before = machine(), empty()
    pending = offer_routed_output_v0(arch, before, spike())
    assert len(pending.pending_output) == 1
    assert pending.admitted_events == ()
    admitted = admit_routed_event_v0(arch, pending, 1)
    assert admitted.pending_output == ()
    assert admitted.admitted_events == (spike(),)
    completed = consume_routed_event_v0(arch, admitted, 1, target_pe_id="PE1")
    assert completed.pending_output == ()
    assert completed.admitted_events == ()
    assert completed.consumed_ids == (1,)
    assert before == empty()


def test_output_capacity_fails_closed():
    arch = machine(output=1)
    pending = offer_routed_output_v0(arch, empty(), spike())
    with pytest.raises(RoutedStorageBlockedV0) as exc:
        offer_routed_output_v0(arch, pending, spike(2))
    assert (exc.value.pe_id, exc.value.domain, exc.value.occupied, exc.value.capacity) == ("PE0", "OUTPUT", 1, 1)
    assert len(pending.pending_output) == 1


def test_event_capacity_fails_closed_without_losing_pending():
    arch = machine(events=1)
    pending = offer_routed_output_v0(arch, empty(), spike(1))
    admitted = admit_routed_event_v0(arch, pending, 1)
    second = offer_routed_output_v0(arch, admitted, spike(2))
    with pytest.raises(RoutedStorageBlockedV0) as exc:
        admit_routed_event_v0(arch, second, 2)
    assert exc.value.domain == "EVENT"
    assert second.pending_output == (spike(2),)
    assert second.admitted_events == (spike(1),)
    freed = consume_routed_event_v0(arch, second, 1, target_pe_id="PE1")
    assert admit_routed_event_v0(arch, freed, 2).admitted_events == (spike(2),)


def test_parallel_occurrences_not_deduplicated():
    arch = machine()
    state = offer_routed_output_v0(arch, empty(), spike(1))
    state = offer_routed_output_v0(arch, state, spike(2))
    assert len(state.pending_output) == 2
    state = admit_routed_event_v0(arch, state, 1)
    state = admit_routed_event_v0(arch, state, 2)
    assert {item.event_id for item in state.admitted_events} == {1, 2}
    assert state.admitted_events[0].delivery_event_time == state.admitted_events[1].delivery_event_time


def test_repeated_identity_rejected_while_pending():
    arch = machine()
    state = offer_routed_output_v0(arch, empty(), spike(1))
    with pytest.raises(ValueError, match="reused event identity"):
        offer_routed_output_v0(arch, state, spike(1))


def test_repeated_identity_rejected_after_consumption():
    arch = machine()
    state = offer_routed_output_v0(arch, empty(), spike(1))
    state = admit_routed_event_v0(arch, state, 1)
    state = consume_routed_event_v0(arch, state, 1, target_pe_id="PE1")
    with pytest.raises(ValueError, match="reused event identity"):
        offer_routed_output_v0(arch, state, spike(1))


def test_transfer_requires_pending_occurrence():
    with pytest.raises(ValueError, match="not pending"):
        admit_routed_event_v0(machine(), empty(), 1)


def test_consume_requires_admission():
    state = offer_routed_output_v0(machine(), empty(), spike())
    with pytest.raises(ValueError, match="not admitted"):
        consume_routed_event_v0(machine(), state, 1, target_pe_id="PE1")


def test_wrong_consumer_pe_rejected():
    arch = machine()
    state = admit_routed_event_v0(arch, offer_routed_output_v0(arch, empty(), spike()), 1)
    with pytest.raises(ValueError, match="wrong consuming PE"):
        consume_routed_event_v0(arch, state, 1, target_pe_id="PE0")


def test_unknown_pe_rejected():
    with pytest.raises(ValueError, match="unknown source or target PE"):
        offer_routed_output_v0(machine(), empty(), spike(source_pe_id="PX"))


def test_epoch_mismatch_rejected():
    with pytest.raises(ValueError, match="event epoch mismatch"):
        offer_routed_output_v0(machine(), empty(), spike(epoch_id="E1"))


def test_profile_mismatch_rejected():
    with pytest.raises(ValueError, match="profile mismatch"):
        routed_storage_usage_v0(machine(), replace(empty(), profile_id="other"))


def test_usage_counts_both_distinct_domains():
    arch = machine(output=2, events=1)
    state = offer_routed_output_v0(arch, empty(), spike(1))
    state = admit_routed_event_v0(arch, state, 1)
    state = offer_routed_output_v0(arch, state, spike(2))
    usage = {item.pe_id: item for item in routed_storage_usage_v0(arch, state)}
    assert (usage["PE0"].pending_output, usage["PE0"].output_capacity) == (1, 2)
    assert (usage["PE1"].admitted_events, usage["PE1"].event_capacity) == (1, 1)


def test_zero_output_capacity_blocks_first_offer():
    with pytest.raises(RoutedStorageBlockedV0) as exc:
        offer_routed_output_v0(machine(output=0), empty(), spike())
    assert exc.value.domain == "OUTPUT"


def test_zero_event_capacity_blocks_transfer():
    arch = machine(events=0)
    state = offer_routed_output_v0(arch, empty(), spike())
    with pytest.raises(RoutedStorageBlockedV0) as exc:
        admit_routed_event_v0(arch, state, 1)
    assert exc.value.domain == "EVENT"


def test_same_pe_transfer_uses_output_then_event_slot():
    arch = machine(output=1, events=1)
    e = spike(target_pe_id="PE0", target_node_id="A")
    state = offer_routed_output_v0(arch, empty(), e)
    state = admit_routed_event_v0(arch, state, 1)
    usage = {item.pe_id: item for item in routed_storage_usage_v0(arch, state)}
    assert usage["PE0"].pending_output == 0
    assert usage["PE0"].admitted_events == 1


def test_invalid_event_time_delay():
    with pytest.raises(ValueError, match="nonpositive"):
        spike(delivery_event_time=2)


def test_boolean_id_rejected():
    with pytest.raises(ValueError, match="invalid event_id"):
        spike(event_id=True)


def test_negative_channel_rejected():
    with pytest.raises(ValueError, match="invalid target_channel"):
        spike(target_channel=-1)


def test_duplicate_ids_cannot_exist_in_stored_state():
    with pytest.raises(ValueError, match="duplicate event identity"):
        replace(empty(), pending_output=(spike(1),), admitted_events=(spike(1),))


def test_state_is_immutable():
    state = empty()
    with pytest.raises(FrozenInstanceError):
        state.pending_output = ()


def test_deterministic_replay():
    arch = machine()
    def run():
        state = offer_routed_output_v0(arch, empty(), spike(1))
        state = admit_routed_event_v0(arch, state, 1)
        return consume_routed_event_v0(arch, state, 1, target_pe_id="PE1")
    assert run() == run()


def test_invalid_preexisting_overcapacity_state():
    arch = machine(output=1)
    forged = replace(empty(), pending_output=(spike(1), spike(2)))
    with pytest.raises(ValueError, match="pre-existing storage exceeds capacity"):
        routed_storage_usage_v0(arch, forged)
