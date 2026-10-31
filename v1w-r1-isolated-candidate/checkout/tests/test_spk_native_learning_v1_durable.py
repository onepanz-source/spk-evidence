"""Durability, safety, restart, continuous P and frozen-boundary tests."""
from pathlib import Path
import json, sqlite3, hashlib
import pytest
from spk_native_learning_v1 import durable_runtime_v1 as d
from spk_native_learning_v1.live_learning_scheduler_v1r import (
    execute_resume_learning_v1r, LiveBVRejected, LiveBVPlanV0e)
from spk_native_learning_v1.conformance_v1 import setup,run,observed,compare_frozen_when_learning_off

@pytest.fixture(autouse=True)
def source_pins_in_partial_checkout(monkeypatch):
    root=Path.cwd()
    target=root/'spk_backvalidation_v0/live_dual_scheduler_v0e.py'
    genuine=target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()==\
             '2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9'
    if not genuine:monkeypatch.setattr(d,'pin_sources',lambda _: {'LOCAL_TEST_FIXTURE':True})

@pytest.mark.parametrize('choice,goal,post',[(12,11,11),(11,12,12)])
def test_original_intrinsic_P_transition_survives_new_fork(choice,goal,post):
    r=execute_resume_learning_v1r(*setup(choice,goal),bv=LiveBVPlanV0e(assessor='A'))
    b=[x for x in r['forward']['batches'] if x['node']=='C']
    assert [x['P_version'] for x in b]==[0,1]
    assert [x['P_choice'] for x in b]==[choice,post]
    assert [x['outputs'] for x in b]==[[choice],[post]]

@pytest.mark.parametrize('cut', [1,2,3,9,13,14,15,16,22,24])
def test_interrupted_durable_replay_matches_uninterrupted(tmp_path,cut):
    db=tmp_path/'learning.db'
    with pytest.raises(d.SimulatedPowerLoss):d.run_epoch(db,0,12,11,pause_after=cut)
    assert d.ledger_inventory(db)['epochs'][0]['status']=='RUNNING'
    r=d.run_epoch(db,0,12,11)
    assert r['final_P']['choice']==11
    assert r['final_P']['version']==1
    assert r['C_PE_reads']==[[10,0,12,[12]],[30,1,11,[11]]]
    assert len(r['P_grants'])==1
    assert r['new_tick_rows']==r['tick_count']-cut
    again=d.run_epoch(db,0,12,11)
    assert again['new_tick_rows']==0
    assert again['output_sha256']==r['output_sha256']
    assert d.ledger_inventory(db)['ticks']==r['tick_count']

def test_true_cross_epoch_P_inheritance_and_relearning(tmp_path):
    db=tmp_path/'m.db'
    a=d.run_epoch(db,0,12,11)
    b=d.run_epoch(db,1,12,11)
    c=d.run_epoch(db,2,12,12)
    assert [a['final_P']['version'],b['final_P']['version'],c['final_P']['version']]==[1,1,2]
    assert [a['final_P']['choice'],b['final_P']['choice'],c['final_P']['choice']]==[11,11,12]
    assert b['initial_P']==a['final_P'] and c['initial_P']==b['final_P']
    assert b['C_PE_reads'][0]==[10,1,11,[11]]
    assert c['C_PE_reads'][1]==[30,2,12,[12]]
    assert all(r['status']=='CLOSED' for r in (a,b,c))
    assert d.run_epoch(db,1,12,11)['new_tick_rows']==0

@pytest.mark.parametrize('bad_epoch',[-1,1,2,'0',True])
def test_out_of_order_epoch_denied(tmp_path,bad_epoch):
    with pytest.raises(d.DurableReject):d.run_epoch(tmp_path/'m.db',bad_epoch,12,11)

@pytest.mark.parametrize('change',[(11,11),(12,12),(11,12)])
def test_same_epoch_cannot_change_inputs(tmp_path,change):
    db=tmp_path/'m.db';d.run_epoch(db,0,12,11)
    with pytest.raises(d.DurableReject,match='SOURCE_OR_INPUT_FINGERPRINT_CHANGED'):
        d.run_epoch(db,0,*change)

@pytest.mark.parametrize('col,value',[
    ('snapshot','{}'),('prev_sha','0'*64),('row_sha','f'*64)])
def test_tick_tamper_rejected_and_not_repaired(tmp_path,col,value):
    db=tmp_path/'m.db';d.run_epoch(db,0,12,11)
    con=sqlite3.connect(db)
    con.execute(f'UPDATE ticks SET {col}=? WHERE epoch=0 AND seq=14',(value,));con.commit();con.close()
    with pytest.raises(d.DurableReject,match='COMMITTED_CAUSAL_PREFIX_DRIFT'):
        d.run_epoch(db,0,12,11)

@pytest.mark.parametrize('bad',[
    {'choice':13,'domain':'P','grants':1,'owner':'C','version':1},
    {'choice':11,'domain':'S','grants':1,'owner':'C','version':1},
    {'choice':11,'domain':'P','grants':1,'owner':'A','version':1},
    {'choice':11,'domain':'P','grants':0,'owner':'C','version':1},
    {'choice':11,'domain':'P','grants':True,'owner':'C','version':1},
])
def test_spoofed_initial_P_denied(bad):
    with pytest.raises(LiveBVRejected,match='INITIAL_P_CUSTODY_INVALID'):
        execute_resume_learning_v1r(*setup(12,11),initial_P=bad,bv=LiveBVPlanV0e(assessor='A'))

@pytest.mark.parametrize('cut', [1,14,22])
def test_incomplete_epoch_blocks_successor(tmp_path,cut):
    db=tmp_path/'m.db'
    with pytest.raises(d.SimulatedPowerLoss):d.run_epoch(db,0,12,11,pause_after=cut)
    with pytest.raises(d.DurableReject,match='PREVIOUS_EPOCH_NOT_CLOSED'):
        d.run_epoch(db,1,12,11)

def test_mutated_parent_P_denied(tmp_path):
    db=tmp_path/'m.db'
    d.run_epoch(db,0,12,11); d.run_epoch(db,1,12,11)
    con=sqlite3.connect(db)
    con.execute("UPDATE epochs SET final_p=? WHERE id=0",(d.canonical({'owner':'C','domain':'P','choice':12,'version':1,'grants':1}),))
    con.commit();con.close()
    with pytest.raises(d.DurableReject,match='PREVIOUS_P_CONTINUITY_BROKEN|FINALIZED_EPOCH_REPLAY_DRIFT'):
        d.run_epoch(db,1,12,11)

def test_final_epoch_digest_tamper_denied(tmp_path):
    db=tmp_path/'m.db';d.run_epoch(db,0,12,11)
    con=sqlite3.connect(db)
    con.execute("UPDATE epochs SET result_sha='forged' WHERE id=0");con.commit();con.close()
    with pytest.raises(d.DurableReject,match='FINALIZED_EPOCH_REPLAY_DRIFT'):
        d.run_epoch(db,0,12,11)

def test_no_double_grant_after_crash_at_grant(tmp_path):
    db=tmp_path/'m.db'
    with pytest.raises(d.SimulatedPowerLoss):d.run_epoch(db,0,12,11,pause_after=15)
    p=d.run_epoch(db,0,12,11)
    assert len(p['P_grants'])==1 and p['final_P']['grants']==1
    assert d.run_epoch(db,0,12,11)['final_P']['grants']==1

def test_no_C_mutation_without_BV_credit():
    from spk_native_learning_v1.live_learning_scheduler_v1r import LearningPlanV1, LiveBVPlanV0e
    for bv,learn in ((LiveBVPlanV0e(enabled=False,assessor='A'),LearningPlanV1()),
                     (LiveBVPlanV0e(assessor='A'),LearningPlanV1(enabled=False)),
                     (LiveBVPlanV0e(assessor='A'),LearningPlanV1(mode='verify')),
                     (LiveBVPlanV0e(assessor='A'),LearningPlanV1(max_grants=0))):
        r=execute_resume_learning_v1r(*setup(12,11),bv=bv,learn=learn)
        assert not r['learning']['grants'] and r['learning']['final']['version']==0

def test_no_frozen_v0e_regression():
    assert compare_frozen_when_learning_off()['frozen_PE_forward_and_BV_resource_parity']

def test_ledger_does_not_claim_external_durability():
    assert d.SCHEMA == 'spk-native-learning-durable-tick-ledger/v1'

@pytest.mark.parametrize('field,value',[
    ('input_sha','changed'),
    ('request_json','{"choice":11,"goal":11,"second_tick":30}'),
    ('initial_p','{}'),
])
def test_epoch_authority_input_tamper_rejected(tmp_path,field,value):
    db=tmp_path/'m.db';d.run_epoch(db,0,12,11)
    con=sqlite3.connect(db)
    con.execute(f'UPDATE epochs SET {field}=? WHERE id=0',(value,));con.commit();con.close()
    with pytest.raises((d.DurableReject,LiveBVRejected)):
        d.run_epoch(db,0,12,11)

def test_parent_replay_prevents_initial_P_forgery(tmp_path):
    db=tmp_path/'m.db';d.run_epoch(db,0,12,11)
    con=sqlite3.connect(db)
    con.execute("UPDATE epochs SET final_p=? WHERE id=0",(d.canonical({'owner':'C','domain':'P','choice':12,'version':1,'grants':1}),))
    con.commit();con.close()
    with pytest.raises(d.DurableReject,match='FINALIZED_EPOCH_REPLAY_DRIFT'):
        d.run_epoch(db,1,12,11)
