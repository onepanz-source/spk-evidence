"""Research-only regression of native producer discovery without guessed filenames."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from spk_bv_research.paired_runs_v0o import TARGET, PairError, pins, capture, load_capture

RUNTIME = 'spk_bv_research/native_scheduler_engine_v0e.py'
HELPER = 'spk_bv_research/native_schedule_helpers.py'


def repo(tmp_path, *, imports=True, transitive=True):
    root=tmp_path/'root'
    (root/'tests').mkdir(parents=True)
    (root/'spk_bv_research').mkdir()
    source='''import pytest
from spk_bv_research.native_scheduler_engine_v0e import run_scheduler
@pytest.fixture
def runs():
    return run_scheduler()
def test_feedback_causes_forward_source_link_wait(runs):
    raise AssertionError('test body must never run')
''' if imports else '''import pytest
@pytest.fixture
def runs(): return (0, 1)
def test_feedback_causes_forward_source_link_wait(runs): pass
'''
    (root/TARGET).write_text(source)
    (root/RUNTIME).write_text('''from .native_schedule_helpers import PAIR

def run_scheduler(): return PAIR
''' if transitive else '''def run_scheduler(): return (1, 2)
''')
    if transitive:
        (root/HELPER).write_text('PAIR = ({"off": 3}, {"on": 5})\n')
    return root


def test_concrete_native_local_module_not_a_guessed_name(tmp_path):
    root=repo(tmp_path, transitive=False)
    p=pins(root)
    assert p['producer_resolution']=='STATIC_LOCAL_IMPORT_CLOSURE_NOT_RUNTIME_PROOF'
    assert set(p['source_sha256'])=={TARGET,RUNTIME}


def test_transitive_relative_import_module_is_pinned(tmp_path):
    root=repo(tmp_path)
    p=pins(root)
    assert set(p['source_sha256'])=={TARGET,RUNTIME,HELPER}
    assert p['source_sha256'][HELPER]==hashlib.sha256((root/HELPER).read_bytes()).hexdigest()


def test_transitive_change_alters_source_pins(tmp_path):
    root=repo(tmp_path)
    initial=pins(root)
    (root/HELPER).write_text('PAIR = (2, 4)\n')
    assert pins(root)!=initial


def test_no_false_local_import_proof(tmp_path):
    root=repo(tmp_path, imports=False)
    with pytest.raises(PairError,match='approved paths'):
        pins(root)


def test_test_imports_from_real_scheduler_need_not_be_legacy_path(tmp_path):
    root=repo(tmp_path)
    obj=capture([{'off':1},{'on':2}],pins(root))
    report=tmp_path/'report.json'
    report.write_text(json.dumps(obj))
    assert load_capture(report)==obj


def test_non_source_symlink_cannot_be_accepted(tmp_path):
    root=repo(tmp_path)
    (root/RUNTIME).unlink()
    (root/RUNTIME).symlink_to(root/HELPER)
    with pytest.raises(PairError,match='symlink'):
        pins(root)


def test_symlink_package_dir_cannot_be_accepted(tmp_path):
    root=repo(tmp_path)
    (root/RUNTIME).unlink(); (root/HELPER).unlink()
    (root/'spk_bv_research').rmdir()
    external=tmp_path/'outside'; external.mkdir()
    (external/'native_scheduler_engine_v0e.py').write_text('VALUE=1\n')
    (root/'spk_bv_research').symlink_to(external, target_is_directory=True)
    with pytest.raises(PairError,match='unsafe'):
        pins(root)


def test_capture_real_fixture_skip_body(tmp_path):
    root=repo(tmp_path, imports=False)
    (root/TARGET).write_text('''import pytest
from spk_native_scheduler_engine_v0e import run_scheduler
@pytest.fixture
def runs():
    return run_scheduler()
def test_feedback_causes_forward_source_link_wait(runs):
    raise AssertionError("test body must never run")
''')
    (root/'spk_native_scheduler_engine_v0e.py').write_text('''from spk_native_schedule_helpers import PAIR
def run_scheduler(): return PAIR
''')
    (root/'spk_native_schedule_helpers.py').write_text('PAIR = ({"off": 3}, {"on": 5})\n')
    output=tmp_path/'capture.json'
    current=Path(__file__).resolve().parents[1]
    env={**os.environ, 'PYTHONPATH': str(root)+os.pathsep+str(current), 'PYTHONHASHSEED':'13'}
    run=subprocess.run([sys.executable,'-m','search.spk_bv_v0o_capture','--root',str(root),'--out',str(output)],
                        cwd=current,text=True,capture_output=True,env=env)
    assert run.returncode==0,(run.stdout,run.stderr)
    assert set(load_capture(output)['producer_pins']['source_sha256'])=={
        TARGET,'spk_native_scheduler_engine_v0e.py','spk_native_schedule_helpers.py'}


def test_reproducible_hashseeds(tmp_path):
    root=repo(tmp_path)
    script='import json,sys;from pathlib import Path;from spk_bv_research.paired_runs_v0o import pins;print(json.dumps(pins(Path(sys.argv[1])),sort_keys=True))'
    current=Path(__file__).resolve().parents[1]
    outs=[]
    for seed in ('13','811'):
        run=subprocess.run([sys.executable,'-c',script,str(root)],cwd=current,text=True,capture_output=True,
                           env={**os.environ,'PYTHONHASHSEED':seed})
        assert run.returncode==0,run.stderr
        outs.append(run.stdout)
    assert outs[0]==outs[1]


def test_invalid_path_in_attestation_denied(tmp_path):
    root=repo(tmp_path)
    pin=pins(root)
    pin['source_sha256']['../outside.py']='0'*64
    with pytest.raises(PairError,match='source path'):
        capture({'sample':1},pin)


def test_empty_closure_denied_even_if_test_imports_pytest(tmp_path):
    root=repo(tmp_path,imports=False)
    (root/RUNTIME).unlink(); (root/HELPER).unlink()
    with pytest.raises(PairError,match='no concrete local'):
        pins(root)


def test_python_modules_not_imported(tmp_path):
    root=repo(tmp_path,transitive=False)
    (root/RUNTIME).write_text('raise AssertionError("import executed")\n')
    assert RUNTIME in pins(root)['source_sha256']
