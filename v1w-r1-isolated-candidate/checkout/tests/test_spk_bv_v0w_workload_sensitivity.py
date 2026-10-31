"""BV v0w synthetic and adversarial tests; never native source equivalence."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from pathlib import Path

import pytest
from spk_bv_research import workload_sensitivity_v0w as w
from spk_bv_research import inflight_pressure_v0v as v
from spk_bv_research import off_on_v0t as t


@dataclass(frozen=True)
class Event:
    timestamp: int
    node_id: str = 'A'
    channel: int = 0


@dataclass(frozen=True)
class Case:
    events: tuple = (Event(1),Event(3))
    invariant: int = 49


@dataclass
class MutableCase:
    events: tuple = (Event(1), Event(3))
    witness: object = None


@dataclass(frozen=True)
class Fabric:
    pe_ids: tuple = ('PE0','PE1','PE2')


@dataclass(frozen=True)
class Transport:
    max_inflight_occurrences: int = 4
    cross_pe_extra_ticks: int = 0


@dataclass(frozen=True)
class Links:
    fabric_slots_per_tick: int = 1
    link_slots_per_tick: int = 1
    max_link_span_ticks: int = 128
    max_outbox_per_pe: int = 16


@dataclass(frozen=True)
class Control:
    enabled: bool = True
    priority: str = 'forward-first'


def fixture():
    return Case(),Fabric(),(Transport(), 11, 12, Links())


def executor(case, fabric, tp, pp, mp, lp, control):
    on=control.enabled
    count=len(case.events)
    stamps=[x.timestamp for x in case.events]
    peak=1 if lp.fabric_slots_per_tick==1 else 2
    peak=min(tp.max_inflight_occurrences, peak)
    if not on: peak=1
    delay=2 if on and control.priority=='feedback-first' and lp.fabric_slots_per_tick==1 else 0
    final=max(stamps)+2+delay
    grants=2*count if on else 0
    forward_grants = [{'wait':delay}]
    return {
        'schema':'spk-bv-live-dual-event-scheduler/v0e',
        'policy':control.priority,'enabled':on,
        'forward':{
            'states':{'A':count,'B':0,'C':0},
            'batches':[{'tick':stamp} for stamp in stamps],
            'processed_batches':count,'processed_events':count,
            'emissions':[{'timestamp':stamp+2+delay,'node_id':'C','channel':7} for stamp in stamps],
            'terminal':[{'timestamp':final,'node_id':'C','channel':7}],
            'link_grants':forward_grants,'occurrences':[{'id':'r1'}],
        },
        'feedback':{
            'assessments':[{'id':'a1'}] if on else [],
            'deliveries':[{'tick':final+i+1} for i in range(grants)],
            'link_grants':[{'wait':i%2} for i in range(grants)],
            'unique_receiver_votes':grants,
        },
        'resources':{
            'bv_link_grants':grants,'bv_service_units':grants,
            'bv_memory_units':2*grants,'forward_reserved_memory_units':count*3,
            'peak_cross_inflight':peak,
            'contention':{'fabric_link':int(on and lp.fabric_slots_per_tick==1)},
            'timeline':[{'tick':i,'feedback_sends':int(on and i>0),
                'memory_total':count*3+2*grants,'pe_service_total':count+grants,
                'link_total':count+grants} for i in range(count+grants+1)],
        },
    }


def scan(**kw):
    return w.scan(kw.pop('fixture_fn',fixture),kw.pop('executor',executor),
                  kw.pop('plan_type',Control),root=Path.cwd(),pin_sources=False,**kw)


def v0v_ref():
    ref=v.scan(fixture,executor,Control,root=Path.cwd(),pin_sources=False)
    ref['v0u_reference_check']={
        'status':'TWO_NATIVE_V0U_CAPACITY_CELLS_REPLAYED',
        'v0u_v0t_v0o_reference_chain':True,
    }
    return ref


def test_all_30_three_arm_cells_and_base_anchor():
    result=scan()
    assert len(result['cells']) == 15
    assert len(result['workloads'])==5
    assert result['same_fixture_before_after_every_run']
    assert w.verify_v0v_anchors(result,v0v_ref())['status']==\
        'THREE_NATIVE_V0V_REFERENCE_CELLS_REPLAYED'
    assert all(set(cell['runs'])=={'off','on_forward_first','on_feedback_first'} for cell in result['cells'])
    assert all(cell['runs']['off']['metrics']['feedback_deliveries']==0 for cell in result['cells'])
    assert all(cell['runs']['on_forward_first']['metrics']['feedback_deliveries']>0 for cell in result['cells'])
    assert all('contention_by_reason' in arm for cell in result['cells'] for arm in cell['runs'].values())


def test_exact_stimulus_rewrites_and_plan_preservation():
    result=scan()
    expected={'baseline':[1,3],'coincident':[1,1], 'second_plus_1':[1,4],
              'second_plus_3':[1,6], 'repeated_episode':[1,3,9,11]}
    for c in result['cells']:
        assert c['stimulus_timestamps']==expected[c['workload']]
        assert c['stimulus_count']==len(expected[c['workload']])
        assert (c['fabric_slots_per_tick'],c['max_inflight_occurrences']) in w.CAPACITY_PROFILES
    assert scan()==scan()


def test_every_case_only_changes_events():
    x=Case()
    for name in w.WORKLOADS:
        y=w.make_workload(x,name)
        assert y.invariant==x.invariant
        assert y.events[0] is x.events[0]
    assert x==Case()


def test_within_cell_controls_share_input_but_cross_workload_changes_it():
    result=scan()
    assert len({c['shared_cell_input_sha256'] for c in result['cells']})==15
    for c in result['cells']:
        assert c['interventions']['toggle_enabled_only']['metric_deltas']['bv_link_grants']>0
        assert c['interventions']['change_priority_only']['metric_deltas']['bv_link_grants']==0


@pytest.mark.parametrize('name',('invalid','origin','repeated',None,12))
def test_unsupported_workload_is_rejected(name):
    with pytest.raises(t.InterventionError,match='unsupported workload'):
        w.make_workload(Case(),name)


@pytest.mark.parametrize('bad,reason',[
    (Case(events=(Event(1),)), 'exactly two'),
    (Case(events=(Event(1),Event(4))), 'timestamps changed'),
    (Case(events=[Event(1),Event(3)]), 'exactly two'),
    (Case(events=(1,3)), 'external event dataclass'),
    (Case(events=(Event(True),Event(3))), 'external event fields'),
    (Case(events=(Event(1,node_id=4),Event(3))), 'external event fields'),
])
def test_invalid_native_external_events_fail_closed(bad,reason):
    with pytest.raises(t.InterventionError,match=reason):
        w.make_workload(bad,'baseline')


@pytest.mark.parametrize('mutator,match',[
    (lambda x:x.update(schema='BAD'),'invalid v0w report'),
    (lambda x:x.update(status='BAD'),'invalid v0w report'),
    (lambda x:x.update(source_sha256={'fake':1}),'native source/fixture drift'),
    (lambda x:x.update(original_fixture_sha256='0'*64),'native source/fixture drift'),
    (lambda x:x['cells'][0].update(shared_cell_input_sha256='x'),'input SHA mismatch'),
    (lambda x:x['cells'][1]['runs']['off'].update(whole_result_sha256='BAD'),'output drift'),
    (lambda x:x['cells'][0].update(fabric_slots_per_tick=4),'baseline control mismatch'),
    (lambda x:x['cells'].pop(),'invalid reference or workload grid'),
])
def test_tampered_workload_report_rejected(mutator,match):
    result=scan()
    mutator(result)
    with pytest.raises(t.InterventionError,match=match):
        w.verify_v0v_anchors(result,v0v_ref())


@pytest.mark.parametrize('mutator,match',[
    (lambda x:x.update(schema='WRONG'),'invalid v0v native reference'),
    (lambda x:x.update(status='WRONG'),'invalid v0v native reference'),
    (lambda x:x['v0u_reference_check'].update(v0u_v0t_v0o_reference_chain=False),'reference lacks'),
    (lambda x:x.update(same_fixture_before_after_every_run=False),'fixture integrity'),
    (lambda x:x['cells'].pop(),'invalid reference or workload grid'),
    (lambda x:x['cells'][0]['runs']['off']['metrics'].update(bv_link_grants=99),'output drift'),
])
def test_tampered_v0v_reference_rejected(mutator,match):
    reference=v0v_ref()
    mutator(reference)
    with pytest.raises(t.InterventionError,match=match):
        w.verify_v0v_anchors(scan(),reference)


def test_rejection_from_scheduler_is_not_ignored():
    def rejecting(case,*args):
        if len(case.events)>2:
            raise ValueError('simulator rejected bounded temporal horizon')
        return executor(case,*args)
    with pytest.raises(ValueError,match='bounded temporal horizon'):
        scan(executor=rejecting)


def test_mutation_of_original_case_is_caught():
    classlike = MutableCase(witness=[])
    def bad_fixture():
        case,fab,plans=fixture()
        return classlike,fab,plans
    def mutating_executor(case,*args):
        case.witness.append('tamper')
        return executor(case,*args)
    with pytest.raises(t.InterventionError,match='fixture modified'):
        scan(fixture_fn=bad_fixture, executor=mutating_executor)


def test_off_control_leaking_feedback_rejected():
    def wrong(case,*args):
        report=executor(case,*args)
        if not args[-1].enabled:
            report['feedback']['link_grants']=[{'wait':0}]
        return report
    with pytest.raises(t.InterventionError,match='grant/service accounting|OFF control'):
        scan(executor=wrong)


def test_cli_refuses_overwrite_or_repo_output(tmp_path):
    from search import spk_bv_v0w_workload_sensitivity as cli
    ref=tmp_path/'ref.json';ref.write_text('{}')
    out=tmp_path/'exists.json';out.write_text('{}')
    assert cli.main(['--root',str(tmp_path),'--reference-v0v',str(ref),'--out',str(out)])==2
    assert cli.main(['--root',str(tmp_path),'--reference-v0v',str(ref),
                     '--out',str(tmp_path/'inside_repo.json')])==2
    assert not (tmp_path/'inside_repo.json').exists()


def test_cli_refuses_missing_or_symlink_reference(tmp_path):
    from search import spk_bv_v0w_workload_sensitivity as cli
    assert cli.main(['--root',str(tmp_path),'--reference-v0v',str(tmp_path/'none'),
                     '--out',str(tmp_path/'new.json')])==2
    real=tmp_path/'real.json';real.write_text('{}')
    ref=tmp_path/'ref.json';ref.symlink_to(real)
    assert cli.main(['--root',str(tmp_path),'--reference-v0v',str(ref),
                     '--out',str(tmp_path/'new.json')])==2


def test_cli_independent_native_module_stub(tmp_path,monkeypatch):
    from search import spk_bv_v0w_workload_sensitivity as cli
    import json,types,sys
    root=tmp_path/'repo';root.mkdir()
    ref=tmp_path/'ref.json';ref.write_text(json.dumps(v0v_ref()))
    out=tmp_path/'new.json'
    monkeypatch.setattr(cli,'source_pins',lambda *_:None)
    monkeypatch.setattr(cli,'scan',lambda *a,**kw:deepcopy(scan()))
    mod_sched=types.ModuleType('spk_backvalidation_v0.live_dual_scheduler_v0e')
    mod_sched.execute_live_v0e=executor
    mod_sched.LiveBVPlanV0e=Control
    mod_fix=types.ModuleType('search.spk_bv_v0e_live_evidence')
    mod_fix.fixture=fixture
    pkg=types.ModuleType('spk_backvalidation_v0');pkg.__path__=[]
    monkeypatch.setitem(sys.modules,'spk_backvalidation_v0',pkg)
    monkeypatch.setitem(sys.modules,mod_sched.__name__,mod_sched)
    monkeypatch.setitem(sys.modules,mod_fix.__name__,mod_fix)
    import search
    monkeypatch.setattr(pkg,'live_dual_scheduler_v0e',mod_sched,raising=False)
    monkeypatch.setattr(search,'spk_bv_v0e_live_evidence',mod_fix,raising=False)
    assert cli.main(['--root',str(root),'--reference-v0v',str(ref),'--out',str(out)])==0
    assert out.is_file()
    assert json.loads(out.read_text())['v0v_reference_check']['status']==\
           'THREE_NATIVE_V0V_REFERENCE_CELLS_REPLAYED'
    assert cli.main(['--root',str(root),'--reference-v0v',str(ref),'--out',str(out)])==2


def test_frozen_source_not_misrepresented_as_native_when_unpinned():
    x=scan()
    assert x['source_sha256'] is None
    assert 'no-learning-or-neuron-program-adaptation' in x['claims_excluded']
    assert x['variation_scope']=='external_event_timestamps_and_episode_repetition_only'


def test_reject_non_numeric_native_contention_reason():
    def malformed(case,*args):
        result=executor(case,*args)
        result['resources']['contention']['inflight']=True
        return result
    with pytest.raises(t.InterventionError,match='invalid native contention reason'):
        scan(executor=malformed)


def test_reject_counter_not_equal_to_summary():
    # Impossible when using the v0t summarizer unchanged; emulate a tampered
    # summarizer at the strict _arm boundary to confirm explicit validation.
    from spk_bv_research import workload_sensitivity_v0w as mod
    original=mod._arm
    def dishonest(*args,**kwargs):
        result=original(*args,**kwargs)
        result['metrics']['fabric_link_contention']+=9
        return result
    from pytest import MonkeyPatch
    with MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(mod,'_arm',dishonest)
        with pytest.raises(t.InterventionError,match='reported fabric contention differs'):
            scan()
