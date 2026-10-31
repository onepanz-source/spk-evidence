"""v1w queued sensory source -> original PE selection -> BV-owned P tests."""
import hashlib,json,multiprocessing as mp,sqlite3
from pathlib import Path
import pytest
from spk_native_learning_v1 import ingress_scheduler_v1w as w
from spk_native_learning_v1 import sensed_context_v1v as s,contextual_durable_v1u as d
from spk_native_learning_v1.conformance_v1 import ORIGINAL

CASES=(((40,42),11,15),((41,43),11,12),((40,42,99),11,15),
       ((41,43,99),11,12),((40,42),11,11))

@pytest.fixture(autouse=True)
def partial_original_admission(monkeypatch):
    # Test-only local fallback; release gate demands actual frozen file SHA pins.
    if not all(Path.cwd().joinpath(p).is_file() and hashlib.sha256(Path.cwd().joinpath(p).read_bytes()).hexdigest()==h for p,h in ORIGINAL.items()):
        monkeypatch.setattr(s,'pin_sources',lambda _:dict(ORIGINAL))
        monkeypatch.setattr(d,'pin_sources',lambda _:dict(ORIGINAL))

def test_queued_sensor_has_no_context_before_processing(tmp_path):
    p=tmp_path/'g.db';r=w.enqueue(p,0,(40,42),11,15)
    assert r['queued'] and r['context'] is None
    with sqlite3.connect(p) as db:
        assert db.execute('SELECT COUNT(*) FROM ctx_epochs').fetchone()[0]==0
        assert db.execute('SELECT COUNT(*) FROM v1w_stages').fetchone()[0]==1
    result=w.advance(p,0)
    assert result['derived_context']=='ctx0' and result['P_grants']==2
    assert result['first_C_PE_read']==[10,0,11,[11]]
    assert [x['stages'] for x in w.audit(p)['episodes']]==[5]

def test_five_episodes_signature_P_bank_and_replay(tmp_path):
    p=tmp_path/'g.db';first=[w.run_epoch(p,i,*case) for i,case in enumerate(CASES)]
    assert [x['P_grants'] for x in first]==[2,1,0,0,1]
    assert [x['P_to']['version'] for x in first]==[2,1,2,1,3]
    assert [x['derived_context'] for x in first]==['ctx0','ctx1','ctx0','ctx1','ctx0']
    assert [x['first_C_PE_read'] for x in first]==[
        [10,0,11,[11]],[10,0,11,[11]],[10,2,15,[15]],
        [10,1,12,[12]],[10,2,15,[15]]]
    proof=w.audit(p)
    assert proof['P_bank']['ctx0']['version']==3
    assert proof['P_bank']['ctx1']['version']==1
    assert [w.run_epoch(p,i,*case)['new_tick_rows'] for i,case in enumerate(CASES)]==[0]*5
    assert w.audit(p)==proof
    with sqlite3.connect(p) as db:
        assert db.execute('SELECT COUNT(*) FROM ctx_ticks').fetchone()[0]==325
        assert db.execute('SELECT COUNT(*) FROM v1w_stages').fetchone()[0]==25

def test_reverse_order_keeps_signature_not_context_number(tmp_path):
    p=tmp_path/'r.db';w.run_epoch(p,0,*CASES[1]);w.run_epoch(p,1,*CASES[0])
    a=w.audit(p)
    assert a['signatures']=={'s72':'ctx0','s71':'ctx1'}
    assert a['P_bank']['ctx0']['choice']==12 and a['P_bank']['ctx1']['choice']==15

@pytest.mark.parametrize('stage',('OBSERVED','PE_CLASSIFIED','P_SELECTED','BV_COMPLETED'))
def test_stage_cut_idempotent_resume(tmp_path,stage):
    p=tmp_path/'x.db'
    with pytest.raises(w.PowerCut):w.run_epoch(p,0,(40,42),11,15,crash_after_stage=stage)
    q=w.advance(p,0)
    assert q['P_to']['version']==2
    assert q['new_tick_rows'] in (0,65)
    assert w.advance(p,0)['new_tick_rows']==0
    assert w.audit(p)['episodes'][0]['stages']==5

@pytest.mark.parametrize('cut',(1,9,13,14,15,27,60))
def test_crash_inside_BV_and_replay(tmp_path,cut):
    p=tmp_path/'x.db'
    with pytest.raises(d.SimulatedPowerLoss):w.run_epoch(p,0,(40,42),11,15,pause_after=cut)
    q=w.advance(p,0)
    assert cut+q['new_tick_rows']==65
    assert w.audit(p)['P_bank']['ctx0']['choice']==15

@pytest.mark.parametrize('column,altered',[
 ('observations','[41,43]'),('choice',12),('goal',11),('request_sha','f'*64)])
def test_queued_intake_mutation_denied(tmp_path,column,altered):
    p=tmp_path/'x.db';w.run_epoch(p,0,(40,42),11,15)
    with sqlite3.connect(p) as db:db.execute(f'UPDATE v1w_intake SET {column}=? WHERE epoch=0',(altered,))
    with pytest.raises(w.IngressReject):w.audit(p)

@pytest.mark.parametrize('column,altered',[
 ('stage','NOT_A_STAGE'),('payload','{}'),('previous_sha','a'*64),('row_sha','f'*64)])
def test_stage_receipt_mutation_denied(tmp_path,column,altered):
    p=tmp_path/'x.db';w.run_epoch(p,0,(40,42),11,15)
    with sqlite3.connect(p) as db:db.execute(f'UPDATE v1w_stages SET {column}=? WHERE epoch=0 AND seq=1',(altered,))
    with pytest.raises(w.IngressReject):w.audit(p)

@pytest.mark.parametrize('column,altered',[
 ('signature','s99'),('context','ctx9'),('first_epoch',4)])
def test_signature_binding_mutation_denied(tmp_path,column,altered):
    p=tmp_path/'x.db';w.run_epoch(p,0,(40,42),11,15)
    with sqlite3.connect(p) as db:db.execute(f'UPDATE v1w_binding SET {column}=?',(altered,))
    with pytest.raises(w.IngressReject):w.audit(p)

@pytest.mark.parametrize('column,altered',[
 ('context','ctx9'),('signature','s99'),('request_sha','a'*64)])
def test_permit_mutation_denied(tmp_path,column,altered):
    p=tmp_path/'x.db';w.run_epoch(p,0,(40,42),11,15)
    with sqlite3.connect(p) as db:db.execute(f'UPDATE v1w_permit SET {column}=?',(altered,))
    with pytest.raises(w.IngressReject):w.audit(p)

def test_direct_old_context_api_is_fenced_on_v1w_database(tmp_path):
    p=tmp_path/'x.db';w.enqueue(p,0,(40,42),11,15)
    with pytest.raises(sqlite3.IntegrityError,match='V1W_DIRECT_CONTEXT_BYPASS_DENIED'):
        d.run_epoch(p,0,'ctx0',11,15)
    assert w.advance(p,0)['P_grants']==2
    with pytest.raises(sqlite3.IntegrityError,match='V1W_DIRECT_CONTEXT_BYPASS_DENIED'):
        d.run_epoch(p,1,'ctx0',11,15)
    assert w.audit(p)['episodes'][0]['context']=='ctx0'

def test_previous_context_api_cannot_bypass_fence(tmp_path):
    p=tmp_path/'x.db';w.enqueue(p,0,(40,42),11,15)
    with pytest.raises(sqlite3.IntegrityError,match='V1W_DIRECT_CONTEXT_BYPASS_DENIED'):
        s.run_epoch(p,0,(40,42),11,15)
    assert w.advance(p,0)['P_to']['choice']==15

def test_pe_signature_and_observation_match_at_replay(tmp_path):
    p=tmp_path/'x.db';w.run_epoch(p,0,(40,42),11,15)
    with sqlite3.connect(p) as db:db.execute('UPDATE v1w_intake SET observations=? WHERE epoch=0',('[40,42,99]',))
    with pytest.raises(w.IngressReject):w.advance(p,0)

def test_noncanonical_no_PE_credit(tmp_path):
    p=tmp_path/'x.db';w.enqueue(p,0,(40,43),11,15)
    with pytest.raises(w.IngressReject,match='PE_SENSORY_DENIAL'):
        w.advance(p,0)
    with sqlite3.connect(p) as db:
        assert db.execute('SELECT COUNT(*) FROM ctx_epochs').fetchone()[0]==0
        assert db.execute('SELECT COUNT(*) FROM v1w_stages WHERE stage=?',('P_SELECTED',)).fetchone()[0]==0

@pytest.mark.parametrize('bad',[(40,),(40,40,42),(40,43),(40,41,42,43),(42,40),(40,42,111),(40,42,True)])
def test_bad_signal_no_P_commit(tmp_path,bad):
    p=tmp_path/'x.db'
    try:w.enqueue(p,0,bad,11,15)
    except w.IngressReject:pass
    else:
        with pytest.raises(w.IngressReject):w.advance(p,0)
        with sqlite3.connect(p) as db:assert db.execute('SELECT COUNT(*) FROM ctx_epochs').fetchone()[0]==0

def test_nonsequential_and_queued_request_immutable(tmp_path):
    p=tmp_path/'x.db'
    with pytest.raises(w.IngressReject):w.enqueue(p,1,(40,42),11,15)
    w.enqueue(p,0,(40,42),11,15)
    with pytest.raises(w.IngressReject,match='QUEUED_INGRESS_REWRITE_DENIED'):
        w.enqueue(p,0,(41,43),11,15)
    with pytest.raises(w.IngressReject,match='PREVIOUS_INGRESS_PENDING'):
        w.enqueue(p,1,(41,43),11,12)

def _worker(path,queue):
    try:queue.put(('PASS',w.run_epoch(path,0,(40,42),11,15,wait_seconds=10)['new_tick_rows']))
    except BaseException as e:queue.put(('ERR',type(e).__name__,str(e)))

def test_two_processes_do_not_duplicate_P(tmp_path):
    p=tmp_path/'x.db';q=mp.get_context('fork').Queue()
    children=[mp.get_context('fork').Process(target=_worker,args=(p,q)) for _ in range(2)]
    for child in children:child.start()
    for child in children:child.join(20)
    for child in children:
        if child.is_alive():child.terminate();child.join()
    assert all(x.exitcode==0 for x in children)
    assert sorted([q.get(timeout=5),q.get(timeout=5)])==[('PASS',0),('PASS',65)]
    assert len(w.audit(p)['episodes'])==1

def test_source_import_substitution_refused(tmp_path,monkeypatch):
    from spk_architecture_v1 import pe_execution_v1b as original
    monkeypatch.setattr(original,'_compute_local',lambda *args:(0,False,()))
    with pytest.raises(s.SensorReject,match='ORIGINAL_PE_PROVENANCE_DENIED'):
        w.enqueue(tmp_path/'x.db',0,(40,42),11,15)

def test_recovery_verifies_foreign_P_not_only_ingress(tmp_path):
    p=tmp_path/'x.db';w.run_epoch(p,0,(40,42),11,15)
    with sqlite3.connect(p) as db:db.execute("UPDATE ctx_epochs SET final_p='{}' WHERE id=0")
    with pytest.raises((w.IngressReject,d.ContextReject)):w.audit(p)


def test_existing_legacy_P_cannot_get_retroactive_PE_certification(tmp_path):
    p=tmp_path/'legacy.db'
    d.run_epoch(p,0,'ctx0',11,15)
    with sqlite3.connect(p) as db:
        old_schema=db.execute("SELECT name FROM sqlite_master WHERE name LIKE 'v1w_%'").fetchall()
    with pytest.raises(w.IngressReject,match='LEGACY_CONTEXT_HISTORY_WITHOUT_PE_INGRESS'):
        w.enqueue(p,0,(40,42),11,15)
    with pytest.raises(w.IngressReject,match='LEGACY_CONTEXT_HISTORY_WITHOUT_PE_INGRESS'):
        w.audit(p)
    with sqlite3.connect(p) as db:
        assert db.execute("SELECT name FROM sqlite_master WHERE name LIKE 'v1w_%'").fetchall()==old_schema
