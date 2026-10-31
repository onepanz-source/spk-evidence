"""SPK v1s: cooperative *process* serialization of verified durable v1r epochs.

No frozen code modification. Every public operation holds an exclusive Linux
flock while replaying original PE+BV ticks, committing and checking the epoch.
SQLite remains the atomic tick journal; flock is an additive *cooperative*
writer contract, not a security boundary against privileged local processes.
External irreversible side effects are not supported.
"""
from __future__ import annotations
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import stat
import time
from spk_native_learning_v1 import durable_runtime_v1 as d

SCHEMA='spk-native-learning-serialized-durable-epochs/v1s'
class SerialReject(RuntimeError): pass

def _safe_path(value):
    path=Path(value).absolute()
    if path.name in ('', '.', '..') or path.is_symlink():
        raise SerialReject('UNSAFE_LEDGER_PATH')
    if path.exists() and not path.is_file():
        raise SerialReject('LEDGER_NOT_REGULAR_FILE')
    if path.parent.is_symlink():
        raise SerialReject('UNSAFE_LEDGER_PARENT')
    path.parent.mkdir(parents=True,exist_ok=True)
    return path

@contextmanager
def serialized_ownership(db_path, *, wait_seconds=5.0):
    """Exclusive cooperative ownership spanning *replay* and *commit*.

    File locks are advisory, per-process-open and released by kernel on exit.
    An external process invoking legacy v1r directly is outside this guarantee.
    """
    if type(wait_seconds) not in (int,float) or not 0<=wait_seconds<=60:
        raise SerialReject('INVALID_LOCK_TIMEOUT')
    path=_safe_path(db_path)
    lock=path.with_name(path.name+'.spk-v1s.lock')
    flags=os.O_CREAT|os.O_RDWR|getattr(os,'O_CLOEXEC',0)|getattr(os,'O_NOFOLLOW',0)
    try:
        fd=os.open(lock,flags,0o600)
    except (OSError,ValueError) as exc:
        raise SerialReject('LOCK_FILE_UNSAFE_OR_UNAVAILABLE') from exc
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise SerialReject('LOCK_FILE_NOT_REGULAR')
        deadline=time.monotonic()+wait_seconds
        while True:
            try:
                fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
                break
            except BlockingIOError as exc:
                if time.monotonic()>=deadline:
                    raise SerialReject('CONCURRENT_WRITER_BUSY') from exc
                time.sleep(min(0.02,max(0.001,deadline-time.monotonic())))
        yield path
    finally:
        try:fcntl.flock(fd,fcntl.LOCK_UN)
        finally:os.close(fd)

def _rows(path):
    if not path.is_file():return []
    # Read-only: avoid initializing or mutating the evidence being audited.
    with sqlite3.connect('file:'+path.as_posix()+'?mode=ro',uri=True) as db:
        return db.execute('SELECT id,status,request_json,initial_p,final_p,result_sha FROM epochs ORDER BY id').fetchall()

def _audit_locked(path,root):
    rows=_rows(path)
    chain=[]; prior=None
    for index,(eid,status,request,initial,final,result_sha) in enumerate(rows):
        if eid!=index:raise SerialReject('EPOCH_SEQUENCE_GAP')
        if status!='CLOSED':raise SerialReject('EPOCH_NOT_CLOSED')
        try:
            args=json.loads(request)
            if set(args)!= {'choice','goal','second_tick'}:
                raise ValueError('unexpected arguments')
            observed=d.run_epoch(path,eid,args['choice'],args['goal'],second_tick=args['second_tick'],root=root)
        except (KeyError,TypeError,ValueError) as exc:
            raise SerialReject('EPOCH_REQUEST_INVALID') from exc
        if observed['new_tick_rows']!=0:
            raise SerialReject('AUDIT_MUST_NOT_APPEND_TICKS')
        if (d.canonical(observed['initial_P'])!=initial or
            d.canonical(observed['final_P'])!=final or observed['output_sha256']!=result_sha):
            raise SerialReject('EPOCH_RESULT_OR_P_DRIFT')
        if prior is not None and observed['initial_P']!=prior:
            raise SerialReject('CROSS_EPOCH_P_DISCONTINUITY')
        if not observed['C_PE_reads'] or observed['C_PE_reads'][0][1]!=observed['initial_P']['version']:
            raise SerialReject('PE_DID_NOT_USE_COMMITTED_P')
        prior=observed['final_P']
        chain.append({'epoch':eid,'tick_count':observed['tick_count'],
                     'P_from':observed['initial_P']['version'],
                     'P_to':observed['final_P']['version'],
                     'C_first_PE_read':observed['C_PE_reads'][0],
                     'output_sha256':observed['output_sha256'],
                     'journal_head_sha256':observed['journal_head_sha256']})
    return {'schema':SCHEMA,'status':'SERIAL_CAUSAL_CHAIN_VERIFIED',
            'epochs':chain,'epoch_count':len(chain),'last_P':prior,
            'chain_sha256':d.sha(d.canonical(chain)),
            'security_boundary':'ADVISORY_COOPERATIVE_FLOCK_NOT_PRIVILEGED_HOST'}

def audit(db_path, *, root='.',wait_seconds=5.0):
    with serialized_ownership(db_path,wait_seconds=wait_seconds) as path:
        return _audit_locked(path,root)

def run_epoch(db_path,epoch,choice,goal,*,second_tick=30,pause_after=None,root='.',wait_seconds=5.0):
    with serialized_ownership(db_path,wait_seconds=wait_seconds) as path:
        report=d.run_epoch(path,epoch,choice,goal,second_tick=second_tick,pause_after=pause_after,root=root)
        chain=_audit_locked(path,root)
        if chain['epoch_count']<=epoch or chain['epochs'][epoch]['output_sha256']!=report['output_sha256']:
            raise SerialReject('POST_COMMIT_AUDIT_FAILED')
        return {'schema':SCHEMA,'operation':'COMMITTED_OR_REPLAYED','epoch':report,
                'chain_sha256':chain['chain_sha256'],'audited_epochs':chain['epoch_count']}

def run_sequence(db_path, cases,*,root='.',wait_seconds=5.0,interrupt_after_epoch=None):
    """Cooperatively serialize entire series. Partial completed prefix is recoverable.

    IMPORTANT: sequence is NOT a multi-epoch atomic transaction. If interrupted,
    completed epochs remain committed. Repeating the same sequence is idempotent.
    """
    if type(cases) not in (tuple,list) or not cases:
        raise SerialReject('EMPTY_OR_INVALID_SEQUENCE')
    if interrupt_after_epoch is not None and (type(interrupt_after_epoch) is not int or
                                               interrupt_after_epoch<0):
        raise SerialReject('INVALID_INTERRUPT_INDEX')
    with serialized_ownership(db_path,wait_seconds=wait_seconds) as path:
        reports=[]
        for index,spec in enumerate(cases):
            if type(spec) not in (list,tuple) or len(spec)!=2 or any(type(x) is not int for x in spec):
                raise SerialReject('INVALID_CASE_SHAPE')
            result=d.run_epoch(path,index,spec[0],spec[1],root=root)
            reports.append(result)
            if interrupt_after_epoch==index:
                raise d.SimulatedPowerLoss('SIMULATED_PROCESS_EXIT_AFTER_CLOSED_EPOCH:'+str(index))
        chain=_audit_locked(path,root)
        if chain['epoch_count']!=len(cases):
            raise SerialReject('EXPECTED_FULL_CHAIN_MISMATCH')
        return {'schema':SCHEMA,'operation':'SERIAL_SEQUENCE_COMPLETE',
                'chain':chain,'new_tick_rows':sum(r['new_tick_rows'] for r in reports),
                'C_PE_reads_by_epoch':[r['C_PE_reads'] for r in reports]}
