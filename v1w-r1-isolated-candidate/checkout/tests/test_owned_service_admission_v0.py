"""S3.7d/3b2b2k/24a: owner-selected service admission, never physical-effect confirmation."""
from dataclasses import replace

import pytest

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_simulator.causal_service_quantum_v0 import (
    ServiceQuantumStateV0 as State,
    ServiceConfirmedV0,
    ServiceWorkV0,
    advance_service_quantum_v0 as advance,
)
from tests.test_release_aware_scheduler_v0 import machine, req, graph


def run(requests, *, dependencies=None, state=None, owned=None, grants=(), confirm=(), capacity=1):
    if dependencies is None:
        dependencies = graph(*((r.request_id, ()) for r in sorted(requests, key=lambda r: r.request_id)))
    return advance(
        machine(capacity), requests, dependencies, State() if state is None else state,
        owned_service_request_ids=owned,
        granted_memory_request_ids=grants,
        confirmed_request_ids=confirm,
    )


def served(step):
    return tuple(x.request_id for x in step.slices)


def test_no_filter_preserves_legacy_service_selection():
    requests = (req(0), req(1, pe='PE1'))
    assert served(run(requests)) == (0, 1)


def test_explicit_empty_owner_selection_advances_clock_without_work():
    step = run((req(0),), owned=())
    assert not step.slices
    assert step.state.next_service_tick == 1
    assert step.frontier.ready_request_ids == (0,)


def test_only_owned_ready_request_spends_service():
    step = run((req(0), req(1)), owned=(1,))
    assert served(step) == (1,)
    assert step.work_finished_request_ids == (1,)


def test_other_pe_cannot_spend_unowned_bandwidth():
    step = run((req(0), req(1, pe='PE1')), owned=(0,))
    assert served(step) == (0,)
    assert step.pe_units == (('PE0', 1), ('PE1', 0))


def test_owner_can_select_both_pes():
    step = run((req(0), req(1, pe='PE1')), owned=(0, 1))
    assert set(served(step)) == {0, 1}


def test_owned_filter_does_not_confirm_or_finish_other_requests():
    step = run((req(0), req(1)), owned=(0,))
    assert {r.request_id for r in step.state.confirmed} == set()
    assert {r.request_id for r in step.state.awaiting_confirmation} == {0}


def test_partial_request_must_remain_with_same_dispatch_owner():
    initial = State(partial=(ServiceWorkV0(0, 1),))
    with pytest.raises(ValueError, match='in-flight service lacks dispatch ownership'):
        run((req(0, units=3), req(1)), state=initial, owned=(1,))


def test_partial_request_can_resume_under_same_owner():
    initial = State(partial=(ServiceWorkV0(0, 1),))
    step = run((req(0, units=3), req(1)), state=initial, owned=(0,))
    assert served(step) == (0,)
    assert step.state.partial == (ServiceWorkV0(0, 2),)


def test_legacy_partial_can_resume_without_filter():
    initial = State(partial=(ServiceWorkV0(0, 1),))
    step = run((req(0, units=3),), state=initial)
    assert served(step) == (0,)


def test_no_memory_grant_may_target_unowned_request():
    with pytest.raises(ValueError, match='memory grant for unowned'):
        run((req(0, kind=Kind.ROUTE_ENQUEUE),), owned=(), grants=(0,))


def test_owned_route_remains_memory_gated_without_grant():
    step = run((req(0, kind=Kind.ROUTE_ENQUEUE),), owned=(0,))
    assert not step.slices
    assert step.frontier.waiting_memory_ids == (0,)


def test_owned_route_requires_both_grant_and_dispatch_admission():
    step = run((req(0, kind=Kind.ROUTE_ENQUEUE),), owned=(0,), grants=(0,))
    assert step.work_finished_request_ids == (0,)
    assert not step.state.confirmed


def test_completed_work_can_be_confirmed_without_a_new_service_grant():
    first = run((req(0),), owned=(0,))
    second = run((req(0),), state=first.state, owned=(), confirm=(0,))
    assert not second.slices
    assert second.state.confirmed == (ServiceConfirmedV0(0, 1),)


def test_confirmation_unblocks_only_an_owned_successor():
    requests = (req(0), req(1), req(2, pe='PE1'))
    deps = graph((0, ()), (1, (0,)), (2, (0,)))
    first = run(requests, dependencies=deps, owned=(0,))
    second = run(requests, dependencies=deps, state=first.state,
                 owned=(2,), confirm=(0,))
    assert served(second) == (2,)
    assert second.frontier.ready_request_ids == (1, 2)


def test_dispatched_request_still_obeys_causal_dependency():
    requests = (req(0), req(1))
    deps = graph((0, ()), (1, (0,)))
    step = run(requests, dependencies=deps, owned=(1,))
    assert not step.slices


def test_invalid_noncanonical_selection_rejected():
    with pytest.raises(ValueError, match='noncanonical'):
        run((req(0), req(1)), owned=(1, 0))


def test_duplicate_selection_rejected():
    with pytest.raises(ValueError, match='noncanonical'):
        run((req(0),), owned=(0, 0))


def test_non_tuple_selection_rejected():
    with pytest.raises(ValueError, match='noncanonical'):
        run((req(0),), owned=[0])


def test_bool_selection_rejected():
    with pytest.raises(ValueError, match='noncanonical'):
        run((req(0),), owned=(True,))


def test_unknown_dispatch_request_rejected():
    with pytest.raises(ValueError, match='unknown owned service request'):
        run((req(0),), owned=(99,))


def test_selected_requests_still_respect_pe_bandwidth():
    step = run(tuple(req(i, units=3) for i in range(5)), owned=(0,1,2,3,4), capacity=2)
    assert sum(x.units for x in step.slices) == 2
    assert step.pe_units[0] == ('PE0', 2)


def test_selection_reordering_of_requests_is_deterministic():
    requests = (req(0), req(1, pe='PE1'))
    assert run(requests, owned=(0,1)) == run(requests[::-1], owned=(0,1))


def test_dispatch_cannot_use_unsigned_work_finished_as_effect():
    first = run((req(0),), owned=(0,))
    after = run((req(0),), state=first.state, owned=())
    assert not after.state.confirmed
    assert after.state.awaiting_confirmation == first.state.awaiting_confirmation
