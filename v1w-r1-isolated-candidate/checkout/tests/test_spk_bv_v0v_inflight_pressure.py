"""BV v0v: independent synthetic/adversarial tests; native gate is separate."""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from copy import deepcopy

import pytest

from spk_bv_research import inflight_pressure_v0v as v
from spk_bv_research import link_pressure_v0u as u
from spk_bv_research import off_on_v0t as t


@dataclass(frozen=True)
class Transport:
    max_inflight_occurrences: int = 4
    cross_pe_extra_ticks: int = 0


@dataclass(frozen=True)
class Link:
    fabric_slots_per_tick: int = 1
    link_slots_per_tick: int = 1
    max_link_span_ticks: int = 128
    max_outbox_per_pe: int = 16


@dataclass(frozen=True)
class Input:
    events: tuple = (1, 3)


@dataclass
class Mutable:
    events: list


@dataclass(frozen=True)
class Plan:
    enabled: bool = True
    priority: str = 'forward-first'


def fixture():
    return Input(),Input(events=(2,3)),(Transport(),11,12,Link())


def fake(case, fabric, tplan, pplan, mplan, lplan, control):
    enabled=control.enabled; priority=control.priority
    fab=lplan.fabric_slots_per_tick; inflight=tplan.max_inflight_occurrences
    # Simulated independent saturation: 1 cross-PE credit restores contention.
    restricted = int(enabled and (fab==1 or inflight==1))
    cont=(5 if priority=='forward-first' else 2)*restricted
    last=5 + (2 if enabled and priority=='feedback-first' and restricted else 0)
    fb_grants=4 if enabled else 0
    fwait=2 if enabled and priority=='feedback-first' and restricted else 0
    bwait=5 if enabled and priority=='forward-first' and restricted else 0
    peak = min(fab,inflight) if enabled else 1
    return {
        'schema':'spk-bv-live-dual-event-scheduler/v0e',
        'enabled':enabled,'policy':priority,
        'forward':{
            'states':{'A':1},'processed_events':2,'processed_batches':2,
            'batches':[{},{}],
            'emissions':[{'node_id':'A','channel':7,'timestamp':last}],
            'terminal':[{'node_id':'A','channel':7,'timestamp':last}],
            'link_grants':[{'wait':fwait}], 'occurrences':[{}],
        },
        'feedback':{
            'assessments':[{}] if enabled else [],
            'deliveries':[{'tick':last+i} for i in range(fb_grants)],
            'link_grants':[{'wait':bwait if i==0 else 0} for i in range(fb_grants)],
            'unique_receiver_votes':fb_grants,
        },
        'resources':{
            'bv_link_grants':fb_grants, 'bv_service_units':fb_grants,
            'bv_memory_units':2*fb_grants,'forward_reserved_memory_units':10,
            'peak_cross_inflight':peak,'contention':{'fabric_link':cont},
            'timeline':[{'tick':i,'feedback_sends':1 if enabled and i>0 else 0,
                         'memory_total':2 if enabled else 0,
                         'link_total':1,'pe_service_total':1} for i in range(10)]
        },
    }


def sweep(**kwargs):
    return v.scan(kwargs.pop('fixture_fn',fixture),kwargs.pop('executor',fake),
                  kwargs.pop('plan_type',Plan),root=Path.cwd(),pin_sources=False,**kwargs)


def ref_v0u():
    x=u.scan(fixture,fake,Plan,root=Path.cwd(),pin_sources=False)
    x['v0t_baseline_check']={'status':'PINNED_V0T_AND_V0O_BASELINE_REPLAYED'}
    return x


def test_full_factorial_grid_and_three_arms():
    x=sweep()
    assert x['schema']==v.SCHEMA and x['status']==v.STATUS
    assert len(x['cells'])==6 and len(x['grid'])==6
    assert x['same_fixture_before_after_every_run']
    assert x['capacity_changes_only_link_fabric_and_transport_inflight']
    for cell in x['cells']:
        assert set(cell['runs'])=={'off','on_forward_first','on_feedback_first'}
        assert cell['runs']['off']['metrics']['feedback_link_grants']==0
        assert cell['runs']['on_forward_first']['metrics']['feedback_link_grants']==4
        assert cell['runs']['on_feedback_first']['metrics']['feedback_link_grants']==4
        assert all(row['metrics']['peak_cross_inflight']<=cell['capacity']['max_inflight_occurrences']
                   for row in cell['runs'].values())
        assert cell['capacity']['directional_link_slots_per_tick']==1
        assert cell['status']=='COMPLETE_THREE_ARM_CAPACITY_CELL'


def test_computed_resource_interaction():
    rows=sweep()['cells']
    # Baseline link2/inflight4 has headroom, link2/inflight1 no longer has it.
    assert rows[1]['runs']['on_feedback_first']['last_forward_terminal_tick']==5
    assert rows[4]['runs']['on_feedback_first']['last_forward_terminal_tick']==7
    assert rows[1]['runs']['on_feedback_first']['metrics']['fabric_link_contention']==0
    assert rows[4]['runs']['on_feedback_first']['metrics']['fabric_link_contention']==2


def test_original_input_immutable():
    x=fixture(); before=t.snapshot(x)
    sweep()
    assert t.snapshot(x)==before


def test_hashseed_independent_python_order():
    assert sweep()==sweep()


def test_source_claim_not_promoted_without_pins():
    assert sweep()['source_sha256'] is None


def test_capacity_cells_anchor_native_v0u_reports():
    assert v.verify_v0u_reference(sweep(),ref_v0u())['status']==\
        'TWO_NATIVE_V0U_CAPACITY_CELLS_REPLAYED'


@pytest.mark.parametrize('mutator,pattern',[
    (lambda r:r.update(schema='fake'),'bad v0v schema'),
    (lambda r:r.update(original_fixture_sha256='x'*64),'fixture drift'),
    (lambda r:r.update(source_sha256={'x':'bogus'}),'source pins'),
    (lambda r:r['cells'][0]['runs']['off'].update(whole_result_sha256='0'*64),'anchor mismatch'),
    (lambda r:r['cells'][1]['runs']['on_feedback_first']['metrics'].update(bv_link_grants=200),'anchor mismatch'),
    (lambda r:r['cells'][0].update(shared_cell_input_sha256='0'*64),'anchor fixture bytes'),
    (lambda r:r['cells'][0]['capacity'].update(fabric_slots_per_tick=8),'anchor capacity'),
    (lambda r:r['cells'].pop(),'invalid scan cells'),
])
def test_reference_rejects_modified_v0v_report(mutator,pattern):
    x=sweep();mutator(x)
    with pytest.raises(t.InterventionError,match=pattern):
        v.verify_v0u_reference(x,ref_v0u())


@pytest.mark.parametrize('mutator,pattern',[
    (lambda r:r.update(status='INVALID'),'invalid v0u native reference'),
    (lambda r:r.update(schema='INVALID'),'invalid v0u native reference'),
    (lambda r:r.update(original_fixture_sha256='0'*64),'fixture drift'),
    (lambda r:r.update(same_fixture_before_after_every_run=False),'mutated'),
    (lambda r:r['v0t_baseline_check'].update(status='fake'),'not pinned'),
    (lambda r:r['cells'].pop(),'invalid reference cell set'),
    (lambda r:r['cells'][1]['runs']['on_forward_first'].update(last_feedback_delivery_tick=300),'anchor mismatch'),
])
def test_reference_rejects_modified_v0u_report(mutator,pattern):
    x=ref_v0u();mutator(x)
    with pytest.raises(t.InterventionError,match=pattern):
        v.verify_v0u_reference(sweep(),x)


def test_reject_baseline_transport_quota_wrong():
    def bad():
        a,b,c=fixture()
        return a,b,(replace(c[0],max_inflight_occurrences=2),)+c[1:]
    with pytest.raises(t.InterventionError,match='original transport'):
        sweep(fixture_fn=bad)


def test_reject_bool_baseline_transport():
    def bad():
        a,b,c=fixture()
        return a,b,(replace(c[0],max_inflight_occurrences=True),)+c[1:]
    with pytest.raises(t.InterventionError,match='original transport'):
        sweep(fixture_fn=bad)


def test_reject_non_dataclass_transport():
    def bad():
        a,b,c=fixture()
        return a,b,({'max_inflight_occurrences':4},)+c[1:]
    with pytest.raises(t.InterventionError,match='transport plan dataclass'):
        sweep(fixture_fn=bad)


def test_reject_bad_link_baseline():
    def bad():
        a,b,c=fixture()
        return a,b,c[:3]+(replace(c[3],fabric_slots_per_tick=2),)
    with pytest.raises(t.InterventionError,match='baseline link plan'):
        sweep(fixture_fn=bad)


def test_reject_fixture_mutation():
    def mutable():
        a,b,c=fixture()
        return Mutable([1,2]),b,c
    def tamper(case,*args):
        case.events.append(99)
        return fake(case,*args)
    with pytest.raises(t.InterventionError,match='fixture modified'):
        sweep(fixture_fn=mutable,executor=tamper)


def test_reject_reported_peak_exceeding_limit():
    def cheating(*args):
        x=fake(*args)
        x['resources']['peak_cross_inflight']=42
        return x
    with pytest.raises(t.InterventionError,match='peak exceeding'):
        sweep(executor=cheating)


def test_reject_scheduler_disabled_control_ignored():
    def broken(*args):
        x=fake(*args)
        x['enabled']=True
        return x
    with pytest.raises(t.InterventionError,match='honor control'):
        sweep(executor=broken)


def test_reject_missing_feedback_on():
    def broken(*args):
        x=fake(*args)
        if args[-1].enabled:
            x['feedback']['link_grants']=[]
            x['resources']['bv_link_grants']=0
            x['resources']['bv_service_units']=0
            x['resources']['bv_memory_units']=0
            x['feedback']['deliveries']=[]
            x['feedback']['unique_receiver_votes']=0
        return x
    with pytest.raises(t.InterventionError,match='missing expected'):
        sweep(executor=broken)


def test_reject_unsupported_bounded_horizon_not_silent():
    def bounded(*args):
        if args[2].max_inflight_occurrences==1:
            raise ValueError('bounded logical horizon exceeded')
        return fake(*args)
    with pytest.raises(ValueError,match='bounded logical horizon'):
        sweep(executor=bounded)


def test_policy_intervention_signaled_per_cell():
    for cell in sweep()['cells']:
        assert cell['interventions']['toggle_enabled_only']['metric_deltas']['bv_link_grants']==4
        assert cell['interventions']['change_priority_only']['metric_deltas']['bv_link_grants']==0


def test_no_hardware_or_learning_claims():
    excluded=sweep()['claims_excluded']
    assert 'no-learning-or-informational-benefit' in excluded
    assert 'no-hardware-latency-energy' in excluded
    assert 'not-general-capacity-threshold-proof' in excluded


def test_cli_rejects_existing_output(tmp_path):
    from search import spk_bv_v0v_inflight_pressure as cli
    ref=tmp_path/'ref.json';ref.write_text('{}')
    out=tmp_path/'exists.json';out.write_text('{}')
    assert cli.main(['--root',str(tmp_path),'--reference-v0u',str(ref),'--out',str(out)])==2


def test_cli_rejects_missing_reference(tmp_path):
    from search import spk_bv_v0v_inflight_pressure as cli
    out=tmp_path/'new.json'
    assert cli.main(['--root',str(tmp_path),'--reference-v0u',str(tmp_path/'missing'),
                     '--out',str(out)])==2


def test_cli_does_not_silently_overwrite_repository(tmp_path):
    from search import spk_bv_v0v_inflight_pressure as cli
    ref=tmp_path/'ref.json';ref.write_text('{}')
    out=tmp_path/'inside.json'
    assert cli.main(['--root',str(tmp_path),'--reference-v0u',str(ref),
                     '--out',str(out)])==2
    assert not out.exists()


def test_cli_synthetic_new_file(tmp_path,monkeypatch):
    from search import spk_bv_v0v_inflight_pressure as cli
    import sys,types,json
    root=tmp_path/'repo';root.mkdir()
    ref=tmp_path/'ref.json';ref.write_text(json.dumps(ref_v0u()))
    out=tmp_path/'result.json'
    monkeypatch.setattr(cli,'source_pins',lambda root: None)
    x=sweep()
    monkeypatch.setattr(cli,'scan',lambda *a,**kw:deepcopy(x))
    modules={
        'spk_backvalidation_v0.live_dual_scheduler_v0e':types.ModuleType('spk_backvalidation_v0.live_dual_scheduler_v0e'),
        'search.spk_bv_v0e_live_evidence':types.ModuleType('search.spk_bv_v0e_live_evidence'),
    }
    modules['spk_backvalidation_v0.live_dual_scheduler_v0e'].execute_live_v0e=fake
    modules['spk_backvalidation_v0.live_dual_scheduler_v0e'].LiveBVPlanV0e=Plan
    modules['search.spk_bv_v0e_live_evidence'].fixture=fixture
    package=types.ModuleType('spk_backvalidation_v0')
    package.__path__=[]
    monkeypatch.setitem(sys.modules,'spk_backvalidation_v0',package)
    import search
    monkeypatch.setattr(package,'live_dual_scheduler_v0e',modules['spk_backvalidation_v0.live_dual_scheduler_v0e'],raising=False)
    monkeypatch.setattr(search,'spk_bv_v0e_live_evidence',modules['search.spk_bv_v0e_live_evidence'],raising=False)
    for name,obj in modules.items():monkeypatch.setitem(sys.modules,name,obj)
    assert cli.main(['--root',str(root),'--reference-v0u',str(ref),'--out',str(out)])==0
    assert out.exists()
    assert json.loads(out.read_text())['v0u_reference_check']['status']==\
        'TWO_NATIVE_V0U_CAPACITY_CELLS_REPLAYED'
    assert cli.main(['--root',str(root),'--reference-v0u',str(ref),'--out',str(out)])==2
