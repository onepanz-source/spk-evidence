"""Multi-process cooperative ownership and full-ancestry versioned P integrity."""
from pathlib import Path
import hashlib
import multiprocessing as mp
import sqlite3
import os
import pytest
from spk_native_learning_v1 import durable_runtime_v1 as d
from spk_native_learning_v1 import serialized_runtime_v1s as s

CASES=((12,11),(12,11),(12,12))

@pytest.fixture(autouse=True)
def partial_checkout_pin(monkeypatch):
    from spk_native_learning_v1.conformance_v1 import ORIGINAL
    if not all((Path.cwd()/rel).is_file() and hashlib.sha256((Path.cwd()/rel).read_bytes()).hexdigest()==pin
               for rel,pin in ORIGINAL.items()):
        monkeypatch.setattr(d,'pin_sources',lambda _: {'ISOLATED_TEST_ONLY':True})

def test_three_epochs_and_real_PE_P_rebinding(tmp_path):
    path=tmp_path/'run.db'
    first=s.run_sequence(path,CASES)
    assert first['chain']['epoch_count']==3
    assert [x['P_to'] for x in first['chain']['epochs']]==[1,1,2]
    assert [x[0] for x in first['C_PE_reads_by_epoch']]==[
        [10,0,12,[12]],[10,1,11,[11]],[10,1,11,[11]]]
    assert first['C_PE_reads_by_epoch'][2][-1]==[30,2,12,[12]]
    second=s.run_sequence(path,CASES)
    assert second['new_tick_rows']==0
    assert first['chain']==second['chain']==s.audit(path)

@pytest.mark.parametrize('cut',[1,9,13,14,15,22,24])
def test_process_exit_after_committed_tick(tmp_path,cut):
    path=tmp_path/'tick.db'
    with pytest.raises(d.SimulatedPowerLoss):
        s.run_epoch(path,0,12,11,pause_after=cut)
    e=s.run_epoch(path,0,12,11)
    assert e['epoch']['new_tick_rows']==e['epoch']['tick_count']-cut
    assert e['epoch']['C_PE_reads']==[[10,0,12,[12]],[30,1,11,[11]]]
    assert s.audit(path)['epochs'][0]['P_to']==1

@pytest.mark.parametrize('cut',[0,1])
def test_restart_after_completed_epoch(tmp_path,cut):
    path=tmp_path/'epochs.db'
    with pytest.raises(d.SimulatedPowerLoss):
        s.run_sequence(path,CASES,interrupt_after_epoch=cut)
    assert s.audit(path)['epoch_count']==cut+1
    resumed=s.run_sequence(path,CASES)
    assert resumed['new_tick_rows']>0
    assert resumed['chain']['epoch_count']==3
    assert s.run_sequence(path,CASES)['new_tick_rows']==0

@pytest.mark.parametrize('col,val',[
    ('snapshot','{}'),('row_sha','0'*64),('prev_sha','a'*64)])
def test_tamper_tick_denied(tmp_path,col,val):
    path=tmp_path/'t.db';s.run_sequence(path,CASES)
    with sqlite3.connect(path) as c:
        c.execute('UPDATE ticks SET '+col+'=? WHERE epoch=1 AND seq=12',(val,))
    with pytest.raises(d.DurableReject):s.audit(path)

@pytest.mark.parametrize('col,val',[
    ('final_p','{"choice":12}'),('result_sha','x'*64)])
def test_parent_rewrite_denied(tmp_path,col,val):
    path=tmp_path/'t.db';s.run_sequence(path,CASES)
    with sqlite3.connect(path) as c:
        c.execute('UPDATE epochs SET '+col+'=? WHERE id=0',(val,))
    with pytest.raises((d.DurableReject,s.SerialReject)):s.audit(path)

def test_empty_audit_does_not_initialize_db(tmp_path):
    path=tmp_path/'missing.db'
    r=s.audit(path)
    assert r['epoch_count']==0 and not path.exists()

@pytest.mark.parametrize('bad',[[],(),None,'bad',[(11,12,13)],[('12',11)]])
def test_invalid_sequence_rejected(tmp_path,bad):
    with pytest.raises(s.SerialReject):s.run_sequence(tmp_path/'db',bad)

@pytest.mark.parametrize('bad',[-1,61,True,float('nan'),'5',None])
def test_bad_lock_timeout_rejected(tmp_path,bad):
    with pytest.raises(s.SerialReject):
        with s.serialized_ownership(tmp_path/'db',wait_seconds=bad):pass

def test_symlink_database_denied(tmp_path):
    real=tmp_path/'real.db';real.touch()
    link=tmp_path/'link.db';link.symlink_to(real)
    with pytest.raises(s.SerialReject,match='UNSAFE_LEDGER_PATH'):s.audit(link)

def test_symlink_lock_file_denied(tmp_path):
    path=tmp_path/'ledger.db'
    (tmp_path/'ledger.db.spk-v1s.lock').symlink_to(tmp_path/'other')
    with pytest.raises(s.SerialReject,match='LOCK_FILE_UNSAFE_OR_UNAVAILABLE'):s.audit(path)

def test_wrong_request_does_not_rewrite_committed_epoch(tmp_path):
    path=tmp_path/'db';s.run_sequence(path,CASES)
    digest=s.audit(path)['chain_sha256']
    with pytest.raises(d.DurableReject):s.run_epoch(path,1,11,12)
    assert s.audit(path)['chain_sha256']==digest

def test_external_process_lock_contention(tmp_path):
    """An independently opened FD is denied while owner holds the lock."""
    path=tmp_path/'db'
    ctx=mp.get_context('fork')
    signal=ctx.Event(); release=ctx.Event(); result=ctx.Queue()
    def owner():
        with s.serialized_ownership(path,wait_seconds=1.0):
            signal.set();release.wait(5)
    p=ctx.Process(target=owner);p.start()
    try:
        assert signal.wait(5)
        with pytest.raises(s.SerialReject,match='CONCURRENT_WRITER_BUSY'):
            s.run_epoch(path,0,12,11,wait_seconds=0)
    finally:
        release.set();p.join(5)
        if p.is_alive():p.terminate();p.join(5)
    assert p.exitcode==0
    assert s.run_epoch(path,0,12,11)['epoch']['final_P']['version']==1

def test_two_processes_same_episode_only_one_appends(tmp_path):
    path=tmp_path/'db'
    ctx=mp.get_context('fork')
    q=ctx.Queue()
    def worker():
        try:q.put(('OK',s.run_epoch(path,0,12,11,wait_seconds=5)['epoch']['new_tick_rows']))
        except Exception as exc:q.put(('ERROR',type(exc).__name__+':'+str(exc)))
    a=ctx.Process(target=worker); b=ctx.Process(target=worker)
    a.start();b.start();a.join(8);b.join(8)
    assert a.exitcode==b.exitcode==0
    outcomes=[q.get(timeout=5) for _ in range(2)]
    assert sorted(outcomes)==[('OK',0),('OK',s.audit(path)['epochs'][0]['tick_count'])]
    assert s.audit(path)['epoch_count']==1

def test_owner_failure_releases_kernel_flock(tmp_path):
    path=tmp_path/'db'
    with pytest.raises(RuntimeError,match='crash'):
        with s.serialized_ownership(path):raise RuntimeError('crash')
    assert s.audit(path)['epoch_count']==0

def test_audit_digest_is_canonical_of_epoch_evidence(tmp_path):
    a=s.run_sequence(tmp_path/'db',CASES)['chain']
    assert a['chain_sha256']==d.sha(d.canonical(a['epochs']))
    assert a['security_boundary']=='ADVISORY_COOPERATIVE_FLOCK_NOT_PRIVILEGED_HOST'
