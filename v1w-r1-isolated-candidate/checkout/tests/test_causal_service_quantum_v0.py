"""S3.7d/3b2b2d: finite PE service progress, no invented completions."""
from dataclasses import FrozenInstanceError, replace
import pytest

from spk_architecture.access_v0 import AccessIntentKindV0 as Kind
from spk_simulator.causal_service_quantum_v0 import (
    ServiceQuantumStateV0 as State,
    ServiceWorkV0, ServiceFinishedV0, ServiceConfirmedV0,
    advance_service_quantum_v0 as advance,
)
from tests.test_release_aware_scheduler_v0 import (
    machine, req, graph, ingress, arrival, release,
)


def step(requests=None, deps=None, state=None, *, capacity=1, confirm=(),
         grants=(), arrivals=None):
    requests = (req(0),) if requests is None else requests
    deps = graph(*((r.request_id, ()) for r in sorted(requests, key=lambda x: x.request_id))) if deps is None else deps
    return advance(machine(capacity), requests, deps, State() if state is None else state,
                   confirmed_request_ids=confirm,
                   granted_memory_request_ids=grants,
                   ingress=arrivals)


def test_one_request_finishes_service_but_not_causally_confirmed():
    out = step()
    assert out.work_finished_request_ids == (0,)
    assert not out.state.confirmed
    assert out.state.awaiting_confirmation == (ServiceFinishedV0(0, 1),)
    assert out.state.next_service_tick == 1


def test_explicit_confirmation_advances_completion():
    first = step()
    second = step(state=first.state, confirm=(0,))
    assert second.state.confirmed == (ServiceConfirmedV0(0, 1),)
    assert second.status == 'PROGRESSED'
    assert not second.slices


def test_no_early_confirmation():
    with pytest.raises(ValueError, match='non-finished'):
        step(confirm=(0,))


def test_finish_is_not_automatically_confirmation():
    first = step()
    second = step(state=first.state)
    assert second.status == 'WAITING'
    assert second.state.awaiting_confirmation == first.state.awaiting_confirmation


def test_successor_waits_until_confirmation():
    requests = (req(0), req(1))
    deps = graph((0, ()), (1, (0,)))
    first = step(requests, deps)
    assert first.work_finished_request_ids == (0,)
    second = step(requests, deps, first.state)
    assert second.frontier.waiting_dependency_ids == (1,)
    assert not second.slices
    third = step(requests, deps, second.state, confirm=(0,))
    assert third.work_finished_request_ids == (1,)
    assert third.slices[0].service_tick == 2


def test_active_partial_consumes_one_unit_each_tick_with_bandwidth_one():
    requests = (req(0, units=3),)
    s0 = step(requests)
    assert s0.state.partial == (ServiceWorkV0(0, 1),)
    s1 = step(requests, state=s0.state)
    assert s1.state.partial == (ServiceWorkV0(0, 2),)
    s2 = step(requests, state=s1.state)
    assert s2.work_finished_request_ids == (0,)
    assert s2.state.awaiting_confirmation == (ServiceFinishedV0(0, 3),)


def test_capacity_two_spends_two_units_same_cycle():
    out = step((req(0, units=3),), capacity=2)
    assert out.pe_units == (('PE0', 2), ('PE1', 0))
    assert [x.request_id for x in out.slices] == [0, 0]
    assert out.state.partial == (ServiceWorkV0(0, 2),)


def test_same_pe_request_id_order_at_capacity_one():
    out = step((req(2), req(0)))
    assert [x.request_id for x in out.slices] == [0]
    assert out.frontier.ready_request_ids == (0, 2)


def test_independent_pe_progresses_concurrently():
    out = step((req(0), req(1, pe='PE1')))
    assert {x.request_id for x in out.slices} == {0, 1}
    assert out.pe_units == (('PE0', 1), ('PE1', 1))


def test_partial_precedes_new_ready_on_same_pe():
    requests = (req(0), req(1, units=3))
    initial = State(partial=(ServiceWorkV0(1, 1),))
    out = step(requests, state=initial)
    assert out.slices[0].request_id == 1
    assert out.state.partial == (ServiceWorkV0(1, 2),)


def test_memory_gated_offer_needs_explicit_claim():
    requests = (req(0, kind=Kind.EMISSION_RECORD),)
    blocked = step(requests)
    assert blocked.frontier.waiting_memory_ids == (0,)
    assert not blocked.slices
    admitted = step(requests, state=blocked.state, grants=(0,))
    assert admitted.work_finished_request_ids == (0,)


def test_memory_gated_route_needs_explicit_claim():
    requests = (req(0, kind=Kind.ROUTE_ENQUEUE),)
    assert not step(requests).slices
    assert step(requests, grants=(0,)).work_finished_request_ids == (0,)


def test_caller_cannot_grant_completed_request():
    requests = (req(0, kind=Kind.ROUTE_ENQUEUE),)
    first = step(requests, grants=(0,))
    with pytest.raises(ValueError, match='replayed'):
        step(requests, state=first.state, grants=(0,))


def test_release_respected_independently_from_event_time():
    requests = (req(0, event_time=2),)
    binding = ingress((arrival(0, 3),), (release(0, 3, (0,)),))
    state = State()
    for tick in range(3):
        out = step(requests, state=state, arrivals=binding)
        assert not out.slices
        assert out.frontier.waiting_release_ids == (0,)
        state = out.state
    out = step(requests, state=state, arrivals=binding)
    assert out.slices[0].service_tick == 3
    assert out.slices[0].event_time == 2


def test_release_and_dependency_are_both_required():
    requests = (req(0), req(1))
    deps = graph((0, ()), (1, (0,)))
    bound = ingress((arrival(0, 4, consume=1),), (release(0, 0, ()), release(1, 4, (0,))))
    first = step(requests, deps, arrivals=bound)
    second = step(requests, deps, first.state, confirm=(0,), arrivals=bound)
    assert second.frontier.waiting_release_ids == (1,)
    assert not second.slices


def test_tampered_partial_exceeds_units_rejected():
    state = State(partial=(ServiceWorkV0(0, 2),))
    with pytest.raises(ValueError, match='partial service'):
        step((req(0, units=2),), state=state)


def test_unknown_confirmed_rejected():
    state = State(confirmed=(ServiceConfirmedV0(55, 0),))
    with pytest.raises(ValueError, match='unknown finished'):
        step(state=state)


def test_wrong_type_state_rejected():
    with pytest.raises(TypeError, match='state'):
        advance(machine(), (req(0),), graph((0, ())), None)


def test_noncanonical_grants_rejected():
    with pytest.raises(ValueError, match='noncanonical'):
        step((req(0, kind=Kind.ROUTE_ENQUEUE),), grants=(0, 0))


def test_noncanonical_confirm_rejected():
    with pytest.raises(ValueError, match='noncanonical'):
        step(confirm=(1, 0))


def test_missing_dependency_rejected():
    with pytest.raises(ValueError, match='coverage'):
        step((req(0), req(1)), deps=graph((0, ())))


def test_graph_cycle_rejected():
    with pytest.raises(ValueError, match='cyclic'):
        step((req(0), req(1)), deps=graph((0, (1,)), (1, (0,))))


def test_input_request_reordering_deterministic():
    requests = (req(0), req(1, pe='PE1'))
    assert step(requests) == step(requests[::-1])


def test_empty_request_set_idle():
    out = step((), graph())
    assert out.slices == ()
    assert out.status == 'IDLE'


def test_state_immutable():
    with pytest.raises((FrozenInstanceError, AttributeError)):
        State().next_service_tick = 9


def test_repeated_tick_is_not_a_valid_snapshot_replay():
    first = step()
    again = step(state=first.state)
    assert first.service_tick == 0 and again.service_tick == 1


def test_partial_and_finished_overlap_rejected():
    with pytest.raises(ValueError, match='multiple service lifecycle'):
        State(partial=(ServiceWorkV0(0, 1),),
              awaiting_confirmation=(ServiceFinishedV0(0, 0),))


def test_completed_dependency_must_precede_service():
    with pytest.raises(ValueError, match='unfinished'):
        step((req(0), req(1, units=2)), deps=graph((0, ()), (1, (0,))),
             state=State(next_service_tick=1, partial=(ServiceWorkV0(1, 1),)))


def test_bandwidth_never_exceeded_under_contention():
    requests = tuple(req(i, units=3, pe=('PE0' if i % 2 == 0 else 'PE1')) for i in range(10))
    state = State()
    for _ in range(10):
        out = step(requests, state=state, capacity=2)
        assert all(amount <= 2 for _, amount in out.pe_units)
        assert all(len([item for item in out.slices if item.pe_id == pe]) <= 2
                   for pe in ('PE0', 'PE1'))
        state = out.state


def test_finished_cannot_receive_service_twice():
    first = step()
    second = step(state=first.state)
    assert second.slices == ()
    assert second.work_finished_request_ids == ()
