#!/usr/bin/env python3
"""SPK V5 T3XYZ passive frozen producer observation (research-only).

T3X read-only Python function visibility, T3Y byte-exact report parity,
T3Z strict semantic verdict nonpromotion + falsification.
NO edits to frozen source and NO claim of single-pass native BV.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

EXPECTED_T3OPQ_REPORT_SHA = '813753afd706eabff52653cf0a7674e1a44755981df61c6760fcbd4652c790d2'
PINS = {
 'search/spk_bv_v0e_live_evidence.py':'1e93f1a71c1099a3ce3c5e14d2cb9cfa47b8bfa9027832785d9f09af0c2bbc70',
 'spk_backvalidation_v0/live_dual_scheduler_v0e.py':'2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9',
 'tests/test_spk_bv_live_dual_scheduler_v0e.py':'6de34cd1ff6c85c96faad3dc047066406cf49d9675ac87fc77b260814f18dfa8',
}
SCRIPTS = (
 'search/spk_v5_t3opq_source_bridge_gate.sh',
 'search/spk_v5_t3rst_cumulative_gate.sh',
 'search/spk_v5_t3uvw_source_custody_gate.sh',
 'research/spk_v5_t3rst/src/spk_t3rst.py',
 'research/spk_v5_t3uvw/t3uvw.py',
 'research/spk_v5_t3xyz/t3xyz.py',
 'research/spk_v5_t3xyz/instrument/sitecustomize.py',
 'research/spk_v5_t3xyz/instrument/usercustomize.py',
 'research/spk_v5_t3xyz/instrument/spk_t3xyz_hook.py',
)
MAX_TRACE_BYTES = 32_000_000
class GateError(Exception):
    pass

def require(v:bool,msg:str):
    if not v:
        raise GateError(msg)

def sha_file(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def source_snapshot(root:Path):
    result={}
    for name in (*PINS,*SCRIPTS):
        p=root/name
        require(p.is_file(),f'SOURCE_MISSING:{name}')
        result[name]=sha_file(p)
    for name,digest in PINS.items():
        require(result[name]==digest,f'FROZEN_PIN_MISMATCH:{name}')
    return result

def read_trace(path:Path,root:Path)->dict[str,Any]:
    require(path.is_file(), 'PROBE_TRACE_MISSING')
    require(0 < path.stat().st_size <= MAX_TRACE_BYTES,'PROBE_TRACE_SIZE_INVALID')
    counts={'probe_loaded':0,'compute_call':0,'compute_return':0}
    pids=set(); sources={}; example=[]; seq_by_pid={}; errors=[]; truncated=False
    for lineno,line in enumerate(path.read_text(encoding='utf-8').splitlines(),1):
        try:
            e=json.loads(line)
        except json.JSONDecodeError:
            errors.append(f'CORRUPT_JSONL_LINE:{lineno}');continue
        kind=e.get('kind');pid=e.get('pid');seq=e.get('seq')
        if kind not in counts or type(pid) is not int or type(seq) is not int:
            errors.append(f'UNRECOGNIZED_TRACE_RECORD:{lineno}');continue
        if seq <= seq_by_pid.get(pid,0):
            errors.append(f'NONMONOTONE_PROCESS_SEQUENCE:{lineno}')
        seq_by_pid[pid]=seq
        pids.add(pid);counts[kind]+=1
        if kind=='compute_call':
            source=e.get('source','')
            if type(source) is not str:
                errors.append(f'INVALID_SOURCE:{lineno}');continue
            p=Path(source)
            # The source is only informational until the file digest is tied
            # to this exact checkout. System paths are never native proof.
            try:
                rel=str(p.resolve().relative_to(root.resolve()))
            except ValueError:
                rel='OUTSIDE_CHECKOUT'
            if rel not in sources:
                sources[rel]={'calls':0,'sha256':sha_file(p) if p.is_file() else None}
            sources[rel]['calls']+=1
            if len(example)<12:
                example.append({'source':rel,'function':e.get('function'),
                                'locals':e.get('locals'), 'stack':e.get('stack')})
        if lineno > 50000:
            truncated=True
    require(not errors, 'PROBE_TRACE_INVALID:'+repr(errors[:4]))
    return {'events':counts,'process_count':len(pids),'observed_compute_sources':sources,
            'bounded_examples':example,'truncated':truncated,
            'structural_compute_observed':counts['compute_call']>0,
            'host_profile_not_neuron_authentication':True}

def validate_report(doc:Any):
    require(type(doc) is dict,'T3OPQ_NOT_JSON_OBJECT')
    require(doc.get('schema')=='spk-v5-t3opq-source-custody-and-shared-resource-dual-replay/research-v0', 'WRONG_T3OPQ_SCHEMA')
    require(doc.get('status')=='SOURCE_BV_V0E_DUAL_VERDICT_LINEAGE_WITH_SHADOW_LEARNING','WRONG_T3OPQ_STATUS')
    table=doc.get('C_verdict_table',{})
    c=table.get('counts',{})
    require(table.get('cases')==180 and c.get('REJECT_NO_UPDATE')==138 and c.get('SHADOW_SOURCE_REPLAY_ELIGIBLE')==42,'T3OPQ_COUNTS_DRIFT')
    require(doc.get('total_online_episodes')==720 and doc.get('total_credited_updates')==617,'T3OPQ_UPDATES_DRIFT')
    exclusions=doc.get('claims_excluded',[])
    require(any('dual BV-v0e source invocations' in x for x in exclusions),'DUAL_INVOCATIONS_UNDISCLOSED')
    require(any('host selects terminal observer' in x for x in exclusions),'HOST_POSTHOC_SELECTION_UNDISCLOSED')
    return {'shadow_eligible':42,'dual_replay':True,'host_posthoc_selection':True}

def interpretation(trace:dict[str,Any],original:dict[str,Any])->dict[str,Any]:
    # C's semantic opinion is NOT a CPython function return: it needs actual
    # source-authored, receiver-visible bound forward+reverse receipt. The frozen
    # producer and this passive profile offer no such proof.
    require(original['dual_replay'] and original['host_posthoc_selection'],'UNEXPECTED_ORIGINAL_CONTRACT')
    return {'structural_compute_visible':trace['structural_compute_observed'],
            'native_C_authored_single_pass_verdict_proven':False,
            'native_BV_semantic_receipt_proven':False,
            'native_operator_update_proven':False,
            'independent_sensor_authentication':False,
            'blind_independent_goal':False,
            'what_is_missing':[
              'Single runtime execution with a C-authored semantic verdict, not posthoc observer selection',
              'A signed/otherwise independently authenticated C sensor and receiver provenance',
              'Source-bound forward decision / receiver assessment / reverse credit in one native custody chain',
              'Native actor intake and atomic commit/rollback to a scoped operator',
            ],
            'no_promotion':True}

def run(root:Path,output:Path):
    root=root.resolve();out=output.resolve()
    require(root.is_dir() and out.parent.is_dir(), 'ROOT_OR_OUTPUT_PARENT_INVALID')
    base=out.with_suffix('')
    trace=Path(str(base)+'-profile.jsonl')
    producer=Path(str(base)+'-original.json')
    log=Path(str(base)+'-original.log')
    require(len({str(x) for x in (out,trace,producer,log)})==4,'PATH_COLLISION')
    before=source_snapshot(root)
    for p in (trace,producer,log):
        p.unlink(missing_ok=True)
    # The probe is only loaded by the Python children created by the original
    # shell gate; never import sitecustomize into this controller process.
    env=os.environ.copy()
    instrument=str(root/'research/spk_v5_t3xyz/instrument')
    env['PYTHONPATH']=instrument+os.pathsep+env['PYTHONPATH'] if env.get('PYTHONPATH') else instrument
    env['SPK_T3XYZ_CAPTURE']='1';env['SPK_T3XYZ_TRACE_FILE']=str(trace)
    env['SPK_T3XYZ_MAX_EVENTS']='25000'
    # Reject blocked sitecustomize/usercustomize BEFORE spending time on the
    # expensive source gate. Do not silently fall back to a fixture.
    preflight=subprocess.run([sys.executable,'-c',
        "import sys;sys.exit(0 if 'spk_t3xyz_hook' in sys.modules else 7)"],
        cwd=str(root),env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
    require(preflight.returncode==0,
            'PASSIVE_PYTHON_HOOK_UNAVAILABLE: existing site/usercustomize or isolated interpreter overrides injection')
    gate=root/'search/spk_v5_t3opq_source_bridge_gate.sh'
    with log.open('w',encoding='utf-8') as fp:
        cp=subprocess.run(['bash',str(gate),str(producer)],cwd=str(root),env=env,
                          stdout=fp,stderr=subprocess.STDOUT,check=False)
    require(cp.returncode==0,f'T3OPQ_GATE_FAILED_EXIT_{cp.returncode}: {log}')
    after=source_snapshot(root)
    require(before==after,'SOURCE_MODIFIED_WHILE_PROFILING')
    require(producer.is_file(),'INSTRUMENTED_PRODUCER_REPORT_MISSING')
    digest=sha_file(producer)
    require(digest==EXPECTED_T3OPQ_REPORT_SHA, f'PROBE_PERTURBED_ORIGINAL_OUTPUT:{digest}')
    original=validate_report(json.loads(producer.read_text()))
    observed=read_trace(trace,root)
    require(observed['events']['probe_loaded']>1,'NO_SOURCE_GATE_PYTHON_PROBE_OBSERVED')
    require(observed['events']['compute_call']>0,'NO_COMPUTE_LOCAL_OBSERVED_IN_SOURCE_GATE')
    result={
        'schema':'spk-v5-t3xyz-live-readonly-python-observation/research-v0',
        'status':'PASSIVE_PROBE_GATE_EXECUTED_NO_NATIVE_SEMANTIC_BV_PROVEN',
        'X_passive_instrumentation':observed,
        'Y_source_parity':{'original_gate':'search/spk_v5_t3opq_source_bridge_gate.sh',
                           'source_hashes':before,'source_unchanged':True,
                           'reference_report_sha256':EXPECTED_T3OPQ_REPORT_SHA,
                           'observed_report_sha256':digest,'byte_identical_to_reference':True,
                           'same_checkout_not_independent_replica':True},
        'Z_causal_semantic_boundary':interpretation(observed,original),
        'reports':{'profile_jsonl':str(trace),'producer_json':str(producer),'producer_log':str(log)},
        'promotion_allowed':False,
        'limits':['sys.setprofile observes Python calls, not native events nor trustworthy causality',
                  'CPython instrumentation may be bypassed by -S/-I, C runtime, profiling replacement or child environment sanitization',
                  'time.monotonic_ns measures host observation, not simulated tick time',
                  'source snapshot covers pinned files and declared additive scripts only, not complete transitive imports',
                  'no independent hardware attestation, no blind evaluation, no real native learning']
    }
    out.write_text(json.dumps(result,ensure_ascii=True,sort_keys=True,indent=2)+'\n')
    print('T3XYZ PASSIVE SOURCE OBSERVATION COMPLETE (RESEARCH): NO NATIVE VERDICT OR LEARNING PROMOTION')
    print('compute_calls_observed',observed['events']['compute_call'])
    print('producer_report_sha256',digest)
    print('report',out)
    return result

def main()->int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    run(a.repo,a.output)
    return 0

if __name__=='__main__':
    try:
        sys.exit(main())
    except (GateError,OSError,ValueError,KeyError) as exc:
        print('T3XYZ FAIL CLOSED:',exc,file=sys.stderr)
        sys.exit(3)
