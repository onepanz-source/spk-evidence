"""Research-only harness; synthetic temp fixtures validate capture mechanics, not BV v0h."""
from __future__ import annotations
import dataclasses
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from spk_bv_research.native_capture_v0k import (
    CAPTURE_SCHEMA, TARGETS, NativeCaptureError, canonical_fixture,
    capture_result, shape_report, verify_probe, _sha,
)


def create_root(tmp_path):
    root = tmp_path/'fake_native_repo'
    (root/'search').mkdir(parents=True)
    (root/'tests').mkdir()
    contents = [
        b'# Native generator fixture surrogate. NOT actual BV v0h.\n',
        ("import pytest\n@pytest.fixture\ndef real_trace():\n"
         "    return {'packets':[{'packet_id':'native-1','batch':3,'receiver':'n3'}],"
         "'path':('a','b')}\n"
         "def test_context_aggregation_refuses_unverified_trace(real_trace):\n"
         "    raise AssertionError('the test body MUST NOT execute for capture')\n").encode(),
        b'#!/usr/bin/env bash\n# fake native v0h gate\n',
    ]
    doc={'schema':'spk-bv-native-source-probe/v0j','status':'STATIC_DISCOVERY_ONLY',
         'files_scanned':3,'scan_truncated':False,'files':[]}
    for rel, raw in zip(TARGETS,contents):
        path=root/rel;path.write_bytes(raw)
        doc['files'].append({'path':rel,'bytes':len(raw),
                             'source_sha256':hashlib.sha256(raw).hexdigest()})
    probe=tmp_path/'native-probe.json';probe.write_text(json.dumps(doc))
    return root,probe


def test_valid_probe(tmp_path):
    root,probe=create_root(tmp_path)
    pins=verify_probe(root,probe)
    assert pins['status']=='PINNED_BYTES_ONLY'
    assert len(pins['source_sha256'])==3


def test_probe_wrong_source_hash_rejected(tmp_path):
    root,probe=create_root(tmp_path)
    (root/TARGETS[1]).write_text('changed')
    with pytest.raises(NativeCaptureError,match='source hash/size mismatch'):
        verify_probe(root,probe)


def test_probe_missing_target_rejected(tmp_path):
    root,probe=create_root(tmp_path)
    doc=json.loads(probe.read_text())
    doc['files']=doc['files'][:2];doc['files_scanned']=2
    probe.write_text(json.dumps(doc))
    with pytest.raises(NativeCaptureError,match='required v0h source absent'):
        verify_probe(root,probe)


def test_probe_truncated_rejected(tmp_path):
    root,probe=create_root(tmp_path)
    doc=json.loads(probe.read_text());doc['scan_truncated']=True
    probe.write_text(json.dumps(doc))
    with pytest.raises(NativeCaptureError,match='probe incomplete'):
        verify_probe(root,probe)


def test_probe_duplicate_keys_rejected(tmp_path):
    root,probe=create_root(tmp_path)
    doc=probe.read_text();probe.write_text(doc[:-1]+',"status":"STATIC_DISCOVERY_ONLY"}')
    with pytest.raises(NativeCaptureError,match='duplicate JSON key'):
        verify_probe(root,probe)


def test_probe_symlink_rejected(tmp_path):
    root,probe=create_root(tmp_path)
    target=root/TARGETS[1];content=target.read_bytes();target.unlink()
    real=tmp_path/'outside.py';real.write_bytes(content)
    target.symlink_to(real)
    with pytest.raises(NativeCaptureError,match='unsafe target path'):
        verify_probe(root,probe)


def test_scalar_tuples_not_silently_collapsed():
    a=canonical_fixture({'v':[1,2],'w':(1,2)})
    assert _sha(canonical_fixture([1,2])) != _sha(canonical_fixture((1,2)))
    assert a['$t']=='dict'
    assert 'dict' in shape_report(a)['node_types']


def test_dict_order_independent():
    assert _sha(canonical_fixture({'a':1,'b':2})) == _sha(canonical_fixture({'b':2,'a':1}))


def test_unsupported_object_fails_not_stringified():
    with pytest.raises(NativeCaptureError,match='unsupported native object'):
        canonical_fixture(object())


def test_cycle_fails_closed():
    x=[];x.append(x)
    with pytest.raises(NativeCaptureError,match='cyclic object graph'):
        canonical_fixture(x)


def test_nonfinite_rejected():
    with pytest.raises(NativeCaptureError,match='nonfinite float'):
        canonical_fixture({'value':float('nan')})


def test_dataclass_structure():
    @dataclasses.dataclass
    class Packet:
        packet_id: str
        tick: int
    with pytest.raises(NativeCaptureError,match='local-class dataclass'):
        canonical_fixture(Packet('t1',3))


def test_large_int_rejected():
    with pytest.raises(NativeCaptureError,match='integer out of bound'):
        canonical_fixture(2**64)


def test_shape_candidate_sequence_report():
    out=capture_result({'feedback_packets':[{'id':'A'},{'id':'B'}]},
                       {'source_sha256':{},'status':'PINNED_BYTES_ONLY'})
    assert out['schema']==CAPTURE_SCHEMA
    assert out['native_v0h_verified'] is False
    assert out['structure']['candidate_sequences'][0]['count']==2
    assert 'physical-packet-bijection' in out['excluded_claims']


def test_duplicate_native_values_preserved():
    result=canonical_fixture([{'packet_id':'a'}, {'packet_id':'a'}])
    assert len(result['items'])==2


def test_source_capture_pytest_fixture_executed_not_test_body(tmp_path):
    root,probe=create_root(tmp_path)
    dst=tmp_path/'captured.json'
    cmd=[sys.executable,'-m','search.spk_bv_v0k_capture',
         '--root',str(root),'--probe',str(probe),'--out',str(dst)]
    env=os.environ|{'PYTHONPATH':str(Path(__file__).resolve().parents[1]),'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'}
    result=subprocess.run(cmd,cwd=Path(__file__).resolve().parents[1],
                          capture_output=True,text=True,env=env)
    assert result.returncode==0,(result.stdout,result.stderr)
    data=json.loads(dst.read_text())
    assert data['native_fixture_sha256']
    assert any(x['path'].endswith('/packets') and x['count']==1
               for x in data['structure']['candidate_sequences'])
    assert data['selected_test']=='test_context_aggregation_refuses_unverified_trace'
    assert data['native_v0h_verified'] is False
    # v0k must not claim independent verification of the synthetic fixture.
    assert 'BV-v0h-equivalence' in data['excluded_claims']


def test_capture_does_not_overwrite(tmp_path):
    root,probe=create_root(tmp_path)
    dst=tmp_path/'captured.json';dst.write_text('sentinel')
    cmd=[sys.executable,'-m','search.spk_bv_v0k_capture','--root',str(root),
         '--probe',str(probe),'--out',str(dst)]
    env=os.environ|{'PYTHONPATH':str(Path(__file__).resolve().parents[1]),'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'}
    result=subprocess.run(cmd,capture_output=True,text=True,env=env)
    assert result.returncode==2
    assert dst.read_text()=='sentinel'


def test_capture_missing_fixture_rejected(tmp_path):
    root,probe=create_root(tmp_path)
    file=root/TARGETS[1]
    file.write_text('def test_context_aggregation_refuses_unverified_trace():\n    pass\n')
    doc=json.loads(probe.read_text())
    for record in doc['files']:
        if record['path']==TARGETS[1]:
            raw=file.read_bytes();record['bytes']=len(raw);record['source_sha256']=hashlib.sha256(raw).hexdigest()
    probe.write_text(json.dumps(doc))
    dst=tmp_path/'captured.json'
    cmd=[sys.executable,'-m','search.spk_bv_v0k_capture', '--root',str(root),
         '--probe',str(probe),'--out',str(dst)]
    env=os.environ|{'PYTHONPATH':str(Path(__file__).resolve().parents[1]),'PYTEST_DISABLE_PLUGIN_AUTOLOAD':'1'}
    result=subprocess.run(cmd,capture_output=True,text=True,env=env)
    assert result.returncode==2 and not dst.exists(),(result.stdout,result.stderr)


def test_static_import_dependency_census_finds_unscanned_modules(tmp_path):
    from spk_bv_research.dependency_census_v0k import census
    root,probe=create_root(tmp_path)
    (root/'spk_bv_research').mkdir()
    (root/'spk_bv_research'/'native_events.py').write_text(
        'def emit(packet):\n    return packet["physical_packet_id"]\n')
    entry=root/TARGETS[0]
    entry.write_text('from spk_bv_research.native_events import emit\n')
    result=census(root)
    paths={x['path'] for x in result['files']}
    assert 'spk_bv_research/native_events.py' in paths
    assert 'physical_packet_id' in next(x for x in result['files'] if x['path']=='spk_bv_research/native_events.py')['literal_subscript_keys']


def test_census_no_import_execution(tmp_path):
    from spk_bv_research.dependency_census_v0k import census
    root,probe=create_root(tmp_path)
    target=tmp_path/'should-not-exist'
    (root/TARGETS[0]).write_text(f'from pathlib import Path\nPath({str(target)!r}).write_text("leaked")\n')
    report=census(root)
    assert report['files_scanned']==2
    assert not target.exists()


def test_census_rejects_symlinked_dependency(tmp_path):
    from spk_bv_research.dependency_census_v0k import census
    root,probe=create_root(tmp_path)
    (root/'spk_bv_research').mkdir()
    outside=tmp_path/'native.py';outside.write_text('def answer(): return 1\n')
    (root/'spk_bv_research'/'native.py').symlink_to(outside)
    (root/TARGETS[0]).write_text('from spk_bv_research.native import answer\n')
    with pytest.raises(NativeCaptureError,match='dependency is a symlink'):
        census(root)
