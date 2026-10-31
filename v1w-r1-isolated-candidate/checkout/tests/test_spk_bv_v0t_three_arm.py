from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import copy
import json

import pytest
from spk_bv_research import off_on_v0t as m

@dataclass(frozen=True)
class Plan:
    enabled: bool=True
    priority: str='forward-first'
    assessor: str='C'

@dataclass(frozen=True)
class Input:
    events: tuple=(1,3)


def base_fixture():
    return Input(),Input(events=(4,5)),(1,2,3,4)


def fake_scheduler(case,fabric,a,b,c,d,bv):
    assert (a,b,c,d)==(1,2,3,4)
    assert case.events==(1,3)
    assert fabric.events==(4,5)
    is_on=bv.enabled
    is_bf=bv.priority=='feedback-first'
    term=5+2*is_bf if is_on else 4
    feedback_grants=4 if is_on else 0
    feedback_rows=[{'tick':i+2,'packet_id':'p'+str(i)} for i in range(feedback_grants)]
    forward_grants=[{'wait':2 if is_bf else 0}]
    return {'schema':'spk-bv-live-dual-event-scheduler/v0e',
            'enabled':is_on,'policy':bv.priority,
            'forward':{'states':{'A':1},'processed_events':2,'processed_batches':2,
                       'batches':[{},{}],
                       'emissions':[{'node_id':'A','channel':7,'timestamp':term}],
                       'terminal':[{'node_id':'A','channel':7,'timestamp':term}],
                       'link_grants':forward_grants,'occurrences':[{}]},
            'feedback':{'assessments':[{}] if is_on else [],
                        'deliveries': feedback_rows, 'link_grants':[{'wait':2 if is_bf else 1} for _ in range(feedback_grants)],
                        'unique_receiver_votes':feedback_grants},
            'resources':{'bv_link_grants':feedback_grants, 'bv_service_units':feedback_grants,
                         'bv_memory_units':feedback_grants*2,'forward_reserved_memory_units':10,
                         'peak_cross_inflight':1, 'contention':{'fabric_link':2 if is_bf else 5 if is_on else 0},
                         'timeline':[{'tick':i, 'feedback_sends':1 if is_on and 2<=i<6 else 0,
                                      'memory_total':2 if is_on else 0,
                                      'link_total':1 if is_on else 0,
                                      'pe_service_total':1} for i in range(9)]}}


def make():
    return m.execute_three(base_fixture,fake_scheduler,Plan,root=Path.cwd(),pin_sources=False)


def test_three_runs_and_toggle_only():
    x=make()
    assert x['schema']==m.SCHEMA and x['status']==m.STATUS
    assert x['runs']['off']['metrics']['feedback_link_grants']==0
    assert x['runs']['on_forward_first']['metrics']['feedback_link_grants']==4
    assert x['runs']['on_feedback_first']['metrics']['feedback_link_grants']==4
    assert x['interventions']['toggle_enabled_only']['metric_deltas']['bv_service_units']==4
    assert x['interventions']['change_priority_only']['metric_deltas']['bv_service_units']==0
    assert x['interventions']['change_priority_only']['last_terminal_tick_delta']==2
    assert x['interventions']['toggle_enabled_only']['last_terminal_tick_delta']==1


def test_conserved_results_not_assumed_from_timestamp():
    x=make(); y=x['interventions']['change_priority_only']
    assert y['state_hash_equal'] and y['terminal_payload_multiset_equal']
    assert x['runs']['off']['forward_states_sha256']==x['runs']['on_forward_first']['forward_states_sha256']


def test_deterministic_replay():
    a=make();b=make()
    assert a==b
    assert m.snapshot(a)==m.snapshot(b)

@pytest.mark.parametrize('attr', ['enabled','priority'])
def test_reject_scheduler_ignoring_control(attr):
    def run(*args):
        result=fake_scheduler(*args)
        result[attr if attr=='enabled' else 'policy'] = False if attr=='enabled' else 'wrong'
        return result
    with pytest.raises(m.InterventionError, match='honor control'):
        m.execute_three(base_fixture,run,Plan,root=Path.cwd(),pin_sources=False)


def test_reject_mutation_of_fixture():
    def f():return Input(),Input(),([1],2,3,4)
    def run(case,fabric,a,b,c,d,bv):
        a.append(1)
        return fake_scheduler(case,Input(events=(4,5)),1,2,3,4,bv)
    with pytest.raises(m.InterventionError,match='mutated'):
        m.execute_three(f,run,Plan,root=Path.cwd(),pin_sources=False)


def test_reject_off_feedback():
    def run(*args):
        result=fake_scheduler(*args)
        if args[-1].enabled is False:
            result['feedback']['assessments']=[{}]
        return result
    with pytest.raises(m.InterventionError,match='OFF control'):
        m.execute_three(base_fixture,run,Plan,root=Path.cwd(),pin_sources=False)


def test_reject_off_timeline_feedback():
    def run(*args):
        result=fake_scheduler(*args)
        if args[-1].enabled is False:result['resources']['timeline'][0]['feedback_sends']=1
        return result
    with pytest.raises(m.InterventionError,match='OFF control'):
        m.execute_three(base_fixture,run,Plan,root=Path.cwd(),pin_sources=False)


def test_reject_no_feedback_activity():
    def run(*args):
        x=fake_scheduler(*args)
        x['resources']['bv_link_grants']=0
        x['resources']['bv_service_units']=0
        x['resources']['bv_memory_units']=0
        x['feedback']['assessments']=[];x['feedback']['deliveries']=[]
        x['feedback']['link_grants']=[];x['feedback']['unique_receiver_votes']=0
        return x
    with pytest.raises(m.InterventionError,match='no feedback'):
        m.execute_three(base_fixture,run,Plan,root=Path.cwd(),pin_sources=False)


def test_reject_bad_fixture_length():
    with pytest.raises(m.InterventionError,match='fixture'):
        m.execute_three(lambda:(1,2,(1,2,3)),fake_scheduler,Plan,root=Path.cwd(),pin_sources=False)


def test_reject_wrong_plan_type():
    with pytest.raises(m.InterventionError,match='dataclass'):
        m.execute_three(base_fixture,fake_scheduler,str,root=Path.cwd(),pin_sources=False)

@pytest.mark.parametrize('mutation,reason', [
    (lambda x:x['forward'].__setitem__('processed_batches',False),'nonnegative int'),
    (lambda x:x['forward'].__setitem__('batches',[]),'accounting mismatch'),
    (lambda x:x['resources'].__setitem__('bv_memory_units',999),'memory accounting'),
    (lambda x:x['resources']['timeline'][1].__setitem__('tick',0),'duplicated timeline'),
    (lambda x:x['forward']['terminal'][0].__setitem__('timestamp',False),'timestamp'),
    (lambda x:x['feedback'].__setitem__('link_grants',{}),'bad list'),
])
def test_reject_invalid_observation(mutation,reason):
    x=fake_scheduler(*base_fixture()[:2],*base_fixture()[2],Plan())
    mutation(x)
    with pytest.raises(m.InterventionError,match=reason):
        m.summarize(x,enabled=True,priority='forward-first')


def test_source_pins_good_and_drift(tmp_path,monkeypatch):
    paths={'tests/native.py':b'hello','search/fixture.py':b'def fixture():return None'}
    monkeypatch.setattr(m,'PINNED',{p:sha256(data).hexdigest() for p,data in paths.items()})
    for p,data in paths.items():
        f=tmp_path/p;f.parent.mkdir(exist_ok=True);f.write_bytes(data)
    assert m.source_pins(tmp_path)==m.PINNED
    (tmp_path/'tests/native.py').write_bytes(b'evil')
    with pytest.raises(m.InterventionError,match='drift'):m.source_pins(tmp_path)


def test_source_pins_symlink(tmp_path,monkeypatch):
    a=tmp_path/'a.py';a.write_text('ok')
    (tmp_path/'b.py').symlink_to(a)
    monkeypatch.setattr(m,'PINNED',{'b.py':sha256(b'ok').hexdigest()})
    with pytest.raises(m.InterventionError,match='unsafe'):m.source_pins(tmp_path)


def test_source_pins_missing(tmp_path,monkeypatch):
    monkeypatch.setattr(m,'PINNED',{'missing.py':'0'*64})
    with pytest.raises(m.InterventionError,match='absent'):m.source_pins(tmp_path)


def test_hist_payload_duplicate_multiplicity():
    a=[{'id':1,'timestamp':2},{'id':1,'timestamp':3}]
    b=[{'id':1,'timestamp':3},{'id':2,'timestamp':2}]
    assert m.hist_payload(a,('timestamp',))!=m.hist_payload(b,('timestamp',))


def test_no_witness_of_hardware_cost():
    x=make()
    assert 'no-hardware-latency-energy' in x['claims_excluded']
    assert 'no-proof-of-BV-informational-benefit' in x['claims_excluded']


def test_runtime_module_pinning_fails_external(monkeypatch,tmp_path):
    def fixture():pass
    with pytest.raises(m.InterventionError,match='runtime module'):
        m.runtime_modules_bound(tmp_path,fake_scheduler,fixture,Plan)


def test_reference_exact_on_replay():
    from spk_bv_research.native_capture_v0k import canonical_fixture
    report=make()
    case,fabric,plans=base_fixture()
    f= fake_scheduler(case,fabric,*plans,Plan(enabled=True,priority='forward-first'))
    b= fake_scheduler(case,fabric,*plans,Plan(enabled=True,priority='feedback-first'))
    typed=canonical_fixture((case,fabric,plans,f,b))
    assert m.compare_reference_v0o(report,typed)['reference_shared_input_equal']


def test_reference_wrong_on_output_rejected():
    from spk_bv_research.native_capture_v0k import canonical_fixture
    report=make()
    case,fabric,plans=base_fixture()
    f=fake_scheduler(case,fabric,*plans,Plan(enabled=True,priority='forward-first'))
    b=fake_scheduler(case,fabric,*plans,Plan(enabled=True,priority='feedback-first'))
    f['forward']['terminal'][0]['timestamp']=50
    typed=canonical_fixture((case,fabric,plans,f,b))
    with pytest.raises(m.InterventionError,match='differs from'):
        m.compare_reference_v0o(report,typed)


def test_reference_wrong_input_rejected():
    from spk_bv_research.native_capture_v0k import canonical_fixture
    report=make()
    case,fabric,plans=base_fixture()
    f=fake_scheduler(case,fabric,*plans,Plan(enabled=True,priority='forward-first'))
    b=fake_scheduler(case,fabric,*plans,Plan(enabled=True,priority='feedback-first'))
    typed=canonical_fixture((Input(events=(2,3)),fabric,plans,f,b))
    with pytest.raises(m.InterventionError,match='input !='):
        m.compare_reference_v0o(report,typed)


def test_reference_bad_tuple_rejected():
    with pytest.raises(m.InterventionError,match='tuple'):
        m.compare_reference_v0o(make(),{'$t':'tuple','items':[1,2]})


def test_hashseed_invariant_fake_model_subprocess(tmp_path):
    import subprocess, sys, os
    test_path=Path(__file__).resolve()
    script='''import importlib.util,sys
p=sys.argv[1]
s=importlib.util.spec_from_file_location("bv_v0t_local_fixture",p)
m=importlib.util.module_from_spec(s)
sys.modules[s.name]=m
s.loader.exec_module(m)
print(m.m.snapshot(m.make()))'''
    hashes=[]
    for seed in ('13','811'):
        env=os.environ.copy()
        env['PYTHONHASHSEED']=seed
        env['PYTHONPATH']=str(test_path.parents[1])+os.pathsep+env.get('PYTHONPATH','')
        p=subprocess.run([sys.executable,'-c',script,str(test_path)],
                         env=env,check=True,capture_output=True,text=True,timeout=10)
        hashes.append(p.stdout.strip())
    assert hashes[0]==hashes[1]
