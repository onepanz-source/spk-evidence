"""k24e: process-local custody admission, CAS, handoff and trace replay."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace

import pytest

from spk_simulator.owned_root_single_clock_v0 import (
    initialize_owned_root_single_clock_v0,
    advance_owned_root_single_clock_v0,
)
from spk_simulator.owned_root_authority_custody_v0 import (
    CustodyActionV0 as Action,
    CustodyPhaseV0 as Phase,
    CustodyPhaseErrorV0,
    CustodyStaleRevisionV0,
    OwnedRootAuthorityRegistryV0,
    replay_custody_trace_v0,
)
from tests.test_owned_root_terminal_commit_v0 import prepared_root, neuron
from tests import test_owned_root_batch_consumption_v0 as root_fixtures
from spk_simulator import owned_root_authority_custody_v0 as custody_module


def installed(monkeypatch, *, quiet=True, commit_units=1):
    root = prepared_root(monkeypatch, quiet=quiet, commit_units=commit_units)
    registry = OwnedRootAuthorityRegistryV0()
    view = registry.install(root)
    return registry, view


def closed(registry, view, *, limit=30):
    for _ in range(limit):
        if view.phase is Phase.CLOSED:
            return view
        view = registry.advance_terminal(expected_revision=view.revision).view
    pytest.fail('terminal owner did not finish')


def test_install_historical_root_and_empty_replay(monkeypatch):
    reg, view = installed(monkeypatch)
    assert view.phase is Phase.ROOT_OWNED
    assert view.revision == 0 and view.terminal is None and view.trace == ()
    assert reg.verify() == view
    assert replay_custody_trace_v0(view.root, ()) == view


def test_cannot_install_twice_even_same_root_or_equal_clone(monkeypatch):
    reg, view = installed(monkeypatch)
    with pytest.raises(CustodyPhaseErrorV0, match='already consumed'):
        reg.install(view.root)
    with pytest.raises(CustodyPhaseErrorV0, match='already consumed'):
        reg.install(replace(view.root))
    assert reg.snapshot() == view


def test_cannot_access_uninstalled_registry(monkeypatch):
    reg = OwnedRootAuthorityRegistryV0()
    with pytest.raises(CustodyPhaseErrorV0, match='no custody installation'):
        reg.snapshot()
    with pytest.raises(CustodyPhaseErrorV0):
        reg.verify()
    with pytest.raises(CustodyPhaseErrorV0):
        reg.advance_root(expected_revision=0)
    with pytest.raises(CustodyPhaseErrorV0):
        reg.handoff(expected_revision=0)
    with pytest.raises(CustodyPhaseErrorV0):
        reg.advance_terminal(expected_revision=0)
    with pytest.raises(TypeError):
        reg.install(None)


@pytest.mark.parametrize('bad', [-1, True, 0.0, '0', None])
def test_noncanonical_revision_rejected_without_mutation(monkeypatch, bad):
    reg, old = installed(monkeypatch)
    with pytest.raises(TypeError, match='expected_revision'):
        reg.handoff(expected_revision=bad)
    assert reg.snapshot() == old


def test_handoff_does_not_advance_service_clock(monkeypatch):
    reg, start = installed(monkeypatch)
    after = reg.handoff(expected_revision=0)
    assert after.phase is Phase.COMMIT_OWNED
    assert after.revision == 1
    assert after.root is start.root
    assert after.terminal.handoff is start.root
    assert after.terminal.image == start.root.image
    assert after.next_service_tick == start.next_service_tick
    assert after.trace[-1].action is Action.HANDOFF
    assert reg.verify() == after


def test_terminal_quantum_and_final_close(monkeypatch):
    reg, start = installed(monkeypatch, commit_units=7)
    transfer = reg.handoff(expected_revision=start.revision)
    terminal = closed(reg, transfer)
    assert terminal.phase is Phase.CLOSED
    assert terminal.revision == len(terminal.trace)
    assert terminal.terminal.committed
    assert neuron(terminal.root).version == 0
    assert neuron(terminal.terminal).version == 1
    assert terminal.trace[0].action is Action.HANDOFF
    assert all(e.action is Action.TERMINAL_STEP for e in terminal.trace[1:])
    assert terminal.trace[-1].phase is Phase.CLOSED
    assert terminal.next_service_tick > transfer.next_service_tick
    assert reg.verify() == terminal


def test_duplicate_handoff_rejected_without_effect(monkeypatch):
    reg, before = installed(monkeypatch)
    after = reg.handoff(expected_revision=before.revision)
    with pytest.raises(CustodyStaleRevisionV0):
        reg.handoff(expected_revision=before.revision)
    with pytest.raises(CustodyPhaseErrorV0):
        reg.handoff(expected_revision=after.revision)
    assert reg.snapshot() == after


def test_root_service_forbidden_after_transfer_even_with_current_revision(monkeypatch):
    reg, before = installed(monkeypatch)
    after = reg.handoff(expected_revision=before.revision)
    with pytest.raises(CustodyPhaseErrorV0):
        reg.advance_root(expected_revision=after.revision)
    assert reg.snapshot() == after


def test_terminal_service_forbidden_before_transfer(monkeypatch):
    reg, view = installed(monkeypatch)
    with pytest.raises(CustodyPhaseErrorV0):
        reg.advance_terminal(expected_revision=view.revision)
    assert reg.snapshot() == view


def test_duplicate_terminal_step_rejected_without_double_spend(monkeypatch):
    reg, start = installed(monkeypatch, commit_units=7)
    after = reg.handoff(expected_revision=0)
    step = reg.advance_terminal(expected_revision=after.revision)
    with pytest.raises(CustodyStaleRevisionV0):
        reg.advance_terminal(expected_revision=after.revision)
    assert reg.snapshot() == step.view
    assert reg.verify() == step.view


def test_closed_registry_refuses_any_more_operations(monkeypatch):
    reg, _ = installed(monkeypatch)
    end = closed(reg, reg.handoff(expected_revision=0))
    for operation in (reg.advance_root, reg.handoff, reg.advance_terminal):
        with pytest.raises(CustodyPhaseErrorV0):
            operation(expected_revision=end.revision)
    with pytest.raises(CustodyPhaseErrorV0):
        reg.install(end.root)
    assert reg.verify() == end


def test_failure_to_handoff_unprepared_root_preserves_custody(monkeypatch):
    # A fresh k24b owner does not yet possess the physical Core preparation.
    prepared_root(monkeypatch)
    fresh = initialize_owned_root_single_clock_v0(root_fixtures.seeded(confirmed=()))
    reg = OwnedRootAuthorityRegistryV0()
    before = reg.install(fresh)
    with pytest.raises(ValueError):
        reg.handoff(expected_revision=0)
    assert reg.snapshot() == before
    assert reg.verify() == before


def test_output_bearing_handoff_fails_without_consuming_authority(monkeypatch):
    reg, before = installed(monkeypatch, quiet=False)
    with pytest.raises(ValueError, match='output-bearing'):
        reg.handoff(expected_revision=0)
    assert reg.snapshot() == before


def test_root_service_advances_using_exact_k24b_api(monkeypatch):
    prepared_root(monkeypatch)
    fresh = initialize_owned_root_single_clock_v0(root_fixtures.seeded(confirmed=()))
    reg = OwnedRootAuthorityRegistryV0()
    start = reg.install(fresh)
    expected = advance_owned_root_single_clock_v0(fresh)
    step = reg.advance_root(expected_revision=start.revision)
    assert step.root_step == expected
    assert step.terminal_step is None
    assert step.view.root == expected.state
    assert step.view.next_service_tick == start.next_service_tick + 1
    assert step.view.trace == (replace(step.view.trace[0]),)
    assert reg.verify() == step.view


def test_full_installation_to_terminal_commit_using_one_registry(monkeypatch):
    # Establish quiet Core on seeded() and exercise every k24b root boundary
    # through the custody API before transferring.
    prepared_root(monkeypatch)
    fresh = initialize_owned_root_single_clock_v0(root_fixtures.seeded(confirmed=()))
    reg = OwnedRootAuthorityRegistryV0()
    view = reg.install(fresh)
    for _ in range(50):
        if view.root.prepared:
            break
        view = reg.advance_root(expected_revision=view.revision).view
    assert view.root.prepared
    start_tick = view.next_service_tick
    before = view
    view = reg.handoff(expected_revision=view.revision)
    assert view.next_service_tick == start_tick
    assert before.root == view.root
    end = closed(reg, view)
    assert end.phase is Phase.CLOSED
    assert end.terminal.committed
    assert neuron(end.root).version == 0
    assert neuron(end.terminal).version == 1
    assert reg.verify() == end


def test_stale_root_revision_refuses_service(monkeypatch):
    prepared_root(monkeypatch)
    fresh = initialize_owned_root_single_clock_v0(root_fixtures.seeded(confirmed=()))
    reg = OwnedRootAuthorityRegistryV0()
    reg.install(fresh)
    after = reg.advance_root(expected_revision=0).view
    with pytest.raises(CustodyStaleRevisionV0):
        reg.advance_root(expected_revision=0)
    assert reg.snapshot() == after


def test_concurrent_handoff_same_revision_has_exactly_one_winner(monkeypatch):
    reg, before = installed(monkeypatch)

    def race(_):
        try:
            return reg.handoff(expected_revision=before.revision)
        except ValueError as error:
            return error

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(race, (0, 1)))
    assert sum(x.phase is Phase.COMMIT_OWNED for x in outcomes if not isinstance(x, Exception)) == 1
    assert sum(isinstance(x, CustodyStaleRevisionV0) for x in outcomes) == 1
    assert len(reg.snapshot().trace) == 1
    assert reg.verify() == reg.snapshot()


def test_trace_forged_revision_rejected(monkeypatch):
    reg, before = installed(monkeypatch)
    end = reg.handoff(expected_revision=0)
    fake = (replace(end.trace[0], revision=2),)
    with pytest.raises(ValueError, match='revision'):
        replay_custody_trace_v0(before.root, fake)


def test_trace_forged_clock_rejected(monkeypatch):
    reg, before = installed(monkeypatch)
    end = reg.handoff(expected_revision=0)
    fake = (replace(end.trace[0], next_service_tick=end.next_service_tick + 1),)
    with pytest.raises(ValueError, match='not reconstructible'):
        replay_custody_trace_v0(before.root, fake)


def test_trace_forged_phase_rejected(monkeypatch):
    reg, before = installed(monkeypatch)
    end = reg.handoff(expected_revision=0)
    fake = (replace(end.trace[0], phase=Phase.CLOSED),)
    with pytest.raises(ValueError, match='not reconstructible'):
        replay_custody_trace_v0(before.root, fake)


def test_trace_reordered_and_duplicated_handoff_rejected(monkeypatch):
    reg, before = installed(monkeypatch)
    end = closed(reg, reg.handoff(expected_revision=0))
    with pytest.raises((ValueError, CustodyPhaseErrorV0)):
        replay_custody_trace_v0(before.root, tuple(reversed(end.trace)))
    with pytest.raises((ValueError, CustodyPhaseErrorV0)):
        replay_custody_trace_v0(before.root, end.trace[:1] + end.trace[:1])


def test_trace_missing_terminal_step_does_not_support_closed_claim(monkeypatch):
    reg, before = installed(monkeypatch)
    end = closed(reg, reg.handoff(expected_revision=0))
    truncated = replay_custody_trace_v0(before.root, end.trace[:-1])
    assert truncated.phase is Phase.COMMIT_OWNED
    assert truncated != end
    assert truncated.terminal.image != end.terminal.image


def test_trace_rejects_untyped_action_or_trace(monkeypatch):
    reg, before = installed(monkeypatch)
    end = reg.handoff(expected_revision=0)
    with pytest.raises(TypeError, match='tuple'):
        replay_custody_trace_v0(before.root, list(end.trace))
    with pytest.raises(TypeError, match='noncanonical'):
        replay_custody_trace_v0(before.root, (replace(end.trace[0], action='HANDOFF'),))
    with pytest.raises(TypeError):
        replay_custody_trace_v0(None, ())


def test_snapshot_is_immutable_but_not_a_revoke_capability(monkeypatch):
    reg, before = installed(monkeypatch)
    after = reg.handoff(expected_revision=0)
    with pytest.raises(FrozenInstanceError):
        after.revision = 7
    # Direct imports of pure k24b APIs remain possible. This test deliberately
    # documents that custody requires exclusive orchestration, not merely a flag.
    old_root_is_still_accessible = before.root is after.root
    assert old_root_is_still_accessible
    assert reg.snapshot() == after


def test_separate_registry_instances_remain_an_explicit_fork_risk(monkeypatch):
    root = prepared_root(monkeypatch)
    left, right = OwnedRootAuthorityRegistryV0(), OwnedRootAuthorityRegistryV0()
    left.install(root)
    right.install(root)
    assert left.handoff(expected_revision=0).terminal == right.handoff(expected_revision=0).terminal
    assert left is not right


def test_injected_handoff_failure_is_atomic(monkeypatch):
    reg, before = installed(monkeypatch)

    def fail(_):
        raise ValueError('injected handoff failure')

    with monkeypatch.context() as patch:
        patch.setattr(custody_module, 'handoff_owned_root_terminal_commit_v0', fail)
        with pytest.raises(ValueError, match='injected'):
            reg.handoff(expected_revision=before.revision)
    assert reg.snapshot() == before
    assert reg.verify() == before


def test_injected_terminal_failure_is_atomic(monkeypatch):
    reg, start = installed(monkeypatch)
    before = reg.handoff(expected_revision=start.revision)

    def fail(_):
        raise ValueError('injected terminal failure')

    with monkeypatch.context() as patch:
        patch.setattr(custody_module, 'advance_owned_root_terminal_commit_v0', fail)
        with pytest.raises(ValueError, match='injected'):
            reg.advance_terminal(expected_revision=before.revision)
    assert reg.snapshot() == before
    assert reg.verify() == before


def test_injected_root_failure_is_atomic(monkeypatch):
    prepared_root(monkeypatch)
    fresh = initialize_owned_root_single_clock_v0(root_fixtures.seeded(confirmed=()))
    reg = OwnedRootAuthorityRegistryV0()
    before = reg.install(fresh)

    def fail(_):
        raise ValueError('injected root failure')

    with monkeypatch.context() as patch:
        patch.setattr(custody_module, 'advance_owned_root_single_clock_v0', fail)
        with pytest.raises(ValueError, match='injected'):
            reg.advance_root(expected_revision=before.revision)
    assert reg.snapshot() == before
    assert reg.verify() == before
