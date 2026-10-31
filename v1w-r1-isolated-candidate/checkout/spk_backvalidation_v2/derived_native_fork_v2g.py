"""BV v2g: pinned in-memory *derived* v0e function with call-site instrumentation.

Only four historically audited call sites are wrapped. This is not a change to
frozen SPK, a producer-authenticated spike stream or receiver-local feedback.
The effectful native function is called once, with its original arguments;
no results are rewritten. All claims require 45 paired runtime replays on fwork.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from types import FunctionType
from typing import Callable

PINNED_SCHED = '2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9'
RELATIVE_PATH = 'spk_backvalidation_v0/live_dual_scheduler_v0e.py'
EXPECTED_CALLS = (('_admit', 49), ('_admit_plan', 50),
                  ('offer_feedback', 150), ('offer_feedback', 206))
PORT_VERSION = 'spk-bv-experimental-callsite-seam/v2g'
MAX_RECORDS = 32768

class NativeForkError(ValueError):
    pass

def guard(ok, message):
    if not ok:
        raise NativeForkError(message)

@dataclass(frozen=True, slots=True)
class CallsiteRecord:
    ordinal: int
    callsite: str
    source_line: int
    returned: bool

class CallsiteObserver:
    """Bounded Python-local metadata log, not actor-issued semantic messages."""
    def __init__(self, capacity: int = MAX_RECORDS, sink: Callable[[CallsiteRecord], None] | None = None):
        guard(type(capacity) is int and 1 <= capacity <= MAX_RECORDS, 'bad observer capacity')
        guard(sink is None or callable(sink), 'bad observer sink')
        self.capacity, self.sink = capacity, sink
        self.records: list[CallsiteRecord] = []
        self.offered = 0
        self.overflow = False
        self.sink_failed = False

    def emit(self, name, line, returned):
        self.offered += 1
        if len(self.records) >= self.capacity:
            self.overflow = True
            return
        record = CallsiteRecord(self.offered - 1, name, line, returned)
        self.records.append(record)
        if self.sink is not None and not self.sink_failed:
            try:
                self.sink(record)
            except Exception:
                self.sink_failed = True

    def counts(self):
        counts = {name:0 for name in sorted({x[0] for x in EXPECTED_CALLS})}
        for r in self.records:counts[r.callsite] += 1
        return counts

    def attest(self):
        return {'port_version':PORT_VERSION,
                'calls_observed':len(self.records),'calls_offered':self.offered,
                'counts':self.counts(),'overflow':self.overflow,
                'sink_failed':self.sink_failed,
                'semantic_spikes_attested':0,'native_receiver_packets':0,
                'independent_clock':False,'native_source_owned':False,
                'source_is_versioned_clone':True}


def _callee(node):
    return node.id if isinstance(node, ast.Name) else (
        node.attr if isinstance(node, ast.Attribute) else None)


def audited_function(source_bytes: bytes, *, expected_calls=EXPECTED_CALLS,
                     enforce_sha=True):
    guard(type(source_bytes) is bytes and len(source_bytes) <= 600000,
          'unsafe source length/type')
    if enforce_sha:
        guard(sha256(source_bytes).hexdigest()==PINNED_SCHED,'frozen scheduler hash drift')
    tree = ast.parse(source_bytes, filename=RELATIVE_PATH)
    candidates = [n for n in tree.body if isinstance(n, ast.FunctionDef)
                  and n.name=='execute_live_v0e']
    guard(len(candidates)==1, 'frozen entrypoint AST absent or duplicated')
    node = candidates[0]
    guard(not node.decorator_list and not node.args.kwonlyargs and
          not node.args.vararg and not node.args.kwarg and
          [x.arg for x in node.args.args]==
          ['case','fabric','tplan','pplan','mplan','lplan','bv'],
          'frozen function AST API unexpected')
    calls = sorted((name, n.lineno) for n in ast.walk(node)
                   if isinstance(n,ast.Call)
                   if (name:=_callee(n.func)) in {'_admit','_admit_plan','offer_feedback'})
    guard(calls==sorted(expected_calls),f'unsafe or ambiguous audited callsite inventory: {calls}')
    return deepcopy(node), tuple(calls)

class _Instrument(ast.NodeTransformer):
    def __init__(self):
        self.count=0
    def visit_Call(self, node):
        self.generic_visit(node)
        name=_callee(node.func)
        if name in {'_admit','_admit_plan','offer_feedback'}:
            self.count+=1
            node.func=ast.Call(func=ast.Name(id='__spk_v2g_wrap',ctx=ast.Load()),
                args=[ast.Constant(value=name),ast.Constant(value=node.lineno),node.func],keywords=[])
        return node


def derive_executor(source_bytes:bytes, original_executor, observer:CallsiteObserver,
                    *, expected_calls=EXPECTED_CALLS, enforce_sha=True):
    """Construct isolated function globals. Do not mutate any frozen module."""
    guard(type(observer) is CallsiteObserver and isinstance(original_executor,FunctionType)
          and original_executor.__name__=='execute_live_v0e', 'bad native executor or observer')
    node, calls=audited_function(source_bytes,expected_calls=expected_calls,
                                 enforce_sha=enforce_sha)
    modifier=_Instrument()
    rewritten=modifier.visit(node)
    guard(modifier.count==len(calls),'unaccounted callsite transformation')
    # Instrumented function body is compiled in memory in an isolated globals
    # namespace, with original dependencies only read. No source write, patch,
    # hook/trace mutation or monkeypatch to the original module is performed.
    module=ast.Module(body=[ast.ImportFrom(module='__future__',
                       names=[ast.alias(name='annotations')],level=0),rewritten],
                      type_ignores=[])
    ast.fix_missing_locations(module)
    namespace=dict(original_executor.__globals__)
    def wrap(name,line,function):
        guard(callable(function),'callsite callee not callable')
        def inner(*args,**kwargs):
            try:
                answer=function(*args,**kwargs)
            except BaseException:
                observer.emit(name,line,False)
                raise
            observer.emit(name,line,True)
            return answer
        return inner
    namespace['__spk_v2g_wrap']=wrap
    code=compile(module,'<research-v2g-in-memory-derived-v0e>','exec')
    exec(code,namespace)
    derived=namespace['execute_live_v0e']
    guard(derived is not original_executor and
          list(derived.__code__.co_varnames[:7])==
          ['case','fabric','tplan','pplan','mplan','lplan','bv'],
          'derived function changed positional API')
    return derived, calls


def read_pinned_source(root:Path):
    p=(root/RELATIVE_PATH)
    guard(p.is_file() and not p.is_symlink() and p.resolve(strict=True)==p,
          'unsafe source path')
    raw=p.read_bytes()
    guard(sha256(raw).hexdigest()==PINNED_SCHED,'frozen source changed')
    return raw
