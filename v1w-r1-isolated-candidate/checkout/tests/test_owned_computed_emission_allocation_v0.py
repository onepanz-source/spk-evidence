"""Owned identity allocation must not be mistaken for OUTPUT publication."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_network.model_v0 import NetworkEdgeV0
from spk_simulator.computed_topology_routing_v0 import ComputedFanoutCapacityV0
from spk_simulator.owned_computed_emission_allocation_v0 import (
    OwnedComputedEmissionAllocationV0, ComputedEmissionAllocationLedgerV0,
    initialize_computed_emission_allocation_v0 as init,
    allocate_computed_emission_v0 as allocate,
)
from spk_simulator.versioned_core_transition_v0 import (
    prepare_core_transition_v0, commit_core_transition_v0,
)
from tests.test_computed_topology_routing_v0 import context


def setup(node='C', timestamp=3, *, existing=(0, 11), first=None):
    arch, net, placement, image, prepared, _ = context(node, timestamp)
    ledger = init(arch, net, placement, image,
                  existing_request_ids=existing, first_dynamic_request_id=first)
    return arch, net, placement, image, prepared, ledger


def step(c):
    return allocate(c[0], c[3], c[4], c[5])


def changed(c, index, value):
    return (*c[:index], value, *c[index+1:])


def test_allocates_one_emission_and_two_parallel_route_ids():
    s = step(setup())
    assert s.allocation.emission_request_id == 12
    assert s.allocation.route_request_ids == (13, 14)
    assert s.ledger.next_request_id == 15
    assert s.allocation.topology.required_output_slots == 2


def test_event_ids_are_identical_to_route_request_ids():
    s = step(setup())
    assert tuple(x.occurrence.event_id for x in s.allocation.topology.routes) == s.allocation.route_request_ids


def test_terminal_only_allocates_emission_id_but_no_route_ids():
    s = step(setup('B', 4))
    assert s.allocation.emission_request_id == 12
    assert s.allocation.route_request_ids == ()
    assert len(s.allocation.topology.terminal_outputs) == 1
    assert s.ledger.next_request_id == 13


def test_allocates_from_zero_without_existing_requests():
    s = step(setup(existing=()))
    assert s.allocation.emission_request_id == 0
    assert s.allocation.route_request_ids == (1, 2)
    assert s.ledger.next_request_id == 3


def test_explicit_namespace_start_preserves_gap():
    s = step(setup(first=99))
    assert (s.allocation.emission_request_id, s.allocation.route_request_ids) == (99, (100, 101))


def test_second_node_uses_owner_cursor_not_caller_cursor():
    c = setup()
    first = step(c)
    prepared = prepare_core_transition_v0(c[1], c[3], node_id='A', timestamp=2, channels=(0,))
    second = allocate(c[0], c[3], prepared, first.ledger)
    assert second.allocation.emission_request_id == 15
    assert second.allocation.route_request_ids == (16,)
    assert second.ledger.next_request_id == 17


def test_terminal_followed_by_routed_emission_does_not_reuse_request_id():
    c = setup('B', 4)
    first = step(c)
    prepared = prepare_core_transition_v0(c[1], c[3], node_id='A', timestamp=2, channels=(0,))
    second = allocate(c[0], c[3], prepared, first.ledger)
    assert (first.allocation.emission_request_id, second.allocation.emission_request_id) == (12, 13)
    assert second.allocation.route_request_ids == (14,)


def test_same_neuron_version_cannot_be_allocated_twice():
    c = setup()
    s = step(c)
    with pytest.raises(ValueError, match='already allocated'):
        allocate(c[0], c[3], c[4], s.ledger)


def test_later_version_can_receive_new_ids():
    c = setup()
    first = step(c)
    updated = commit_core_transition_v0(c[1], c[3], c[4]).state
    prepared = prepare_core_transition_v0(c[1], updated, node_id='C', timestamp=4, channels=(0,))
    # This validates namespace progress, not an authorized physical state commit.
    assert prepared.candidate_outputs
    after = allocate(c[0], updated, prepared, first.ledger)
    assert after.allocation.emission_request_id == 15
    assert after.ledger.next_request_id > first.ledger.next_request_id


def test_successor_keeps_old_state_unchanged():
    c = setup()
    before = c[5]
    out = step(c)
    assert before.allocations == () and before.next_request_id == 12
    assert out.ledger is not before


def test_repeat_initial_snapshot_is_deterministic_not_publication():
    c = setup()
    assert step(c) == step(c)
    assert c[5].allocations == ()


def test_snapshot_reuse_after_one_alloc_fails_closed():
    c = setup()
    s = step(c)
    assert len(s.ledger.allocations) == 1
    with pytest.raises(ValueError, match='already allocated'):
        allocate(c[0], c[3], c[4], s.ledger)


def test_ledger_immutable():
    c = setup()
    with pytest.raises((FrozenInstanceError, AttributeError)):
        c[5].next_request_id = 999


def test_allocation_immutable():
    s = step(setup())
    with pytest.raises((FrozenInstanceError, AttributeError)):
        s.allocation.emission_request_id = 77


def test_incorrect_cursor_is_detected_during_restore():
    s = step(setup())
    with pytest.raises(ValueError, match='cursor/history mismatch'):
        replace(s.ledger, next_request_id=999)


def test_wrong_first_dynamic_cursor_is_rejected():
    s = step(setup())
    with pytest.raises(ValueError):
        replace(s.ledger, first_dynamic_request_id=11)


def test_noncanonical_restored_history_is_rejected():
    s = step(setup())
    with pytest.raises(ValueError, match='noncanonical emission allocation history'):
        replace(s.ledger, allocations=s.ledger.allocations * 2)


def test_forged_route_identity_is_detected():
    s = step(setup())
    a = s.allocation
    r = a.topology.routes[0]
    forged = replace(r, occurrence=replace(r.occurrence, event_id=900))
    forged_topology = replace(a.topology, routes=(forged,) + a.topology.routes[1:])
    with pytest.raises(ValueError, match='route/request identity mismatch'):
        replace(s.ledger, allocations=(replace(a, topology=forged_topology),))


def test_forged_emission_request_identity_is_detected():
    s = step(setup())
    with pytest.raises(ValueError, match='noncanonical emission allocation history'):
        replace(s.ledger, allocations=(replace(s.allocation, emission_request_id=99),))


def test_forged_route_provenance_is_detected():
    s = step(setup())
    a = s.allocation
    r = a.topology.routes[0]
    forged = replace(r, occurrence=replace(r.occurrence, epoch_id='E1'))
    forged_topology = replace(a.topology, routes=(forged,) + a.topology.routes[1:])
    with pytest.raises(ValueError, match='owned route provenance mismatch'):
        replace(s.ledger, allocations=(replace(a, topology=forged_topology),))


@pytest.mark.parametrize('existing', [(1, 1), (2, 1), (-1,), (True,), (1.5,), [1], ('1',)])
def test_malformed_existing_request_namespace_rejected(existing):
    with pytest.raises(ValueError, match='noncanonical request IDs'):
        setup(existing=existing)


@pytest.mark.parametrize('first', [0, 10, -1, True, 12.0])
def test_cannot_overlap_existing_service_requests(first):
    with pytest.raises(ValueError, match='dynamic identity cursor'):
        setup(first=first)


def test_start_may_equal_max_existing_plus_one():
    assert step(setup(first=12)).allocation.emission_request_id == 12


def test_existing_requests_are_not_ever_reallocated():
    s = step(setup(existing=(0, 1, 1000)))
    assert s.allocation.emission_request_id == 1001
    assert set(s.allocation.route_request_ids).isdisjoint((0, 1, 1000))


def test_wrong_owner_network_rejected():
    c = setup()
    forged_image = replace(c[3], network=replace(c[1], edges=()))
    with pytest.raises(ValueError, match='profile/network/epoch mismatch'):
        allocate(c[0], forged_image, c[4], c[5])


def test_wrong_owner_epoch_rejected():
    c = setup()
    with pytest.raises(ValueError, match='profile/network/epoch mismatch'):
        allocate(c[0], replace(c[3], epoch_id='E1'), c[4], c[5])


def test_wrong_owner_profile_rejected():
    c = setup()
    with pytest.raises(ValueError, match='profile/network/epoch mismatch'):
        allocate(replace(c[0], profile_id='OTHER'), c[3], c[4], c[5])


def test_forged_core_result_rejected_without_spending_id():
    c = setup()
    fake = replace(c[4], candidate_outputs=((3, 99),))
    with pytest.raises(ValueError, match='computed Core preparation mismatch'):
        allocate(c[0], c[3], fake, c[5])
    assert c[5].next_request_id == 12


def test_stale_core_version_rejected_without_spending_id():
    c = setup()
    fake = replace(c[4], base_version=11)
    with pytest.raises(ValueError, match='computed Core preparation mismatch'):
        allocate(c[0], c[3], fake, c[5])


def test_insufficient_output_capacity_rejected_without_spending_id():
    c = setup()
    narrow = replace(c[0], pes=tuple(replace(p, output_slots=1) for p in c[0].pes))
    with pytest.raises(ComputedFanoutCapacityV0):
        allocate(narrow, c[3], c[4], c[5])
    assert c[5].allocations == ()


def test_parallel_identical_edges_allocate_distinct_request_ids():
    c = setup()
    net = replace(c[1], edges=c[1].edges + (c[1].edges[-1],))
    image = replace(c[3], network=net)
    prepared = prepare_core_transition_v0(net, image, node_id='C', timestamp=3, channels=(0,))
    widened = replace(c[0], pes=tuple(replace(p, output_slots=3) for p in c[0].pes))
    state = init(widened, net, c[2], image, existing_request_ids=(0, 11))
    out = allocate(widened, image, prepared, state)
    assert out.allocation.route_request_ids == (13, 14, 15)
    assert out.ledger.next_request_id == 16


def test_event_time_does_not_depend_on_request_cursor():
    s = step(setup(first=200))
    assert s.allocation.topology.event_time == 3
    assert {r.occurrence.delivery_event_time for r in s.allocation.topology.routes} == {5, 6}


def test_no_output_batch_does_not_allocate_any_request_id():
    c = setup()
    no_output = replace(c[4], candidate_outputs=())
    with pytest.raises(ValueError, match='computed Core preparation mismatch'):
        allocate(c[0], c[3], no_output, c[5])
    assert c[5].next_request_id == 12


def test_no_published_storage_created_by_owner():
    s = step(setup())
    assert not hasattr(s.ledger, 'storage')
    assert not hasattr(s.ledger, 'completed_emission_ids')


def test_proposal_records_terminal_channels_without_creating_routed_ids():
    s = step(setup('B', 4))
    assert s.allocation.topology.terminal_outputs[0].timestamp == 4
    assert s.allocation.route_request_ids == ()


def test_allocating_independent_nodes_preserves_prior_provenance():
    c = setup()
    first = step(c)
    second_prepared = prepare_core_transition_v0(c[1], c[3], node_id='A', timestamp=2, channels=(0,))
    second = allocate(c[0], c[3], second_prepared, first.ledger)
    assert second.ledger.allocations[0] == first.allocation
    assert second.ledger.allocations[1] == second.allocation


def test_wrong_initialized_topology_rejected():
    c = setup()
    bad = replace(c[1], edges=(NetworkEdgeV0('A',7,'A',0,1),))
    with pytest.raises(ValueError, match='allocation network/placement mismatch'):
        init(c[0], bad, c[2], c[3])


def test_older_core_snapshot_cannot_allocate_after_newer_version():
    c = setup()
    version1 = commit_core_transition_v0(c[1], c[3], c[4]).state
    prep1 = prepare_core_transition_v0(c[1], version1, node_id='C', timestamp=4, channels=(0,))
    first = allocate(c[0], version1, prep1, c[5])
    # Attempt to allocate from the old version-0 image after the version-1 allocation.
    with pytest.raises(ValueError, match='nonmonotone neuron version'):
        allocate(c[0], c[3], c[4], first.ledger)


def test_restored_nonmonotone_version_history_rejected():
    c = setup()
    first = step(c)
    version1 = commit_core_transition_v0(c[1], c[3], c[4]).state
    prep1 = prepare_core_transition_v0(c[1], version1, node_id='C', timestamp=4, channels=(0,))
    second = allocate(c[0], version1, prep1, first.ledger)
    # Even internally consistent ID ranges cannot hide a reverted Core version.
    a1, a2 = second.ledger.allocations
    bad_second = replace(a2, topology=replace(a2.topology, base_version=0))
    with pytest.raises(ValueError, match='nonmonotone neuronal version'):
        replace(second.ledger, allocations=(a1, bad_second))


def test_missing_node_in_initial_placement_rejected():
    c = setup()
    new_usage = tuple(replace(u, node_ids=tuple(n for n in u.node_ids if n != 'B'))
                      for u in c[2].pe_usage)
    bad_placement = replace(c[2], pe_usage=new_usage)
    with pytest.raises(ValueError, match='placement/network node coverage'):
        init(c[0], c[1], bad_placement, c[3])


def test_duplicate_initial_node_placement_rejected():
    c = setup()
    usages = c[2].pe_usage
    bad_placement = replace(c[2], pe_usage=(replace(usages[0], node_ids=usages[0].node_ids + ('B',)),) + usages[1:])
    with pytest.raises(ValueError, match='placement/network node coverage'):
        init(c[0], c[1], bad_placement, c[3])
