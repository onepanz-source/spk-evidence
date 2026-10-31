"""Self-contained negative cases; no source trees, fixtures or pytest import tricks."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import pytest
from spk_bv_research.value_boundary_v0x import (
    SCHEMA, STATUS, BoundaryError, summarize, validate,
)
from spk_bv_research.workload_sensitivity_v0w import (
    WORKLOADS, CAPACITY_PROFILES, SCHEMA as W_SCHEMA, STATUS as W_STATUS,
)


def arm(enabled, priority, grants=2):
    m = {k: 0 for k in ('bv_link_grants','bv_service_units','bv_memory_units',
         'timeline_link_unit_sum','timeline_service_unit_sum','timeline_memory_unit_sum',
         'feedback_grant_wait_sum','forward_grant_wait_sum','feedback_assessments',
         'feedback_deliveries','forward_batches','forward_terminal',
         'feedback_link_grants','feedback_unique_receiver_votes','fabric_link_contention')}
    m.update({'forward_batches': 3,'forward_terminal': 1,
              'timeline_link_unit_sum': 2, 'timeline_service_unit_sum': 3,
              'timeline_memory_unit_sum': 20})
    if enabled:
        m.update({'bv_link_grants':grants, 'bv_service_units':grants,
                  'bv_memory_units':2*grants, 'feedback_assessments':1,
                  'feedback_deliveries':grants,'feedback_link_grants':grants,
                  'feedback_unique_receiver_votes':grants,
                  'timeline_link_unit_sum':2+grants,
                  'timeline_service_unit_sum':3+grants,
                  'timeline_memory_unit_sum':20+2*grants})
    return {'enabled':enabled,'priority':priority,'whole_result_sha256':'a'*64,
            'forward_states_sha256':'b'*64,
            'forward_emission_payload_multiset_sha256':'c'*64,
            'forward_terminal_payload_multiset_sha256':'d'*64,
            'last_forward_terminal_tick':4,'metrics':m,'contention_by_reason':{}}


def report():
    cells=[]
    for name in WORKLOADS:
        for fabric, inflight in CAPACITY_PROFILES:
            cells.append({'workload':name,'fabric_slots_per_tick':fabric,
                          'max_inflight_occurrences':inflight,
                          'shared_cell_input_sha256':'c'*64,
                          'stimulus_timestamps':[1,3],
                          'status':'COMPLETE_THREE_ARM_WORKLOAD_CELL',
                          'runs':{'off':arm(False,'forward-first',0),
                                  'on_forward_first':arm(True,'forward-first'),
                                  'on_feedback_first':arm(True,'feedback-first')},
                          'interventions':{k:{'state_hash_equal':True,
                            'emission_payload_multiset_equal':True,
                            'terminal_payload_multiset_equal':True} for k in
                            ('toggle_enabled_only','change_priority_only',
                             'off_to_feedback_first_combined')}})
    return {'schema':W_SCHEMA,'status':W_STATUS,
            'same_fixture_before_after_every_run':True,
            'variation_scope':'external_event_timestamps_and_episode_repetition_only',
            'v0v_reference_check':{
                'status':'THREE_NATIVE_V0V_REFERENCE_CELLS_REPLAYED',
                'v0v_v0u_v0t_v0o_chain':True},
            'source_sha256':{'a':'a'*64,'b':'b'*64,'c':'c'*64},
            'original_fixture_sha256':'f'*64,'cells':cells}


def test_structural_contract_and_non_identifiability():
    s=summarize(report())
    assert (s['schema'],s['status'])==(SCHEMA,STATUS)
    assert s['native_cells']==15 and s['native_arms_examined']==45
    assert s['forward_outcome_conservation_cells']==15
    assert s['forward_first_zero_delay_cells']==15
    assert s['feedback_first_positive_delay_cells']==0
    assert s['aggregate_link_grants_across_repeated_capacity_cells_not_independent_trials']==30
    assert 'NOT_IDENTIFIABLE' in s['observed_forward_information_benefit']
    assert 'judgment' in s['required_next_contract']
    assert 'predeclared_external_score' in s['required_next_contract']['evaluation']


@pytest.mark.parametrize('mutate',[
    lambda r: r.update(schema='wrong'),
    lambda r: r.update(status='wrong'),
    lambda r: r.update(same_fixture_before_after_every_run=False),
    lambda r: r.update(variation_scope='changed-network'),
    lambda r: r.update(v0v_reference_check={'status':'missing'}),
    lambda r: r.update(source_sha256={}),
    lambda r: r['cells'].pop(),
    lambda r: r['cells'].__setitem__(0,copy.deepcopy(r['cells'][1])),
    lambda r: r['cells'][0].update(status='FAILED'),
    lambda r: r['cells'][0].update(shared_cell_input_sha256=''),
    lambda r: r['cells'][0].update(fabric_slots_per_tick=99),
    lambda r: r['cells'][0].update(runs={}),
    lambda r: r['cells'][0]['runs']['off'].update(enabled=True),
    lambda r: r['cells'][0]['runs']['on_forward_first'].update(enabled=False),
    lambda r: r['cells'][0]['runs']['on_feedback_first'].update(priority='other'),
    lambda r: r['cells'][0]['runs']['off']['metrics'].update(feedback_deliveries=1),
    lambda r: r['cells'][0]['runs']['off']['metrics'].update(bv_service_units=2),
    lambda r: r['cells'][0]['runs']['on_feedback_first'].update(forward_states_sha256='z'*64),
    lambda r: r['cells'][0]['runs']['on_feedback_first'].update(forward_emission_payload_multiset_sha256='z'*64),
    lambda r: r['cells'][0]['runs']['on_feedback_first'].update(forward_terminal_payload_multiset_sha256='z'*64),
    lambda r: r['cells'][0]['runs']['on_feedback_first']['metrics'].update(forward_batches=4),
    lambda r: r['cells'][0]['runs']['on_feedback_first']['metrics'].update(feedback_assessments=3),
    lambda r: r['cells'][0]['runs']['on_forward_first']['metrics'].update(bv_link_grants=-1),
    lambda r: r['cells'][0]['runs']['on_forward_first']['metrics'].update(bv_link_grants=True),
    lambda r: r['cells'][0]['runs']['on_forward_first']['metrics'].update(bv_memory_units=-1),
    lambda r: r['cells'][0]['runs']['on_forward_first'].update(contention_by_reason={'inflight':-2}),
    lambda r: r['cells'][0]['runs']['on_forward_first'].update(contention_by_reason={'fabric_link':3}),
    lambda r: r['cells'][0]['interventions']['toggle_enabled_only'].update(state_hash_equal=False),
    lambda r: r['cells'][0]['runs']['on_forward_first'].update(whole_result_sha256='x'),
    lambda r: r['cells'][0]['runs']['off'].update(metrics={}),
])
def test_rejects_corrupted_evidence(mutate):
    r=report()
    mutate(r)
    with pytest.raises((BoundaryError,KeyError,TypeError)):
        validate(r)


def test_rejects_cost_inconsistent_with_link_grants():
    r=report()
    r['cells'][1]['runs']['on_forward_first']['metrics']['timeline_link_unit_sum']+=1
    with pytest.raises(BoundaryError, match='feedback grants'):
        summarize(r)


def test_rejects_negative_delay_without_renaming_it_as_benefit():
    r=report()
    r['cells'][1]['runs']['on_feedback_first']['last_forward_terminal_tick'] = 3
    with pytest.raises(BoundaryError,match='negative last-output delay'):
        summarize(r)


def test_tracks_nonfabric_contention_separately():
    r=report()
    r['cells'][1]['runs']['on_forward_first']['contention_by_reason']={'inflight':3}
    r['cells'][1]['runs']['on_feedback_first']['contention_by_reason']={'directional_link':4}
    s=summarize(r)
    assert s['contention_attempt_counters_across_cells_not_independent_trials']=={
        'directional_link':4,'inflight':3}


def test_repeated_episode_not_independent_sample():
    s=summarize(report())
    assert 'no-independent-replicates' in ' '.join(s['claims_excluded'])
    assert 'no-learned-performance' in ' '.join(s['claims_excluded'])


def test_cli_output_and_reject_overwrite(tmp_path,monkeypatch,capsys):
    from search.spk_bv_v0x_value_boundary import main
    from spk_bv_research import off_on_v0t
    monkeypatch.setattr('search.spk_bv_v0x_value_boundary.source_pins',
                        lambda root:report()['source_sha256'])
    r=tmp_path/'source.json';r.write_text(json.dumps(report()))
    out=tmp_path/'output.json'
    outside=tmp_path/'repo';outside.mkdir()
    # output inside tmp_path but outside --root.
    assert main(['--root',str(outside),'--v0w-13',str(r),'--out',str(out)])==0
    assert json.loads(out.read_text())['native_cells']==15
    assert main(['--root',str(outside),'--v0w-13',str(r),'--out',str(out)])==2
    assert 'REJECTED' in capsys.readouterr().err


def test_cli_mismatched_replay(tmp_path,monkeypatch,capsys):
    from search.spk_bv_v0x_value_boundary import main
    monkeypatch.setattr('search.spk_bv_v0x_value_boundary.source_pins',
                        lambda root:report()['source_sha256'])
    root=tmp_path/'repo';root.mkdir()
    p=tmp_path/'13.json';p.write_text(json.dumps(report()))
    other=report();other['cells'][0]['runs']['off']['last_forward_terminal_tick']=50
    q=tmp_path/'811.json';q.write_text(json.dumps(other))
    assert main(['--root',str(root),'--v0w-13',str(p),
                 '--v0w-811',str(q),'--out',str(tmp_path/'out.json')])==2
    assert 'process captures differ' in capsys.readouterr().err


def test_cli_rejects_unpinned_source(tmp_path,monkeypatch):
    from search.spk_bv_v0x_value_boundary import main
    monkeypatch.setattr('search.spk_bv_v0x_value_boundary.source_pins',lambda root: {})
    root=tmp_path/'repo';root.mkdir()
    p=tmp_path/'input.json';p.write_text(json.dumps(report()))
    assert main(['--root',str(root),'--v0w-13',str(p),
                 '--out',str(tmp_path/'out.json')])==2


def test_cli_rejects_repo_output(tmp_path,monkeypatch):
    from search.spk_bv_v0x_value_boundary import main
    root=tmp_path/'repo';root.mkdir()
    p=tmp_path/'input.json';p.write_text(json.dumps(report()))
    assert main(['--root',str(root),'--v0w-13',str(p),
                 '--out',str(root/'out.json')])==2


def test_cli_rejects_symlink_source(tmp_path,monkeypatch):
    from search.spk_bv_v0x_value_boundary import main
    root=tmp_path/'repo';root.mkdir()
    p=tmp_path/'input.json';p.write_text(json.dumps(report()))
    alias=tmp_path/'alias.json';alias.symlink_to(p)
    assert main(['--root',str(root),'--v0w-13',str(alias),
                 '--out',str(tmp_path/'out.json')])==2
