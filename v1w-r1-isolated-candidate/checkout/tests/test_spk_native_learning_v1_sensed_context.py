"""PE sensed-context v1v: original PE, bounded evidence and durable replay."""
from pathlib import Path
import hashlib,multiprocessing as mp,sqlite3
import pytest
from spk_native_learning_v1 import sensed_context_v1v as s, contextual_durable_v1u as d
CASES=(((40,42),11,15),((41,43),11,12),((40,42,99),11,15),((41,43,99),11,12),((40,42),11,11))
@pytest.fixture(autouse=True)
def partial_original_pin_only(monkeypatch):
 from spk_native_learning_v1.conformance_v1 import ORIGINAL
 if not all(Path.cwd().joinpath(p).is_file() and hashlib.sha256(Path.cwd().joinpath(p).read_bytes()).hexdigest()==v for p,v in ORIGINAL.items()):
  monkeypatch.setattr(s,'pin_sources',lambda _: dict(ORIGINAL))
  monkeypatch.setattr(d,'pin_sources',lambda _: dict(ORIGINAL))

def test_classifier_real_frozen_pe():
 from spk_architecture_v1.pe_execution_v1b import _compute_local
 assert s.classify((40,42))['pe_emissions']==[71]
 assert s.classify((41,43))['pe_emissions']==[72]
 assert s.classify((40,42,99))['signature']==s.classify((40,42))['signature']
 assert s.classify((41,43,99))['signature']==s.classify((41,43))['signature']
 assert s.classify.__globals__['_source_check'].__module__==s.__name__
 assert _compute_local.__module__=='spk_architecture_v1.pe_execution_v1b'

@pytest.mark.parametrize('bad',[(),(40,),(40,41),(42,43),(40,43),(41,42),(40,40,42),(41,43,43),(40,41,42,43),(40,41,42,43,99),(42,40),(40,42,42),(40,42,111),(40,42,True),('40',42),(40,42,99,99),(99,99)])
def test_bad_observations_fail_closed(bad):
 with pytest.raises(s.SensorReject):s.classify(bad)

def test_sequence_and_heldout_noise_pe_recall(tmp_path):
 p=tmp_path/'s.db';r=s.run_sequence(p,CASES);r2=s.run_sequence(p,CASES)
 assert r['new_tick_rows']==325 and r2['new_tick_rows']==0
 assert r['audit']==r2['audit']==s.audit(p)
 assert [x['episode']['final_P']['version'] for x in r['episodes']]==[2,1,2,1,3]
 assert [len(x['episode']['P_grants']) for x in r['episodes']]==[2,1,0,0,1]
 assert [x['derived_context'] for x in r['episodes']]==['ctx0','ctx1','ctx0','ctx1','ctx0']
 assert [x['episode']['C_PE_reads'][0] for x in r['episodes']]==[
  [10,0,11,[11]],[10,0,11,[11]],[10,2,15,[15]],[10,1,12,[12]],[10,2,15,[15]]]
 assert r['audit']['selector']['bindings']=={'s71':'ctx0','s72':'ctx1'}

def test_reverse_order_swaps_internal_names_not_signature_association(tmp_path):
 first=s.run_sequence(tmp_path/'ab.db',CASES[:2])
 other=s.run_sequence(tmp_path/'ba.db',(CASES[1],CASES[0]))
 assert first['audit']['selector']['bindings']=={'s71':'ctx0','s72':'ctx1'}
 assert other['audit']['selector']['bindings']=={'s72':'ctx0','s71':'ctx1'}
 assert {sig:first['audit']['contextual']['bank'][ctx]['choice'] for sig,ctx in first['audit']['selector']['bindings'].items()} == {sig:other['audit']['contextual']['bank'][ctx]['choice'] for sig,ctx in other['audit']['selector']['bindings'].items()}

@pytest.mark.parametrize('cut',[1,9,13,14,15,27,60])
def test_crash_recovery_same_observation(tmp_path,cut):
 p=tmp_path/'bank.db'
 with pytest.raises(d.SimulatedPowerLoss):s.run_epoch(p,0,(40,42),11,15,pause_after=cut)
 r=s.run_epoch(p,0,(40,42),11,15)
 assert r['episode']['new_tick_rows']+cut==65
 assert s.run_epoch(p,0,(40,42),11,15)['episode']['new_tick_rows']==0
 assert s.audit(p)['contextual']['bank']['ctx0']['choice']==15

def test_rebind_same_epoch_denied(tmp_path):
 p=tmp_path/'bank.db';s.run_epoch(p,0,(40,42),11,15)
 with pytest.raises(s.SensorReject):s.run_epoch(p,0,(41,43),11,15)
 with pytest.raises(s.SensorReject):s.run_epoch(p,0,(40,42,99),11,15)

def test_pending_selector_resume(tmp_path,monkeypatch):
 p=tmp_path/'bank.db';real=d.run_epoch
 def fail(*a,**kw):raise d.SimulatedPowerLoss('BEFORE_CONTEXT_EPOCH_JOURNAL')
 monkeypatch.setattr(d,'run_epoch',fail)
 with pytest.raises(d.SimulatedPowerLoss):s.run_epoch(p,0,(40,42),11,15)
 monkeypatch.setattr(d,'run_epoch',real)
 assert s.run_epoch(p,0,(40,42),11,15)['episode']['final_P']['version']==2
 assert s.audit(p)['selector']['bindings']=={'s71':'ctx0'}

@pytest.mark.parametrize('field,value',[('signature','s72'),('context','ctx1'),('evidence_json','{}'),('raw_json','[41,43]'),('previous_sha','0'*64),('record_sha','0'*64),('source_sha','f'*64)])
def test_sensor_ledger_tamper_detected(tmp_path,field,value):
 p=tmp_path/'bank.db';s.run_sequence(p,CASES[:2])
 with sqlite3.connect(p) as db:db.execute(f'UPDATE sensed_epoch SET {field}=? WHERE epoch=0',(value,))
 with pytest.raises(s.SensorReject):s.audit(p)

@pytest.mark.parametrize('field,value',[('signature','s99'),('context','ctx9'),('first_epoch',5),('pe_emission',72),('source_sha','f'*64)])
def test_sensor_binding_tamper_detected(tmp_path,field,value):
 p=tmp_path/'bank.db';s.run_sequence(p,CASES[:2])
 with sqlite3.connect(p) as db:db.execute(f'UPDATE sensed_bindings SET {field}=? WHERE signature=?',(value,'s71'))
 with pytest.raises(s.SensorReject):s.audit(p)

def test_cross_context_P_tamper_detected(tmp_path):
 p=tmp_path/'bank.db';s.run_sequence(p,CASES[:2])
 with sqlite3.connect(p) as db:db.execute("UPDATE ctx_epochs SET context='ctx0' WHERE id=1")
 with pytest.raises(s.SensorReject):s.audit(p)

def test_new_epoch_refuses_prior_sensor_tamper(tmp_path):
 p=tmp_path/'bank.db';s.run_sequence(p,CASES[:2])
 with sqlite3.connect(p) as db:db.execute("UPDATE sensed_epoch SET raw_json='[40,42,99]' WHERE epoch=0")
 with pytest.raises(s.SensorReject):s.run_epoch(p,2,(40,42),11,15)

def test_invalid_epoch_and_case_shape(tmp_path):
 with pytest.raises(s.SensorReject):s.run_epoch(tmp_path/'x.db',True,(40,42),11,15)
 with pytest.raises(s.SensorReject):s.run_sequence(tmp_path/'x.db',(((40,42),11),))


def _worker(p,q):
 try:q.put(('OK',s.run_epoch(p,0,(40,42),11,15,wait_seconds=10)['episode']['new_tick_rows']))
 except BaseException as e:q.put(('ERR',type(e).__name__,str(e)))

def test_parallel_cooperative_no_duplication(tmp_path):
 ctx=mp.get_context('fork');q=ctx.Queue();p=tmp_path/'shared.db'
 children=[ctx.Process(target=_worker,args=(p,q)) for _ in range(2)]
 for c in children:c.start()
 for c in children:c.join(20)
 for c in children:
  if c.is_alive():c.terminate();c.join()
 assert all(c.exitcode==0 for c in children)
 assert sorted([q.get(timeout=5),q.get(timeout=5)])==[('OK',0),('OK',65)]

def test_rejected_signal_does_not_mutate_P(tmp_path):
 p=tmp_path/'bank.db';s.run_epoch(p,0,(40,42),11,15)
 before=s.audit(p)
 for bad in ((40,43),(40,41,42,43),(99,99)):
  with pytest.raises(s.SensorReject):s.run_epoch(p,1,bad,11,12)
 assert s.audit(p)==before

def test_plain_context_api_bypass_detected_at_sensed_audit(tmp_path):
 p=tmp_path/'bank.db';s.run_epoch(p,0,(40,42),11,15)
 d.run_epoch(p,1,'ctx0',11,15)
 with pytest.raises(s.SensorReject):s.audit(p)

def test_classifier_rejects_import_substitution(tmp_path,monkeypatch):
 from spk_architecture_v1 import pe_execution_v1b as frozen
 old=frozen._compute_local
 monkeypatch.setattr(frozen,'_compute_local',lambda *args: (0,False,()))
 with pytest.raises(s.SensorReject,match='ORIGINAL_PE_PROVENANCE_DENIED'):
  s.run_epoch(tmp_path/'x.db',0,(40,42),11,15)
 monkeypatch.setattr(frozen,'_compute_local',old)
