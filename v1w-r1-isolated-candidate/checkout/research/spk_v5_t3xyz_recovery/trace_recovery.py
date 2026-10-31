#!/usr/bin/env python3
"""T3XYZ trace-volume recovery, read-only, RESEARCH ONLY.

Recovers an original, already collected CPython profile after legacy 32MB
validation rejected it. No synthetic verdicts, no native-learning promotion.
"""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys

REPORT_SHA='813753afd706eabff52653cf0a7674e1a44755981df61c6760fcbd4652c790d2'
TRACE_SHA='21ac7a5197c56cdff3edb816b86233d1c4749e601848eadac1c7413232e17484'
LOG_SHA='1554f4f89a46a7b889c1986f5ab1e5305b0926c535e60230e8e734e0833cc110'
PINS={
 'search/spk_bv_v0e_live_evidence.py':'1e93f1a71c1099a3ce3c5e14d2cb9cfa47b8bfa9027832785d9f09af0c2bbc70',
 'spk_backvalidation_v0/live_dual_scheduler_v0e.py':'2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9',
 'tests/test_spk_bv_live_dual_scheduler_v0e.py':'6de34cd1ff6c85c96faad3dc047066406cf49d9675ac87fc77b260814f18dfa8',
}
EXPECTED_COMPUTE_SOURCE='spk_architecture_v1/pe_execution_v1b.py'
MAX_BYTES=128_000_000
MAX_LINE_BYTES=32_768
MAX_EVENTS=250_000
MAX_PIDS=128
PER_PROCESS_CAPTURE_CAP=25_000  # from original T3XYZ launcher environment, compute call/return only
class AuditError(ValueError): pass

def check(condition:bool,why:str):
    if not condition:raise AuditError(why)

def digest(path:Path)->str:
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def snapshots(root:Path)->dict:
    # Frozen pins are independently checked now, but not a third-party signature.
    hashes={}
    for rel,expected in PINS.items():
        fp=root/rel
        check(fp.is_file(),'FROZEN_SOURCE_MISSING:'+rel)
        actual=digest(fp)
        check(actual==expected,'FROZEN_SOURCE_PIN_MISMATCH:'+rel)
        hashes[rel]=actual
    sp=root/EXPECTED_COMPUTE_SOURCE
    check(sp.is_file(),'OBSERVED_COMPUTE_SOURCE_MISSING')
    hashes[EXPECTED_COMPUTE_SOURCE]=digest(sp)
    return hashes

def analyze_trace(trace:Path,root:Path|None=None):
    check(trace.is_file(),'TRACE_MISSING')
    size=trace.stat().st_size
    check(0 < size <= MAX_BYTES,'TRACE_SIZE_INVALID:'+str(size))
    trace_sha=digest(trace)
    per_pid=defaultdict(Counter)
    last_seq={}
    calls=Counter()
    timestamps={}
    kinds=Counter()
    seen_stack=Counter()
    sources=Counter()
    line_count=0
    with trace.open('rb') as f:
      for raw in f:
        line_count+=1
        check(line_count<=MAX_EVENTS,'TRACE_EVENT_COUNT_EXCESS')
        check(0<len(raw)<=MAX_LINE_BYTES,'TRACE_LINE_SIZE_INVALID:'+str(line_count))
        check(raw.endswith(b'\n'),'TRACE_UNTERMINATED_LINE:'+str(line_count))
        try:item=json.loads(raw)
        except (UnicodeDecodeError,json.JSONDecodeError) as exc:
            raise AuditError('TRACE_JSON_INVALID:'+str(line_count)) from exc
        check(type(item) is dict,'TRACE_RECORD_NOT_OBJECT:'+str(line_count))
        kind=item.get('kind');pid=item.get('pid');seq=item.get('seq')
        check(kind in {'probe_loaded','compute_call','compute_return'},'TRACE_KIND_INVALID:'+str(line_count))
        check(type(pid) is int and pid>0 and type(seq) is int and seq>0,'TRACE_PID_SEQUENCE_INVALID:'+str(line_count))
        check(seq==last_seq.get(pid,0)+1,'TRACE_PID_SEQUENCE_GAP_OR_REPLAY:'+str(line_count))
        last_seq[pid]=seq
        check(len(last_seq)<=MAX_PIDS,'TRACE_PROCESS_COUNT_EXCESS')
        if kind=='probe_loaded':
            check(seq==1,'TRACE_LATE_PROBE_LOAD')
            check(item.get('scope')=='cpython_profile_only_not_native_attestation','TRACE_SCOPE_INVALID')
        else:
            check(per_pid[pid]['probe_loaded']==1,'TRACE_COMPUTE_WITHOUT_PROBE')
            check(item.get('function')=='_compute_local','TRACE_COMPUTE_FUNCTION_INVALID')
            source=item.get('source')
            check(type(source) is str,'TRACE_SOURCE_NOT_STRING')
            if root is not None:
                actual_source=Path(source).resolve()
                expected_source=(root/EXPECTED_COMPUTE_SOURCE).resolve()
                check(actual_source==expected_source,'TRACE_SOURCE_NOT_REPO_COMPUTE_LOCAL')
            else:
                check(Path(source).name=='pe_execution_v1b.py','TRACE_COMPUTE_FILENAME_UNKNOWN')
            sources[source]+=1 if kind=='compute_call' else 0
            if kind=='compute_call':
                stack=item.get('stack')
                check(type(stack) is list,'TRACE_STACK_INVALID')
                seen_stack[tuple((x.get('file'),x.get('function')) for x in stack[:3] if type(x) is dict)]+=1
                declared=item.get('declared_argument_names')
                check(declared==['node','state','timestamp','channels'],'TRACE_SIGNATURE_UNEXPECTED')
                calls[pid]+=1
            else:
                check(calls[pid]>0,'TRACE_UNPAIRED_COMPUTE_RETURN')
                calls[pid]-=1
            tick=item.get('host_monotonic_ns')
            check(type(tick) is int and tick>0,'TRACE_MONOTONIC_CLOCK_MISSING')
            # same process has monotone time on these observed events; no clock causality proof
            if pid in timestamps:
                check(tick>=timestamps[pid],'TRACE_HOST_MONOTONIC_CLOCK_BACKWARDS')
            timestamps[pid]=tick
        per_pid[pid][kind]+=1
        kinds[kind]+=1
    check(kinds['probe_loaded']>1 and kinds['compute_call']>0,'TRACE_NO_SOURCE_GATE_COMPUTE')
    check(all(v==0 for v in calls.values()),'TRACE_OBSERVED_CALL_RETURN_UNBALANCED')
    check(kinds['compute_call']==kinds['compute_return'],'TRACE_CALL_RETURN_TOTAL_MISMATCH')
    capped=sorted(pid for pid,c in per_pid.items()
                  if c['compute_call']+c['compute_return']>=PER_PROCESS_CAPTURE_CAP)
    # The cap causes silent omission of subsequent computation events.
    # Even without a reached cap, profiler completeness is not guaranteed.
    return {
        'bytes':size, 'sha256':trace_sha, 'jsonl_records':line_count,
        'event_counts':dict(kinds), 'process_count':len(per_pid),
        'observed_compute_sources':dict(sources),
        'observed_callsite_top3':[
            {'frames':[{'file':f,'function':fn} for f,fn in stack], 'calls':n}
            for stack,n in seen_stack.most_common(12)],
        'saturated_pid_count':len(capped),'saturated_pid_list':capped,
        'per_process_cap_events':PER_PROCESS_CAPTURE_CAP,
        'processes_at_capture_cap':len(capped)>0,
        'complete_execution_coverage_proven':False,
        'host_CPyth_profile_only':True,
        'C_authored_semantic_verdict_observed':False,
        'native_learning_observed':False,
    }

def validate_producer(doc:Path,log:Path):
    check(doc.is_file() and log.is_file(),'ORIGINAL_REPORT_OR_LOG_MISSING')
    check(digest(doc)==REPORT_SHA,'ORIGINAL_PRODUCER_SHA_DRIFT')
    check(digest(log)==LOG_SHA,'ORIGINAL_GATE_LOG_SHA_DRIFT')
    report=json.loads(doc.read_text(encoding='utf8'))
    check(report.get('schema')=='spk-v5-t3opq-source-custody-and-shared-resource-dual-replay/research-v0', 'PRODUCER_SCHEMA_INVALID')
    check(report.get('status')=='SOURCE_BV_V0E_DUAL_VERDICT_LINEAGE_WITH_SHADOW_LEARNING','PRODUCER_STATUS_INVALID')
    check(report.get('total_online_episodes')==720 and report.get('total_credited_updates')==617,'PRODUCER_COUNTS_INVALID')
    excluded=report.get('claims_excluded',[])
    check(any('host selects terminal observer' in x for x in excluded),'HOST_POSTHOC_SELECTION_UNDISCLOSED')
    logs=log.read_text(encoding='utf-8')
    check(len(logs)<200_000,'ORIGINAL_GATE_LOG_TOO_LARGE')
    check('T3OPQ BV-v0e SOURCE CAUSAL VERDICT BRIDGE PASS' in logs,'ORIGINAL_GATE_NO_PASS_EVIDENCE')
    check('T3OPQ DUAL BV v0e SOURCE REPLAY BYTE-EXACT PASS' in logs,'ORIGINAL_GATE_NO_DUAL_REPLAY')
    check('Ran 421 tests' in logs and 'OK (skipped=5)' in logs and '46 passed' in logs,'ORIGINAL_GATE_MISSING_REGRESSIONS')
    return {'producer_report_sha256':REPORT_SHA,'producer_log_sha256':digest(log),
            'report_status':report['status'],'source_gate_log_contains_pass':True,
            'dual_replay':True,'host_selects_terminal_after_both_passes':True,
            '421_research_tests_logged':True,'46_frozen_regressions_logged':True,
            'five_skipped_tests_logged':True}

def run(root:Path,trace:Path,producer:Path,log:Path,output:Path):
    root=root.resolve()
    check(root.is_dir(),'REPO_MISSING')
    check(output.parent.is_dir(),'OUTPUT_PARENT_MISSING')
    paths=[trace.resolve(),producer.resolve(),log.resolve(),output.resolve()]
    check(len(set(paths))==4,'EVIDENCE_PATH_COLLISION')
    pinned_before=snapshots(root)
    prod=validate_producer(producer,log)
    profile=analyze_trace(trace,root)
    check(profile['sha256']==TRACE_SHA, 'UPLOADED_TRACE_SHA_DRIFT')
    pinned_after=snapshots(root)
    check(pinned_before==pinned_after,'SOURCE_DRIFT_DURING_AUDIT')
    result={
        'schema':'spk-v5-t3xyz-trace-volume-recovery/research-v0',
        'status':'PASSIVE_TRACE_VALID_WITH_BOUNDED_COVERAGE_NOT_NATIVE_BV',
        'original_T3XYZ_gate':'FAIL_CLOSED_PROBE_TRACE_SIZE_INVALID',
        'root_source_hashes_at_audit':pinned_before,
        'original_T3OPQ':prod,
        'passive_profile':profile,
        'limits':[
            'Captured CPython calls/returns are structural only, never semantic C verdicts',
            'Original T3XYZ hard-coded 32MB threshold was exceeded; this hotfix streams up to 128MB',
            'Two observed PIDs reach 25000 call/return events; further events may have been omitted',
            'No source provenance authentication, verified native BV single pass, or learning',
            'Only current checkout source digests and report hash, not full transitive source attestation',
            'Original T3XYZ command did not reach its final gate, hotfix is an independent audit',
        ],
        'native_single_pass_C_verdict_proven':False,
        'native_semantic_BV_proven':False,
        'native_learning_proven':False,
        'promotion_allowed':False,
    }
    temp=output.with_name(output.name+'.tmp')
    try:
        temp.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf8')
        temp.replace(output)
    finally:temp.unlink(missing_ok=True)
    print('T3XYZ TRACE-VOLUME RECOVERY PASS: OBSERVED PYTHON COMPUTE, NO NATIVE BV')
    print('Trace bytes',profile['bytes'],'events',profile['jsonl_records'],
          'compute_calls',profile['event_counts']['compute_call'],
          'saturated_processes',profile['saturated_pid_count'])
    print('report',output)
    return result

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo',type=Path,required=True)
    p.add_argument('--trace',type=Path,required=True)
    p.add_argument('--producer',type=Path,required=True)
    p.add_argument('--log',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    run(a.repo,a.trace,a.producer,a.log,a.output)
    return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (AuditError,OSError,ValueError,KeyError) as e:
        print('T3XYZ RECOVERY FAIL CLOSED:',e,file=sys.stderr)
        sys.exit(3)
