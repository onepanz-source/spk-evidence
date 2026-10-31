"""Integration tests using SPK's established real observed Network fixture."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_simulator.atomic_emission_admission_v0 import (
    AtomicEmissionAdmissionV0, AtomicEmissionCapacityV0, admit_atomic_emissions_v0,
)
from tests.test_service_reservation_gate_v0 import scenario


def source(*, output=3, events=3, same_pe=False, initial=None):
    architecture, manifest, plan, requests, _, _ = scenario(
        output=output, events=events, same_pe=same_pe, initial=initial)
    return architecture, manifest, plan, requests


def check(*args):
    return admit_atomic_emissions_v0(*args)


def test_real_three_route_fanout():
    got = check(*source())
    assert isinstance(got, AtomicEmissionAdmissionV0)
    assert got.routed_occurrence_count == 3
    assert any(len(group.route_request_ids) == 3 for group in got.groups)


def test_parallel_routes_distinct():
    got = check(*source())
    ids = [rid for group in got.groups for rid in group.route_request_ids]
    assert len(ids) == len(set(ids)) == 3


def test_source_output_required_matches_exact_fanout():
    got = check(*source())
    bundle = next(g for g in got.groups if g.route_request_ids)
    assert bundle.required_output_slots == 3
    assert bundle.output_capacity == 3


def test_atomic_fanout_exceeds_source_output_rejected():
    with pytest.raises(AtomicEmissionCapacityV0) as caught:
        check(*source(output=2))
    exc = caught.value
    assert (exc.code, exc.pe_id, exc.required, exc.capacity) == (
        'ATOMIC_EMISSION_FANOUT_EXCEEDS_OUTPUT', 'PE0', 3, 2)


def test_single_slot_rejected():
    with pytest.raises(AtomicEmissionCapacityV0):
        check(*source(output=1))


def test_output_capacity_four_admitted():
    got = check(*source(output=4))
    assert got.routed_occurrence_count == 3


def test_zero_routing_empty_input():
    got = check(*source(initial=()))
    assert got.routed_occurrence_count == 0


def test_same_pe_route_allowed():
    got = check(*source(same_pe=True))
    assert got.routed_occurrence_count == 3


def test_input_objects_remain_unchanged():
    args = source()
    original = repr(args)
    check(*args)
    assert repr(args) == original


def test_output_is_frozen():
    got = check(*source())
    with pytest.raises((FrozenInstanceError, AttributeError)):
        got.groups = ()


def test_deterministic():
    args = source()
    assert check(*args) == check(*args)


def test_wrong_architecture_rejected():
    a, *rest = source()
    with pytest.raises(TypeError):
        check(None, *rest)


def test_wrong_manifest_rejected():
    a, m, p, r = source()
    with pytest.raises(TypeError):
        check(a, None, p, r)


def test_wrong_plan_rejected():
    a, m, _, r = source()
    with pytest.raises(TypeError):
        check(a, m, None, r)


def test_wrong_requests_rejected():
    a, m, p, _ = source()
    with pytest.raises(TypeError):
        check(a, m, p, None)


def test_wrong_profile_rejected():
    a, m, p, r = source()
    with pytest.raises(ValueError, match='profile'):
        check(replace(a, profile_id='DIFFERENT'), m, p, r)


def test_wrong_epoch_rejected():
    a, m, p, r = source()
    with pytest.raises(ValueError, match='epoch'):
        check(a, replace(m, epoch_id='DIFFERENT'), p, r)


def test_missing_request_rejected():
    a, m, p, r = source()
    with pytest.raises(ValueError, match='coverage'):
        check(a, m, p, r[:-1])


def test_missing_route_binding_rejected():
    a, m, p, r = source()
    with pytest.raises(ValueError, match='coverage'):
        check(a, replace(m, routes=m.routes[:-1]), p, r)


def test_corrupt_target_pe_rejected():
    a, m, p, r = source()
    route = m.routes[0]
    bad = replace(route, occurrence=replace(route.occurrence, target_pe_id='PE0'))
    with pytest.raises(ValueError, match='identity'):
        check(a, replace(m, routes=(bad,) + m.routes[1:]), p, r)


def test_wrong_reference_request_identity_rejected():
    a, m, p, r = source()
    with pytest.raises(ValueError, match='mismatch'):
        altered = replace(r[0], principal_id='OK', requester_pe_id='PE1')
        check(a, m, p, (altered,) + r[1:])


def test_duplicate_service_request_rejected():
    a, m, p, r = source()
    with pytest.raises(ValueError, match='coverage'):
        check(a, m, p, r + (r[0],))
