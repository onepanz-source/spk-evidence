#!/usr/bin/env python3
"""T4ABC research-only C-verdict causal boundary dossier.

T4A: pin recovered evidence and frozen scheduler / compute source.
T4B: inspect source-level entry points for the C / source BV research bridge.
T4C: profile call-chain census and bounded allowlisted source dossier.

This does NOT establish native semantic BV. It cannot infer authorship from a
Python stack, and does not alter/patch any source file.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter, defaultdict
import hashlib
import io
import json
import os
from pathlib import Path
import tarfile

RECOVERY_SHA='4546d8070272736e1362f50fa408961331f5e198030fb7a9f4f102c8c240da7b'
TRACE_SHA='21ac7a5197c56cdff3edb816b86233d1c4749e601848eadac1c7413232e17484'
ORIGINAL_SHA='813753afd706eabff52653cf0a7674e1a44755981df61c6760fcbd4652c790d2'
FROZEN={
 'spk_architecture_v1/pe_execution_v1b.py':'8e9d08ddc165e0c6e307ca16cc849feb7eabad33c148c26f4faa436c890d752c',
 'spk_backvalidation_v0/live_dual_scheduler_v0e.py':'2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9',
 'search/spk_bv_v0e_live_evidence.py':'1e93f1a71c1099a3ce3c5e14d2cb9cfa47b8bfa9027832785d9f09af0c2bbc70'
}
# Every basename below is narrowly scoped to source observed in the actual
# T3XYZ profile; do not turn into an unrestricted copy of repository content.
TARGET_NAMES={
 'island_source_bv_bridge_v5t3o.py',
 'island_c_owned_credit_v5t3h.py',
 'island_source_admission_v5t3p.py',
 'island_source_bridge_audit_v5t3q.py',
 'island_online_credit_v5t3i.py',
}
REQUIRED_NAMES={'island_source_bv_bridge_v5t3o.py','island_c_owned_credit_v5t3h.py'}
MAX_SOURCE_BYTES=256_000
MAX_TRACE_BYTES=128_000_000
MAX_AST_FUNCTIONS=600
SKIP_DIRS={'.git','.venv','venv','__pycache__','node_modules','.pytest_cache','.mypy_cache','build','dist','site-packages'}

class GateError(Exception): pass

def require(cond,msg):
 if not cond: raise GateError(msg)

def sha(path:Path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()

def read_json(path:Path):
 try: return json.loads(path.read_text(encoding='utf8'))
 except (OSError,ValueError) as e: raise GateError(f'JSON_INVALID:{path}:{e}') from e

def verify_inputs(recovery:Path,trace:Path):
 require(recovery.is_file() and trace.is_file(),'EVIDENCE_INPUT_MISSING')
 require(0<trace.stat().st_size<=MAX_TRACE_BYTES,'TRACE_SIZE_INVALID')
 require(sha(recovery)==RECOVERY_SHA,'RECOVERY_SHA_MISMATCH')
 require(sha(trace)==TRACE_SHA,'TRACE_SHA_MISMATCH')
 r=read_json(recovery)
 require(r.get('schema')=='spk-v5-t3xyz-trace-volume-recovery/research-v0','RECOVERY_SCHEMA_INVALID')
 require(r.get('status')=='PASSIVE_TRACE_VALID_WITH_BOUNDED_COVERAGE_NOT_NATIVE_BV','RECOVERY_STATUS_INVALID')
 require(r.get('promotion_allowed') is False and r.get('native_single_pass_C_verdict_proven') is False,'RECOVERY_FALSE_PROMOTION')
 p=r['passive_profile']
 require(p.get('sha256')==TRACE_SHA and p.get('jsonl_records')==64615,'TRACE_RECEIPT_COUNTS_INVALID')
 require(p.get('saturated_pid_count')==2 and p.get('complete_execution_coverage_proven') is False,'COVERAGE_LIMIT_NOT_DISCLOSED')
 require(r['original_T3OPQ']['producer_report_sha256']==ORIGINAL_SHA and r['original_T3OPQ']['dual_replay'] is True,'ORIGINAL_CUSTODY_INVALID')
 return r

def verify_frozen(root:Path):
 files={}
 for rel,expected in FROZEN.items():
  path=root/rel
  require(path.is_file() and not path.is_symlink(),f'FROZEN_SOURCE_MISSING_OR_LINK:{rel}')
  digest=sha(path)
  require(digest==expected,f'FROZEN_SOURCE_SHA_DRIFT:{rel}')
  files[rel]=digest
 return files

def find_allowlisted(root:Path):
 hits=defaultdict(list)
 for folder,dirs,files in os.walk(root, followlinks=False):
  dirs[:]=[d for d in dirs if d not in SKIP_DIRS and not (Path(folder)/d).is_symlink()]
  for name in files:
   if name in TARGET_NAMES:
    path=Path(folder)/name
    require(not path.is_symlink() and path.is_file(),f'TARGET_SOURCE_LINK:{name}')
    hits[name].append(path)
 for name,paths in hits.items():require(len(paths)==1,f'TARGET_DUPLICATE:{name}')
 for name in REQUIRED_NAMES: require(len(hits[name])==1,f'TARGET_MISSING_OR_AMBIGUOUS:{name}:{len(hits[name])}')
 return dict(hits)

def call_name(n):
 if isinstance(n,ast.Name):return n.id
 if isinstance(n,ast.Attribute):
  if isinstance(n.value,ast.Name):return n.value.id+'.'+n.attr
  return n.attr
 return 'dynamic'

def inspect_source(path:Path, root:Path):
 raw=path.read_bytes()
 require(0<len(raw)<=MAX_SOURCE_BYTES, f'TARGET_SOURCE_SIZE_INVALID:{path.name}')
 try: tree=ast.parse(raw.decode('utf8'),filename=str(path))
 except (UnicodeDecodeError,SyntaxError) as e:raise GateError(f'TARGET_SOURCE_INVALID:{path.name}:{e}') from e
 funs=[]
 for node in ast.walk(tree):
  if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):
   calls=Counter(call_name(x.func) for x in ast.walk(node) if isinstance(x,ast.Call))
   funs.append({'name':node.name,'line':node.lineno,'end_line':node.end_lineno,'calls':dict(calls.most_common(15))})
 require(len(funs)<=MAX_AST_FUNCTIONS,'AST_FUNCTIONS_LIMIT')
 return {'path':str(path.relative_to(root)),'sha256':hashlib.sha256(raw).hexdigest(),
         'bytes':len(raw),'functions':sorted(funs,key=lambda x:x['line']),
         'limits':['syntax-level calls are not a complete dynamic call graph',
                   'no inference of C-authored semantics from symbols alone']}

def census_trace(path:Path,root:Path):
 counts=Counter(); pids=set(); capped=set(); per_pid=Counter(); per_stack=Counter(); per_process={}; prev={}
 original_root=str(root.resolve())
 with path.open('rt',encoding='utf8') as f:
  for n,line in enumerate(f,1):
   try:e=json.loads(line)
   except (ValueError,UnicodeError) as exc: raise GateError(f'TRACE_INVALID_JSON_LINE:{n}') from exc
   kind=e.get('kind');pid=e.get('pid');seq=e.get('seq')
   require(kind in ('probe_loaded','compute_call','compute_return') and type(pid) is int and type(seq) is int,'INVALID_TRACE_RECORD')
   require(seq==prev.get(pid,0)+1,f'TRACE_SEQUENCE_GAP:{pid}:{n}')
   prev[pid]=seq;counts[kind]+=1;pids.add(pid)
   if kind=='probe_loaded':
    require(pid not in per_process,f'DUPLICATE_PROCESS_LOAD:{pid}')
    per_process[pid]=e.get('argv',[])
   else:
    per_pid[pid]+=1
    if kind=='compute_call':
     source=e.get('source','')
     require(type(source) is str and source.startswith(original_root+'/'),f'UNBOUND_COMPUTE_SOURCE:{n}')
     frames=e.get('stack',[])
     require(type(frames) is list,'INVALID_STACK')
     parent=tuple((f.get('file'),f.get('function')) for f in frames[:5] if type(f) is dict)
     per_stack[parent]+=1
 require(counts==Counter({'compute_call':32298,'compute_return':32298,'probe_loaded':19}),'TRACE_AGGREGATE_DRIFT')
 require(len(pids)==19 and len(per_process)==19,'PROCESS_COUNT_MISMATCH')
 require(max(per_pid.values())==25000,'CAP_NOT_PRESENT')
 capped={pid for pid,total in per_pid.items() if total==25000}
 require(len(capped)==2,'SATURATED_PROCESS_COUNT_MISMATCH')
 top=[]
 for stack,n in per_stack.most_common(35):
  top.append({'calls':n,'frames':[{'file':name,'function':fn} for name,fn in stack]})
 boundary_calls=sum(n for stack,n in per_stack.items() if any(file=='island_source_bv_bridge_v5t3o.py' for file,fn in stack))
 c_credit_calls=sum(n for stack,n in per_stack.items() if any(file=='island_c_owned_credit_v5t3h.py' for file,fn in stack))
 source_v0e_calls=sum(n for stack,n in per_stack.items() if any(file=='live_dual_scheduler_v0e.py' for file,fn in stack))
 return {'bytes':path.stat().st_size,'events':dict(counts),'processes':len(pids),
         'processes_at_event_cap':len(capped),'per_process_cap_events':25000,
         'observable_bridge_compute_calls':boundary_calls,
         'observable_C_credit_module_compute_calls':c_credit_calls,
         'observable_BV_v0e_compute_calls':source_v0e_calls,
         'top_callstacks':top,'source_trace_sha256':TRACE_SHA,
         'coverage_complete':False,
         'credit_authorship_proven':False,
         'limitations':['Two capped processes make total capture incomplete',
                        'Stack module name demonstrates Python ancestry only',
                        'Neither a C-issued native event nor receiver receipt is observable from compute call stacks']}

def produce(root:Path,recovery_path:Path,trace_path:Path,out:Path,bundle:Path):
 root=root.resolve();out=out.resolve();bundle=bundle.resolve()
 require(root.is_dir() and out.parent.is_dir() and bundle.parent.is_dir(),'PATHS_INVALID')
 require(out!=bundle and bundle.suffixes[-2:]==['.tar','.gz'],'OUTPUT_PATH_INVALID')
 require(not out.exists() and not bundle.exists(),'OUTPUT_ALREADY_EXISTS_USE_FRESH_NAMES')
 recovered=verify_inputs(recovery_path,trace_path)
 frozen_before=verify_frozen(root)
 found=find_allowlisted(root)
 source_index=[]
 entries=[]
 for name in sorted(found):
  path=found[name][0];raw=path.read_bytes()
  info=inspect_source(path,root);source_index.append(info)
  entries.append((info['path'],raw))
 # Stronger snapshot: candidate source SHA in addition to legacy pinned sources.
 profile=census_trace(trace_path,root)
 require(profile['observable_bridge_compute_calls']>0,'BRIDGE_NEVER_OBSERVED')
 require(profile['observable_C_credit_module_compute_calls']>0,'C_CREDIT_MODULE_NEVER_OBSERVED')
 require(profile['observable_BV_v0e_compute_calls']>0,'V0E_NEVER_OBSERVED')
 require(frozen_before==verify_frozen(root),'FROZEN_CHANGED_DURING_AUDIT')
 for index in source_index:
  require(index['sha256']==sha(root/index['path']),f'TARGET_CHANGED_DURING_AUDIT:{index["path"]}')
 # Only explicit source allowlist in the tarball. Tar metadata made deterministic.
 with tarfile.open(bundle,'w:gz',format=tarfile.PAX_FORMAT) as tar:
  for name,raw in entries:
   info=tarfile.TarInfo(name)
   info.size=len(raw);info.mtime=0;info.uid=0;info.gid=0;info.uname='';info.gname='';info.mode=0o644
   tar.addfile(info,io.BytesIO(raw))
 result={
  'schema':'spk-v5-t4abc-causal-origin-dossier/research-v0',
  'status':'SOURCE_BOUNDARY_LOCALIZED_NATIVE_SEMANTIC_VERDICT_UNPROVEN',
  'A_evidence_custody':{'recovery_sha256':RECOVERY_SHA,'trace_sha256':TRACE_SHA,
                        'original_t3opq_sha256':ORIGINAL_SHA,'frozen_sha256':frozen_before,
                        'frozen_source_changed':False},
  'B_candidate_source_map':source_index,
  'C_observed_profile':profile,
  'source_bundle':{'path':str(bundle),'sha256':sha(bundle),'members':[n for n,_ in entries]},
  'next_gate_requirements':[
   'Inspect source and identify exact expression selecting C terminal after dual replay',
   'Design an additive single-execution C-authored verdict experiment, without editing frozen scheduler',
   'Use a receiver-readable source-bound event with measured ordering and replay rejection',
   'Separate synthetic C sensor value from genuine authenticated sensor observations',
   'Do not claim native BV or weight update until native source commits are observed'
  ],
  'limitations':['Syntax-only inspection, not verified runtime dataflow',
                 'Existing trace records CPython ancestry, not C event authorship',
                 'Source bundle contains only allowlisted research code and excludes frozen Architecture source',
                 'No sensor authentication or independent blind task labels'],
  'single_pass_C_authored_semantic_verdict_proven':False,
  'native_semantic_BV_proven':False,
  'native_learning_proven':False,
  'promotion_allowed':False,
 }
 out.write_text(json.dumps(result,sort_keys=True,indent=2,ensure_ascii=True)+'\n',encoding='utf8')
 print('T4ABC CAUSAL ORIGIN DOSSIER PASS; NOT NATIVE BV')
 print('bridge_calls',profile['observable_bridge_compute_calls'],
       'C_credit_module_calls',profile['observable_C_credit_module_compute_calls'],
       'BV_v0e_calls',profile['observable_BV_v0e_compute_calls'])
 print('report',out,'bundle',bundle)
 print('SHA256',sha(out),sha(bundle))
 return result

def main():
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--repo',required=True,type=Path)
 ap.add_argument('--recovery',required=True,type=Path)
 ap.add_argument('--trace',required=True,type=Path)
 ap.add_argument('--output',required=True,type=Path)
 ap.add_argument('--bundle',required=True,type=Path)
 a=ap.parse_args()
 try:produce(a.repo,a.recovery,a.trace,a.output,a.bundle)
 except (GateError,OSError,KeyError,TypeError,ValueError) as exc:
  print('T4ABC FAIL CLOSED:',exc,flush=True)
  return 3
 return 0

if __name__=='__main__':raise SystemExit(main())
