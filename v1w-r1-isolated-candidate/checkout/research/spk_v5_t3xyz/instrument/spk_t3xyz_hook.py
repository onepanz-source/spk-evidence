"""SPK T3XYZ passive CPython probe. NO neuron modification and NO verdict synthesis.

Loaded by CPython via PYTHONPATH in *child processes*. Writes only a bounded,
separate JSONL evidence file; exits transparently if it cannot write. Events are
host-level function observations, NOT native event receipts.
"""
from __future__ import annotations
import os
import sys
import json
import threading
import time

_TRACE_FILE = os.environ.get('SPK_T3XYZ_TRACE_FILE')
_ENABLED = os.environ.get('SPK_T3XYZ_CAPTURE', '') == '1' and bool(_TRACE_FILE)
_MAX = int(os.environ.get('SPK_T3XYZ_MAX_EVENTS','25000')) if _ENABLED else 0
_COUNT = 0
_SEQ = 0
_FD = None
_GUARD = threading.local()
_WRITE_LOCK = threading.Lock()
_TARGET_NAMES = frozenset({'_compute_local'})
_PID = os.getpid()


def _safe_scalar(v):
    if v is None or type(v) in (int, bool, str):
        return v if type(v) is not str or len(v) < 160 else v[:160]
    if type(v) is float:
        return v if v == v and v not in (float('inf'),float('-inf')) else 'nonfinite'
    if type(v) is dict:
        return {'kind':'dict','keys':sorted(str(x)[:80] for x in v.keys() if type(x) in (str, int))[:16],'size':len(v)}
    if type(v) in (tuple, list):
        return {'kind':type(v).__name__,'size':len(v)}
    return {'kind':type(v).__name__,'opaque':True}


def _emit(event):
    global _SEQ
    if _FD is None:
        return
    with _WRITE_LOCK:
        _SEQ += 1
        event.update({'pid':_PID, 'seq':_SEQ})
        try:
            os.write(_FD, (json.dumps(event, sort_keys=True, separators=(',',':'))+'\n').encode('utf-8'))
        except OSError:
            pass


def _profile(frame,event,arg):
    global _COUNT
    # Never observe arbitrary foreign object attributes, manipulate a return
    # value, modify frozen program state, or create semantic credit.
    if event not in ('call','return') or frame.f_code.co_name not in _TARGET_NAMES:
        return
    if getattr(_GUARD,'busy',False):
        return
    if _COUNT >= _MAX:
        return
    _GUARD.busy = True
    try:
        _COUNT += 1
        parents=[]
        p=frame.f_back
        for _ in range(6):
            if p is None:
                break
            parents.append({'file':os.path.basename(p.f_code.co_filename), 'function':p.f_code.co_name})
            p=p.f_back
        item={'kind':'compute_'+event,'function':frame.f_code.co_name,
              'source':frame.f_code.co_filename,'line':frame.f_code.co_firstlineno,
              'host_monotonic_ns':time.monotonic_ns(),'stack':parents}
        if event=='call':
            d=frame.f_locals
            item['locals']={k:_safe_scalar(d[k]) for k in ('node','timestamp','channels') if k in d}
            item['declared_argument_names']=list(frame.f_code.co_varnames[:frame.f_code.co_argcount])
        else:
            item['return_type']=type(arg).__name__
            item['return_scalar']=_safe_scalar(arg)
        _emit(item)
    finally:
        _GUARD.busy = False


if _ENABLED:
    try:
        _FD = os.open(_TRACE_FILE, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        _emit({'kind':'probe_loaded','argv':sys.argv[:8],
               'python_executable':sys.executable,
               'scope':'cpython_profile_only_not_native_attestation',
               'host_monotonic_ns':time.monotonic_ns()})
        sys.setprofile(_profile)
        threading.setprofile(_profile)
    except (OSError, ValueError):
        _FD = None
