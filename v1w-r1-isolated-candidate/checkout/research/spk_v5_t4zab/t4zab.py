#!/usr/bin/env python3
"""T4ZAB: live source-side PE C-step observation; FORK FEASIBILITY ONLY.

One frozen BV-v0e execution per case, with a temporary, return-transparent
function hook inside a *fresh isolated producer process*. It observes original
PE _compute_local while case C computes; it does not author C messages, authenticate
C, or claim real neuronal receipt. No source file, library artifact, or PE program
is modified. A SHA-pinned snapshot of two frozen modules is bundled for the NEXT
experimental fork to be written against real code, not guessed source.
"""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import contextmanager
from hashlib import sha256
import inspect
import io
import json
from pathlib import Path
import tarfile

SCHEMA='spk-v5-t4zab-live-C-PE-seam/research-v0'
STATUS='FROZEN_PE_C_STEP_OBSERVED_IN_SINGLE_BV_EXECUTION_NOT_C_AUTHORED'
WXY_SHA='37c29062f235b36d7f1ba3b41c1b5bc5f9f2b0cf8e3da0fc0eb06be14c9933c3'
GHI_SHA='dc98a1a5e45270d665e5119540ae960e405f4d02b703bd0c52d04202873abef3'
PE_SHA='8e9d08ddc165e0c6e307ca16cc849feb7eabad33c148c26f4faa436c890d752c'
BV_SHA='2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9'
SOURCE_NAMES=(
 ('spk_architecture_v1/pe_execution_v1b.py',PE_SHA),
 ('spk_backvalidation_v0/live_dual_scheduler_v0e.py',BV_SHA),
)
MAX_C_OBSERVATIONS_PER_CASE=128
class GateError(ValueError): pass

def need(ok, why):
    if not ok: raise GateError(why)

def sha(p): return sha256(Path(p).read_bytes()).hexdigest()
def canon(obj):return json.dumps(obj,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def checksum(obj):return sha256(canon(obj)).hexdigest()
def read(p):return json.loads(Path(p).read_bytes())
def write_once(path, obj):
    p=Path(path)
    need(not p.exists() and not p.is_symlink(),'REPORT_PATH_ALREADY_EXISTS')
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:
        json.dump(obj,f,sort_keys=True,indent=2,allow_nan=False);f.write('\n')

def wxy_ref(p):
    p=Path(p)
    need(p.is_file() and not p.is_symlink(),'WXY_REFERENCE_MISSING')
    need(sha(p)==WXY_SHA,'WXY_REFERENCE_SHA_DRIFT')
    x=read(p)
    need(x.get('status')=='EXPERIMENTAL_C_CONTEXT_COMPUTE_AND_EMIT_HOST_PROVISIONED_NOT_NATIVE' and
         x.get('W_original_BV_scheduler_calls')==0 and x.get('X_receiver_process_commits')==24 and
         x.get('Y_host_can_forge_even_with_reference_C_context',{}).get('host_outside_C_can_forge') is True and
         x.get('Y_native_neuron_identity_verified') is False and
         x.get('promotion_allowed') is False, 'WXY_REFERENCE_UNSAFE_OR_DRIFT')
    return x

def verify_origins(root, wxy):
    root=Path(root).resolve()
    original=wxy['source_pins']
    need(type(original) is dict and len(original)==12,'SOURCE_PIN_LIST_INVALID')
    for rel,pin in original.items():
        p=root/rel
        need(p.is_file() and not p.is_symlink(),'SOURCE_MISSING_OR_SYMLINK:'+rel)
        need(sha(p)==pin,'SOURCE_SHA_DRIFT:'+rel)
    need(all(original.get(rel)==pin for rel,pin in SOURCE_NAMES),'FROZEN_PE_OR_BV_SOURCE_DRIFT')
    return dict(sorted(original.items()))

@contextmanager
def observe_C_steps(pe, events):
    """Only in an isolated process. Transparent wrapper, restored on exit.

    The callback remains host-controlled Python; observing computation does not
    establish C-authored emission. Guard against false attribution by verifying
    node identity and calling original _compute_local exactly once.
    """
    original=pe._compute_local
    sig=inspect.signature(original)
    need(tuple(sig.parameters)==('node','state','timestamp','channels'),'PE_COMPUTE_SIGNATURE_DRIFT')
    need('_compute_local' in pe.execute_on_pes_v1b.__code__.co_names,'PE_CALL_GRAPH_DRIFT')
    def watched(node,state,timestamp,channels):
        result=original(node,state,timestamp,channels)
        if getattr(node,'node_id',None)=='C':
            need(type(timestamp) is int and timestamp>=0,'C_COMPUTE_TIMESTAMP_INVALID')
            need(type(channels) in (tuple,list) and all(type(x) is int for x in channels),
                 'C_COMPUTE_CHANNELS_INVALID')
            need(len(events)<MAX_C_OBSERVATIONS_PER_CASE,'C_COMPUTE_OBSERVATION_OVERFLOW')
            events.append({'timestamp':timestamp,'input_channels':list(channels),
                           'returned_type':type(result).__name__})
        return result
    need(pe._compute_local is original,'PE_OBSERVER_NESTED')
    pe._compute_local=watched
    try:yield
    finally:
        pe._compute_local=original
        need(pe._compute_local is original,'PE_COMPUTE_NOT_RESTORED')

def observe_once(source_fn, pe, m, arm):
    rec=[]
    with observe_C_steps(pe,rec):
        result=source_fn(m,arm)
    need(len(rec)>0,'C_NOT_EXECUTED_INSIDE_BV_SOURCE')
    need(any(e['timestamp']>=14 for e in rec),'C_LATE_STEP_NOT_OBSERVED')
    return result,rec

def case_row(i, ident, measurement,arm,historic, result,steps, t4ghi):
    need(type(i) is int and i==historic['index'],'CASE_ORDER_DRIFT')
    need(ident['failure']==historic['failure'] and ident['arm']==historic['arm'] and
         ident['context']==historic['context'] and ident['C_sensor']==historic['C_sensor'],
         'MEASUREMENT_RECIPE_DRIFT_'+str(i))
    dgst=t4ghi.digest(result)
    need(dgst==historic['source_sha256'],'SOURCE_BYTE_PARITY_DRIFT_'+str(i))
    obs=t4ghi.observe_forward_result(result)
    sign=obs['C_sign_candidate_from_same_source_forward_output']
    need(sign==historic['C_sign_candidate_from_same_source_forward_output'],
         'SOURCE_SIGN_OBSERVATION_DRIFT_'+str(i))
    need(obs['event_candidate_paths']==historic['event_candidate_paths'],
         'SOURCE_EVENT_DRIFT_'+str(i))
    need(len(steps)<=MAX_C_OBSERVATIONS_PER_CASE,'C_RECORD_CAP_BROKEN')
    # No way to reconstruct a neuron-authored packet from this trace; it's Python.
    return {'index':i,'source_sha256':dgst,'source_sign_observed_posthoc':sign,
            'C_compute_call_count':len(steps),
            'C_compute_tick_sequence':[x['timestamp'] for x in steps],
            'C_return_type_inventory':dict(sorted(Counter(x['returned_type'] for x in steps).items())),
            'C_compute_input_channels':[x['input_channels'] for x in steps],
            'research_status':'HOST_OBSERVED_PE_C_EXECUTION_NOT_C_AUTHORITY',
            'native_C_packet_origin_verified':False}

def live_180(root, wxy, reference_path):
    from research.spk_v5_t4ghi import t4ghi
    import spk_architecture_v1.pe_execution_v1b as pe
    reference_path=Path(reference_path)
    need(reference_path.is_file() and not reference_path.is_symlink(),'GHI_REFERENCE_MISSING')
    need(sha(reference_path)==GHI_SHA,'GHI_REFERENCE_SHA_DRIFT')
    ref=read(reference_path)
    need(ref.get('status')=='SINGLE_SOURCE_SIGN_VISIBILITY_RESEARCH_ONLY' and len(ref.get('H_rows',[]))==180,
         'GHI_REFERENCE_STATUS_OR_ROWS_INVALID')
    need(all(wxy['source_pins'].get(k)==v for k,v in ref.get('source_pins',{}).items()) and len(ref.get('source_pins',{}))==9,'GHI_PIN_MISMATCH')
    orig=pe._compute_local
    rows=[]
    hist=ref['H_rows']
    for i,((ident,m,arm),h) in enumerate(zip(t4ghi.prev.table_cases(),hist)):
        source,steps=observe_once(t4ghi.source_once,pe,m,arm)
        need(pe._compute_local is orig,'SOURCE_FN_NOT_RESTORED_'+str(i))
        rows.append(case_row(i,ident,m,arm,h,source,steps,t4ghi))
    need(len(rows)==180 and sum(x['source_sign_observed_posthoc'] in (-1,1) for x in rows)==72,
         'LIVE_SOURCE_CARDINALITY_DRIFT')
    return rows

def snapshot_two(root,out):
    """Deterministic tiny source-only bundle; no secrets, no generated runtime code."""
    root=Path(root)
    out=Path(out)
    need(not out.exists() and not out.is_symlink(),'SOURCE_ARCHIVE_ALREADY_EXISTS')
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('xb') as stream:
        with tarfile.open(fileobj=stream,mode='w:gz',format=tarfile.PAX_FORMAT,compresslevel=9) as tf:
            for rel,pin in SOURCE_NAMES:
                p=root/rel
                need(p.is_file() and not p.is_symlink() and sha(p)==pin,'FROZEN_SOURCE_CHANGED:'+rel)
                data=p.read_bytes()
                info=tarfile.TarInfo(rel)
                info.size=len(data);info.mtime=0;info.uid=0;info.gid=0
                info.uname='';info.gname='';info.mode=0o444
                tf.addfile(info,io.BytesIO(data))
    return sha(out)

def run(root,reference,out):
    root=Path(root).resolve();out=Path(out)
    wxy=wxy_ref(reference)
    pins=verify_origins(root,wxy)
    ghi=root/'research/spk_v5_t4jkl/reference/t4ghi-one-pass-sign.json'
    rows=live_180(root,wxy,ghi)
    need(verify_origins(root,wxy)==pins,'SOURCE_MUTATED_DURING_GATE')
    # The source-copy output is a deliverable, not an authority for these 180 runs.
    signed=Counter(str(r['source_sign_observed_posthoc']) for r in rows if r['source_sign_observed_posthoc'] in (-1,1))
    need(signed==Counter({'1':36,'-1':36}),'SIGN_COUNTS_DRIFT')
    need(all(r['C_compute_call_count']>0 for r in rows),'MISSING_C_COMPUTE')
    return {'schema':SCHEMA,'status':STATUS,
            'reference_T4WXY_sha256':WXY_SHA,'reference_T4GHI_sha256':GHI_SHA,
            'original_BV_source_invocations':180,'genuine_C_compute_observation_rows':len(rows),
            'C_compute_calls_total':sum(x['C_compute_call_count'] for x in rows),
            'signed_source_results':72,'sign_counts':dict(sorted(signed.items())),
            'rows_sha256':checksum(rows),'rows':rows,
            'source_pins':pins,
            'source_snapshot_names':[rel for rel,_ in SOURCE_NAMES],
            'original_modules_unchanged':True,'host_callback_can_forge_C_claim':True,
            'C_execution_owned_emission_proven':False,
            'C_origin_authenticated':False,'receiver_native_semantic_receipts':0,
            'native_learning_proven':False,'promotion_allowed':False,
            'limits':['PE _compute_local executes on C in the same original BV-v0e invocation',
                'An out-of-band Python wrapper sees the C step after the local computation but before its caller consumes the result',
                'The observed sign is checked from the returned BV result, NOT emitted or authenticated by the PE C node',
                'Temporary host-installed hook is restored; it is NOT a native C-owned emitter',
                'Host can forge the trace, as T4TUV/T4WXY established; no issuer authority is inferred',
                'Both source SHA pins and byte-identical source results remain invariant',
                'No authenticated C sensor, independent goal or native learning transaction']}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=['run','bundle'])
    p.add_argument('--root',type=Path,required=True)
    p.add_argument('--reference',type=Path)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    try:
        if a.command=='bundle':
            digest=snapshot_two(a.root,a.out)
            print('T4ZAB SOURCE BUNDLE ONLY',digest)
        else:
            need(a.reference is not None,'MISSING_WXY_REFERENCE')
            report=run(a.root,a.reference,a.out)
            write_once(a.out,report)
            print('T4ZAB',STATUS,'180 sources; C compute callbacks',report['C_compute_calls_total'])
            print('SHA256',sha(a.out))
    except (GateError,AssertionError,OSError,ValueError,KeyError,TypeError,RuntimeError) as e:
        raise SystemExit('T4ZAB FAIL CLOSED: '+str(e))
if __name__=='__main__':main()
