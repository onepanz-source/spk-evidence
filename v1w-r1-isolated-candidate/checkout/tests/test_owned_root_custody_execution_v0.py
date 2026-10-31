"""k24f: one cooperating entrypoint, no direct-owner path in its API."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace

import pytest

from tests import test_owned_root_batch_consumption_v0 as fixtures
from tests.test_owned_root_terminal_commit_v0 import prepared_root
from spk_simulator import owned_root_authority_custody_v0 as custody
from spk_simulator.owned_root_custody_execution_v0 import (
    OwnedRootCustodyExecutionV0 as Runner,
    OwnedRootExecutionViewV0, OwnedRootExecutionStepV0, OwnedRootExecutionRunV0,
)
from spk_simulator.owned_root_authority_custody_v0 import (
    CustodyActionV0 as Action, CustodyPhaseV0 as Phase,
    CustodyPhaseErrorV0, CustodyStaleRevisionV0,
)


def driver(monkeypatch, *, quiet=True, commit_units=1):
    # Actual finite SPK EVENT/P/S service graph and frozen Core. Only the
    # threshold and unit sizes come from the existing k24d test fixture.
    prepared_root(monkeypatch, quiet=quiet, commit_units=commit_units)
    return Runner(fixtures.seeded(confirmed=()))


def until_handoff(driver_instance, *, budget=64):
    for _ in range(budget):
        state = driver_instance.snapshot()
        if state.phase is not Phase.ROOT_OWNED:
            return state
        driver_instance.advance(expected_revision=state.revision)
    pytest.fail('no root handoff within finite test budget')


def until_prepared(driver_instance, *, budget=64):
    # Public integration intentionally does not expose its raw root. Detect
    # readiness in this test using the registry's internal test-only handle.
    for _ in range(budget):
        before = driver_instance._registry.snapshot()
        if before.root.prepared:
            return driver_instance.snapshot()
        driver_instance.advance(expected_revision=before.revision)
    pytest.fail('no Core preparation within finite test budget')


def run_closed(driver_instance, *, budget=100):
    first = driver_instance.snapshot()
    result = driver_instance.run(expected_revision=first.revision, max_actions=budget)
    assert result.completed, 'finite fixture failed to close'
    return result


def test_from_fresh_shared_epoch_does_not_preconfirm(monkeypatch):
    r = driver(monkeypatch)
    state = r.snapshot()
    assert state.phase is Phase.ROOT_OWNED
    assert state.revision == 0
    assert state.commit_receipt is None
    assert all(n.version == 0 for n in state.neurons)
    assert r.trace() == ()
    assert r.audit() == state


def test_public_projection_has_no_owner_or_registry(monkeypatch):
    r = driver(monkeypatch)
    view = r.snapshot()
    assert type(view) is OwnedRootExecutionViewV0
    for forbidden in ('root', 'terminal', 'registry', 'shared', 'service', 'handoff'):
        assert not hasattr(view, forbidden)
    with pytest.raises(FrozenInstanceError):
        view.revision = 99
    assert not hasattr(r, 'advance_root')
    assert not hasattr(r, 'handoff')
    assert not hasattr(r, 'advance_terminal')
    # This is API containment, not protection against Python introspection.
    assert hasattr(r, '_registry')


def test_accepted_root_step_advances_exactly_one_service_tick(monkeypatch):
    r = driver(monkeypatch)
    before = r.snapshot()
    step = r.advance(expected_revision=before.revision)
    assert type(step) is OwnedRootExecutionStepV0
    assert step.action is Action.ROOT_STEP
    assert step.before_revision == 0
    assert step.service_ticks_spent == 1
    assert step.after.revision == 1
    assert step.after.next_service_tick == before.next_service_tick + 1
    assert r.audit() == step.after


def test_finite_real_path_root_handoff_terminal_close(monkeypatch):
    r = driver(monkeypatch)
    result = run_closed(r)
    assert result.completed and type(result) is OwnedRootExecutionRunV0
    assert result.after.phase is Phase.CLOSED
    assert result.after.commit_receipt is not None
    assert result.after.commit_receipt.old_version == 0
    assert result.after.commit_receipt.new_version == 1
    assert result.after.commit_receipt.candidate_outputs == ()
    assert any(n.version == 1 for n in result.after.neurons)
    assert len([n for n in result.after.neurons if n.version == 1]) == 1
    assert result.after == r.audit()
    assert result.after.revision == len(r.trace())


def test_actions_follow_single_owner_and_handoff_costs_zero(monkeypatch):
    r = driver(monkeypatch)
    result = run_closed(r)
    types = tuple(x.action for x in result.steps)
    assert types.count(Action.HANDOFF) == 1
    idx = types.index(Action.HANDOFF)
    assert idx > 0
    assert all(x is Action.ROOT_STEP for x in types[:idx])
    assert all(x is Action.TERMINAL_STEP for x in types[idx + 1:])
    assert len(types[idx + 1:]) >= 1
    assert [x.service_ticks_spent for x in result.steps] == [
        0 if a is Action.HANDOFF else 1 for a in types
    ]
    assert result.after.next_service_tick - result.steps[0].after.next_service_tick == len(types) - 2
    assert result.after.revision == len(types)


def test_handoff_exactly_once_and_without_extra_service(monkeypatch):
    r = driver(monkeypatch)
    before = until_prepared(r)
    step = r.advance(expected_revision=before.revision)
    assert step.action is Action.HANDOFF
    assert step.service_ticks_spent == 0
    assert step.after.phase is Phase.COMMIT_OWNED
    assert step.after.next_service_tick == before.next_service_tick
    assert step.after.revision == before.revision + 1
    assert r.audit() == step.after


def test_old_owner_no_longer_selected_after_transfer(monkeypatch):
    r = driver(monkeypatch)
    handoff = until_handoff(r)
    assert handoff.phase is Phase.COMMIT_OWNED
    step = r.advance(expected_revision=handoff.revision)
    assert step.action is Action.TERMINAL_STEP
    assert step.service_ticks_spent == 1
    assert step.after.revision == handoff.revision + 1
    assert all(x.action is not Action.ROOT_STEP for x in r.trace()[handoff.revision:])


def test_no_second_commit_or_any_advance_after_close(monkeypatch):
    r = driver(monkeypatch)
    closed = run_closed(r).after
    with pytest.raises(CustodyPhaseErrorV0):
        r.advance(expected_revision=closed.revision)
    assert r.audit() == closed


def test_terminal_state_visibility_only_after_confirmation(monkeypatch):
    r = driver(monkeypatch, commit_units=7)
    handoff = until_handoff(r)
    assert handoff.phase is Phase.COMMIT_OWNED
    assert handoff.commit_receipt is None
    assert all(n.version == 0 for n in handoff.neurons)
    intermediate = r.advance(expected_revision=handoff.revision).after
    assert intermediate.phase is Phase.COMMIT_OWNED
    assert intermediate.commit_receipt is None
    assert all(n.version == 0 for n in intermediate.neurons)
    finished = r.run(expected_revision=intermediate.revision, max_actions=60)
    assert finished.completed
    assert finished.after.commit_receipt.new_version == 1


@pytest.mark.parametrize('bad', [-1, True, 0.0, '0', None, [], {}])
def test_noncanonical_advance_revision_rejected_without_effect(monkeypatch, bad):
    r = driver(monkeypatch)
    before = r.snapshot()
    with pytest.raises(TypeError, match='expected_revision'):
        r.advance(expected_revision=bad)
    assert r.snapshot() == before
    assert r.trace() == ()


def test_stale_advance_never_spends_service(monkeypatch):
    r = driver(monkeypatch)
    step = r.advance(expected_revision=0)
    with pytest.raises(CustodyStaleRevisionV0):
        r.advance(expected_revision=0)
    assert r.snapshot() == step.after
    assert len(r.trace()) == 1


def test_stale_run_rejected_before_any_operation(monkeypatch):
    r = driver(monkeypatch)
    r.advance(expected_revision=0)
    before = r.snapshot()
    with pytest.raises(CustodyStaleRevisionV0):
        r.run(expected_revision=0, max_actions=100)
    assert r.snapshot() == before


@pytest.mark.parametrize('bad', [0, -1, True, 3.14, '2', None])
def test_noncanonical_run_budget_rejected_without_effect(monkeypatch, bad):
    r = driver(monkeypatch)
    before = r.snapshot()
    with pytest.raises(TypeError, match='max_actions'):
        r.run(expected_revision=0, max_actions=bad)
    assert r.snapshot() == before


def test_one_action_budget_reports_incomplete_and_resumable(monkeypatch):
    r = driver(monkeypatch)
    first = r.run(expected_revision=0, max_actions=1)
    assert not first.completed
    assert len(first.steps) == 1
    assert first.after.revision == 1
    rest = r.run(expected_revision=1, max_actions=100)
    assert rest.completed
    assert first.after.next_service_tick < rest.after.next_service_tick
    assert len(first.steps) + len(rest.steps) == rest.after.revision


def test_one_action_budget_around_handoff_resumable(monkeypatch):
    r = driver(monkeypatch)
    ready = until_prepared(r)
    result = r.run(expected_revision=ready.revision, max_actions=1)
    assert len(result.steps) == 1
    assert result.steps[0].action is Action.HANDOFF
    assert not result.completed
    assert result.after.next_service_tick == ready.next_service_tick
    after = r.run(expected_revision=result.after.revision, max_actions=60)
    assert after.completed


def test_run_after_closed_is_zero_action_noop(monkeypatch):
    r = driver(monkeypatch)
    done = run_closed(r).after
    repeated = r.run(expected_revision=done.revision, max_actions=10)
    assert repeated.completed
    assert repeated.steps == ()
    assert repeated.after == done
    assert r.audit() == done


def test_run_stale_after_close_does_not_claim_success(monkeypatch):
    r = driver(monkeypatch)
    done = run_closed(r).after
    with pytest.raises(CustodyStaleRevisionV0):
        r.run(expected_revision=done.revision - 1, max_actions=1)
    assert r.snapshot() == done


def test_concurrent_advance_one_revision_single_winner(monkeypatch):
    r = driver(monkeypatch)
    def attempt(_):
        try:
            return r.advance(expected_revision=0)
        except CustodyStaleRevisionV0 as error:
            return error
    with ThreadPoolExecutor(max_workers=3) as pool:
        outcomes = list(pool.map(attempt, range(3)))
    assert sum(type(x) is OwnedRootExecutionStepV0 for x in outcomes) == 1
    assert sum(isinstance(x, CustodyStaleRevisionV0) for x in outcomes) == 2
    assert r.audit().revision == 1


def test_concurrent_runs_single_winner_for_initial_revision(monkeypatch):
    r = driver(monkeypatch)
    def attempt(_):
        try:
            return r.run(expected_revision=0, max_actions=2)
        except CustodyStaleRevisionV0 as error:
            return error
    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(attempt, range(2)))
    assert sum(type(x) is OwnedRootExecutionRunV0 for x in outcomes) == 1
    assert sum(isinstance(x, CustodyStaleRevisionV0) for x in outcomes) == 1
    assert r.audit().revision == 2


def test_fault_in_root_owner_does_not_publish_partial_step(monkeypatch):
    r = driver(monkeypatch)
    before = r.snapshot()
    with monkeypatch.context() as m:
        m.setattr(custody, 'advance_owned_root_single_clock_v0',
                  lambda state: (_ for _ in ()).throw(ValueError('root injected')))
        with pytest.raises(ValueError, match='root injected'):
            r.advance(expected_revision=0)
    assert r.snapshot() == before
    assert r.audit() == before


def test_fault_in_handoff_preserves_root_and_no_fallback(monkeypatch):
    r = driver(monkeypatch)
    ready = until_prepared(r)
    with monkeypatch.context() as m:
        m.setattr(custody, 'handoff_owned_root_terminal_commit_v0',
                  lambda state: (_ for _ in ()).throw(ValueError('handoff injected')))
        with pytest.raises(ValueError, match='handoff injected'):
            r.advance(expected_revision=ready.revision)
    assert r.snapshot() == ready
    assert r.trace()[-1].action is Action.ROOT_STEP
    assert r.audit() == ready


def test_fault_in_terminal_preserves_state_then_retry(monkeypatch):
    r = driver(monkeypatch)
    before = until_handoff(r)
    with monkeypatch.context() as m:
        m.setattr(custody, 'advance_owned_root_terminal_commit_v0',
                  lambda state: (_ for _ in ()).throw(ValueError('terminal injected')))
        with pytest.raises(ValueError, match='terminal injected'):
            r.advance(expected_revision=before.revision)
    assert r.snapshot() == before
    assert r.advance(expected_revision=before.revision).action is Action.TERMINAL_STEP


def test_output_bearing_root_fails_closed_at_handoff(monkeypatch):
    r = driver(monkeypatch, quiet=False)
    ready = until_prepared(r)
    with pytest.raises(ValueError, match='output-bearing'):
        r.advance(expected_revision=ready.revision)
    assert r.snapshot() == ready
    assert all(n.version == 0 for n in ready.neurons)
    assert r.audit() == ready


def test_no_direct_root_or_terminal_advance_in_execution_module():
    from spk_simulator import owned_root_custody_execution_v0 as module
    assert not hasattr(module, 'advance_owned_root_single_clock_v0')
    assert not hasattr(module, 'advance_owned_root_terminal_commit_v0')
    assert not hasattr(module, 'advance_service_quantum_v0')


def test_audit_detects_forged_custody_trace(monkeypatch):
    r = driver(monkeypatch)
    r.advance(expected_revision=0)
    prior = r.trace()
    with monkeypatch.context():
        # Privileged same-process mutation demonstrates audit's integrity
        # check, NOT tamper resistance against arbitrary Python code.
        r._registry._trace = (replace(prior[0], next_service_tick=999),)
        with pytest.raises(ValueError, match='not reconstructible'):
            r.audit()
    r._registry._trace = prior
    assert r.audit() == r.snapshot()


def test_failed_fresh_initialization_rejects_untrusted_confirmations(monkeypatch):
    prepared_root(monkeypatch)
    seeded = fixtures.seeded(confirmed=())
    from spk_simulator.owned_root_single_clock_v0 import initialize_owned_root_single_clock_v0
    first_root = initialize_owned_root_single_clock_v0(seeded)
    # The fresh epoch contract must not accept a caller-supplied prepared owner.
    with pytest.raises(TypeError):
        Runner(first_root)
