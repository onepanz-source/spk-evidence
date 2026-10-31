"""Regression tests for BV v0o source-path hotfix. No native fwork claims."""
from __future__ import annotations
import json
from pathlib import Path
from copy import deepcopy
import subprocess
import sys

import pytest

from spk_bv_research.paired_runs_v0o import (
    PairError, TARGET, PRODUCER_CANDIDATES, pins, capture, load_capture,
)

LEGACY, PKG, PKG2, ROOT = PRODUCER_CANDIDATES


def work(tmp_path: Path, *, test_source: str = 'def test_feedback_causes_forward_source_link_wait(): pass\n',
         sources: tuple[str, ...] = (PKG,)):
    repo=tmp_path/'work'; (repo/'tests').mkdir(parents=True)
    (repo/TARGET).write_text(test_source)
    for rel in sources:
        path=repo/rel
        path.parent.mkdir(exist_ok=True, parents=True)
        path.write_text('SYMBOL = 1\n')
    return repo


def test_pkg_path_pins_no_legacy_requirement(tmp_path):
    repo=work(tmp_path)
    doc=pins(repo)
    assert set(doc['source_sha256'])=={TARGET,PKG}
    assert doc['producer_resolution']=='UNIQUE_APPROVED_PATH_NOT_IMPORT_PROOF'


def test_pkg_fully_qualified_path_is_stable_under_hashseed(tmp_path):
    repo=work(tmp_path)
    code='from pathlib import Path;from spk_bv_research.paired_runs_v0o import pins;import json,sys;print(json.dumps(pins(Path(sys.argv[1])),sort_keys=True))'
    root=Path(__file__).resolve().parents[1]
    outs=[]
    for seed in ('13','811'):
        import os
        r=subprocess.run([sys.executable,'-c',code,str(repo)],cwd=root,text=True,capture_output=True,env={**os.environ,'PYTHONHASHSEED':seed})
        assert r.returncode==0,r.stderr
        outs.append(r.stdout)
    assert outs[0]==outs[1]


def test_missing_source_fails_closed_and_is_diagnostic(tmp_path):
    repo=work(tmp_path,sources=())
    with pytest.raises(PairError,match='approved paths'):
        pins(repo)


def test_ambiguous_sources_not_silently_preferred(tmp_path):
    repo=work(tmp_path,sources=(PKG,LEGACY))
    with pytest.raises(PairError,match='ambiguous'):
        pins(repo)


def test_explicit_test_import_resolves_two_present_sources(tmp_path):
    repo=work(tmp_path,test_source='from spk_bv_research.live_dual_scheduler_v0e import SYMBOL\n',sources=(PKG,LEGACY))
    doc=pins(repo)
    assert set(doc['source_sha256'])=={TARGET,PKG}
    assert doc['producer_resolution']=='STATIC_DIRECT_IMPORT_MATCH_NOT_RUNTIME_PROOF'


def test_legacy_path_still_supported(tmp_path):
    repo=work(tmp_path,sources=(LEGACY,))
    assert set(pins(repo)['source_sha256'])=={TARGET,LEGACY}


@pytest.mark.parametrize('location',[PKG,LEGACY])
def test_symlink_source_rejected_even_if_other_exists(tmp_path,location):
    repo=work(tmp_path,sources=(PKG,LEGACY))
    target=repo/location
    target.unlink()
    (repo/'safe.py').write_text('SYMBOL = 2')
    target.symlink_to(repo/'safe.py')
    with pytest.raises(PairError,match='symlink'): pins(repo)


def test_directory_instead_of_source_rejected(tmp_path):
    repo=work(tmp_path,sources=())
    (repo/PKG).mkdir(parents=True)
    with pytest.raises(PairError,match='unsafe'): pins(repo)


def test_mutating_source_changes_pin(tmp_path):
    repo=work(tmp_path)
    first=pins(repo)
    (repo/PKG).write_text('SYMBOL = 99\n')
    assert first!=pins(repo)


def test_package_pin_capture_load_roundtrip(tmp_path):
    repo=work(tmp_path)
    doc=capture({'runs':[0,1]},pins(repo))
    out=tmp_path/'run.json';out.write_text(json.dumps(doc))
    assert load_capture(out)==doc


def test_tampered_producer_path_is_rejected(tmp_path):
    repo=work(tmp_path)
    doc=capture({'runs':[0,1]},pins(repo))
    hashes=doc['producer_pins']['source_sha256']
    hashes['search/fictional_module_v0e.py']=hashes.pop(PKG)
    out=tmp_path/'tampered.json';out.write_text(json.dumps(doc))
    with pytest.raises(PairError,match='source path'):load_capture(out)


def test_invalid_resolution_marker_is_rejected(tmp_path):
    repo=work(tmp_path)
    doc=capture({'runs':[0,1]},pins(repo))
    doc['producer_pins']['producer_resolution']='PROVED_RUNTIME_IDENTITY'
    out=tmp_path/'bad_resolution.json';out.write_text(json.dumps(doc))
    with pytest.raises(PairError,match='resolution'):load_capture(out)


def test_package_layout_cli_skips_real_body(tmp_path):
    code='''import pytest\nfrom pathlib import Path\n@pytest.fixture\ndef runs():\n    return {'off': {'end_tick':3}, 'on': {'end_tick':5}}\ndef test_feedback_causes_forward_source_link_wait(runs):\n    Path(%r).write_text('BAD')\n''' % str(tmp_path/'body-was-run')
    repo=work(tmp_path,test_source=code)
    out=tmp_path/'capture.json'
    root=Path(__file__).resolve().parents[1]
    cmd=[sys.executable,'-m','search.spk_bv_v0o_capture','--root',str(repo),'--out',str(out)]
    r=subprocess.run(cmd,cwd=root,capture_output=True,text=True)
    assert r.returncode==0,(r.stdout,r.stderr)
    assert not (tmp_path/'body-was-run').exists()
    result=load_capture(out)
    assert PKG in result['producer_pins']['source_sha256']


def test_unapproved_root_outside_rejected(tmp_path):
    repo=work(tmp_path,sources=())
    (tmp_path/'spk_bv_live_dual_scheduler_v0e.py').write_text('S=1')
    with pytest.raises(PairError,match='approved paths'):pins(repo)
