"""BV v1o: entirely synthetic fixtures; all native claims remain zero."""
from __future__ import annotations
import copy,hashlib,json
from pathlib import Path
import pytest
from spk_bv_research.off_on_v0t import InterventionError
from spk_bv_research.receiver_knowledge_disclosure_v1n import SCHEMA as NS, STATUS as NT
from spk_bv_research.decision_disclosure_boundary_v1o import (
    analyze,canon,example_record,inspect,SCHEMA,STATUS,WORLD_IDS,EXCLUDED,
)
from search import spk_bv_v1o_decision_disclosure as cli

sha=lambda b:hashlib.sha256(b).hexdigest()


def specimen():
    m={'schema':'spk-bv-native-passive-two-port-trace-projection/v1m',
       'status':'NATIVE_POSTHOC_ENDPOINT_TRACES_NOT_INDEPENDENT_OBSERVER',
       'full_native_scheduler_runs_recomputed_in_this_run':4,
       'native_fixture_sha256':'synthetic-fixture-only',
       'frozen_native_sources':{'test':'not-a-native-source'}}
    mb=canon(m)
    worlds=[
      {'world_id':WORLD_IDS[0],'ingress_count':0,'sender_port_count':0,
       'expected':True,'covered':True,'world_origin':'HYPOTHETICAL_NOT_EXECUTED',
       'hidden_decision_cause':'OPERATOR_CAUSE_ASSUMED'},
      {'world_id':WORLD_IDS[1],'ingress_count':0,'sender_port_count':0,
       'expected':True,'covered':True,'world_origin':'HYPOTHETICAL_NOT_EXECUTED',
       'hidden_decision_cause':'EXTERNAL_CAUSE_ASSUMED'},
    ]
    for i in range(6):
        worlds.append({'world_id':f'OTHER_WORLD_{i}',
          'ingress_count':i%2,'sender_port_count':i%2,
          'expected':None,'covered':False,'world_origin':'HYPOTHETICAL_NOT_EXECUTED',
          'hidden_decision_cause':'NOT_IDENTIFIED'})
    n={'schema':NS,'status':NT,'reference_v1m_sha256':sha(mb),
       'native_v1m_recomputation_verified_in_this_run':True,
       'native_traces_in_v1m':4,'attested_direct_A_to_B':True,
       'attested_direct_A_to_C':False,'native_disclosure_channel_to_receiver_present':False,
       'native_full_two_port_observer_present':False,
       'native_receiver_can_identify_missing_sender_decision':False,
       'shadow_internal_cause_ambiguous_even_through_T3':True,
       'native_learning_proven':False,'native_absence_witnesses':0,
       'native_scored_receiver_judgments':0,'native_operator_updates':0,
       'native_fixture_sha256':m['native_fixture_sha256'],
       'frozen_native_sources':m['frozen_native_sources'],
       'native_original_edge_A_B':{'sender_emissions':2,'receiver_ingress':2},
       'native_variant_edge_A_B':{'sender_emissions':0,'receiver_ingress':0},
       'shadow_worlds':worlds,
       'shadow_tier_authority':'COUNTERFACTUAL_DISCLOSURE_MODEL_ONLY',
       'shadow_projection_tiers':[{'tier':i} for i in range(4)],
       'shadow_distinguishability_tests':[
           {'world_left':WORLD_IDS[0],'world_right':WORLD_IDS[1],
            'first_distinguishable_at':'NOT_DISTINGUISHABLE_THROUGH_T3'}]}
    return n,canon(n),m,mb


def outcome():return analyze(*specimen())


def test_schema_scope_and_counts():
    r=outcome()
    assert r['schema']==SCHEMA and r['status']==STATUS
    assert r['shadow_case_count']==10
    assert r['native_authenticated_decision_records']==r['native_receiver_judgments']==0
    assert r['native_sender_operator_updates']==0 and r['native_learning_proven'] is False
    assert r['native_v1n_recomputation_verified_in_this_run'] is False
    assert r['shadow_direct_link']=='A->B:7->0'
    assert r['T3_worlds_indistinguishable'] is True
    assert r['shadow_actions_do_not_identify_causal_utility'] is True
    counter=r['shadow_same_declared_decision_distinct_possible_causes']
    assert counter['same_action']=='OPERATOR_VARIANT_SELECTED'
    assert len(set(counter['hidden_cause_labels']))==2
    assert counter['cause_identified_by_decision_record'] is False
    assert counter['worlds_native_executed'] is False
    assert all(not x['native_authority'] and not x['record_transmitted_in_native_spk']
               for x in r['shadow_case_classifications'])


def test_hashes_source_bound():
    n,nb,m,mb=specimen();r=analyze(n,nb,m,mb)
    assert r['reference_v1n_sha256']==sha(nb)
    assert r['reference_v1m_sha256']==sha(mb)
    assert r['frozen_native_sources']==m['frozen_native_sources']


def test_same_T3_but_declared_action_differs():
    r=outcome();a,b=[w['record'] for w in r['shadow_decision_record_examples']]
    assert a['action']!=b['action']
    assert a['episode_id']==b['episode_id']
    assert a['expected_event_id']==b['expected_event_id']
    assert r['shadow_laboratory_record_differentiates_declared_actions_only']


@pytest.mark.parametrize('which',list(range(10)))
def test_all_ten_cases(which):
    r=outcome();row=r['shadow_case_classifications'][which]
    expected=('NO_DECISION_RECORD','UNAUTHENTICATED_LAB_CLAIM',
        'NOT_RECEIVED_BY_SHADOW_OBSERVER','NO_PREDECISION_EXPECTATION',
        'NO_INDEPENDENT_COVERAGE','CONDITIONALLY_VISIBLE_IN_CLOSED_LAB_ONLY',
        'WRONG_DIRECT_EDGE','TIMING_OR_REPLAY_INVALID','UNBOUND_IDENTITY','UNBOUND_IDENTITY')
    assert row['classification']==expected[which]


@pytest.mark.parametrize('field,bad',[
 ('schema','other'),('status','VERIFIED'),('reference_v1m_sha256','0'*64),
 ('native_v1m_recomputation_verified_in_this_run',False),
 ('native_traces_in_v1m',3),('attested_direct_A_to_C',True),
 ('attested_direct_A_to_B',False),('native_disclosure_channel_to_receiver_present',True),
 ('native_full_two_port_observer_present',True),
 ('native_receiver_can_identify_missing_sender_decision',True),
 ('shadow_internal_cause_ambiguous_even_through_T3',False),
 ('native_learning_proven',True),('native_absence_witnesses',1),
 ('native_scored_receiver_judgments',1),('native_operator_updates',1),
 ('native_fixture_sha256','OTHER'),('frozen_native_sources',{}),
 ('native_original_edge_A_B',{'sender_emissions':0,'receiver_ingress':0}),
 ('native_variant_edge_A_B',{'sender_emissions':2,'receiver_ingress':2}),
 ('shadow_tier_authority','NATIVE_AUTHENTICATED'),
 ('shadow_projection_tiers',[]),('shadow_distinguishability_tests',[]),
])
def test_predecessor_promotions_rejected(field,bad):
    n,_,m,mb=specimen();n[field]=bad
    with pytest.raises((InterventionError,ValueError,AssertionError)):
        analyze(n,canon(n),m,mb)


@pytest.mark.parametrize('field,bad',[
 ('ingress_count',1),('sender_port_count',1),('expected',False),('covered',False),
 ('hidden_decision_cause','VERIFIED'),('world_origin','NATIVE'),
])
def test_T3_cause_falsifications_rejected(field,bad):
    n,_,m,mb=specimen();n['shadow_worlds'][0][field]=bad
    with pytest.raises((InterventionError,ValueError,AssertionError)):
        analyze(n,canon(n),m,mb)


def test_duplicate_world_rejected():
    n,_,m,mb=specimen();n['shadow_worlds'][2]['world_id']=n['shadow_worlds'][0]['world_id']
    with pytest.raises((InterventionError,ValueError,AssertionError)):
        analyze(n,canon(n),m,mb)


def test_noncanonical_report_rejected():
    n,nb,m,mb=specimen()
    with pytest.raises((InterventionError,ValueError,AssertionError)):
        analyze(n,nb.rstrip(),m,mb)


def test_wrong_linkage_rejected():
    n,nb,m,mb=specimen();m['native_fixture_sha256']='other'
    with pytest.raises((InterventionError,ValueError,AssertionError)):
        analyze(n,nb,m,canon(m))


@pytest.mark.parametrize('field,bad,status',[
 ('schema','fake','MALFORMED_RECORD'),('authority','NATIVE','MALFORMED_RECORD'),
 ('sender','C','WRONG_DIRECT_EDGE'),('receiver','C','WRONG_DIRECT_EDGE'),
 ('source_channel',0,'WRONG_DIRECT_EDGE'),('receiver_channel',7,'WRONG_DIRECT_EDGE'),
 ('episode_id','bad','UNBOUND_IDENTITY'),('decision_id','bad','UNBOUND_IDENTITY'),
 ('expected_event_id','bad','UNBOUND_IDENTITY'),('action','BAD','MALFORMED_RECORD'),
 ('ack_tick',2,'TIMING_OR_REPLAY_INVALID'),('decision_tick',0,'TIMING_OR_REPLAY_INVALID'),
 ('receipt_tick',5,'TIMING_OR_REPLAY_INVALID'),('verdict_tick',3,'TIMING_OR_REPLAY_INVALID'),
 ('decision_tick',True,'TIMING_OR_REPLAY_INVALID'),
])
def test_shadow_record_adversarial(field,bad,status):
    d=example_record('OPERATOR_VARIANT_SELECTED');d[field]=bad
    assert inspect(d,declared_lab_producer=True,independent_receipt=True,
                   covered=True,expected=True)==status


def test_more_fields_rejected():
    d=example_record('OPERATOR_VARIANT_SELECTED');d['fake_attestation']=True
    assert inspect(d,declared_lab_producer=True,independent_receipt=True,
                   covered=True,expected=True)=='MALFORMED_RECORD'


def test_type_confusion_rejected():
    d=example_record('OPERATOR_VARIANT_SELECTED');d['source_channel']=True
    assert inspect(d,declared_lab_producer=True,independent_receipt=True,
                   covered=True,expected=True)=='WRONG_DIRECT_EDGE'


def test_no_decision_record_not_vote():
    assert inspect(None)=='NO_DECISION_RECORD'
    assert not any('learn' in x.lower() and 'no-' not in x.lower() for x in EXCLUDED)


def test_negative_claims_preserved():
    r=outcome();assert 'sha256-content-integrity-not-sender-authentication' in r['claims_excluded']
    assert 'a-recorded-decision-is-not-proof-that-it-caused-an-absent-spike' in r['claims_excluded']


def test_lab_flags_not_native_evidence():
    d=example_record('OPERATOR_VARIANT_SELECTED')
    assert inspect(d,declared_lab_producer=True,independent_receipt=True,
                   expected=True,covered=True)=='CONDITIONALLY_VISIBLE_IN_CLOSED_LAB_ONLY'
    assert inspect(d,declared_lab_producer=True,independent_receipt=True,
                   expected=False,covered=True)=='NO_PREDECISION_EXPECTATION'
    assert inspect(d,declared_lab_producer=True,independent_receipt=False,
                   expected=True,covered=True)=='NOT_RECEIVED_BY_SHADOW_OBSERVER'


def test_cli_full_predecessor_recompute_required(tmp_path,monkeypatch):
    n,nb,m,mb=specimen()
    root=tmp_path/'checkout';root.mkdir()
    paths={}
    for name in cli.NAMES:
        p=tmp_path/f'{name}.json';p.write_bytes(nb if name=='v1n' else mb)
        paths[name]=p
    def fake_main(argv):
        Path(argv[argv.index('--out')+1]).write_bytes(nb)
        return 0
    monkeypatch.setattr(cli,'nmain',fake_main)
    argv=['--root',str(root)]
    for name in cli.NAMES:argv.extend(('--'+name,str(paths[name])))
    # Many predecessor references intentionally share identical synthetic bytes;
    # distinct files are still distinct inputs and our safe_input verifies paths.
    argv+=['--out',str(tmp_path/'out.json')]
    assert cli.main(argv)==0
    out=json.loads((tmp_path/'out.json').read_bytes())
    assert out['native_v1n_recomputation_verified_in_this_run'] is True
    assert cli.main(argv)==2 # fail-closed existing output
    assert cli.main(argv[:-1]+[str(paths['v1n'])])==2


def test_cli_recompute_byte_drift_rejected(tmp_path,monkeypatch):
    n,nb,m,mb=specimen()
    root=tmp_path/'checkout';root.mkdir()
    paths={}
    for name in cli.NAMES:
        p=tmp_path/f'{name}.json';p.write_bytes(nb if name=='v1n' else mb);paths[name]=p
    def fake_main(argv):
        Path(argv[argv.index('--out')+1]).write_bytes(b'{}\n');return 0
    monkeypatch.setattr(cli,'nmain',fake_main)
    argv=['--root',str(root)]
    for name in cli.NAMES:argv.extend(('--'+name,str(paths[name])))
    argv+=['--out',str(tmp_path/'out.json')]
    assert cli.main(argv)==2 and not (tmp_path/'out.json').exists()
