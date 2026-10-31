"""SPK BV v1c: bounded, isolated native local-kernel program-operand sensitivity.

Changes *only* a dataclass copy of a neuron; no scheduler, no native feedback,
no learned update, no oracle and no utility classification. Native source custody
and its OFF run are separately checked by the inherited v1b.1 generator.
"""
from __future__ import annotations
from dataclasses import dataclass, is_dataclass, replace
from hashlib import sha256
from collections import Counter
from spk_bv_research.off_on_v0t import InterventionError, require, snapshot

SCHEMA='spk-bv-native-isolated-operand-sensitivity/v1c'
STATUS='BOUNDED_NATIVE_KERNEL_COUNTERFACTUAL_NO_UTILITY_OR_LEARNING'
# Predeclared probes, independent of kernel results; (initial raw, incoming channels).
DOMAIN=((0,(0,)),(0,(1,)),(0,(0,0)),(0,(0,1)),(1,(0,)),(1,(1,)))
TIMESTAMP=10
PREVIOUS_TICK=9
# These are operand perturbations, NOT operator substitutions or neural judgments.
CANDIDATES=(
 ('A',0,('SHIFT',0)),
 ('A',1,('ACC',(2,0))),
 ('A',2,('CMP',2)),
 ('B',1,('CMP',2)),
 ('C',1,('CMP',2)),
)
EXCLUSIONS=[
 'operand-changes-not-proven-admissible-algebra-rewrites',
 'no-change-to-frozen-SPK-runtime-or-original-neuron',
 'probe-domain-is-synthetic-not-independent-heldout-distribution',
 'different-kernel-output-is-not-improved-output',
 'no-independent-objective-truth-or-receiver-judgment',
 'no-network-level-forward-counterfactual-or-feedback-to-operator-map',
 'no-committed-update-no-rollback-no-learning-claim',
 'not-N-node-scalability-or-hardware-metrics-or-architecture-promotion',
]


def validate_reference(v1b, v1b_bytes, v1a, v0w, v0w_bytes):
    require(type(v1b) is dict and v1b.get('schema')=='spk-bv-native-readonly-compute-replay/v1b'
            and v1b.get('status')=='SOURCE_BOUND_FROZEN_A1_LOCAL_COMPUTATION_OBSERVED_ONLY',
            'wrong v1b.1 schema/status')
    require(v1b.get('verified_forward_batches')==6 and
            v1b.get('native_operator_substitutions')==0 and
            v1b.get('native_judgments_observed')==0 and
            v1b.get('native_learning_proven') is False, 'v1b.1 baseline did not remain observational')
    require(v1b.get('v0w_sha256')==sha256(v0w_bytes).hexdigest(), 'v1b.1/v0w file anchor drift')
    progs=v1b.get('neuron_instruction_programs')
    require(type(progs) is dict and set(progs)=={'A','B','C'}, 'v1b.1 neuron inventory drift')
    expected={
      'A':(('SHIFT',1),('ACC',(1,0)),('CMP',1),('EMIT',7),('RESET',0)),
      'B':(('ACC',(1,0)),('CMP',1),('EMIT',7),('RESET',0)),
      'C':(('ACC',(1,0)),('CMP',1),('EMIT',7),('RESET',0)),
    }
    # Fixed control fixture layout, not an assertion about a universal SPK ISA.
    for nid,program in expected.items():
        require(progs[nid].get('instruction_program_sha256')==snapshot(program),
                'v1b.1 native neuron program drift: '+nid)
    require(type(v1a) is dict and type(v0w) is dict, 'reference types')
    return {'v1b1_file_sha256':sha256(v1b_bytes).hexdigest(),
            'v0w_file_sha256':sha256(v0w_bytes).hexdigest(),
            'expected_programs':expected}


def _computed(compute, node, raw, channels):
    """Call native kernel twice without mutating its inputs; fail closed."""
    state=[raw,PREVIOUS_TICK]
    input_channels=list(channels)
    before_node=snapshot(node)
    outs=[]
    for _ in (0,1):
        arg_state=list(state); arg_channels=list(input_channels)
        result=compute(node,arg_state,TIMESTAMP,arg_channels)
        require(arg_state==state and arg_channels==input_channels and
                snapshot(node)==before_node, 'native compute mutated isolated arguments')
        require(type(result) in (tuple,list) and len(result)==3 and
                type(result[0]) is int and type(result[2]) in (tuple,list) and
                all(type(v) is int for v in result[2]), 'bad native kernel output')
        outs.append(snapshot(result))
    require(outs[0]==outs[1], 'nondeterministic native kernel')
    return outs[0]


def sensitivity(nodes, compute, *, expected_programs):
    """Run exactly the predeclared 5 x 6 probe matrix; reject silently skipped cells."""
    require(type(nodes) is dict and set(nodes)=={'A','B','C'}, 'native node set drift')
    require(all(is_dataclass(v) and not isinstance(v,type) for v in nodes.values()),
            'native neuron is not safely replaceable as dataclass')
    original_nodes={k:snapshot(v) for k,v in nodes.items()}
    items=[]
    for nid,index,replacement in CANDIDATES:
        node=nodes[nid]
        require(is_dataclass(node) and not isinstance(node,type),
                'native neuron is not safely replaceable as dataclass')
        program=getattr(node,'instructions',None)
        require(type(program) is tuple and program==expected_programs[nid],
                'native admitted program drift')
        require(0<=index<len(program) and program[index]!=replacement and
                type(program[index]) is tuple and type(program[index][0]) is str and
                replacement[0]==program[index][0],
                'candidate changes native opcode identity or is a noop')
        candidate_program=program[:index]+(replacement,)+program[index+1:]
        variant=replace(node,instructions=candidate_program)
        require(snapshot(variant)!=snapshot(node) and snapshot(node)==original_nodes[nid],
                'variant was not isolated')
        results=[]
        for raw,channels in DOMAIN:
            baseline=_computed(compute,node,raw,channels)
            try:
                counterfactual=_computed(compute,variant,raw,channels)
                outcome='DIFFERENT' if baseline!=counterfactual else 'SAME'
                reason=None
            except (ValueError,TypeError,OverflowError,IndexError,AssertionError) as exc:
                if isinstance(exc, InterventionError):
                    raise  # native input mutation, invalid output and nondeterminism are fatal
                counterfactual=None
                outcome='REJECTED'
                reason=type(exc).__name__ # no guessed reason, no silent suppression
            results.append({'raw':raw,'channels':list(channels),
                            'baseline_result_sha256':baseline,
                            'counterfactual_result_sha256':counterfactual,
                            'outcome':outcome,'rejection_exception_type':reason})
            require(snapshot(node)==original_nodes[nid] and
                    snapshot(variant)!=snapshot(node), 'native neuron changed during probe')
        counts=Counter(r['outcome'] for r in results)
        require(sum(counts.values())==len(DOMAIN), 'incomplete native probe')
        items.append({'neuron_id':nid,'instruction_index':index,
            'original_instruction':list(program[index]),
            'candidate_instruction':list(replacement),
            'original_program_sha256':snapshot(program),
            'candidate_program_sha256':snapshot(candidate_program),
            'domain_outcomes':results,
            'different':counts['DIFFERENT'],'same':counts['SAME'],
            'rejected':counts['REJECTED']})
    require(all(snapshot(nodes[n])==original_nodes[n] for n in nodes),
            'native nodes were changed by study')
    counts=Counter(r['outcome'] for item in items for r in item['domain_outcomes'])
    return {'candidates':items,'candidate_count':len(items),'input_cases_per_candidate':len(DOMAIN),
            'probe_pairs':sum(counts.values()),'different_pairs':counts['DIFFERENT'],
            'same_pairs':counts['SAME'],'rejected_pairs':counts['REJECTED'],
            'original_nodes_immutable':True}


def build(v1b, v1b_bytes, v1a, v0w, v0w_bytes, native_baseline, native_fixture,
          admit, compute):
    a=validate_reference(v1b,v1b_bytes,v1a,v0w,v0w_bytes)
    require(native_baseline==v1b,'native v1b.1 reconstruction differs from saved report')
    before=snapshot(native_fixture)
    require(before==v1b['native_fixture_sha256'], 'fixture drift')
    nodes,_=admit(native_fixture[0],native_fixture[1])
    require(snapshot(native_fixture)==before, 'admission mutated fixture')
    report=sensitivity(nodes,compute,expected_programs=a['expected_programs'])
    require(snapshot(native_fixture)==before,'probe mutated fixture')
    return {'schema':SCHEMA,'status':STATUS,
            'reference_v1b1_sha256':a['v1b1_file_sha256'],
            'reference_v0w_sha256':a['v0w_file_sha256'],
            'frozen_native_sources':v1b['frozen_native_sources'],
            'native_fixture_sha256':before,
            'source_bound_native_baseline_batches':v1b['verified_forward_batches'],
            'domain_spec':{'timestamp':TIMESTAMP,'prior_tick':PREVIOUS_TICK,
                'input_states_and_channels':[{'raw':r,'channels':list(c)} for r,c in DOMAIN]},
            **report,
            'native_judgments_observed':0,'native_updates_applied':0,
            'native_utility_identified':False,'native_learning_proven':False,
            'claims_excluded':EXCLUSIONS}
