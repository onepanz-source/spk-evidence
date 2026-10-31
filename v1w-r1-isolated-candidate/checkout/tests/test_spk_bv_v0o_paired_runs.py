"""BV v0o research tests: no inference of real v0e treatment parity from synthetic data."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from spk_bv_research.paired_runs_v0o import (
    CASE, SCHEMA, STATUS, PAIR_STATUS, TARGET, MODULE, PairError,
    capture, pins, load_capture, inventory, compare, publish_new,
)

PINS={'status':'LOCAL_SOURCE_BYTES_PINNED_NOT_INDEPENDENT','source_sha256':{
    TARGET:'a'*64,'search/'+MODULE:'b'*64}}

def synth():
    return {'disabled':{'inputs':{'seed':19,'events':[(0,1),(2,3)],'placement':['PE0','PE1']},
                        'events':[{'tick':2,'kind':'forward'}], 'last_tick':2,'feedback_grants':[]},
            'enabled':{'inputs':{'seed':19,'events':[(0,1),(2,3)],'placement':['PE0','PE1']},
                       'events':[{'tick':3,'kind':'forward'}], 'last_tick':3,
                       'feedback_grants':[{'tick':2,'packet_id':'p1'},{'tick':3,'packet_id':'p2'}]}}

def spec():
    return {'baseline':['disabled'],'enabled':['enabled'],
            'workload_witnesses':[{'name':'entire-declared-input-object','baseline_path':['inputs'],'enabled_path':['inputs']}],
            'metrics':{
                'forward_end_tick':{'baseline':{'path':['last_tick'],'op':'int'},
                                    'enabled':{'path':['last_tick'],'op':'int'}},
                'feedback_grants':{'baseline':{'path':['feedback_grants'],'op':'count'},
                                   'enabled':{'path':['feedback_grants'],'op':'count'}}}}

def doc(): return capture(synth(),deepcopy(PINS))

def copy_to(tmp_path, obj, name='native.json'):
    path=tmp_path/name
    path.write_text(json.dumps(obj,sort_keys=True))
    return path


def test_capture_typed_and_hash(tmp_path):
    d=doc(); assert d['schema']==SCHEMA and d['status']==STATUS
    assert load_capture(copy_to(tmp_path,d))==d


def test_native_inventory_contains_branches():
    inv=inventory(doc())
    assert inv['status']=='STRUCTURAL_INVENTORY_ONLY'
    paths=[row['path'] for row in inv['entries']]
    assert ['enabled','feedback_grants'] in paths
    assert ['disabled','inputs'] in paths
    assert 'causal-effects' in inv['claims_excluded']


def test_compare_explicitly_declared_structural_parity():
    out=compare(doc(),spec())
    assert out['status']==PAIR_STATUS
    assert out['observed_metrics']['feedback_grants']=={'baseline':0,'enabled':2,'delta_enabled_minus_baseline':2}
    assert out['observed_metrics']['forward_end_tick']['delta_enabled_minus_baseline']==1
    assert out['declared_equal_witnesses'][0]['equal_selected_values'] is True
    assert 'causal-feedback-cost' in out['claims_excluded']


def test_comparison_hashseed_deterministic(tmp_path):
    d=doc();cfg=spec()
    p=copy_to(tmp_path,d)
    c=copy_to(tmp_path,cfg,'spec.json')
    repo=Path(__file__).resolve().parents[1]
    code="import json,sys;from pathlib import Path;from spk_bv_research.paired_runs_v0o import load_capture,compare;print(json.dumps(compare(load_capture(Path(sys.argv[1])),json.load(open(sys.argv[2]))),sort_keys=True))"
    a=subprocess.run([sys.executable,'-c',code,str(p),str(c)],cwd=repo,capture_output=True,text=True,env={**__import__('os').environ,'PYTHONHASHSEED':'13'})
    b=subprocess.run([sys.executable,'-c',code,str(p),str(c)],cwd=repo,capture_output=True,text=True,env={**__import__('os').environ,'PYTHONHASHSEED':'811'})
    assert a.returncode==b.returncode==0,(a.stderr,b.stderr)
    assert a.stdout==b.stdout


@pytest.mark.parametrize('mutate,pattern',[
    (lambda d:d.update(schema='unknown'),'envelope'),
    (lambda d:d.update(status='PASS'),'envelope'),
    (lambda d:d.update(selected_test='anything'),'envelope'),
    (lambda d:d.update(selected_fixture='other'),'envelope'),
    (lambda d:d.update(native_fixture_sha256='f'*64),'hash'),
    (lambda d:d.update(structure={}),'shape'),
    (lambda d:d.update(producer_pins={}), 'provenance'),
    (lambda d:d['producer_pins']['source_sha256'].update({'fake':'c'*64}), 'provenance'),
    (lambda d:d.update(claims_excluded=[]),'exclusions'),
    (lambda d:d.update(native_fixture={'$t':'dict','pairs':[]}), 'hash'),
])
def test_capture_rejects_adversarial_envelope(tmp_path,mutate,pattern):
    d=doc();mutate(d)
    with pytest.raises(PairError,match=pattern):load_capture(copy_to(tmp_path,d))


def test_missing_equal_input_refused():
    d=doc();spec1=spec();spec1['workload_witnesses'][0]['enabled_path']=['last_tick']
    with pytest.raises((ValueError,PairError),match='not equal'):compare(d,spec1)

@pytest.mark.parametrize('alter',[
    lambda s:s.update(baseline=['enabled']),
    lambda s:s.update(enabled=['disabled']),
    lambda s:s.update(baseline=['fake']),
    lambda s:s.update(enabled=[99]),
    lambda s:s.update(workload_witnesses=[]),
    lambda s:s.update(workload_witnesses=[{'name':'x','baseline_path':['inputs']}]),
    lambda s:s.update(metrics={}),
    lambda s:s['metrics']['forward_end_tick']['enabled'].update(op='float'),
    lambda s:s['metrics']['forward_end_tick']['enabled'].update(path=['feedback_grants']),
    lambda s:s['metrics']['feedback_grants']['baseline'].update(path=['last_tick']),
    lambda s:s.update(hardware_energy=9),
    lambda s:s.update(baseline=[True]),
    lambda s:s.update(enabled=['enabled','unseen']),
])
def test_bad_spec_refused(alter):
    s=spec();alter(s)
    with pytest.raises((ValueError,KeyError,TypeError,PairError)):compare(doc(),s)


def test_duplicate_declared_witness_name_refused():
    cfg=spec();cfg['workload_witnesses'].append(deepcopy(cfg['workload_witnesses'][0]))
    with pytest.raises(PairError,match='repeated'): compare(doc(),cfg)


def test_identical_outcomes_refused():
    v=synth();v['enabled']=deepcopy(v['disabled'])
    with pytest.raises(PairError,match='identical'):compare(capture(v,PINS),spec())


def test_input_divergence_refused_even_when_outcome_metrics_same():
    v=synth();v['enabled']['inputs']['seed']=100
    with pytest.raises(PairError,match='not equal'):compare(capture(v,PINS),spec())


def test_output_immutable_and_fail_no_overwrite(tmp_path):
    path=tmp_path/'out.json';publish_new(path,inventory(doc()))
    original=path.read_bytes()
    with pytest.raises(PairError,match='overwrite'):publish_new(path,{'modified':True})
    assert path.read_bytes()==original


def test_output_inside_source_path_refused(tmp_path):
    root=tmp_path/'repo';root.mkdir()
    with pytest.raises(PairError,match='unsafe'):publish_new(root/'bad.json',{},forbidden=(root,))


def test_source_pins_detect_mutations(tmp_path):
    root=tmp_path/'repo'; (root/'tests').mkdir(parents=True);(root/'search').mkdir()
    (root/TARGET).write_text('def hello(): return 1\n')
    (root/'search'/MODULE).write_text('VALUE = 1\n')
    a=pins(root)
    assert len(a['source_sha256'])==2
    (root/TARGET).write_text('def hello(): return 2\n')
    assert a!=pins(root)


def test_source_pins_refuse_symlink(tmp_path):
    root=tmp_path/'repo'; (root/'tests').mkdir(parents=True);(root/'search').mkdir()
    (root/'other.py').write_text('hello')
    (root/TARGET).symlink_to(root/'other.py')
    (root/'search'/MODULE).write_text('v=1')
    with pytest.raises(PairError,match='unsafe'):pins(root)


def test_cli_inspection_no_overwrite(tmp_path):
    d=doc();cap=copy_to(tmp_path,d);out=tmp_path/'report.json'
    repo=Path(__file__).resolve().parents[1]
    args=[sys.executable,'-m','search.spk_bv_v0o_analyze','--capture',str(cap),'--out',str(out),'--expected-fixture-sha',d['native_fixture_sha256']]
    x=subprocess.run(args,cwd=repo,capture_output=True,text=True)
    assert x.returncode==0,x.stderr
    assert json.loads(out.read_text())['schema']=='spk-bv-live-runs-inventory/v0o'
    y=subprocess.run(args,cwd=repo,capture_output=True,text=True)
    assert y.returncode==2


def test_cli_explicit_comparison(tmp_path):
    d=doc();cap=copy_to(tmp_path,d);cfg=copy_to(tmp_path,spec(),'selector.json');out=tmp_path/'report.json'
    repo=Path(__file__).resolve().parents[1]
    cmd=[sys.executable,'-m','search.spk_bv_v0o_analyze','--capture',str(cap),'--out',str(out),'--compare-config',str(cfg),'--expected-fixture-sha',d['native_fixture_sha256']]
    r=subprocess.run(cmd,cwd=repo,capture_output=True,text=True)
    assert r.returncode==0,r.stderr
    assert json.loads(out.read_text())['observed_metrics']['feedback_grants']['enabled']==2


def test_cli_hash_reject_without_creating_file(tmp_path):
    cap=copy_to(tmp_path,doc());out=tmp_path/'bad.json';repo=Path(__file__).resolve().parents[1]
    r=subprocess.run([sys.executable,'-m','search.spk_bv_v0o_analyze','--capture',str(cap),'--out',str(out),'--expected-fixture-sha','0'*64],cwd=repo,capture_output=True,text=True)
    assert r.returncode==2 and not out.exists()


def test_capture_plugin_skips_native_body(tmp_path):
    # Isolated, synthetic pytest producer. Real native v0e must be separately run on fwork.
    root=tmp_path/'repo';(root/'tests').mkdir(parents=True);(root/'search').mkdir()
    marker=tmp_path/'body-executed.txt'
    (root/TARGET).write_text('import pytest\nfrom pathlib import Path\n\n@pytest.fixture\ndef runs():\n    return {"disabled":{"events":[]}, "enabled":{"events":[1]}}\n\ndef test_feedback_causes_forward_source_link_wait(runs):\n    Path('+repr(str(marker))+').write_text("EXECUTED")\n')
    (root/'search'/MODULE).write_text('# local synthetic pinned module\n')
    from search.spk_bv_v0o_capture import run_native
    import os
    cwd=Path.cwd()
    try:
        result=run_native(root)
    finally:
        os.chdir(cwd)
    assert result['enabled']['events']==[1]
    assert not marker.exists()
