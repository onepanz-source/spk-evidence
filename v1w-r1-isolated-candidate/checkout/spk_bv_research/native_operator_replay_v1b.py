"""SPK BV v1b: read-only, source-bound replay of authentic A1 neuron computation.

Uses frozen architecture _compute_local, but never substitutes operators, installs
feedback, trains, commits state, modifies source, or asserts learning.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import fields, is_dataclass
import json
from hashlib import sha256
from pathlib import Path
import ast
import inspect

from spk_bv_research.native_capture_v0k import canonical_fixture
from spk_bv_research.off_on_v0t import (
    InterventionError, PINNED, require, snapshot, summarize, source_pins,
    runtime_modules_bound,
)

SCHEMA='spk-bv-native-readonly-compute-replay/v1b'
STATUS='SOURCE_BOUND_FROZEN_A1_LOCAL_COMPUTATION_OBSERVED_ONLY'
NATIVE_SOURCE='spk_architecture_v1/pe_execution_v1b.py'
EXCLUSIONS=[
    'no-feedback-judgment-to-operator-map',
    'no-native-operator-substitution-or-neuron-update',
    'no-native-learning-or-causal-utility',
    'no-independent-criterion-or-external-truth',
    'read-only-first-episode-not-prospective-heldout',
    'single-frozen-A1-three-node-fixture',
    'no-hardware-or-architecture-promotion',
]


def check_reference(v1a, v0w, v0w_bytes):
    require(type(v1a) is dict and v1a.get('schema')=='spk-bv-prospective-symbolic-holdout-audit/v1a'
            and v1a.get('status')=='NATIVE_CHAIN_ANCHORED_TOY_EVALUATION_ONLY',
            'v1a wrong schema/status')
    require(type(v0w) is dict and v0w.get('schema')=='spk-bv-native-temporal-workload-three-arm/v0w'
            and v0w.get('status')=='SOURCE_BOUND_TEMPORAL_WORKLOAD_MODEL_SCAN_ONLY',
            'v0w wrong schema/status')
    require(v1a.get('v0w_file_sha256')==sha256(v0w_bytes).hexdigest(), 'v1a-v0w anchor drift')
    require(v1a.get('native_operator_updates_applied')==0 and
            v1a.get('native_judgments_observed')==0 and
            v1a.get('observed_native_learning_benefit') is False,
            'v1a misclaims native learning')
    require(v1a.get('source_kind')=='toy-isolated-symbolic-boolean-domain-not-SPK-runtime',
            'v1a toy/native boundary absent')
    demos=v1a.get('synthetic_demos')
    require(type(demos) is list and len(demos)==3 and
            [(r.get('demo'),r.get('correct_count_delta'),r.get('real_neuron_operators_executed'))
             for r in demos]== [('positive',3,False),('negative',-3,False),('tie',0,False)],
            'v1a synthetic positive/negative/tie anchor drift')
    require(type(v0w.get('cells')) is list and len(v0w['cells'])==15 and
            v0w['cells'][0].get('workload')=='baseline' and
            v0w['cells'][0].get('fabric_slots_per_tick')==1 and
            v0w['cells'][0].get('max_inflight_occurrences')==4,
            'v0w baseline first cell unavailable')
    require(v0w.get('source_sha256')=={k:PINNED[k] for k in v0w.get('source_sha256',{})}
            and set(v0w['source_sha256'])==set(PINNED), 'v0w frozen producer pins drift')
    return v0w['cells'][0]['runs']['off']


def valid_native_source(root, function, name):
    p=(root/NATIVE_SOURCE)
    require(p.is_file() and not p.is_symlink() and p.resolve()==p,
            'native A1 source missing or unsafe')
    require(p.stat().st_size<=600_000, 'native A1 source oversized')
    require(function.__name__==name and function.__module__=='spk_architecture_v1.pe_execution_v1b'
            and Path(inspect.getfile(function)).resolve()==p,
            'native function not bound to frozen A1 source: '+name)
    return p


def source_snapshot(root, admit, compute):
    root=root.resolve(strict=True)
    pins=source_pins(root)
    p1=valid_native_source(root,admit,'_admit')
    p2=valid_native_source(root,compute,'_compute_local')
    require(p1==p2,'native functions from distinct sources')
    raw=p1.read_bytes()
    tree=ast.parse(raw,filename=str(p1))
    declared=[n.name for n in tree.body if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
    require(declared.count('_admit')==1 and declared.count('_compute_local')==1,
            'native A1 source does not define expected functions')
    code=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='_compute_local')
    return {'frozen_producer_sha256':pins,'frozen_a1_compute_source_sha256':sha256(raw).hexdigest(),
            'compute_function_ast_sha256':sha256(ast.dump(code,include_attributes=False).encode('utf8')).hexdigest(),
            'compute_function_name':'_compute_local',
            'compute_function_positional_args':[a.arg for a in code.args.args]}


def shape(node):
    """Describe the *observed* A1 instruction representation, not an assumed ISA.

    The frozen native codec already supports literal tokens and tagged compound
    instructions as well as dataclasses.  Reuse its actual typed encoding, and
    refuse unknown Python objects rather than guessing an operator meaning.
    """
    ins=getattr(node,'instructions',None)
    require(type(ins) is tuple and 0<len(ins)<=128,
            'node has no bounded instruction tuple')
    program=canonical_fixture(ins)  # the same strict, lossless codec as snapshot
    require(type(program) is dict and program.get('$t')=='tuple' and
            type(program.get('items')) is list and len(program['items'])==len(ins),
            'native program canonical shape mismatch')
    encoded_size=len(json.dumps(program,sort_keys=True,separators=(',', ':'),
                                ensure_ascii=True).encode('utf8'))
    require(encoded_size<=65536,'native instruction program encoding oversized')
    shapes=[]
    for index, (item, encoded) in enumerate(zip(ins,program['items'])):
        # This is a *readonly inventory*, not an instruction validator: all
        # kinds permitted by the existing lossless fixture codec are observed.
        # Otherwise a new primitive native representation would be silently
        # (and wrongly) forbidden by this research probe.
        representation=(encoded.get('$t') if type(encoded) is dict and
                        type(encoded.get('$t')) is str else type(item).__name__)
        names=[]; kind={}
        if is_dataclass(item) and not isinstance(item,type):
            names=[f.name for f in fields(item)]
            kind={k:getattr(item,k) for k in ('op','opcode','operator','kind')
                  if k in names and type(getattr(item,k)) in (str,int)}
        elif type(item) is str:
            kind={'literal_token':item}
        elif type(item) is tuple and item and type(item[0]) is str:
            kind={'head_token':item[0]}
        elif type(item) is dict:
            names=sorted(k for k in item if type(k) is str)
            kind={k:item[k] for k in ('op','opcode','operator','kind')
                  if k in item and type(item[k]) in (str,int)}
        shapes.append({'index':index,'type':type(item).__qualname__,
                       'representation':representation,'fields':names,
                       'operator_discriminants':kind})
    return {'instruction_count':len(ins),
            'instruction_program_sha256':snapshot(ins),
            'instruction_codec':'strict-v0k-lossless-canonical-fixture',
            'instruction_program_encoding_bytes':encoded_size,
            'canonical_instruction_program':program,
            'instruction_shapes':shapes}


def replay(native, admit, compute, off_result, expected_off, *, expected_fixture_sha256):
    require(type(native) is tuple and len(native)==3 and type(native[2]) is tuple
            and len(native[2])==4, 'bad native fixture tuple')
    base=snapshot(native)
    require(base==expected_fixture_sha256, 'native fixture differs from v0w fixture')
    case,fabric,plans=native
    nodes,owners=admit(case,fabric)
    require(type(nodes) is dict and len(nodes)==3 and type(owners) is dict,
            'native A1 admission did not produce expected bounded nodes')
    require(snapshot(native)==base, '_admit mutated fixture')
    require(type(off_result) is dict and off_result.get('enabled') is False and
            off_result.get('policy')=='forward-first', 'not an OFF forward-first native trace')
    summary=summarize(off_result,enabled=False,priority='forward-first')
    for field in ('whole_result_sha256','forward_states_sha256',
                  'forward_emission_payload_multiset_sha256',
                  'forward_terminal_payload_multiset_sha256',
                  'last_forward_terminal_tick','metrics'):
        require(summary[field]==expected_off[field], 'native OFF reference mismatch: '+field)
    fw=off_result['forward']
    batches=fw['batches']
    require(type(batches) is list and 0<len(batches)<=128, 'native batch list invalid')
    state={nid:[node.initial_raw,0] for nid,node in nodes.items()}
    examined=[]
    for i,row in enumerate(batches):
        require(type(row) is dict and type(row.get('tick')) is int and
                type(row.get('node')) is str and type(row.get('channels')) is list,
                'invalid forward batch for micro-replay')
        nid=row['node']; require(nid in nodes,'unknown node in batch')
        before=snapshot(state[nid]); original=list(state[nid]); node_before=snapshot(nodes[nid])
        tick=row['tick'];channels=list(row['channels'])
        require(tick>=state[nid][1] and all(type(ch) is int for ch in channels),
                'backdated replay or invalid channels')
        state_arg1=list(state[nid]);channels_arg1=list(channels)
        result1=compute(nodes[nid],state_arg1,tick,channels_arg1)
        require(state_arg1==original and channels_arg1==channels,
                'native local kernel mutated its input argument')
        state_arg2=list(state[nid]);channels_arg2=list(channels)
        result2=compute(nodes[nid],state_arg2,tick,channels_arg2)
        require(state_arg2==original and channels_arg2==channels,
                'native local kernel mutated its input argument')
        require(type(result1) in (tuple,list) and len(result1)==3 and
                snapshot(result1)==snapshot(result2), 'native kernel is not deterministic')
        raw,guard,outputs=result1
        require(type(raw) is int and type(outputs) in (tuple,list) and
                all(type(ch) is int for ch in outputs), 'native kernel returned bad types')
        require(raw==row['raw'] and list(outputs)==row['outputs'],
                'native kernel result differs from scheduler forward batch')
        require(snapshot(state[nid])==before and state[nid]==original and
                snapshot(nodes[nid])==node_before and snapshot(native)==base,
                'micro-replay mutated native neuron or fixture')
        examined.append({'batch_index':i,'neuron_id':nid,'tick':tick,
                         'channels':channels,'prestate_sha256':before,
                         'kernel_output_sha256':snapshot(result1),
                         'poststate_raw':raw,'emitted_channels':list(outputs),
                         'guard_type':type(guard).__name__,'guard_sha256':snapshot(guard)})
        state[nid]=[raw,tick]
    require(fw['states']=={n:state[n][0] for n in fw['states']},
            'micro-replay terminal states differ from native OFF')
    require(snapshot(native)==base,'native fixture was modified during replay')
    return {'native_fixture_sha256':base,'native_off_result_sha256':summary['whole_result_sha256'],
            'verified_forward_batches':len(examined),
            'neuron_instruction_programs':{n:shape(nodes[n]) for n in sorted(nodes)},
            'readonly_microtrace':examined}


def generate(v1a,w,wbytes,fixture_fn,executor,plan_type,admit,compute,*,root,pin_sources=True):
    expected=check_reference(v1a,w,wbytes)
    root=root.resolve(strict=True)
    before=source_snapshot(root,admit,compute) if pin_sources else None
    if pin_sources:runtime_modules_bound(root,executor,fixture_fn,plan_type)
    native=fixture_fn()
    require(type(native) is tuple and len(native)==3,'bad native fixture')
    original=snapshot(native)
    bvo=plan_type(enabled=False,priority='forward-first')
    result=executor(native[0],native[1],*native[2],bvo)
    require(snapshot(native)==original,'native OFF run mutated fixture')
    detail=replay(native,admit,compute,result,expected,
                  expected_fixture_sha256=w['original_fixture_sha256'])
    if pin_sources:
        require(before==source_snapshot(root,admit,compute),'native source drift during replay')
        runtime_modules_bound(root,executor,fixture_fn,plan_type)
    return {'schema':SCHEMA,'status':STATUS,
            'v1a_status':v1a['status'],'v0w_sha256':sha256(wbytes).hexdigest(),
            'frozen_native_sources':before,
            **detail,
            'native_operator_substitutions':0,'native_judgments_observed':0,
            'native_heldout_comparisons':0,'native_learning_proven':False,
            'claims_excluded':EXCLUSIONS}
