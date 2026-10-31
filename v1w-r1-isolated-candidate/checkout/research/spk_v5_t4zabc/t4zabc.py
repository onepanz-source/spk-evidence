#!/usr/bin/env python3
"""T4ZABC: differential dynamic callgraph probe, correcting T4ZAB's false premise.

Investigates original BV-v0e and positive-control A1b/T3h with a CPython frame
observer. No PE wrapper is patched; source bytes and results remain unchanged.
The producer has no proof of native C authorship. Frozen source copies are emitted
only as read-only handoff data after SHA verification.
"""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import contextmanager
from hashlib import sha256
import json
from pathlib import Path
import sys

from research.spk_v5_t4zab import t4zab as prior

SCHEMA='spk-v5-t4zabc-differential-runtime-topology/research-v0'
STATUS='BV_SOURCE_RUNTIME_TOPOLOGY_MEASURED_T4ZAB_PREMISE_NOT_ASSUMED'
MAX_CALLS=100000
MAX_SUMMARY_LABELS=32
class BoundaryError(ValueError):pass

def require(ok,code):
    if not ok:raise BoundaryError(code)

def fsha(path):return sha256(Path(path).read_bytes()).hexdigest()
def canon(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def digest(obj):return sha256(canon(obj)).hexdigest()

@contextmanager
def callgraph_probe(pe_filename,bv_filename):
    """Observe Python function-entry events only, strictly restored on exit.

    A name/filename match is descriptive provenance, not an authenticated issuer.
    This does not monkeypatch PE globals and cannot synthesize neuronal events.
    """
    pe_file=str(Path(pe_filename).resolve())
    bv_file=str(Path(bv_filename).resolve())
    before=sys.getprofile()
    require(before is None,'EXISTING_PROFILER_REFUSED')
    tally=Counter()
    nodes=Counter()
    examples=[]
    def observer(frame,event,arg):
        if event!='call':return
        co=frame.f_code
        name=co.co_name
        filename=co.co_filename
        # Existing runtime source files, direct match. Files are SHA-pinned elsewhere.
        if filename==pe_file:
            if name=='execute_on_pes_v1b':tally['pe_executor_calls']+=1
            elif name=='_compute_local':
                tally['pe_compute_calls']+=1
                n=frame.f_locals.get('node')
                ident=getattr(n,'node_id',None)
                label=ident if isinstance(ident,str) else '<unidentified>'
                nodes[label]+=1
                if len(examples)<12:
                    timestamp=frame.f_locals.get('timestamp')
                    channels=frame.f_locals.get('channels')
                    examples.append({'node_id':label,'timestamp':timestamp if type(timestamp) is int else None,
                                     'channel_count':len(channels) if isinstance(channels,(tuple,list)) else None})
        if filename==bv_file and name=='execute_live_v0e':tally['bv_scheduler_calls']+=1
        if tally['pe_compute_calls']>MAX_CALLS:raise BoundaryError('PE_PROBE_CALL_LIMIT_EXCEEDED')
        if len(nodes)>MAX_SUMMARY_LABELS:raise BoundaryError('PE_PROBE_NODE_LABEL_LIMIT_EXCEEDED')
    sys.setprofile(observer)
    try:yield tally,nodes,examples
    finally:
        sys.setprofile(before)
        require(sys.getprofile() is before,'PROFILER_NOT_RESTORED')

def summarize(calls,nodes,examples):
    return {'pe_executor_calls':calls['pe_executor_calls'],
            'pe_compute_calls':calls['pe_compute_calls'],
            'pe_C_compute_calls':nodes.get('C',0),
            'pe_node_id_counts':dict(sorted(nodes.items())),
            'observed_PE_entry_examples':examples,
            'bv_scheduler_calls':calls['bv_scheduler_calls'],
            'source_kind':'CPYTHON_FRAME_OBSERVATION_UNTRUSTED'}

def record_one(fn,pe_filename,bv_filename,*args):
    with callgraph_probe(pe_filename,bv_filename) as (calls,nodes,examples):
        source=fn(*args)
    return source,summarize(calls,nodes,examples)

def classify(positive,rows):
    require(positive['pe_compute_calls']>0 and positive['pe_C_compute_calls']>0,
            'POSITIVE_A1B_PROBE_DID_NOT_OBSERVE_C')
    require(positive['bv_scheduler_calls']==0,'POSITIVE_CONTROL_UNEXPECTED_BV_SCHEDULER')
    require(len(rows)==180,'SOURCE_CASE_COUNT_DRIFT')
    require(all(row['probe']['bv_scheduler_calls']==1 for row in rows),
            'BV_LIVE_SCHEDULER_ENTRY_NOT_OBSERVED_ON_EVERY_CASE')
    total=sum(row['probe']['pe_compute_calls'] for row in rows)
    c_total=sum(row['probe']['pe_C_compute_calls'] for row in rows)
    if total==0:
        return 'FROZEN_BV_V0E_DOES_NOT_ENTER_FROZEN_PE_V1B_COMPUTE_ON_THIS_WORKLOAD'
    if c_total==0:
        return 'BV_V0E_ENTERS_PE_V1B_BUT_NO_NODE_C_COMPUTE_OBSERVED'
    return 'BV_V0E_PE_V1B_C_COMPUTE_OBSERVED_WITH_HOST_ONLY_PROVENANCE'

def run(root):
    """For 180 BV cases prove output parity and characterize PE use, not assume it."""
    from research.spk_v5_t4ghi import t4ghi
    from spk_v5_research.island_c_owned_credit_v5t3h import execute as a1b_execute
    import spk_architecture_v1.pe_execution_v1b as pe
    import spk_backvalidation_v0.live_dual_scheduler_v0e as bv
    root=Path(root).resolve()
    wxy=prior.wxy_ref(root/'research/spk_v5_t4zab/reference/t4wxy-c-context-reference.json')
    pins=prior.verify_origins(root,wxy)
    require(fsha(root/'research/spk_v5_t4zab/t4zab.py')=='aaa08b6204694bb0ffd5dc7677656bbae592f494e63d7dcf6e2a87cc96276dd7',
            'ORIGINAL_T4ZAB_MODULE_DRIFT')
    pe_file=str((root/'spk_architecture_v1/pe_execution_v1b.py').resolve())
    bv_file=str((root/'spk_backvalidation_v0/live_dual_scheduler_v0e.py').resolve())
    require(str(Path(pe.__file__).resolve())==pe_file,'PE_MODULE_PATH_DRIFT')
    require(str(Path(bv.__file__).resolve())==bv_file,'BV_MODULE_PATH_DRIFT')
    refpath=root/'research/spk_v5_t4jkl/reference/t4ghi-one-pass-sign.json'
    require(refpath.is_file() and not refpath.is_symlink() and fsha(refpath)==prior.GHI_SHA,
            'T4GHI_REFERENCE_MISSING_OR_SHA_DRIFT')
    historic=json.loads(refpath.read_bytes())
    prior.need(historic.get('status')=='SINGLE_SOURCE_SIGN_VISIBILITY_RESEARCH_ONLY' and len(historic.get('H_rows',[]))==180,
               'HISTORICAL_T4GHI_INVALID')
    raw=list(t4ghi.prev.table_cases())
    require(len(raw)==180,'CASE_RECIPE_COUNT_DRIFT')
    ident,m,arm=raw[0]
    _,control=record_one(a1b_execute,pe_file,bv_file,m,arm)
    require(control['pe_C_compute_calls']>0,'A1B_NO_C_PE_COMPUTE_POSITIVE_CONTROL')
    rows=[]
    for i,((ident,m,arm),ref) in enumerate(zip(raw,historic['H_rows'])):
        require(i==ref['index'] and all(ident[x]==ref[x] for x in ('failure','arm','context','C_sensor')),
                'CASE_RECIPE_DRIFT_'+str(i))
        source,trace=record_one(t4ghi.source_once,pe_file,bv_file,m,arm)
        expected=ref['source_sha256']
        require(t4ghi.digest(source)==expected,'SOURCE_HASH_PARITY_DRIFT_'+str(i))
        obs=t4ghi.observe_forward_result(source)
        require(obs['C_sign_candidate_from_same_source_forward_output']==ref['C_sign_candidate_from_same_source_forward_output'],
                'SOURCE_SIGN_DRIFT_'+str(i))
        require(obs['event_candidate_paths']==ref['event_candidate_paths'],
                'SOURCE_EVENT_DRIFT_'+str(i))
        rows.append({'index':i,'source_sha256':expected,
            'observed_forward_C_sign_not_native':obs['C_sign_candidate_from_same_source_forward_output'],
            'probe':trace,'native_C_packet_proven':False})
    interpretation=classify(control,rows)
    require(prior.verify_origins(root,wxy)==pins,'SOURCE_PINS_CHANGED_DURING_DIAGNOSTIC')
    return {'schema':SCHEMA,'status':STATUS,'topology_interpretation':interpretation,
        'positive_A1B_control':control,'source_BV_case_count':180,
        'BV_PE_computes':sum(r['probe']['pe_compute_calls'] for r in rows),
        'BV_PE_C_computes':sum(r['probe']['pe_C_compute_calls'] for r in rows),
        'BV_scheduler_entries':sum(r['probe']['bv_scheduler_calls'] for r in rows),
        'BV_observed_source_C_signs':sum(r['observed_forward_C_sign_not_native'] in (-1,1) for r in rows),
        'original_T4ZAB_fail_closed_preserved':True,'source_snapshots_pending_from_frozen_modules':True,
        'T4GHI_reference_sha256':prior.GHI_SHA,
        'T4WXY_reference_sha256':prior.WXY_SHA,
        'original_T4ZAB_module_sha256':'aaa08b6204694bb0ffd5dc7677656bbae592f494e63d7dcf6e2a87cc96276dd7',
        'source_pins':pins,'rows_sha256':digest(rows),'rows':rows,
        'frozen_runtime_changed':False,'native_C_emission_proven':False,
        'native_origin_authenticated':False,'native_BV_receiver_receipt_proven':False,
        'native_learning_proven':False,'promotion_allowed':False,
        'limits':['T4ZAB assumed BV calls PE v1b _compute_local; this hypothesis was not established',
                  'A1b positive control executes a DIFFERENT source path and is not a BV semantic author',
                  'BV forwarded C emission records are not necessarily produced by frozen PE v1b',
                  'CPython frame observation is host-controlled and not C-owned authority',
                  'No native receiver-readable semantic receipt, independent sensor, or learning update']}

def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('command',choices=['run','bundle'])
    a.add_argument('--root',type=Path,required=True)
    a.add_argument('--out',type=Path,required=True)
    opts=a.parse_args()
    try:
        if opts.command=='bundle':
            print('T4ZABC SOURCE HANDOFF',prior.snapshot_two(opts.root,opts.out))
        else:
            report=run(opts.root)
            prior.write_once(opts.out,report)
            print('T4ZABC',STATUS,'topology',report['topology_interpretation'])
            print('BV PE',report['BV_PE_computes'],'BV PE C',report['BV_PE_C_computes'],
                  'BV entries',report['BV_scheduler_entries'],'source signs',report['BV_observed_source_C_signs'])
            print('sha256',fsha(opts.out))
    except (BoundaryError,prior.GateError,OSError,ValueError,KeyError,TypeError,RuntimeError,AssertionError) as e:
        raise SystemExit('T4ZABC FAIL CLOSED: '+str(e))
if __name__=='__main__':main()
