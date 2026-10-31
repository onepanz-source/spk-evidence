"""SPK 24j: in-process host integration (real SPK 24g finite fixtures)."""

from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from unittest.mock import patch

import pytest

from tests.test_owned_root_execution_dispatch_v0 import shared as fixture_shared
from spk_simulator.owned_root_authority_custody_v0 import (
    CustodyActionV0 as Action, CustodyPhaseV0 as Phase,
    CustodyStaleRevisionV0,
)
from spk_simulator.owned_root_execution_dispatch_v0 import (
    DispatchEpochMismatchV0,
    DispatchOperationV0 as Op, DispatchRequestV0 as Request,
)
from spk_simulator.application_runtime_host_v0 import (
    ApplicationRuntimeHostV0 as Host, HostAdmissionErrorV0,
    HostExecutionErrorV0, HostLifecycleErrorV0, HostPhaseV0,
)


def new_host(monkeypatch, *, quiet=True, commit_units=1):
    epoch = fixture_shared(monkeypatch, quiet=quiet, commit_units=commit_units)
    calls = []
    def provider():
        calls.append(True)
        return epoch
    return Host(provider=provider, provider_id='TEST-FIXTURE-NOT-AUTH'), calls


def admitted(monkeypatch, **kw):
    h, calls = new_host(monkeypatch, **kw)
    state = h.admit(epoch_id='E0')
    assert state.phase is HostPhaseV0.ACTIVE and len(calls) == 1
    return h


def cmd(op, rev=None, budget=None, epoch='E0'):
    return Request(epoch, op, rev, budget)


def view(host):
    return host.dispatch(cmd(Op.SNAPSHOT)).view


def finish(host):
    v = view(host)
    r = host.dispatch(cmd(Op.RUN, v.revision, 100))
    assert r.run.completed
    return r


def test_new_status_is_not_success(monkeypatch):
    h, calls = new_host(monkeypatch)
    s = h.status()
    assert s.phase is HostPhaseV0.NEW and s.view is None
    assert s.epoch_id is None and not s.completed and not calls


def test_new_refuses_mutation_and_observation(monkeypatch):
    h, _ = new_host(monkeypatch)
    with pytest.raises(HostLifecycleErrorV0):
        h.dispatch(cmd(Op.SNAPSHOT))
    with pytest.raises(HostLifecycleErrorV0):
        h.dispatch(cmd(Op.ADVANCE, 0))


@pytest.mark.parametrize('name', ['', '  ', 7, None, True])
def test_provider_identity_required(name):
    with pytest.raises(TypeError):
        Host(provider=lambda: None, provider_id=name)


def test_provider_callable_required():
    with pytest.raises(TypeError):
        Host(provider=None, provider_id='fixture')


@pytest.mark.parametrize('epoch', ['', None, True, 3])
def test_bad_admission_identity_does_not_call_provider(monkeypatch, epoch):
    h, calls = new_host(monkeypatch)
    with pytest.raises(TypeError):
        h.admit(epoch_id=epoch)
    assert h.status().phase is HostPhaseV0.NEW and not calls


def test_admit_one_real_fresh_sealed_epoch(monkeypatch):
    h = admitted(monkeypatch)
    s = h.status()
    assert s.provider_id == 'TEST-FIXTURE-NOT-AUTH'
    assert s.epoch_id == 'E0' and s.view.revision == 0
    assert s.view.phase is Phase.ROOT_OWNED
    assert all(n.version == 0 for n in s.view.neurons)
    assert s.diagnostic is s.observation_error is None


def test_admit_wrong_epoch_rejected_before_dispatcher_publication(monkeypatch):
    h, calls = new_host(monkeypatch)
    with pytest.raises(DispatchEpochMismatchV0):
        h.admit(epoch_id='WRONG')
    assert len(calls) == 1 and h.status().phase is HostPhaseV0.NEW
    assert h.status().epoch_id is None
    assert h.admit(epoch_id='E0').phase is HostPhaseV0.ACTIVE


def test_bad_provider_output_rejected_without_install(monkeypatch):
    h = Host(provider=lambda: object(), provider_id='bogus')
    with pytest.raises(TypeError, match='canonical'):
        h.admit(epoch_id='E0')
    assert h.status().phase is HostPhaseV0.NEW


def test_provider_exception_is_an_admission_failure_not_a_commit():
    def broken():
        raise RuntimeError('device unavailable')
    h = Host(provider=broken, provider_id='fixture')
    with pytest.raises(HostAdmissionErrorV0) as error:
        h.admit(epoch_id='E0')
    assert isinstance(error.value.__cause__, RuntimeError)
    assert h.status().phase is HostPhaseV0.NEW and not h.status().completed


def test_provider_not_reinvoked_after_install(monkeypatch):
    h, calls = new_host(monkeypatch)
    h.admit(epoch_id='E0')
    with pytest.raises(HostLifecycleErrorV0):
        h.admit(epoch_id='E0')
    assert len(calls) == 1


def test_no_direct_raw_owner_or_dispatcher_api(monkeypatch):
    h = admitted(monkeypatch)
    for attr in ('root', 'terminal', 'runner', 'registry', 'dispatcher', 'driver', 'advance_root', 'handoff'):
        assert not hasattr(h, attr)
        assert not hasattr(h.status(), attr)
    with pytest.raises(AttributeError):
        h.dispatcher = object()
    with pytest.raises(FrozenInstanceError):
        h.status().epoch_id = 'FORGED'


def test_snapshot_audit_trace_are_read_only(monkeypatch):
    h = admitted(monkeypatch)
    first = h.status().view
    for op in (Op.SNAPSHOT, Op.AUDIT, Op.TRACE):
        reply = h.dispatch(cmd(op))
        assert reply.view == first
    assert h.status().view == first


def test_consumers_cannot_choose_wrong_epoch(monkeypatch):
    h = admitted(monkeypatch)
    before = view(h)
    with pytest.raises(DispatchEpochMismatchV0):
        h.dispatch(cmd(Op.RUN, 0, 5, epoch='E1'))
    assert h.status().phase is HostPhaseV0.ACTIVE
    assert view(h) == before


def test_forged_request_is_validated_again(monkeypatch):
    h = admitted(monkeypatch)
    before = view(h)
    fake = object.__new__(Request)
    object.__setattr__(fake, 'epoch_id', 'E0')
    object.__setattr__(fake, 'operation', Op.RUN)
    object.__setattr__(fake, 'expected_revision', 0)
    object.__setattr__(fake, 'max_actions', 0)
    with pytest.raises(TypeError):
        h.dispatch(fake)
    assert h.status().phase is HostPhaseV0.ACTIVE
    assert view(h) == before


def test_noncanonical_request_rejected(monkeypatch):
    h = admitted(monkeypatch)
    with pytest.raises(TypeError):
        h.dispatch({'operation': 'RUN'})
    assert h.status().phase is HostPhaseV0.ACTIVE


def test_first_bounded_run_incomplete_and_resumable(monkeypatch):
    h = admitted(monkeypatch)
    first = h.dispatch(cmd(Op.RUN, 0, 1))
    assert first.view.revision == 1 and not first.run.completed
    assert not h.status().completed and h.status().phase is HostPhaseV0.ACTIVE
    with pytest.raises(CustodyStaleRevisionV0):
        h.dispatch(cmd(Op.RUN, 0, 10))
    last = h.dispatch(cmd(Op.RUN, first.view.revision, 100))
    assert last.run.completed and h.status().completed


def test_no_implicit_stale_revision_retry(monkeypatch):
    h = admitted(monkeypatch)
    h.dispatch(cmd(Op.ADVANCE, 0))
    before = view(h)
    with pytest.raises(CustodyStaleRevisionV0):
        h.dispatch(cmd(Op.ADVANCE, 0))
    assert h.status().phase is HostPhaseV0.ACTIVE and view(h) == before


def test_real_handoff_single_tick_and_s_commit(monkeypatch):
    h = admitted(monkeypatch, commit_units=7)
    result = finish(h)
    steps = result.run.steps
    actions = [s.action for s in steps]
    assert actions.count(Action.HANDOFF) == 1
    ix = actions.index(Action.HANDOFF)
    assert all(x is Action.ROOT_STEP for x in actions[:ix])
    assert all(x is Action.TERMINAL_STEP for x in actions[ix+1:])
    assert all(s.service_ticks_spent == (0 if s.action is Action.HANDOFF else 1)
               for s in steps)
    v = result.view
    assert v.phase is Phase.CLOSED
    assert v.commit_receipt is not None
    assert v.commit_receipt.old_version == 0
    assert v.commit_receipt.new_version == 1
    assert v.commit_receipt.candidate_outputs == ()
    assert sum(n.version == 1 for n in v.neurons) == 1
    assert h.status().completed


def test_after_close_only_observations_and_no_second_install(monkeypatch):
    h, calls = new_host(monkeypatch)
    h.admit(epoch_id='E0')
    closed = finish(h).view
    for op in (Op.SNAPSHOT, Op.AUDIT, Op.TRACE):
        assert h.dispatch(cmd(op)).view == closed
    with pytest.raises(HostLifecycleErrorV0):
        h.dispatch(cmd(Op.ADVANCE, closed.revision))
    with pytest.raises(HostLifecycleErrorV0):
        h.admit(epoch_id='E0')
    assert len(calls) == 1


def test_shutdown_active_is_incomplete_and_irreversible(monkeypatch):
    h = admitted(monkeypatch)
    s = h.shutdown()
    assert s.phase is HostPhaseV0.FAILED and not s.completed
    assert 'shutdown' in s.diagnostic
    with pytest.raises(HostLifecycleErrorV0):
        h.dispatch(cmd(Op.RUN, 0, 100))
    with pytest.raises(HostLifecycleErrorV0):
        h.admit(epoch_id='E0')
    assert h.dispatch(cmd(Op.AUDIT)).view.revision == 0
    assert h.shutdown().phase is HostPhaseV0.FAILED


def test_shutdown_before_admission_forbids_future_install(monkeypatch):
    h, calls = new_host(monkeypatch)
    s = h.shutdown()
    assert s.phase is HostPhaseV0.FAILED and not s.completed
    assert not calls
    with pytest.raises(HostLifecycleErrorV0):
        h.admit(epoch_id='E0')


def test_shutdown_closed_does_not_uncommit(monkeypatch):
    h = admitted(monkeypatch)
    finish(h)
    s = h.shutdown()
    assert s.phase is HostPhaseV0.CLOSED and s.completed


def test_concurrent_same_revision_only_one_writer(monkeypatch):
    h = admitted(monkeypatch)
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(h.dispatch, cmd(Op.ADVANCE, 0)) for _ in range(8)]
        outcomes = []
        for f in futures:
            try:
                outcomes.append(f.result())
            except CustodyStaleRevisionV0:
                outcomes.append('STALE')
    assert sum(x != 'STALE' for x in outcomes) == 1
    assert h.status().view.revision == 1
    assert h.status().phase is HostPhaseV0.ACTIVE


def test_failure_after_partial_run_is_fail_stop(monkeypatch):
    h = admitted(monkeypatch)
    original = type(h._dispatcher).dispatch
    def partial_then_boom(dispatcher, request):
        if request.operation is Op.RUN:
            original(dispatcher, cmd(Op.ADVANCE, request.expected_revision))
            raise RuntimeError('injected failure after one valid quantum')
        return original(dispatcher, request)
    with patch.object(type(h._dispatcher), 'dispatch', partial_then_boom):
        with pytest.raises(HostExecutionErrorV0):
            h.dispatch(cmd(Op.RUN, 0, 50))
        snap = h.status()
    assert snap.phase is HostPhaseV0.FAILED and not snap.completed
    assert snap.view.revision == 1
    assert 'RuntimeError' in snap.diagnostic
    with pytest.raises(HostLifecycleErrorV0):
        h.dispatch(cmd(Op.RUN, 1, 50))
    assert h.dispatch(cmd(Op.TRACE)).view.revision == 1


def test_invalid_runtime_response_never_promotes_close(monkeypatch):
    h = admitted(monkeypatch)
    original = type(h._dispatcher).dispatch
    def corrupt(dispatcher, request):
        value = original(dispatcher, request)
        if request.operation is Op.ADVANCE:
            return replace(value, epoch_id='WRONG')
        return value
    with patch.object(type(h._dispatcher), 'dispatch', corrupt):
        with pytest.raises(HostExecutionErrorV0):
            h.dispatch(cmd(Op.ADVANCE, 0))
    s = h.status()
    assert s.phase is HostPhaseV0.FAILED and not s.completed
    assert s.view.revision == 1  # 24g did accept that prior substep


def test_output_bearing_core_fails_without_fabricated_receipt(monkeypatch):
    h = admitted(monkeypatch, quiet=False)
    with pytest.raises(HostExecutionErrorV0):
        h.dispatch(cmd(Op.RUN, 0, 100))
    status = h.status()
    assert status.phase is HostPhaseV0.FAILED and not status.completed
    assert status.view.commit_receipt is None
    assert status.view.revision > 0  # prior root steps are not rolled back
    with pytest.raises(HostLifecycleErrorV0):
        h.dispatch(cmd(Op.ADVANCE, status.view.revision))


def test_diagnostic_snapshot_failure_does_not_use_cached_view_as_current(monkeypatch):
    h = admitted(monkeypatch)
    original = type(h._dispatcher).dispatch
    def fail_snapshot(dispatcher, request):
        if request.operation is Op.SNAPSHOT:
            raise OSError('diagnostic channel unavailable')
        return original(dispatcher, request)
    with patch.object(type(h._dispatcher), 'dispatch', fail_snapshot):
        s = h.status()
        assert s.view is None and 'OSError' in s.observation_error
        assert s.phase is HostPhaseV0.ACTIVE
    assert h.status().view is not None


def test_separate_hosts_not_globally_fenced(monkeypatch):
    shared = fixture_shared(monkeypatch)
    h1 = Host(provider=lambda: shared, provider_id='fixture-A')
    h2 = Host(provider=lambda: shared, provider_id='fixture-B')
    assert h1.admit(epoch_id='E0').phase is HostPhaseV0.ACTIVE
    assert h2.admit(epoch_id='E0').phase is HostPhaseV0.ACTIVE
    assert h1.dispatch(cmd(Op.ADVANCE, 0)).view.revision == 1
    assert h2.status().view.revision == 0
    # This intentionally documents the absent cross-host fence, not success.


def test_failed_dispatcher_install_does_not_publish_partial_host(monkeypatch):
    h, calls = new_host(monkeypatch)
    from spk_simulator.application_runtime_host_v0 import OwnedRootExecutionDispatcherV0
    def reject(dispatcher, shared, *, epoch_id):
        raise ValueError('forced installation error')
    with patch.object(OwnedRootExecutionDispatcherV0, 'install', reject):
        with pytest.raises(ValueError, match='forced installation error'):
            h.admit(epoch_id='E0')
    assert h.status().phase is HostPhaseV0.NEW
    assert h.status().epoch_id is None
    assert len(calls) == 1
    assert h.admit(epoch_id='E0').phase is HostPhaseV0.ACTIVE


def test_concurrent_admission_has_only_one_success(monkeypatch):
    h, calls = new_host(monkeypatch)
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = [pool.submit(h.admit, epoch_id='E0') for _ in range(6)]
        outcomes = []
        for f in futures:
            try:
                outcomes.append(f.result().phase)
            except HostLifecycleErrorV0:
                outcomes.append('REJECTED')
    assert outcomes.count(HostPhaseV0.ACTIVE) == 1
    assert outcomes.count('REJECTED') == 5
    assert len(calls) == 1


def test_forged_closed_view_without_receipt_is_fail_stop(monkeypatch):
    h = admitted(monkeypatch)
    original = type(h._dispatcher).dispatch
    def dishonest(dispatcher, request):
        result = original(dispatcher, request)
        if request.operation is Op.ADVANCE:
            return replace(result, view=replace(result.view, phase=Phase.CLOSED))
        return result
    with patch.object(type(h._dispatcher), 'dispatch', dishonest):
        with pytest.raises(HostExecutionErrorV0):
            h.dispatch(cmd(Op.ADVANCE, 0))
    assert h.status().phase is HostPhaseV0.FAILED
    assert not h.status().completed
    assert h.status().view.revision == 1


def test_dispatch_snapshot_failure_enters_fail_stop(monkeypatch):
    h = admitted(monkeypatch)
    original = type(h._dispatcher).dispatch
    def broken(dispatcher, request):
        if request.operation is Op.SNAPSHOT:
            raise OSError('snapshot service broke')
        return original(dispatcher, request)
    with patch.object(type(h._dispatcher), 'dispatch', broken):
        with pytest.raises(HostExecutionErrorV0):
            h.dispatch(cmd(Op.SNAPSHOT))
    assert h.status().phase is HostPhaseV0.FAILED
    with pytest.raises(HostLifecycleErrorV0):
        h.dispatch(cmd(Op.ADVANCE, 0))
