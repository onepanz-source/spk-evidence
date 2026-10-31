"""24h: independent contract checks for the read-only static audit tool.

These tests deliberately avoid importing the simulator's frozen dependencies.
"""

import json
from pathlib import Path

import pytest

from search.spk_application_host_audit_v0 import (
    audit_repository, inspect_source, main,
)


def put(root: Path, rel: str, text: str) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding='utf-8')


def make_repo(tmp_path: Path) -> Path:
    put(tmp_path, 'spk_simulator/owned_root_execution_dispatch_v0.py',
        'class OwnedRootExecutionDispatcherV0: pass\n')
    put(tmp_path, 'tests/test_dispatch.py',
        'from spk_simulator.owned_root_execution_dispatch_v0 import OwnedRootExecutionDispatcherV0\n'
        'def test_one(): assert OwnedRootExecutionDispatcherV0\n')
    return tmp_path


def test_import_without_host_is_not_adoption(tmp_path):
    report = audit_repository(make_repo(tmp_path))
    assert report['status'] == 'NO_APPLICATION_ADOPTION_EVIDENCE'
    assert report['host_candidates'] == []
    assert len(report['dispatcher_references']) == 1
    assert not report['application_dispatcher_candidates']


def test_non_test_import_is_only_candidate_not_proof(tmp_path):
    root = make_repo(tmp_path)
    put(root, 'app/host.py',
        'from spk_simulator.owned_root_execution_dispatch_v0 import OwnedRootExecutionDispatcherV0\n')
    r = audit_repository(root)
    assert r['status'] == 'ADOPTION_CANDIDATE_UNVERIFIED'
    assert r['host_candidates'] == ['app/host.py']
    c = r['application_dispatcher_candidates'][0]
    assert not c['dispatcher_construction_call']
    assert not c['same_binding_install_call']
    assert not c['same_binding_dispatch_call']


def test_local_construct_install_dispatch_only_syntactic_hints(tmp_path):
    root = make_repo(tmp_path)
    put(root, 'host.py',
        'from spk_simulator.owned_root_execution_dispatch_v0 import OwnedRootExecutionDispatcherV0 as Dispatcher\n'
        'd = Dispatcher()\n'
        'd.install(None, epoch_id="x")\n'
        'd.dispatch(None)\n')
    r = audit_repository(root)
    x = r['application_dispatcher_candidates'][0]
    assert (x['dispatcher_construction_call'], x['same_binding_install_call'],
            x['same_binding_dispatch_call']) == (True, True, True)
    assert r['status'] == 'ADOPTION_CANDIDATE_UNVERIFIED'


def test_module_import_as_alias_catches_constructor(tmp_path):
    root = make_repo(tmp_path)
    put(root, 'host.py',
        'import spk_simulator.owned_root_execution_dispatch_v0 as dispatch_mod\n'
        'd = dispatch_mod.OwnedRootExecutionDispatcherV0()\n'
        'd.dispatch(None)\n')
    x = audit_repository(root)['application_dispatcher_candidates'][0]
    assert x['dispatcher_construction_call']
    assert x['same_binding_dispatch_call']
    assert not x['same_binding_install_call']


def test_package_from_import_catches_module_reference(tmp_path):
    root = make_repo(tmp_path)
    put(root, 'host.py',
        'from spk_simulator import owned_root_execution_dispatch_v0 as boundary\n'
        'boundary.OwnedRootExecutionDispatcherV0()\n')
    x = audit_repository(root)['application_dispatcher_candidates'][0]
    assert x['dispatcher_reference']
    assert x['dispatcher_construction_call']


def test_raw_owner_use_is_not_misreported_as_dispatcher_adoption(tmp_path):
    root = make_repo(tmp_path)
    put(root, 'app/legacy.py',
        'from spk_simulator.owned_root_single_clock_v0 import advance_owned_root_single_clock_v0\n'
        'def do_step(s): return advance_owned_root_single_clock_v0(s)\n')
    r = audit_repository(root)
    assert r['status'] == 'NO_APPLICATION_ADOPTION_EVIDENCE'
    assert 'app/legacy.py' in [x['path'] for x in r['raw_owner_importers']]
    assert not r['application_dispatcher_candidates']


def test_internal_owner_chain_is_not_host(tmp_path):
    root = make_repo(tmp_path)
    put(root, 'spk_simulator/owned_root_authority_custody_v0.py',
        'from .owned_root_single_clock_v0 import advance_owned_root_single_clock_v0\n')
    r = audit_repository(root)
    x = r['raw_owner_importers'][0]
    assert x['classification'] == 'simulator_library'
    assert x['raw_owner_modules'] == ['spk_simulator.owned_root_single_clock_v0']
    assert not r['host_candidates']


def test_main_guard_is_candidate_not_proof(tmp_path):
    root = make_repo(tmp_path)
    put(root, 'app/run.py', 'if __name__ == "__main__":\n    print("ready")\n')
    r = audit_repository(root)
    assert r['host_candidates'] == ['app/run.py']
    assert r['status'] == 'NO_APPLICATION_ADOPTION_EVIDENCE'


def test_pyproject_entrypoint_candidate_not_runtime_proof(tmp_path):
    root = make_repo(tmp_path)
    put(root, 'pyproject.toml',
        '[project.scripts]\nspk-host = "my_app.runtime:main"\n')
    r = audit_repository(root)
    assert r['status'] == 'NO_APPLICATION_ADOPTION_EVIDENCE'
    assert r['packaging_entrypoints'] == [
        {'source': 'pyproject.toml', 'script': 'spk-host', 'target': 'my_app.runtime:main'}]
    assert r['host_candidates'] == ['entrypoint:spk-host=my_app.runtime:main']


def test_source_syntax_error_is_incomplete(tmp_path):
    root = make_repo(tmp_path)
    put(root, 'app/broken.py', 'def broken(:\n')
    r = audit_repository(root)
    assert r['status'] == 'INCOMPLETE_STATIC_INVENTORY'
    assert r['parse_errors'][0]['path'] == 'app/broken.py'


def test_dynamic_import_and_star_are_disclosed(tmp_path):
    root = make_repo(tmp_path)
    put(root, 'app/runtime.py',
        'import importlib\n'
        'from spk_simulator.owned_root_single_clock_v0 import *\n'
        'def load(s): return importlib.import_module(s)\n')
    r = audit_repository(root)
    assert r['dynamic_import_or_execution_syntax'] == [
        {'path': 'app/runtime.py', 'forms': ['importlib.import_module']}]
    assert r['star_import_sites'] == [{
        'path': 'app/runtime.py',
        'imports': ['spk_simulator.owned_root_single_clock_v0.*']}]
    assert r['status'] == 'NO_APPLICATION_ADOPTION_EVIDENCE'


def test_research_and_tests_not_host_candidates(tmp_path):
    root = make_repo(tmp_path)
    put(root, 'search/demo.py',
        'from spk_simulator.owned_root_execution_dispatch_v0 import OwnedRootExecutionDispatcherV0\n'
        'if __name__ == "__main__": print(1)\n')
    assert not audit_repository(root)['host_candidates']


def test_fingerprint_and_report_order_are_deterministic(tmp_path):
    root = make_repo(tmp_path)
    put(root, 'z.py', 'print(9)\n')
    put(root, 'a.py', 'print(1)\n')
    first = audit_repository(root)
    assert audit_repository(root) == first
    put(root, 'a.py', 'print(2)\n')
    second = audit_repository(root)
    assert second['python_source_sha256'] != first['python_source_sha256']
    assert second['python_files_scanned'] == first['python_files_scanned']


def test_symlink_target_not_traversed(tmp_path):
    root = make_repo(tmp_path / 'repo')
    outside = tmp_path / 'outside'
    outside.mkdir()
    put(outside, 'evil.py', 'print(42)\n')
    (root / 'external').symlink_to(outside, target_is_directory=True)
    (root / 'link.py').symlink_to(outside / 'evil.py')
    r = audit_repository(root)
    assert r['python_files_scanned'] == 2


def test_cli_audit_and_optional_evidence_gate(tmp_path, capsys):
    root = make_repo(tmp_path / 'repo')
    output = tmp_path / 'report.json'
    assert main(['--repo', str(root), '--json-out', str(output)]) == 0
    report = json.loads(output.read_text(encoding='utf-8'))
    assert report['status'] == 'NO_APPLICATION_ADOPTION_EVIDENCE'
    assert main(['--repo', str(root), '--require-adoption-evidence']) == 2
    put(root, 'app/host.py',
        'from spk_simulator.owned_root_execution_dispatch_v0 import OwnedRootExecutionDispatcherV0\n')
    assert main(['--repo', str(root), '--require-adoption-evidence']) == 0
    assert 'ADOPTION_CANDIDATE_UNVERIFIED' in capsys.readouterr().out


def test_malformed_pyproject_requires_manual_review(tmp_path):
    root = make_repo(tmp_path)
    put(root, 'pyproject.toml', 'invalid = [\n')
    report = audit_repository(root)
    assert report['status'] == 'INCOMPLETE_STATIC_INVENTORY'
    assert any('could not be parsed' in x for x in report['limitations'])


def test_no_repository_mutation(tmp_path):
    root = make_repo(tmp_path)
    original = sorted((p.relative_to(root).as_posix(), p.read_bytes())
                      for p in root.rglob('*') if p.is_file())
    audit_repository(root)
    after = sorted((p.relative_to(root).as_posix(), p.read_bytes())
                   for p in root.rglob('*') if p.is_file())
    assert original == after


def test_explicit_relative_import_under_nested_package():
    rel = 'spk_simulator/owned_root_authority_custody_v0.py'
    code = b'from .owned_root_single_clock_v0 import advance_owned_root_single_clock_v0\n'
    record = inspect_source(rel, code)
    assert record['raw_owner_modules'] == ['spk_simulator.owned_root_single_clock_v0']


def test_dunder_main_on_test_not_a_host(tmp_path):
    root = make_repo(tmp_path)
    put(root, 'tests/test_main.py', 'if __name__ == "__main__": print("x")\n')
    assert audit_repository(root)['host_candidates'] == []


def test_known_source_bundle_collector_is_not_an_application_host(tmp_path):
    root = make_repo(tmp_path)
    # This exact root-level tool was the only 24h candidate on fwork.
    # It contains a main guard, but produces a tar source archive, not an
    # SPK simulation epoch or an execution dispatch.
    put(root, 'spk_24d_collect.py',
        'import tarfile\n'
        'def main():\n    return tarfile.open("x.tar.gz", "w:gz")\n'
        'if __name__ == "__main__": main()\n')
    report = audit_repository(root)
    assert report['host_candidates'] == []
    assert report['status'] == 'NO_APPLICATION_ADOPTION_EVIDENCE'
    assert 'spk_24d_collect.py' in report['non_application_repository_tools']
    assert report['python_files_scanned'] == 3  # included in fingerprint


def test_tool_exclusion_is_exact_not_general_bypass(tmp_path):
    root = make_repo(tmp_path)
    put(root, 'app/spk_24d_collect.py',
        'if __name__ == "__main__": print("app")\n')
    put(root, 'spk_24d_collect_next.py',
        'if __name__ == "__main__": print("new app")\n')
    report = audit_repository(root)
    assert report['host_candidates'] == [
        'app/spk_24d_collect.py', 'spk_24d_collect_next.py']


def test_tool_that_becomes_dispatcher_client_reenters_inventory(tmp_path):
    root = make_repo(tmp_path)
    put(root, 'spk_24d_collect.py',
        'from spk_simulator.owned_root_execution_dispatch_v0 import OwnedRootExecutionDispatcherV0\n'
        'if __name__ == "__main__": print(OwnedRootExecutionDispatcherV0)\n')
    report = audit_repository(root)
    assert report['host_candidates'] == ['spk_24d_collect.py']
    assert report['status'] == 'ADOPTION_CANDIDATE_UNVERIFIED'
    assert any(f['path'] == 'spk_24d_collect.py'
               for f in report['dispatcher_references'])
    assert report['application_dispatcher_candidates'][0]['path'] == 'spk_24d_collect.py'
    assert not report['non_application_repository_tools']


def test_collect_tool_dynamic_execution_requires_review(tmp_path):
    root = make_repo(tmp_path)
    put(root, 'spk_24d_collect.py',
        'import importlib\n'
        'if __name__ == "__main__": importlib.import_module("spk_simulator")\n')
    report = audit_repository(root)
    assert report['host_candidates'] == ['spk_24d_collect.py']
    assert not report['non_application_repository_tools']
    assert report['status'] == 'NO_APPLICATION_ADOPTION_EVIDENCE'
