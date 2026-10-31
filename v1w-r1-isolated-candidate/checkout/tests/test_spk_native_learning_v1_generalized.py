"""Native-v1t real PE, expanded C programs, persistence, rollback and refusals.
Unit-only missing-source waiver is NEVER present in the release gate.
"""
from __future__ import annotations
from pathlib import Path
import hashlib,sqlite3,multiprocessing as mp
import pytest
from spk_native_learning_v1 import generalized_scheduler_v1t as v
from spk_native_learning_v1 import generalized_case_v1t as g
from spk_native_learning_v1 import generalized_conformance_v1t as c
from spk_native_learning_v1 import generalized_durable_v1t as d
from spk_native_learning_v1 import generalized_serial_v1t as s

@pytest.fixture(autouse=True)
def checkout_only_pin_skip(monkeypatch):
    # Only if installed source is NOT the original: the release gate NEVER
    # imports this fixture to replace source admission for its report.
    from spk_native_learning_v1.conformance_v1 import ORIGINAL
    if not all((Path.cwd()/rel).is_file() and hashlib.sha256((Path.cwd()/rel).read_bytes()).hexdigest()==pin
               for rel,pin in ORIGINAL.items()):
        monkeypatch.setattr(d,'pin_sources',lambda _:{'ISOLATED_TEST_ONLY':True})

def execute(initial,goal,*,learning=True,bv=True,mode='execute',budget=8,second_tick=30):
    return v.execute_resume_learning_v1r(*g.setup(initial,goal,second_tick=second_tick),
        bv=v.LiveBVPlanV0e(assessor='A',enabled=bv,max_ticks=256),
        learn=v.LearningPlanV1(enabled=learning,mode=mode,max_grants=budget))

@pytest.mark.parametrize('initial',[11,12,15])
@pytest.mark.parametrize('goal',[11,12,15])
def test_native_C_and_A_PE_on_all_nine_pairs(initial,goal):
    r=execute(initial,goal)
    pe=[b for b in r['forward']['batches'] if b['node']=='C']
    assert len(pe)==4 and pe[0]['P_choice']==initial
    assert pe[-1]['outputs']==[goal]
    expected=0; cur=initial
    while cur!=goal:cur=c.CYCLE[cur];expected+=1
    assert len(r['learning']['grants'])==expected
    assert r['learning']['final']['version']==expected
    assert len(r['feedback']['assessments'])==4
    assert len(r['feedback']['deliveries'])==8
    assert r['resources']['P_learning_memory_units']==expected
    assert all(a['A_PE_output'] == (21 if batch['P_choice']==goal else 22)
               for a,batch in zip(r['feedback']['assessments'],pe))

@pytest.mark.parametrize('initial,goal',[(11,15),(12,11),(15,12)])
def test_feedback_off_must_not_mutate_pe_program(initial,goal):
    for extra in ({'bv':False},{'learning':False},{'mode':'verify'},{'budget':0}):
        r=execute(initial,goal,**extra)
        assert len(r['learning']['grants'])==0
        assert all(b['P_choice']==initial for b in r['forward']['batches'] if b['node']=='C')

def test_frozen_PE_BV_parity_three_choice_when_learning_off():
    assert c.baseline_frozen_parity()['frozen_3choice_PE_BV_parity']

@pytest.mark.parametrize('bad',[None,True,'11',10,13,22])
def test_bad_initial_rejected(bad):
    with pytest.raises(ValueError):g.build_case(bad,11)

@pytest.mark.parametrize('bad',[None,False,10,13,19])
def test_bad_goal_rejected(bad):
    with pytest.raises(ValueError):g.build_case(11,bad)

@pytest.mark.parametrize('bad',[0,19,166,True,10.0])
def test_invalid_tick_cadence_rejected(bad):
    with pytest.raises(ValueError):g.build_case(11,12,second_tick=bad)

def test_versioned_p_reads_inside_actual_pe():
    r=execute(11,15)
    c_reads=[b for b in r['forward']['batches'] if b['node']=='C']
    assert [(b['P_version'],b['P_choice'],b['outputs']) for b in c_reads]==[
        (0,11,[11]),(1,12,[12]),(2,15,[15]),(2,15,[15])]
    assert [(x['P_from'],x['P_to']) for x in r['learning']['grants']]==[(0,1),(1,2)]

def test_serial_cross_epoch_P_and_idempotence(tmp_path):
    db=tmp_path/'p.db';cases=((11,15),(11,15),(11,11))
    first=s.run_sequence(db,cases)
    second=s.run_sequence(db,cases)
    assert [e['P_to'] for e in first['chain']['epochs']]==[2,2,3]
    assert first['chain']==second['chain']==s.audit(db)
    assert second['new_tick_rows']==0
    assert first['C_PE_reads_by_epoch'][1][0]==[10,2,15,[15]]
    assert first['C_PE_reads_by_epoch'][2][1]==[30,3,11,[11]]

@pytest.mark.parametrize('cut',[1,9,13,14,15,27,60])
def test_all_restart_boundaries(tmp_path,cut):
    db=tmp_path/'p.db'
    with pytest.raises(d.SimulatedPowerLoss):s.run_epoch(db,0,11,15,pause_after=cut)
    recovered=s.run_epoch(db,0,11,15)
    assert recovered['epoch']['new_tick_rows']+cut==recovered['epoch']['tick_count']
    assert recovered['epoch']['C_PE_reads'][-1]==[70,2,15,[15]]
    assert s.run_epoch(db,0,11,15)['epoch']['new_tick_rows']==0

@pytest.mark.parametrize('column,val',[('snapshot','{}'),('prev_sha','f'*64),('row_sha','0'*64)])
def test_corrupt_tick_rejected(tmp_path,column,val):
    db=tmp_path/'p.db';s.run_epoch(db,0,11,15)
    with sqlite3.connect(db) as sql:
        sql.execute('UPDATE ticks SET '+column+'=? WHERE epoch=0 AND seq=14',(val,))
    with pytest.raises(d.DurableReject):s.audit(db)

@pytest.mark.parametrize('column,val',[('final_p','{"choice":15}'),('result_sha','0'*64),('input_sha','0'*64)])
def test_corrupt_epoch_rejected(tmp_path,column,val):
    db=tmp_path/'p.db';s.run_epoch(db,0,11,15)
    with sqlite3.connect(db) as sql:
        sql.execute('UPDATE epochs SET '+column+'=? WHERE id=0',(val,))
    with pytest.raises((d.DurableReject,s.SerialReject)):s.audit(db)

def test_changed_goal_cannot_replay_same_episode(tmp_path):
    db=tmp_path/'p.db';s.run_epoch(db,0,11,15)
    with pytest.raises(d.DurableReject):s.run_epoch(db,0,11,12)

def test_inheritance_replays_parent_before_using_P(tmp_path):
    db=tmp_path/'p.db';s.run_epoch(db,0,11,15)
    with sqlite3.connect(db) as sql:
        sql.execute('UPDATE ticks SET snapshot=? WHERE epoch=0 AND seq=20',('{}',))
    with pytest.raises(d.DurableReject):s.run_epoch(db,1,11,15)

def test_cooperative_two_writers_single_real_commit(tmp_path):
    db=tmp_path/'p.db';q=mp.get_context('fork').Queue()
    def worker():
        try:q.put(('OK',s.run_epoch(db,0,11,15,wait_seconds=10)['epoch']['new_tick_rows']))
        except Exception as exc:q.put(('ERR',str(exc)))
    ctx=mp.get_context('fork');p1=ctx.Process(target=worker);p2=ctx.Process(target=worker)
    p1.start();p2.start();p1.join(20);p2.join(20)
    if p1.is_alive():p1.terminate();p1.join()
    if p2.is_alive():p2.terminate();p2.join()
    assert p1.exitcode==0 and p2.exitcode==0
    assert sorted([q.get(timeout=5),q.get(timeout=5)])==[('OK',0),('OK',65)]

def test_symlink_database_refused(tmp_path):
    real=tmp_path/'real.db';real.touch()
    link=tmp_path/'link.db';link.symlink_to(real)
    with pytest.raises(s.SerialReject):s.audit(link)
