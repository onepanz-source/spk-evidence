"""Contextual P bank v1u. Partial-original SHA bypass is test-fixture ONLY.

Release witness and release gate never import this bypass.
"""
from pathlib import Path
import hashlib,multiprocessing as mp,sqlite3
import pytest
from spk_native_learning_v1 import contextual_durable_v1u as d,contextual_serial_v1u as s
CASES=(('alpha',11,15),('beta',11,12),('alpha',11,15),('beta',11,12),('alpha',11,11))
@pytest.fixture(autouse=True)
def waive_pin_for_partial_local_checkout_only(monkeypatch):
 from spk_native_learning_v1.conformance_v1 import ORIGINAL
 if not all((Path.cwd()/p).is_file() and hashlib.sha256((Path.cwd()/p).read_bytes()).hexdigest()==h for p,h in ORIGINAL.items()):
  monkeypatch.setattr(d,'pin_sources',lambda _: {'UNIT_TEST_ONLY':True})

def test_five_interleaved_contexts_real_PE_and_replay(tmp_path):
 p=tmp_path/'c.db';r=s.run_sequence(p,CASES);r2=s.run_sequence(p,CASES)
 assert r['new_tick_rows']==325 and r2['new_tick_rows']==0
 assert r['chain']==r2['chain']==s.audit(p)
 assert [x['P_to'] for x in r['chain']['epochs']]==[2,1,2,1,3]
 assert r['P_grants_by_epoch']==[2,1,0,0,1]
 assert [x[0] for x in r['C_PE_reads_by_epoch']]==[
  [10,0,11,[11]],[10,0,11,[11]],[10,2,15,[15]],[10,1,12,[12]],[10,2,15,[15]]]
 assert r['chain']['bank']['alpha']['version']==3
 assert r['chain']['bank']['beta']['version']==1

@pytest.mark.parametrize('ctx',['alpha','beta','task_1','b-7','x'])
def test_opaque_names_do_not_encode_target(tmp_path,ctx):
 r=s.run_epoch(tmp_path/(ctx+'.db'),0,ctx,11,15)
 assert r['episode']['final_P']['choice']==15

@pytest.mark.parametrize('bad',['','A','X'*25,'a'*25,'../evil','a/b',' x','é',None,True,12])
def test_malformed_context_denied(tmp_path,bad):
 with pytest.raises(d.ContextReject):s.run_epoch(tmp_path/'db',0,bad,11,15)

@pytest.mark.parametrize('choice,goal',[(10,15),(11,14),(True,15),(11,False),(12,17),(0,0),(1.5,11)])
def test_bad_initial_choice_or_goal_denied(tmp_path,choice,goal):
 with pytest.raises(d.ContextReject):s.run_epoch(tmp_path/'db',0,'alpha',choice,goal)

@pytest.mark.parametrize('cut',[1,9,13,14,15,27,60])
def test_seven_durable_crash_boundaries(tmp_path,cut):
 path=tmp_path/'bank.db'
 with pytest.raises(d.SimulatedPowerLoss):s.run_epoch(path,0,'alpha',11,15,pause_after=cut)
 r=s.run_epoch(path,0,'alpha',11,15)
 assert r['episode']['new_tick_rows']+cut==65
 assert r['episode']['final_P']['version']==2
 assert s.run_epoch(path,0,'alpha',11,15)['episode']['new_tick_rows']==0

@pytest.mark.parametrize('column,new',[('context','beta'),('input_sha','0'*64),('request_json','{}'),('initial_p','{}'),('final_p','{}'),('result_sha','0'*64)])
def test_epoch_mutation_detected(tmp_path,column,new):
 p=tmp_path/'bank.db';s.run_sequence(p,CASES)
 with sqlite3.connect(p) as db:db.execute(f'UPDATE ctx_epochs SET {column}=? WHERE id=0',(new,))
 with pytest.raises((d.ContextReject,KeyError,ValueError)):s.audit(p)

@pytest.mark.parametrize('column,new',[('snapshot','{}'),('prev_sha','0'*64),('row_sha','f'*64)])
def test_tick_mutation_detected(tmp_path,column,new):
 p=tmp_path/'bank.db';s.run_sequence(p,CASES)
 with sqlite3.connect(p) as db:db.execute(f'UPDATE ctx_ticks SET {column}=? WHERE epoch=1 AND seq=11',(new,))
 with pytest.raises(d.ContextReject):s.audit(p)

def test_context_genesis_choice_cannot_change(tmp_path):
 p=tmp_path/'bank.db';s.run_epoch(p,0,'alpha',11,15)
 with pytest.raises(d.ContextReject):s.run_epoch(p,1,'alpha',12,15)

def test_context_swap_same_epoch_rejected(tmp_path):
 p=tmp_path/'bank.db';s.run_sequence(p,CASES[:3])
 with pytest.raises(d.ContextReject):s.run_epoch(p,2,'beta',11,15)

def test_global_prior_chain_verified_for_other_context(tmp_path):
 p=tmp_path/'bank.db';s.run_epoch(p,0,'alpha',11,15)
 with sqlite3.connect(p) as db:db.execute("UPDATE ctx_ticks SET snapshot='{}' WHERE epoch=0 AND seq=12")
 with pytest.raises(d.ContextReject):s.run_epoch(p,1,'beta',11,12)

def test_order_independent_bank_but_order_committed(tmp_path):
 first=s.run_sequence(tmp_path/'ab.db',CASES[:2]);other=s.run_sequence(tmp_path/'ba.db',(CASES[1],CASES[0]))
 assert first['chain']['bank']==other['chain']['bank']
 assert first['chain']['chain_sha256']!=other['chain']['chain_sha256']

def test_incomplete_epoch_blocks_new_context(tmp_path):
 p=tmp_path/'bank.db'
 with pytest.raises(d.SimulatedPowerLoss):s.run_epoch(p,0,'alpha',11,15,pause_after=13)
 with pytest.raises(d.ContextReject):s.run_epoch(p,1,'beta',11,12)

def test_closed_prefix_sequence_resume_idempotent(tmp_path):
 p=tmp_path/'bank.db'
 with pytest.raises(d.SimulatedPowerLoss):s.run_sequence(p,CASES,stop_after=1)
 out=s.run_sequence(p,CASES)
 assert out['new_tick_rows']==195
 assert s.run_sequence(p,CASES)['new_tick_rows']==0

def test_invalid_case_shape_denied(tmp_path):
 with pytest.raises(s.SerialReject):s.run_sequence(tmp_path/'bank.db',(('alpha',11),))

def test_symlink_refused(tmp_path):
 real=tmp_path/'real.db';real.touch();link=tmp_path/'link.db';link.symlink_to(real)
 from spk_native_learning_v1.generalized_serial_v1t import SerialReject
 with pytest.raises(SerialReject):s.audit(link)

def _worker(p,q):
 try:q.put(('OK',s.run_epoch(p,0,'alpha',11,15,wait_seconds=10)['episode']['new_tick_rows']))
 except BaseException as e:q.put(('ERR',type(e).__name__,str(e)))

def test_two_cooperative_processes_single_commit(tmp_path):
 ctx=mp.get_context('fork');q=ctx.Queue();p=tmp_path/'bank.db'
 workers=[ctx.Process(target=_worker,args=(p,q)) for _ in range(2)]
 for x in workers:x.start()
 for x in workers:x.join(20)
 for x in workers:
  if x.is_alive():x.terminate();x.join()
 assert all(x.exitcode==0 for x in workers)
 assert sorted((q.get(timeout=5),q.get(timeout=5)))==[('OK',0),('OK',65)]
