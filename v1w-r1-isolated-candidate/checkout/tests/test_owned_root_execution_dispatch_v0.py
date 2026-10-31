"""k24g dispatch contract against actual k24b/k24d/k24e/k24f finite fixtures."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError
import inspect
import pytest

from tests import test_owned_root_batch_consumption_v0 as fixtures
from tests.test_owned_root_terminal_commit_v0 import prepared_root
from spk_simulator import owned_root_authority_custody_v0 as custody
from spk_simulator.owned_root_authority_custody_v0 import (
    CustodyActionV0 as Action, CustodyPhaseV0 as Phase,
    CustodyPhaseErrorV0, CustodyStaleRevisionV0,
)
from spk_simulator.owned_root_execution_dispatch_v0 import (
    DispatchOperationV0 as Op, DispatchRequestV0 as Request,
    DispatchResultV0 as Reply, OwnedRootExecutionDispatcherV0 as Dispatcher,
    DispatchAdmissionErrorV0, DispatchEpochMismatchV0, DispatchNotInstalledV0,
)

EPOCH = 'E0'


def shared(monkeypatch, *, quiet=True, commit_units=1):
    prepared_root(monkeypatch, quiet=quiet, commit_units=commit_units)
    return fixtures.seeded(confirmed=())


def host(monkeypatch, *, quiet=True, commit_units=1):
    entry = shared(monkeypatch, quiet=quiet, commit_units=commit_units)
    d = Dispatcher()
    assert d.install(entry, epoch_id=entry.seal.epoch_id).revision == 0
    return d


def command(op, revision=None, max_actions=None, epoch_id=EPOCH):
    return Request(epoch_id, op, revision, max_actions)


def view(d):
    return d.dispatch(command(Op.SNAPSHOT)).view


def advance(d):
    s = view(d)
    return d.dispatch(command(Op.ADVANCE, s.revision))


def finish(d, bound=100):
    s = view(d)
    answer = d.dispatch(command(Op.RUN, s.revision, bound))
    assert answer.run.completed, 'finite fixture did not close'
    return answer


def until_phase(d, phase, bound=80):
    for _ in range(bound):
        s = view(d)
        if s.phase is phase:
            return s
        advance(d)
    pytest.fail('finite fixture did not reach requested phase')


def test_no_epoch_installed_rejects_observe_and_mutate():
    d = Dispatcher()
    with pytest.raises(DispatchNotInstalledV0):
        d.dispatch(command(Op.SNAPSHOT))
    with pytest.raises(DispatchNotInstalledV0):
        d.dispatch(command(Op.ADVANCE, 0))


def test_install_fresh_sealed_epoch_only(monkeypatch):
    d = host(monkeypatch)
    s = view(d)
    assert s.phase is Phase.ROOT_OWNED
    assert s.revision == 0 and s.commit_receipt is None
    assert all(n.version == 0 for n in s.neurons)


def test_install_rejects_wrong_shared_type():
    d = Dispatcher()
    with pytest.raises(TypeError):
        d.install(None, epoch_id=EPOCH)
    with pytest.raises(DispatchNotInstalledV0):
        d.dispatch(command(Op.SNAPSHOT))


def test_install_rejects_epoch_identity_mismatch(monkeypatch):
    d = Dispatcher()
    s = shared(monkeypatch)
    with pytest.raises(DispatchEpochMismatchV0):
        d.install(s, epoch_id='other')
    assert d.install(s, epoch_id=EPOCH).revision == 0


@pytest.mark.parametrize('epoch', ['', 7, None, True])
def test_install_noncanonical_epoch_never_binds(monkeypatch, epoch):
    d = Dispatcher()
    with pytest.raises(TypeError):
        d.install(shared(monkeypatch), epoch_id=epoch)
    with pytest.raises(DispatchNotInstalledV0):
        d.dispatch(command(Op.SNAPSHOT))


def test_no_second_install_even_same_snapshot(monkeypatch):
    d = host(monkeypatch)
    s = shared(monkeypatch)
    before = view(d)
    with pytest.raises(DispatchAdmissionErrorV0):
        d.install(s, epoch_id=EPOCH)
    assert view(d) == before


def test_no_second_install_after_close(monkeypatch):
    d = host(monkeypatch)
    closed = finish(d).view
    with pytest.raises(DispatchAdmissionErrorV0):
        d.install(shared(monkeypatch), epoch_id=EPOCH)
    assert view(d) == closed


def test_wrong_dispatch_epoch_does_not_consume_service(monkeypatch):
    d = host(monkeypatch)
    before = view(d)
    with pytest.raises(DispatchEpochMismatchV0):
        d.dispatch(command(Op.RUN, 0, 100, epoch_id='E1'))
    assert view(d) == before
    assert d.dispatch(command(Op.TRACE)).trace == ()


def test_replies_never_expose_owner_or_registry(monkeypatch):
    d = host(monkeypatch)
    r = d.dispatch(command(Op.SNAPSHOT))
    assert type(r) is Reply
    for obj in (r, r.view):
        for name in ('root', 'terminal', 'registry', 'shared', 'service', 'driver', 'runner'):
            assert not hasattr(obj, name)
    assert not hasattr(d, 'advance_root')
    assert not hasattr(d, 'advance_terminal')
    assert not hasattr(d, 'handoff')
    with pytest.raises(FrozenInstanceError):
        r.epoch_id = 'another'


def test_snapshot_is_read_only(monkeypatch):
    d = host(monkeypatch)
    a = d.dispatch(command(Op.SNAPSHOT))
    b = d.dispatch(command(Op.SNAPSHOT))
    assert a == b and a.step is a.run is a.trace is None
    assert d.dispatch(command(Op.TRACE)).trace == ()


def test_audit_is_replay_from_initial_snapshot(monkeypatch):
    d = host(monkeypatch)
    advance(d)
    assert d.dispatch(command(Op.AUDIT)).view == view(d)


def test_trace_contains_actual_custody_records(monkeypatch):
    d = host(monkeypatch)
    advance(d)
    reply = d.dispatch(command(Op.TRACE))
    assert len(reply.trace) == 1
    assert reply.trace[0].action is Action.ROOT_STEP
    assert reply.view == view(d)


def test_root_advance_uses_existing_single_service_time(monkeypatch):
    d = host(monkeypatch)
    old = view(d)
    r = d.dispatch(command(Op.ADVANCE, 0))
    assert r.step.action is Action.ROOT_STEP
    assert r.step.service_ticks_spent == 1
    assert r.view.next_service_tick == old.next_service_tick + 1
    assert r.view.revision == 1
    assert r.run is r.trace is None


def test_finite_path_root_handoff_terminal_commit_close(monkeypatch):
    d = host(monkeypatch)
    outcome = finish(d)
    result = outcome.run
    steps = result.steps
    actions = [x.action for x in steps]
    assert actions.count(Action.HANDOFF) == 1
    i = actions.index(Action.HANDOFF)
    assert i > 0
    assert all(x is Action.ROOT_STEP for x in actions[:i])
    assert all(x is Action.TERMINAL_STEP for x in actions[i+1:])
    assert [x.service_ticks_spent for x in steps] == [
        0 if x is Action.HANDOFF else 1 for x in actions
    ]
    assert result.after.phase is Phase.CLOSED
    receipt = result.after.commit_receipt
    assert receipt is not None and receipt.old_version == 0
    assert receipt.new_version == 1 and receipt.candidate_outputs == ()
    assert len([n for n in result.after.neurons if n.version == 1]) == 1
    assert d.dispatch(command(Op.AUDIT)).view == result.after


def test_handoff_spends_no_service_and_terminal_only_after(monkeypatch):
    d = host(monkeypatch)
    before = until_phase(d, Phase.COMMIT_OWNED)
    records = d.dispatch(command(Op.TRACE)).trace
    assert records[-1].action is Action.HANDOFF
    assert records[-1].next_service_tick == records[-2].next_service_tick
    after = advance(d)
    assert after.step.action is Action.TERMINAL_STEP
    assert after.view.next_service_tick == before.next_service_tick + 1


def test_version_hidden_until_terminal_confirmation(monkeypatch):
    d = host(monkeypatch, commit_units=7)
    a = until_phase(d, Phase.COMMIT_OWNED)
    assert a.commit_receipt is None
    assert all(x.version == 0 for x in a.neurons)
    b = advance(d).view
    assert b.commit_receipt is None
    assert all(x.version == 0 for x in b.neurons)
    assert finish(d).view.commit_receipt.new_version == 1


def test_bounded_run_can_resume_without_forged_completion(monkeypatch):
    d = host(monkeypatch)
    first = d.dispatch(command(Op.RUN, 0, 1))
    assert not first.run.completed
    assert first.view.revision == 1
    closed = d.dispatch(command(Op.RUN, first.view.revision, 100))
    assert closed.run.completed
    assert closed.view == view(d)


def test_duplicate_revision_advance_rejected(monkeypatch):
    d = host(monkeypatch)
    advance(d)
    before = view(d)
    with pytest.raises(CustodyStaleRevisionV0):
        d.dispatch(command(Op.ADVANCE, 0))
    assert view(d) == before


def test_duplicate_revision_run_rejected(monkeypatch):
    d = host(monkeypatch)
    advance(d)
    before = view(d)
    with pytest.raises(CustodyStaleRevisionV0):
        d.dispatch(command(Op.RUN, 0, 10))
    assert view(d) == before


def test_closed_rejects_advance_and_run(monkeypatch):
    d = host(monkeypatch)
    end = finish(d).view
    for req in (command(Op.ADVANCE, end.revision), command(Op.RUN, end.revision, 1)):
        with pytest.raises(CustodyPhaseErrorV0, match='closed'):
            d.dispatch(req)
    assert view(d) == end


def test_stale_after_closed_rejected_as_stale(monkeypatch):
    d = host(monkeypatch)
    end = finish(d).view
    with pytest.raises(CustodyStaleRevisionV0):
        d.dispatch(command(Op.RUN, end.revision - 1, 1))
    assert view(d) == end


def test_closed_still_observable_and_auditable(monkeypatch):
    d = host(monkeypatch)
    end = finish(d).view
    assert d.dispatch(command(Op.SNAPSHOT)).view == end
    assert d.dispatch(command(Op.AUDIT)).view == end
    assert len(d.dispatch(command(Op.TRACE)).trace) == end.revision


@pytest.mark.parametrize('args', [
    ('', Op.SNAPSHOT, None, None),
    (None, Op.SNAPSHOT, None, None),
    (1, Op.SNAPSHOT, None, None),
    (EPOCH, 'ADVANCE', 0, None),
    (EPOCH, None, None, None),
    (EPOCH, Op.ADVANCE, True, None),
    (EPOCH, Op.ADVANCE, -1, None),
    (EPOCH, Op.RUN, 0, 0),
    (EPOCH, Op.RUN, 0, True),
    (EPOCH, Op.RUN, 0, 1.0),
    (EPOCH, Op.RUN, None, 1),
    (EPOCH, Op.SNAPSHOT, 0, None),
    (EPOCH, Op.AUDIT, None, 1),
    (EPOCH, Op.TRACE, None, -1),
    (EPOCH, Op.ADVANCE, 0, 1),
])
def test_request_shapes_reject_noncanonical_values(args):
    with pytest.raises(TypeError):
        Request(*args)


def test_nonrequest_refused_at_boundary(monkeypatch):
    d = host(monkeypatch)
    with pytest.raises(TypeError):
        d.dispatch({'operation': 'RUN', 'max_actions': 100})
    assert view(d).revision == 0


def test_forged_request_revalidated_at_dispatch(monkeypatch):
    d = host(monkeypatch)
    forged = object.__new__(Request)
    object.__setattr__(forged, 'epoch_id', EPOCH)
    object.__setattr__(forged, 'operation', Op.RUN)
    object.__setattr__(forged, 'expected_revision', 0)
    object.__setattr__(forged, 'max_actions', -5)
    with pytest.raises(TypeError):
        d.dispatch(forged)
    assert view(d).revision == 0


def test_failed_install_keeps_dispatcher_unbound(monkeypatch):
    d = Dispatcher()
    s = shared(monkeypatch)
    from spk_simulator import owned_root_execution_dispatch_v0 as module
    with monkeypatch.context() as m:
        m.setattr(module, 'OwnedRootCustodyExecutionV0',
                  lambda state: (_ for _ in ()).throw(ValueError('forced init failure')))
        with pytest.raises(ValueError, match='forced init failure'):
            d.install(s, epoch_id=EPOCH)
    assert d.install(s, epoch_id=EPOCH).revision == 0


def test_failed_owner_progress_does_not_publish_dispatch_result(monkeypatch):
    d = host(monkeypatch)
    before = view(d)
    with monkeypatch.context() as m:
        m.setattr(custody, 'advance_owned_root_single_clock_v0',
                  lambda state: (_ for _ in ()).throw(ValueError('forced owner failure')))
        with pytest.raises(ValueError, match='forced owner failure'):
            d.dispatch(command(Op.ADVANCE, 0))
    assert view(d) == before
    assert d.dispatch(command(Op.AUDIT)).view == before


def test_handoff_failure_never_falls_back_to_root(monkeypatch):
    d = host(monkeypatch, quiet=False)
    # An output-bearing Core preparation is incompatible with k24d.
    for _ in range(80):
        from spk_simulator.owned_root_execution_dispatch_v0 import OwnedRootExecutionDispatcherV0
        raw = d._runner._registry.snapshot()
        if raw.root.prepared:
            break
        advance(d)
    else:
        pytest.fail('no Core preparation')
    before = view(d)
    with pytest.raises(ValueError, match='output-bearing'):
        advance(d)
    assert view(d) == before
    assert d.dispatch(command(Op.AUDIT)).view == before


def test_terminal_failure_preserves_accepted_prefix(monkeypatch):
    d = host(monkeypatch)
    before = until_phase(d, Phase.COMMIT_OWNED)
    with monkeypatch.context() as m:
        m.setattr(custody, 'advance_owned_root_terminal_commit_v0',
                  lambda state: (_ for _ in ()).throw(ValueError('terminal failure')))
        with pytest.raises(ValueError, match='terminal failure'):
            advance(d)
    assert view(d) == before
    assert advance(d).step.action is Action.TERMINAL_STEP


def test_concurrent_install_single_winner(monkeypatch):
    d = Dispatcher()
    s = shared(monkeypatch)
    def attempt(_):
        try:
            return d.install(s, epoch_id=EPOCH)
        except DispatchAdmissionErrorV0 as err:
            return err
    with ThreadPoolExecutor(max_workers=3) as pool:
        answers = list(pool.map(attempt, range(3)))
    assert len([x for x in answers if not isinstance(x, Exception)]) == 1
    assert len([x for x in answers if isinstance(x, DispatchAdmissionErrorV0)]) == 2
    assert view(d).revision == 0


def test_concurrent_advance_one_revision_one_winner(monkeypatch):
    d = host(monkeypatch)
    def attempt(_):
        try:
            return d.dispatch(command(Op.ADVANCE, 0))
        except CustodyStaleRevisionV0 as err:
            return err
    with ThreadPoolExecutor(max_workers=3) as pool:
        answers = list(pool.map(attempt, range(3)))
    assert sum(type(x) is Reply for x in answers) == 1
    assert sum(isinstance(x, CustodyStaleRevisionV0) for x in answers) == 2
    assert view(d).revision == 1


def test_concurrent_run_one_revision_one_winner(monkeypatch):
    d = host(monkeypatch)
    def attempt(_):
        try:
            return d.dispatch(command(Op.RUN, 0, 2))
        except CustodyStaleRevisionV0 as err:
            return err
    with ThreadPoolExecutor(max_workers=2) as pool:
        answers = list(pool.map(attempt, range(2)))
    assert sum(type(x) is Reply for x in answers) == 1
    assert sum(isinstance(x, CustodyStaleRevisionV0) for x in answers) == 1
    assert view(d).revision == 2


def test_dispatch_module_never_imports_raw_owner_progress():
    from spk_simulator import owned_root_execution_dispatch_v0 as module
    src = inspect.getsource(module)
    for name in ('advance_owned_root_single_clock_v0',
                 'advance_owned_root_terminal_commit_v0',
                 'advance_service_quantum_v0'):
        assert name not in src


def test_multiple_dispatcher_instances_are_not_globally_fenced(monkeypatch):
    # Deliberate limitation: identical trusted epoch can be installed twice
    # in two independent process-local dispatchers. This is NOT global safety.
    entry = shared(monkeypatch)
    a, b = Dispatcher(), Dispatcher()
    a.install(entry, epoch_id=EPOCH)
    b.install(entry, epoch_id=EPOCH)
    assert finish(a).view == finish(b).view
