"""SPK 24l: source pin, cooperative lease, replay evidence + live 24k path."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import os
import subprocess
import sys
from types import SimpleNamespace

import pytest

from spk_simulator.application_trust_boundary_v0 import (
    EpochLeaseBusyV0, EpochLeasePolicyErrorV0, LocalEpochLeaseV0,
    SourcePinErrorV0, result_fingerprint_v0, resolve_pinned_factory_v0,
    source_file_sha256_v0,
)
from search.spk_24l_pinned_offline_launcher_v0 import (
    OfflineResultDriftV0, main, run_pinned_offline_epoch_v0,
)
from search.spk_application_runtime_launcher_v0 import EXIT_COMPLETED, EXIT_FAILURE, EXIT_INCOMPLETE

PROVIDER = 'tests.spk_offline_demo_epoch_v0:make_epoch'


def trust_dir(tmp_path):
    p = tmp_path / 'trust'
    p.mkdir(mode=0o700)
    p.chmod(0o700)
    return str(p)


def pinned_hash():
    import tests.spk_offline_demo_epoch_v0 as demo
    return source_file_sha256_v0(demo.__file__)


def run_pinned(tmp_path, **overrides):
    args = dict(provider=PROVIDER, expected_source_sha256=pinned_hash(),
                epoch_id='E0', lock_dir=trust_dir(tmp_path),
                max_actions=100, chunk_size=6)
    args.update(overrides)
    return run_pinned_offline_epoch_v0(**args)


def test_source_digest_is_bytes_not_provider_name(tmp_path):
    p = tmp_path / 'provider.py'
    p.write_bytes(b'x=1\n')
    digest = source_file_sha256_v0(p)
    assert digest == hashlib.sha256(b'x=1\n').hexdigest()
    p.write_bytes(b'x=2\n')
    assert source_file_sha256_v0(p) != digest


def test_source_missing_rejected(tmp_path):
    with pytest.raises(SourcePinErrorV0):
        source_file_sha256_v0(tmp_path / 'absent.py')


def test_pinned_real_factory():
    factory = resolve_pinned_factory_v0(PROVIDER, pinned_hash())
    state = factory()
    assert state.seal.epoch_id == 'E0'


@pytest.mark.parametrize('bad', [None, '', '0'*63, '0'*65, 'G'*64, 'F'*64, 0, False])
def test_invalid_sha_pins_fail_closed(bad):
    with pytest.raises(SourcePinErrorV0):
        resolve_pinned_factory_v0(PROVIDER, bad)


@pytest.mark.parametrize('bad', ['', 'x', 'a:b:c', 'a/../b:make', 'tests.foo:bad.attr'])
def test_invalid_spec_fails_closed(bad):
    with pytest.raises(SourcePinErrorV0):
        resolve_pinned_factory_v0(bad, '0'*64)


def test_wrong_source_pin_rejected_even_if_factory_exists():
    with pytest.raises(SourcePinErrorV0, match='mismatch'):
        resolve_pinned_factory_v0(PROVIDER, '0'*64)


def test_lease_same_epoch_refused_without_wait(tmp_path):
    directory = trust_dir(tmp_path)
    with LocalEpochLeaseV0('E0', directory):
        with pytest.raises(EpochLeaseBusyV0):
            with LocalEpochLeaseV0('E0', directory):
                pass


def test_lease_release_allows_sequential_reexecution(tmp_path):
    directory = trust_dir(tmp_path)
    with LocalEpochLeaseV0('E0', directory):
        pass
    with LocalEpochLeaseV0('E0', directory):
        pass  # this is NOT a durable replay fence


def test_different_epoch_can_run_concurrently(tmp_path):
    directory = trust_dir(tmp_path)
    with LocalEpochLeaseV0('E0', directory):
        with LocalEpochLeaseV0('E1', directory):
            pass


def test_separate_directories_are_not_one_authority(tmp_path):
    (tmp_path / 'a').mkdir()
    (tmp_path / 'b').mkdir()
    a = trust_dir(tmp_path / 'a')
    b = trust_dir(tmp_path / 'b')
    with LocalEpochLeaseV0('E0', a):
        with LocalEpochLeaseV0('E0', b):
            pass


def test_invalid_private_directory_rejected(tmp_path):
    d = trust_dir(tmp_path)
    Path(d).chmod(0o755)
    with pytest.raises(EpochLeasePolicyErrorV0):
        with LocalEpochLeaseV0('E0', d):
            pass


def test_symlink_directory_rejected(tmp_path):
    d = trust_dir(tmp_path)
    alias = tmp_path / 'alias'
    alias.symlink_to(d, target_is_directory=True)
    with pytest.raises(EpochLeasePolicyErrorV0):
        with LocalEpochLeaseV0('E0', str(alias)):
            pass


def test_symlink_lease_file_rejected(tmp_path):
    d = trust_dir(tmp_path)
    path = Path(d) / (hashlib.sha256(b'E0').hexdigest() + '.lock')
    path.symlink_to(tmp_path / 'target')
    with pytest.raises(OSError):
        with LocalEpochLeaseV0('E0', d):
            pass


def test_lease_file_permissions_rejected(tmp_path):
    d = trust_dir(tmp_path)
    path = Path(d) / (hashlib.sha256(b'E0').hexdigest() + '.lock')
    path.touch(mode=0o666)
    path.chmod(0o644)
    with pytest.raises(EpochLeasePolicyErrorV0):
        with LocalEpochLeaseV0('E0', d):
            pass


def test_double_acquisition_same_handle_rejected(tmp_path):
    lock = LocalEpochLeaseV0('E0', trust_dir(tmp_path))
    with lock:
        with pytest.raises(EpochLeasePolicyErrorV0):
            with lock:
                pass


def test_lease_released_after_exception(tmp_path):
    d = trust_dir(tmp_path)
    with pytest.raises(RuntimeError):
        with LocalEpochLeaseV0('E0', d):
            raise RuntimeError('simulated execution failure')
    with LocalEpochLeaseV0('E0', d):
        pass


def test_concurrent_threads_only_one_granted(tmp_path):
    d = trust_dir(tmp_path)
    with LocalEpochLeaseV0('E0', d):
        def attempt(_):
            try:
                with LocalEpochLeaseV0('E0', d):
                    return 'BAD'
            except EpochLeaseBusyV0:
                return 'BUSY'
        with ThreadPoolExecutor(max_workers=8) as pool:
            assert list(pool.map(attempt, range(16))) == ['BUSY'] * 16


def test_cross_process_lease_is_real_kernel_lock(tmp_path):
    d = trust_dir(tmp_path)
    source = ("import sys\n"
              "from spk_simulator.application_trust_boundary_v0 import LocalEpochLeaseV0\n"
              "with LocalEpochLeaseV0('E0',sys.argv[1]):\n"
              " print('ACQUIRED', flush=True)\n"
              " sys.stdin.readline()\n")
    p = subprocess.Popen([sys.executable, '-c', source, d], stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert p.stdout.readline().strip() == 'ACQUIRED'
        with pytest.raises(EpochLeaseBusyV0):
            with LocalEpochLeaseV0('E0', d):
                pass
    finally:
        p.stdin.write('\n')
        p.stdin.flush()
        p.communicate(timeout=10)
    with LocalEpochLeaseV0('E0', d):
        pass


def test_real_end_to_end_result_and_receipt(tmp_path):
    report = run_pinned(tmp_path)
    assert report.result.completed and report.result.phase == 'CLOSED'
    assert (report.result.old_version, report.result.new_version) == (0, 1)
    assert report.result.handoffs == 1
    assert report.result.actions == report.result.service_ticks_spent + 1
    assert report.result_sha256 == result_fingerprint_v0(report.result)


def test_different_chunk_sizes_same_public_result(tmp_path):
    (tmp_path / 'a').mkdir()
    (tmp_path / 'b').mkdir()
    first = run_pinned(tmp_path / 'a', chunk_size=1)
    second = run_pinned(tmp_path / 'b', chunk_size=100)
    assert first.result_sha256 == second.result_sha256
    assert first.result == second.result


@pytest.mark.parametrize('bad', [0, -1, True, 1.5])
def test_invalid_run_budget_rejected_before_provider(tmp_path, bad):
    with pytest.raises(ValueError):
        run_pinned(tmp_path, max_actions=bad)


def test_malformed_expected_result_fingerprint_rejected(tmp_path):
    with pytest.raises(SourcePinErrorV0):
        run_pinned(tmp_path, expected_result_sha256='BAD')


def test_limited_run_no_fake_receipt(tmp_path):
    run = run_pinned(tmp_path, max_actions=1)
    assert run.result.phase == 'INCOMPLETE' and not run.result.completed
    assert run.result.new_version is None and run.result.old_version is None


def test_wrong_result_fingerprint_fails_closed(tmp_path):
    with pytest.raises(OfflineResultDriftV0):
        run_pinned(tmp_path, expected_result_sha256='0'*64)


def test_matching_result_fingerprint_passes(tmp_path):
    (tmp_path / 'a').mkdir()
    (tmp_path / 'b').mkdir()
    report = run_pinned(tmp_path / 'a')
    run = run_pinned(tmp_path / 'b',
                     expected_result_sha256=report.result_sha256)
    assert run == report


def test_result_fingerprint_rejects_noncanonical_data():
    with pytest.raises(TypeError):
        result_fingerprint_v0(SimpleNamespace(completed=True))


def test_result_fingerprint_changes_if_summary_changes(tmp_path):
    r = run_pinned(tmp_path)
    altered = replace(r.result, actions=r.result.actions+1)
    assert result_fingerprint_v0(altered) != r.result_sha256


def test_cli_complete_real_fixture(tmp_path, capsys):
    code = main(['--provider', PROVIDER, '--provider-sha256', pinned_hash(),
                 '--lock-dir', trust_dir(tmp_path), '--epoch-id', 'E0',
                 '--max-actions', '100', '--chunk-size', '3'])
    out = json.loads(capsys.readouterr().out)
    assert code == EXIT_COMPLETED and out['completed']
    assert out['new_version'] == 1 and len(out['result_sha256']) == 64


def test_cli_incomplete_nonzero(tmp_path, capsys):
    code = main(['--provider', PROVIDER, '--provider-sha256', pinned_hash(),
                 '--lock-dir', trust_dir(tmp_path), '--epoch-id', 'E0',
                 '--max-actions', '1'])
    out = json.loads(capsys.readouterr().out)
    assert code == EXIT_INCOMPLETE and not out['completed']
    assert out['new_version'] is None


def test_cli_bad_pin_not_success_shaped(tmp_path, capsys):
    code = main(['--provider', PROVIDER, '--provider-sha256', '0'*64,
                 '--lock-dir', trust_dir(tmp_path), '--epoch-id', 'E0',
                 '--max-actions', '100'])
    out = json.loads(capsys.readouterr().out)
    assert code == EXIT_FAILURE and out['status'] == 'ERROR'
    assert 'completed' not in out


def test_cli_wrong_golden_result_not_success_shaped(tmp_path, capsys):
    code = main(['--provider', PROVIDER, '--provider-sha256', pinned_hash(),
                 '--lock-dir', trust_dir(tmp_path), '--epoch-id', 'E0',
                 '--max-actions', '100', '--expected-result-sha256', '0'*64])
    out = json.loads(capsys.readouterr().out)
    assert code == EXIT_FAILURE and out['status'] == 'ERROR'
    assert 'completed' not in out


def test_launcher_uses_existing_24k_host_only():
    import inspect
    from search import spk_24l_pinned_offline_launcher_v0 as launcher
    source = inspect.getsource(launcher)
    for forbidden in ('OwnedRootExecutionDispatcherV0(', 'OwnedRootAuthorityRegistryV0(',
                      'advance_owned_root_', 'advance_owned_terminal_'):
        assert forbidden not in source
