"""Fail-closed derivative and native/fork parity contract."""
import ast
import json
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import pytest

def report_path(name):
    for folder in ('/tmp','/mnt/data'):
        p=Path(folder)/name
        if p.is_file():return p
    return Path('/tmp')/name

from spk_backvalidation_v2.derived_native_fork_v2g import (
  audited_function,derive_executor,CallsiteObserver,NativeForkError,
  EXPECTED_CALLS,PORT_VERSION, PINNED_SCHED,
)
from spk_bv_research.native_fork_differential_v2g import (
  build_report,validate_v2f,validate_v2e,SCHEMA,OFFLINE,STATUS,
)
from spk_bv_research.native_allocation_boundary_v1r import canon

SYN='''\ndef execute_live_v0e(case,fabric,tplan,pplan,mplan,lplan,bv):
    admitted=_admit(case,fabric)
    plan=_admit_plan(admitted,tplan)
    if bv:
        offer_feedback(plan,1)
        offer_feedback(plan,2)
    return {"result":plan,"b":bv,"case":case}
'''
LINES=(('_admit',3),('_admit_plan',4),('offer_feedback',6),('offer_feedback',7))

def _admit(a,b):return a+b

def _admit_plan(x,y):return x*y

def offer_feedback(x,i):return x+i

def execute_live_v0e(case,fabric,tplan,pplan,mplan,lplan,bv):
    admitted=_admit(case,fabric)
    plan=_admit_plan(admitted,tplan)
    if bv:
        offer_feedback(plan,1)
        offer_feedback(plan,2)
    return {'result':plan,'b':bv,'case':case}

@pytest.mark.parametrize('bv', [False, True])
@pytest.mark.parametrize('case,fabric,tplan',[(2,3,4),(0,7,3),(1,-4,9)])
def test_derived_function_matches_original(bv,case,fabric,tplan):
    observer=CallsiteObserver()
    derived, inventory=derive_executor(SYN.encode(),execute_live_v0e,observer,
                                      expected_calls=LINES,enforce_sha=False)
    got=derived(case,fabric,tplan,None,None,None,bv)
    assert got==execute_live_v0e(case,fabric,tplan,None,None,None,bv)
    assert inventory==tuple(sorted(LINES))
    assert observer.counts()=={'_admit':1,'_admit_plan':1,'offer_feedback':2 if bv else 0}
    assert all(x.returned for x in observer.records)
    assert observer.attest()['native_receiver_packets']==0
    assert observer.attest()['native_source_owned'] is False

@pytest.mark.parametrize('capacity', [1,2,3,4])
def test_overflow_has_no_computational_effect(capacity):
    observer=CallsiteObserver(capacity=capacity)
    derived,_=derive_executor(SYN.encode(),execute_live_v0e,observer,
                              expected_calls=LINES,enforce_sha=False)
    assert derived(2,3,4,0,0,0,True)==execute_live_v0e(2,3,4,0,0,0,True)
    assert observer.overflow is (capacity<4)
    assert observer.offered==4

@pytest.mark.parametrize('exc_type', [RuntimeError,ValueError,LookupError])
def test_sink_failure_does_not_change_result(exc_type):
    def sink(_):raise exc_type('observer faulty')
    observer=CallsiteObserver(sink=sink)
    derived,_=derive_executor(SYN.encode(),execute_live_v0e,observer,
                              expected_calls=LINES,enforce_sha=False)
    assert derived(2,3,4,0,0,0,True)==execute_live_v0e(2,3,4,0,0,0,True)
    assert observer.sink_failed

@pytest.mark.parametrize('mutation', [
  'offer_feedback(plan,2)','return {"changed":plan}',
  '_admit_plan(admitted,tplan)','def execute_live_v0e(case,fabric,tplan,pplan,mplan,lplan,bv):',
])
def test_drift_rejected(mutation):
    if mutation=='offer_feedback(plan,2)': src=SYN.replace(mutation,'offer_feedback(plan,3)')
    elif mutation=='return {"changed":plan}': src=SYN.replace('return {"result":plan', 'return {"changed":plan')
    elif mutation=='_admit_plan(admitted,tplan)': src=SYN.replace(mutation,'_admit_plan(admitted,tplan)+_admit_plan(admitted,tplan)')
    else: src=SYN.replace(mutation,'def execute_live_v0e(case,fabric,tplan,pplan,mplan,lplan,observer,bv):')
    with pytest.raises(NativeForkError):
        audited_function(src.encode(),expected_calls=LINES,enforce_sha=True)

@pytest.mark.parametrize('bad', [
 SYN.replace('offer_feedback(plan,2)','none(plan,2)'),
 SYN.replace('offer_feedback(plan,2)','offer_feedback(plan,2)\n        offer_feedback(plan,3)'),
 SYN.replace('def execute_live_v0e(case,fabric,tplan,pplan,mplan,lplan,bv):',
             'def execute_live_v0e(case,fabric,tplan,pplan,mplan,lplan,bv,*args):'),
 SYN+'\ndef execute_live_v0e(case,fabric,tplan,pplan,mplan,lplan,bv):return 0\n',
])
def test_inventory_adversarial_reject(bad):
    with pytest.raises(NativeForkError):
        audited_function(bad.encode(),expected_calls=LINES,enforce_sha=False)


def test_types_fail_closed():
    for value in (0,False,'4',-1,32769):
        with pytest.raises(NativeForkError):CallsiteObserver(capacity=value)
    with pytest.raises(NativeForkError):CallsiteObserver(sink=1)
    with pytest.raises(NativeForkError):derive_executor(SYN.encode(),None,CallsiteObserver(),
                                   expected_calls=LINES,enforce_sha=False)


def test_original_global_not_patched():
    observer=CallsiteObserver()
    before=execute_live_v0e.__globals__['_admit']
    clone,_=derive_executor(SYN.encode(),execute_live_v0e,observer,
                            expected_calls=LINES,enforce_sha=False)
    clone(2,3,4,0,0,0,True)
    assert execute_live_v0e.__globals__['_admit'] is before
    assert '__spk_v2g_wrap' not in execute_live_v0e.__globals__


def test_pin_and_version():
    assert len(PINNED_SCHED)==64
    assert len(EXPECTED_CALLS)==4
    assert PORT_VERSION.endswith('/v2g')


def test_offline_report_from_real_predecessors():
    from pathlib import Path
    paths=[report_path('spk-bv-v2f-integrated-milestone.json'),
           report_path('spk-bv-v2e-native-admission-discrimination.json')]
    if not all(p.exists() for p in paths):pytest.skip('local previous reports not mounted')
    x,y=[p.read_bytes() for p in paths]
    v2f,v2e=json.loads(x),json.loads(y)
    report=build_report(v2f,x,v2e,y)
    assert report['schema']==SCHEMA and report['status']==OFFLINE
    assert not report['derived_executor_has_runtime_invoked_metadata_port']
    assert report['new_frozen_original_runs']==0
    assert report['reference_v2f_sha256']==sha256(x).hexdigest()
    assert report['reference_v2e_sha256']==sha256(y).hexdigest()
    for key in ('native_B_receiver_control_messages','native_receiver_endogenous_judgments',
                'native_producer_authenticated_semantic_spikes','native_learner_updates'):
        assert report[key]==0
    assert canon(report)==canon(json.loads(canon(report)))


def test_invented_native_parity_is_rejected():
    from pathlib import Path
    paths=[report_path('spk-bv-v2f-integrated-milestone.json'),
           report_path('spk-bv-v2e-native-admission-discrimination.json')]
    if not all(p.exists() for p in paths):pytest.skip('local reports absent')
    x,y=[p.read_bytes() for p in paths]
    with pytest.raises((ValueError,KeyError,TypeError)):
        build_report(json.loads(x),x,json.loads(y),y,{'source_custody':False,
          'native_original_runs':45,'derived_runs':45})

@pytest.mark.parametrize('field,value',[
 ('native_receiver_B_control_messages',1),
 ('source_owned_research_micro_executions',64),
 ('frozen_native_source_pins_rechecked_in_this_run',False),
 ('research_control_messages_delivered_in_new_executor',51),
])
def test_predecessor_tamper_v2f(field,value):
    import pathlib
    p=report_path('spk-bv-v2f-integrated-milestone.json')
    q=report_path('spk-bv-v2e-native-admission-discrimination.json')
    if not p.exists() or not q.exists():pytest.skip('local reports absent')
    x=json.loads(p.read_bytes());x[field]=value
    with pytest.raises((ValueError,TypeError,AssertionError)):
        validate_v2f(x,canon(x),q.read_bytes())

@pytest.mark.parametrize('field,value',[
 ('new_frozen_scheduler_executions',44),
 ('full_native_v0w_anchor_replay_count',11),
 ('frozen_native_source_pins_rechecked_in_this_run',False),
 ('native_matrix',[]),
])
def test_predecessor_tamper_v2e(field,value):
    import pathlib
    p=report_path('spk-bv-v2e-native-admission-discrimination.json')
    if not p.exists():pytest.skip('local reports absent')
    x=json.loads(p.read_bytes());x[field]=value
    with pytest.raises((ValueError,TypeError,AssertionError)):
        validate_v2e(x,canon(x))
