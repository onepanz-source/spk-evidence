"""SPK 24k: real k24g/k24j consumer using historical finite input fixtures.

The factory is a fixture, not a production authenticator. All service/PS/Core
transitions under test are executed by existing SPK implementation.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import sys
import types

import pytest

from tests.test_owned_root_execution_dispatch_v0 import shared as sealed_fixture
from spk_simulator.application_runtime_host_v0 import HostExecutionErrorV0
from spk_simulator.application_epoch_provider_v0 import (
    EpochAlreadyIssuedV0, SingleUseSealedEpochProviderV0,
)
from search.spk_application_runtime_launcher_v0 import (
    EXIT_COMPLETED, EXIT_FAILURE, EXIT_INCOMPLETE,
    main, resolve_local_epoch_factory_v0, run_offline_epoch_v0,
    OfflineSessionErrorV0,
)


def factory(monkeypatch, *, quiet=True, commit_units=1):
    epoch = sealed_fixture(monkeypatch, quiet=quiet, commit_units=commit_units)
    calls = []
    def produce():
        calls.append(1)
        return epoch
    return epoch, produce, calls


def run_test(monkeypatch, **kw):
    _, fn, calls = factory(monkeypatch, **{k:kw[k] for k in ('quiet', 'commit_units') if k in kw})
    run_kw = {k:kw[k] for k in ('max_actions', 'chunk_size') if k in kw}
    result = run_offline_epoch_v0(factory=fn, provider_id='FIXTURE-NOT-AUTH',
                                  epoch_id='E0', max_actions=run_kw.get('max_actions', 100),
                                  chunk_size=run_kw.get('chunk_size', 5))
    assert len(calls) == 1
    return result


def test_one_use_epoch_provider(monkeypatch):
    epoch, _, _ = factory(monkeypatch)
    provider = SingleUseSealedEpochProviderV0(epoch, source_id='trusted-by-test')
    assert not provider.issued
    assert provider() is epoch
    assert provider.issued
    with pytest.raises(EpochAlreadyIssuedV0):
        provider()


def test_provider_validates_bad_type():
    with pytest.raises(TypeError):
        SingleUseSealedEpochProviderV0(None, source_id='test')


@pytest.mark.parametrize('source_id', ['', '  ', ' bad ', 3, False, None])
def test_provider_validates_source_id(monkeypatch, source_id):
    epoch, _, _ = factory(monkeypatch)
    with pytest.raises(TypeError):
        SingleUseSealedEpochProviderV0(epoch, source_id=source_id)


def test_provider_issues_once_even_when_called_concurrently(monkeypatch):
    epoch, _, _ = factory(monkeypatch)
    p = SingleUseSealedEpochProviderV0(epoch, source_id='TEST')
    with ThreadPoolExecutor(max_workers=8) as executor:
        calls = [executor.submit(p) for _ in range(8)]
    accepted = 0
    for task in calls:
        try:
            assert task.result() is epoch
            accepted += 1
        except EpochAlreadyIssuedV0:
            pass
    assert accepted == 1


def test_provider_rejects_forged_shared_snapshot(monkeypatch):
    epoch, _, _ = factory(monkeypatch)
    # Bypass dataclass constructor to represent hostile forged history.
    forged = object.__new__(type(epoch))
    for field in epoch.__dataclass_fields__:
        object.__setattr__(forged, field, getattr(epoch, field))
    object.__setattr__(forged, 'external_resident_input_indices', (999,))
    with pytest.raises((ValueError, TypeError)):
        SingleUseSealedEpochProviderV0(forged, source_id='TEST')


def test_single_bounded_root_step_is_incomplete(monkeypatch):
    r = run_test(monkeypatch, max_actions=1)
    assert not r.completed and r.phase == 'INCOMPLETE'
    assert r.actions == 1 and r.revision == 1
    assert r.service_ticks_spent == 1 and r.handoffs == 0
    assert r.old_version is r.new_version is None


def test_handoff_may_exhaust_budget_without_commit(monkeypatch):
    r = run_test(monkeypatch, max_actions=8)
    if not r.completed:
        assert r.old_version is None and r.new_version is None
        assert r.phase == 'INCOMPLETE'
    else:
        assert r.new_version == 1


def test_full_end_to_end_service_and_commit(monkeypatch):
    r = run_test(monkeypatch)
    assert r.completed and r.phase == 'CLOSED'
    assert (r.old_version, r.new_version) == (0, 1)
    assert r.handoffs == 1
    assert r.actions == r.service_ticks_spent + 1
    assert r.next_service_tick > 4
    assert r.revision == r.actions


def test_chunked_execution_matches_single_run(monkeypatch):
    a = run_test(monkeypatch, chunk_size=1)
    b = run_test(monkeypatch, chunk_size=100)
    assert a == b


def test_commit_multiquantum_preserves_accounting(monkeypatch):
    a = run_test(monkeypatch, commit_units=7, chunk_size=2)
    assert a.completed and a.new_version == 1
    assert a.handoffs == 1 and a.actions == a.service_ticks_spent + 1


def test_output_bearing_core_is_rejected(monkeypatch):
    _, fn, _ = factory(monkeypatch, quiet=False)
    with pytest.raises(OfflineSessionErrorV0) as error:
        run_offline_epoch_v0(factory=fn, provider_id='fixture', epoch_id='E0',
                             max_actions=100, chunk_size=3)
    assert isinstance(error.value.__cause__, HostExecutionErrorV0)
    assert error.value.revision is not None and error.value.revision > 0


def test_wrong_epoch_rejected(monkeypatch):
    _, fn, _ = factory(monkeypatch)
    with pytest.raises(ValueError):
        run_offline_epoch_v0(factory=fn, provider_id='fixture', epoch_id='BAD',
                             max_actions=100, chunk_size=3)


@pytest.mark.parametrize('name,value', [
    ('max_actions', 0), ('chunk_size', 0), ('max_actions', -1),
    ('chunk_size', False), ('max_actions', 1.5),
])
def test_budget_validation_precedes_provider(monkeypatch, name, value):
    _, fn, calls = factory(monkeypatch)
    args = dict(factory=fn, provider_id='fixture', epoch_id='E0', max_actions=3, chunk_size=1)
    args[name] = value
    with pytest.raises(ValueError):
        run_offline_epoch_v0(**args)
    assert calls == []


def test_factory_invalid_type_fails_closed():
    with pytest.raises(TypeError):
        run_offline_epoch_v0(factory=lambda: None, provider_id='fixture',
                             epoch_id='E0', max_actions=10, chunk_size=2)


@pytest.mark.parametrize('spec', [None, '', 'a', 'a:b:c', '../a:b', 'a:b.c', 'a:'])
def test_invalid_factory_path_refused_without_import(spec):
    with pytest.raises(ValueError):
        resolve_local_epoch_factory_v0(spec)


def test_resolve_local_factory_module(monkeypatch):
    m = types.ModuleType('spk_lab_trusted_factory')
    def make(): return 42
    m.make = make
    monkeypatch.setitem(sys.modules, m.__name__, m)
    assert resolve_local_epoch_factory_v0('spk_lab_trusted_factory:make') is make


def test_resolve_rejects_noncallable(monkeypatch):
    m = types.ModuleType('spk_lab_trusted_factory')
    m.noncallable = 1
    monkeypatch.setitem(sys.modules, m.__name__, m)
    with pytest.raises(TypeError):
        resolve_local_epoch_factory_v0('spk_lab_trusted_factory:noncallable')


def test_cli_end_to_end_returns_only_data(monkeypatch, capsys):
    _, fn, _ = factory(monkeypatch)
    m = types.ModuleType('spk_lab_trusted_factory')
    m.make = fn
    monkeypatch.setitem(sys.modules, m.__name__, m)
    code = main(['--provider', 'spk_lab_trusted_factory:make', '--epoch-id', 'E0',
                 '--max-actions', '100', '--chunk-size', '3'])
    data = json.loads(capsys.readouterr().out)
    assert code == EXIT_COMPLETED and data['completed']
    assert data['new_version'] == 1 and data['handoffs'] == 1
    assert data['provider_id'] == 'spk_lab_trusted_factory:make'
    assert 'root' not in data and 'dispatcher' not in data


def test_cli_incomplete_has_nonzero_exit_code(monkeypatch, capsys):
    _, fn, _ = factory(monkeypatch)
    m = types.ModuleType('spk_lab_trusted_factory')
    m.make = fn
    monkeypatch.setitem(sys.modules, m.__name__, m)
    code = main(['--provider', 'spk_lab_trusted_factory:make', '--epoch-id', 'E0',
                 '--max-actions', '1'])
    data = json.loads(capsys.readouterr().out)
    assert code == EXIT_INCOMPLETE and data['phase'] == 'INCOMPLETE'
    assert data['old_version'] is None and data['new_version'] is None


def test_cli_bad_source_does_not_report_success(capsys):
    code = main(['--provider', 'unknown_spk_module:make', '--epoch-id', 'E0',
                 '--max-actions', '3'])
    data = json.loads(capsys.readouterr().out)
    assert code == EXIT_FAILURE and data['status'] == 'ERROR'
    assert not data.get('completed', False)


def test_cli_rejected_epoch_has_no_success(monkeypatch, capsys):
    _, fn, _ = factory(monkeypatch)
    m = types.ModuleType('spk_lab_trusted_factory')
    m.make = fn
    monkeypatch.setitem(sys.modules, m.__name__, m)
    code = main(['--provider', 'spk_lab_trusted_factory:make', '--epoch-id', 'WRONG',
                 '--max-actions', '100'])
    data = json.loads(capsys.readouterr().out)
    assert code == EXIT_FAILURE and data['status'] == 'ERROR'


def test_host_launcher_imports_no_owner_module():
    import inspect
    from search import spk_application_runtime_launcher_v0 as launcher
    source = inspect.getsource(launcher)
    for forbidden in ('owned_root_single_clock_v0', 'owned_root_terminal_commit_v0',
                      'OwnedRootAuthorityRegistryV0(', 'OwnedRootCustodyExecutionV0('):
        assert forbidden not in source


def test_demo_provider_full_path_without_pytest_fixture():
    from tests.spk_offline_demo_epoch_v0 import make_epoch
    state = make_epoch()
    assert state.seal.epoch_id == 'E0'
    assert not state.dynamic.transit.service.confirmed
    assert state.external_consumed_input_indices == ()
    r = run_offline_epoch_v0(factory=make_epoch, provider_id='DEMO-NO-AUTH',
                             epoch_id='E0', max_actions=100, chunk_size=6)
    assert r.completed and r.new_version == 1 and r.handoffs == 1


def test_cli_demo_provider_module_is_runnable(capsys):
    code = main(['--provider', 'tests.spk_offline_demo_epoch_v0:make_epoch',
                 '--epoch-id', 'E0', '--max-actions', '100', '--chunk-size', '6'])
    data = json.loads(capsys.readouterr().out)
    assert code == EXIT_COMPLETED and data['completed']
    assert data['old_version'] == 0 and data['new_version'] == 1


def test_rejects_unaccounted_service_tick(monkeypatch):
    from dataclasses import replace
    from spk_simulator.application_runtime_host_v0 import ApplicationRuntimeHostV0
    from spk_simulator.owned_root_execution_dispatch_v0 import DispatchOperationV0
    _, fn, _ = factory(monkeypatch)
    original = ApplicationRuntimeHostV0.dispatch
    def falsify(host, request):
        answer = original(host, request)
        if request.operation is DispatchOperationV0.RUN:
            return replace(answer, view=replace(answer.view,
                next_service_tick=answer.view.next_service_tick + 2))
        return answer
    monkeypatch.setattr(ApplicationRuntimeHostV0, 'dispatch', falsify)
    with pytest.raises(OfflineSessionErrorV0, match='SERVICE_TIME'):
        run_offline_epoch_v0(factory=fn, provider_id='fixture', epoch_id='E0',
                             max_actions=100, chunk_size=5)


def test_rejects_unaccounted_revision(monkeypatch):
    from dataclasses import replace
    from spk_simulator.application_runtime_host_v0 import ApplicationRuntimeHostV0
    from spk_simulator.owned_root_execution_dispatch_v0 import DispatchOperationV0
    _, fn, _ = factory(monkeypatch)
    original = ApplicationRuntimeHostV0.dispatch
    def falsify(host, request):
        answer = original(host, request)
        if request.operation is DispatchOperationV0.RUN:
            return replace(answer, view=replace(answer.view,revision=answer.view.revision + 1))
        return answer
    monkeypatch.setattr(ApplicationRuntimeHostV0, 'dispatch', falsify)
    with pytest.raises(OfflineSessionErrorV0, match='revision advance'):
        run_offline_epoch_v0(factory=fn, provider_id='fixture', epoch_id='E0',
                             max_actions=100, chunk_size=5)


def test_two_independent_providers_can_issue_same_epoch_not_global_fence(monkeypatch):
    epoch, _, _ = factory(monkeypatch)
    first = SingleUseSealedEpochProviderV0(epoch, source_id='FIRST')
    second = SingleUseSealedEpochProviderV0(epoch, source_id='SECOND')
    # Intentionally succeeds: single-use *per provider* is not exclusivity.
    assert first() is epoch and second() is epoch


def test_cli_partial_failure_reports_last_observable_revision(monkeypatch, capsys):
    _, fn, _ = factory(monkeypatch, quiet=False)
    m = types.ModuleType('spk_lab_trusted_factory')
    m.make = fn
    monkeypatch.setitem(sys.modules, m.__name__, m)
    code = main(['--provider', 'spk_lab_trusted_factory:make', '--epoch-id', 'E0',
                 '--max-actions', '100', '--chunk-size', '3'])
    data = json.loads(capsys.readouterr().out)
    assert code == EXIT_FAILURE and data['status'] == 'ERROR'
    assert data['type'] == 'OfflineSessionErrorV0'
    assert data['revision'] is not None and data['revision'] > 0
    assert data.get('completed') is not True
