"""BV v0u isolated/synthetic adversarial checks; native v0e must be run separately."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from spk_bv_research import link_pressure_v0u as u
from spk_bv_research import off_on_v0t as t


@dataclass(frozen=True)
class Link:
    fabric_slots_per_tick: int = 1
    link_slots_per_tick: int = 1
    max_outbox_per_pe: int = 16
    max_link_span_ticks: int = 128


@dataclass(frozen=True)
class Input:
    events: tuple = (1, 3)


@dataclass
class MutableInput:
    events: list


@dataclass(frozen=True)
class Plan:
    enabled: bool = True
    priority: str = 'forward-first'


def fixture():
    return Input(), Input(events=(2, 3)), (11, 12, 13, Link())


def fake(case, fabric, tplan, pplan, mplan, lplan, plan):
    assert isinstance(lplan, Link)
    enable=plan.enabled
    fb=plan.priority=='feedback-first'
    link=lplan.fabric_slots_per_tick
    term=(7 if fb else 5) if link==1 else (5 if fb else 4)
    grant_count=4 if enable else 0
    waits=(0 if fb else 5) if enable else 0
    # Track demand, not physical throughput. Both request classes remain observable.
    contention=(2 if fb else 5) if enable and link==1 else (1 if fb else 2) if enable else 0
    forward=[{'wait':2 if fb and link==1 else 0}]
    return {
        'schema':'spk-bv-live-dual-event-scheduler/v0e',
        'enabled':enable, 'policy':plan.priority,
        'forward':{
            'states':{'A':1},'processed_events':2,'processed_batches':2,
            'batches':[{},{}],
            'emissions':[{'node_id':'A','channel':7,'timestamp':term}],
            'terminal':[{'node_id':'A','channel':7,'timestamp':term}],
            'link_grants':forward,'occurrences':[{}]},
        'feedback':{
            'assessments':[{}] if enable else [],
            'deliveries':[{'tick':term+i} for i in range(grant_count)],
            'link_grants':[{'wait':waits if i==0 else 0} for i in range(grant_count)],
            'unique_receiver_votes':grant_count},
        'resources':{
            'bv_link_grants':grant_count,'bv_service_units':grant_count,
            'bv_memory_units':2*grant_count,'forward_reserved_memory_units':10,
            'peak_cross_inflight':1,'contention':{'fabric_link':contention},
            'timeline':[{'tick':i,'feedback_sends':1 if enable and 2<=i<6 else 0,
                         'memory_total':2 if enable else 0,
                         'link_total':1 if enable else 0,
                         'pe_service_total':1} for i in range(10)]},
    }


def sweep(**kw):
    return u.scan(kw.pop('fixture_fn',fixture), kw.pop('executor',fake),
                  kw.pop('plan_type',Plan), root=Path.cwd(), pin_sources=False, **kw)


def sample_reference():
    x=t.execute_three(fixture,fake,Plan,root=Path.cwd(),pin_sources=False)
    x['v0o_reference_check']={'status':'PINNED_V0O_ON_RUNS_REPLAYED_IN_THREE_ARM'}
    x['producer_source_sha256']=None
    return x


def test_all_cells_complete_three_arms():
    x=sweep()
    assert x['schema']==u.SCHEMA and x['status']==u.STATUS
    assert len(x['cells']) == 5
    assert x['grid'] == [c['link_capacity'] for c in x['cells']]
    for cell in x['cells']:
        assert cell['status']=='THREE_ARMS_OBSERVED'
        assert set(cell['runs'])=={'off','on_forward_first','on_feedback_first'}
        assert cell['runs']['off']['metrics']['feedback_link_grants']==0
        assert cell['runs']['on_feedback_first']['metrics']['feedback_link_grants']==4
        assert cell['runs']['on_forward_first']['metrics']['feedback_link_grants']==4
        assert cell['interventions']['toggle_enabled_only']['metric_deltas']['bv_memory_units']==8
        assert cell['local_proxy_frontier']['nondominated']
        assert isinstance(cell['shared_cell_input_sha256'],str)


def test_base_sha_consistent():
    assert sweep()['original_fixture_sha256'] == t.snapshot(fixture())


def test_first_cell_matches_previous_baseline():
    x=sweep();ref=sample_reference()
    assert u.verify_v0t_baseline(x,ref)['status']=='PINNED_V0T_AND_V0O_BASELINE_REPLAYED'


def test_capacity_change_effect_is_separated_from_policy():
    x=sweep()
    f1=x['cells'][0]['runs']['on_feedback_first']['last_forward_terminal_tick']
    f2=x['cells'][2]['runs']['on_feedback_first']['last_forward_terminal_tick']
    assert f1 == 7 and f2 == 5
    assert x['cells'][0]['runs']['off']['last_forward_terminal_tick']==5
    assert x['cells'][2]['runs']['off']['last_forward_terminal_tick']==4


def test_deterministic_in_process():
    assert sweep()==sweep()


def test_no_source_claim_without_actual_pinning():
    assert sweep()['source_sha256'] is None


def test_claims_excluded():
    assert 'no-proof-of-BV-informational-benefit' in sweep()['claims_excluded']
    assert 'pareto-is-local-to-selected-proxy-metrics' in sweep()['claims_excluded']


@pytest.mark.parametrize('wrong', [
    lambda: (1,2,3),
    lambda: (1,2,(1,2,3)),
    lambda: (1,2,[1,2,3,Link()]),
])
def test_bad_fixture_shape(wrong):
    with pytest.raises(t.InterventionError,match='fixture'):
        sweep(fixture_fn=wrong)


def test_reject_wrong_baseline_link_capacity():
    def altered():
        a,b,c=fixture()
        return a,b,c[:3]+(Link(fabric_slots_per_tick=2),)
    with pytest.raises(t.InterventionError,match='baseline link plan'):
        sweep(fixture_fn=altered)


def test_reject_link_plan_non_dataclass():
    def altered():
        a,b,c=fixture()
        return a,b,c[:3]+({'fabric_slots_per_tick':1,'link_slots_per_tick':1},)
    with pytest.raises(t.InterventionError,match='link plan dataclass'):
        sweep(fixture_fn=altered)


def test_reject_bool_link_capacity():
    def altered():
        a,b,c=fixture()
        return a,b,c[:3]+(Link(fabric_slots_per_tick=True),)
    with pytest.raises(t.InterventionError,match='baseline link plan'):
        sweep(fixture_fn=altered)


def test_reject_wrong_control_type():
    with pytest.raises(t.InterventionError,match='BV control dataclass'):
        sweep(plan_type=str)


def test_reject_mutated_fixture():
    def f():
        return MutableInput([1,2]), Input(),(11,12,13,Link())
    def mutate(*args):
        args[0].events.append(99)
        return fake(*args)
    with pytest.raises(t.InterventionError,match='fixture modified'):
        sweep(fixture_fn=f,executor=mutate)


def test_reject_scheduler_ignores_policy():
    def ignore(*args):
        result=fake(*args)
        result['enabled']=False
        return result
    with pytest.raises(t.InterventionError,match='honor control'):
        sweep(executor=ignore)


def test_reject_feedback_off_activity():
    def improper(*args):
        res=fake(*args)
        if not args[-1].enabled:
            res['feedback']['assessments']=[{}]
        return res
    with pytest.raises(t.InterventionError,match='OFF control'):
        sweep(executor=improper)


def test_reject_no_on_feedback_activity():
    def no_bv(*args):
        res=fake(*args)
        res['resources']['bv_link_grants']=0
        res['resources']['bv_service_units']=0
        res['resources']['bv_memory_units']=0
        res['feedback']['assessments']=[]
        res['feedback']['deliveries']=[]
        res['feedback']['link_grants']=[]
        res['feedback']['unique_receiver_votes']=0
        return res
    with pytest.raises(t.InterventionError,match='no feedback'):
        sweep(executor=no_bv)


def test_reject_corrupt_delivery_tick():
    def broken(*args):
        res=fake(*args)
        if res['feedback']['deliveries']:
            res['feedback']['deliveries'][0]['tick']='5'
        return res
    with pytest.raises(t.InterventionError,match='feedback delivery tick'):
        sweep(executor=broken)


def test_reference_wrong_fixture():
    x=sweep()
    ref=sample_reference()
    ref['shared_fixture_input_sha256']='0'*64
    with pytest.raises(t.InterventionError,match='fixture differs'):
        u.verify_v0t_baseline(x,ref)


def test_reference_wrong_baseline_run():
    x=sweep();ref=sample_reference()
    ref['runs']['off']['whole_result_sha256']='0'*64
    with pytest.raises(t.InterventionError,match='replay pinned'):
        u.verify_v0t_baseline(x,ref)


def test_reference_wrong_source():
    x=sweep();ref=sample_reference()
    ref['producer_source_sha256']={'foo':'bar'}
    with pytest.raises(t.InterventionError,match='pins mismatch'):
        u.verify_v0t_baseline(x,ref)


def test_reference_missing_v0o_custody():
    x=sweep();ref=sample_reference()
    del ref['v0o_reference_check']
    with pytest.raises(t.InterventionError,match='v0o replay'):
        u.verify_v0t_baseline(x,ref)


def test_reference_wrong_schema():
    x=sweep();ref=sample_reference()
    ref['schema']='wrong'
    with pytest.raises(t.InterventionError,match='invalid source'):
        u.verify_v0t_baseline(x,ref)


def test_pareto_incomparable():
    a={'last_forward_terminal_tick':5,'metrics':{'fabric_link_contention':0,'feedback_grant_wait_sum':0}}
    b={'last_forward_terminal_tick':5,'metrics':{'fabric_link_contention':5,'feedback_grant_wait_sum':1}}
    c={'last_forward_terminal_tick':7,'metrics':{'fabric_link_contention':2,'feedback_grant_wait_sum':0}}
    f=u.nondominated_policies({'off':a,'on_forward_first':b,'on_feedback_first':c})
    assert f['nondominated']==['on_feedback_first','on_forward_first']


def test_pareto_strict_dominance():
    a={'last_forward_terminal_tick':5,'metrics':{'fabric_link_contention':0,'feedback_grant_wait_sum':0}}
    b={'last_forward_terminal_tick':5,'metrics':{'fabric_link_contention':5,'feedback_grant_wait_sum':1}}
    c={'last_forward_terminal_tick':5,'metrics':{'fabric_link_contention':2,'feedback_grant_wait_sum':0}}
    f=u.nondominated_policies({'off':a,'on_forward_first':b,'on_feedback_first':c})
    assert f['nondominated']==['on_feedback_first']


def test_pareto_equal_profiles_both_retained():
    a={'last_forward_terminal_tick':5,'metrics':{'fabric_link_contention':0,'feedback_grant_wait_sum':0}}
    b={'last_forward_terminal_tick':5,'metrics':{'fabric_link_contention':5,'feedback_grant_wait_sum':1}}
    f=u.nondominated_policies({'off':a,'on_forward_first':b,'on_feedback_first':b})
    assert len(f['nondominated']) == 2


def test_no_outcome_claim_for_output_mismatch():
    def differ(*args):
        res=fake(*args)
        if args[-1].enabled:
            res['forward']['states']={'A':2}
        return res
    x=sweep(executor=differ)
    assert not x['cells'][0]['interventions']['toggle_enabled_only']['state_hash_equal']


def test_cell_changes_input_hash_from_original():
    x=sweep()
    assert x['cells'][0]['shared_cell_input_sha256']==x['original_fixture_sha256']
    for cell in x['cells'][1:]:
        assert cell['shared_cell_input_sha256']!=x['original_fixture_sha256']


def test_cli_reject_existing_destination_before_runtime(tmp_path, monkeypatch):
    from search import spk_bv_v0u_link_pressure as cli
    existing=tmp_path/'already.json'; existing.write_text('{}')
    assert cli.main(['--root',str(tmp_path),'--reference-v0t',str(existing),
                     '--out',str(existing)]) == 2


def test_cli_reject_missing_reference_before_runtime(tmp_path,monkeypatch):
    from search import spk_bv_v0u_link_pressure as cli
    ref=tmp_path/'missing.json'
    assert cli.main(['--root',str(tmp_path),'--reference-v0t',str(ref),
                     '--out',str(tmp_path.parent/'some-unused-target.json')]) == 2


def test_grid_no_duplicate_capacity_pairs():
    assert len(u.GRID)==len(set(u.GRID))
    assert u.GRID[0] == (1,1)


def test_cross_process_hashseed_reproducibility():
    import subprocess
    import os
    import sys
    path=Path(__file__).resolve()
    code='''import sys,importlib.util
p=sys.argv[1]
spec=importlib.util.spec_from_file_location("bv_v0u_synthetic_fixture",p)
m=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=m
spec.loader.exec_module(m)
print(m.t.snapshot(m.sweep()))'''
    hashes=[]
    for seed in ('13','811'):
        env=os.environ.copy()
        env['PYTHONHASHSEED']=seed
        res=subprocess.run([sys.executable,'-c',code,str(path)],
                           capture_output=True,text=True,env=env,timeout=15,check=True)
        hashes.append(res.stdout.strip())
    assert hashes[0]==hashes[1]
