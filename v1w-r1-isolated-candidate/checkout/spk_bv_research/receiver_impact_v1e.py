"""BV v1e: native-kernel *conditional* recipient readout, not receiver judgment.

A's selected v1d local perturbation affects zero/one channel-7 emissions.
We predeclare a hypothetical ingress translation 7->0 for B and C and
compute each recipient independently on a frozen node copy/state. This is
NOT an attestation that the network routes A to either recipient, nor a live
scheduler replay, actual feedback, a neuron-originated assessment, or utility.
"""
from __future__ import annotations
from dataclasses import replace, is_dataclass
from hashlib import sha256
import json
from spk_bv_research.off_on_v0t import InterventionError,require,snapshot
from spk_bv_research.native_criterion_v1d import (
    SCHEMA as V1D_SCHEMA, STATUS as V1D_STATUS, EVAL_INDEX,
    EVAL_TIMESTAMP,EVAL_PREVIOUS_TICK,observe,
)
from spk_bv_research.native_sensitivity_v1c import CANDIDATES,DOMAIN

SCHEMA='spk-bv-native-conditional-receiver-impact/v1e'
STATUS='ISOLATED_NATIVE_RECEIVER_READOUT_HYPOTHETICAL_INGRESS_ONLY'
INGRESS_MAPPING=((7,0),)
RECEIVER_IDS=('B','C')
RECEIVER_TIMESTAMP=12
RECEIVER_PRIOR_TICK=11
EXCLUSIONS=[
 'channel-7-to-recipient-channel-0-is-declared-not-frozen-network-route-attested',
 'B-and-C-are-separate-conditional-recipients-not-causally-linked-replayed-events',
 'no-endogenous-recipient-judgment-or-assessment-packet',
 'recipient-readout-difference-not-utility-or-independent-objective',
 'no-live-ON-feedback-scheduler-or-credit-assignment',
 'native-operand-perturbation-not-certified-algebra-rewrite',
 'evaluation-domain-remains-synthetic-small-nonindependent',
 'no-committed-operator-update-learning-rollback-or-architecture-promotion',
]

def ingress(emitted):
    """A declared *experimental* conditional translation, not a network route."""
    require(type(emitted) in (tuple,list) and all(type(v) is int for v in emitted),
            'invalid sender emitted-channel representation')
    require(tuple(emitted) in ((),(7,)), 'unsupported sender emission for shadow ingress')
    return () if not emitted else (0,)


def _readout(compute,node,channels):
    require(type(node.initial_raw) is int, 'receiver initial state is not an integer')
    return observe(compute,node,node.initial_raw,channels,
                   timestamp=RECEIVER_TIMESTAMP,prior_tick=RECEIVER_PRIOR_TICK)


def analyze(nodes,compute,v1d):
    require(type(v1d) is dict and v1d.get('schema')==V1D_SCHEMA and
            v1d.get('status')==V1D_STATUS, 'v1d provenance invalid')
    require(v1d.get('native_updates_applied')==0 and v1d.get('native_judgments_observed')==0
            and v1d.get('native_learning_proven') is False, 'v1d native claims drift')
    require(type(nodes) is dict and set(nodes)=={'A','B','C'},'native neuron set drift')
    require(all(is_dataclass(n) and not isinstance(n,type) for n in nodes.values()),
            'nonreplaceable native neuron')
    src={n:snapshot(node) for n,node in nodes.items()}
    winner=v1d.get('selected_candidate_position')
    require(type(winner) is int and 0<=winner<len(CANDIDATES), 'v1d candidate position invalid')
    training=v1d.get('training')
    require(type(training) is list and len(training)==len(CANDIDATES) and
            all(type(t) is dict and type(t.get('correct_count_delta')) is int for t in training),
            'v1d training inventory drift')
    require(winner==max(range(len(training)),key=lambda i:training[i]['correct_count_delta']),
            'v1d winner is inconsistent with declared selection rule')
    nid,idx,instruction=CANDIDATES[winner]
    require(nid=='A', 'selected program is not the declared sender A')
    node=nodes['A']
    original_program=node.instructions
    require(type(original_program) is tuple and 0<=idx<len(original_program) and
            type(original_program[idx]) is tuple and instruction[0]==original_program[idx][0] and
            instruction != original_program[idx], 'native A program/variant drift')
    variant=replace(node,instructions=original_program[:idx]+(instruction,)+original_program[idx+1:])
    require(snapshot(variant)!=snapshot(node),'not an isolated native candidate')
    elected=training[winner]
    require(elected.get('candidate_position')==winner and
            elected.get('neuron_id')==nid and elected.get('instruction_index')==idx and
            elected.get('original_program_sha256')==snapshot(original_program) and
            elected.get('candidate_program_sha256')==snapshot(variant.instructions),
            'native A v1d selected program digests differ')
    evaluation=v1d.get('evaluation')
    require(type(evaluation) is dict and type(evaluation.get('rows')) is list and
            len(evaluation['rows'])==len(EVAL_INDEX), 'v1d evaluation domain missing')
    records=[]
    for k,domain_index in enumerate(EVAL_INDEX):
        row=evaluation['rows'][k]
        require(type(row) is dict and row.get('domain_index')==domain_index, 'reordered v1d evaluation')
        raw,channels=DOMAIN[domain_index]
        require(row.get('raw')==raw and row.get('channels')==list(channels),
                'v1d heldout input mismatch')
        baseline=observe(compute,node,raw,channels,
                         timestamp=EVAL_TIMESTAMP,prior_tick=EVAL_PREVIOUS_TICK)
        candidate=observe(compute,variant,raw,channels,
                          timestamp=EVAL_TIMESTAMP,prior_tick=EVAL_PREVIOUS_TICK)
        require(baseline==row.get('baseline') and candidate==row.get('candidate'),
                'native A v1d readout mismatch')
        baseline_input=ingress(baseline['emitted_channels'])
        candidate_input=ingress(candidate['emitted_channels'])
        for rid in RECEIVER_IDS:
            receiver=nodes[rid]
            recipient_before=_readout(compute,receiver,baseline_input)
            recipient_after=_readout(compute,receiver,candidate_input)
            require(snapshot(receiver)==src[rid], 'native recipient mutated')
            equal=recipient_before==recipient_after
            records.append({'evaluation_domain_index':domain_index,
                'sender_id':'A','receiver_id':rid,
                'sender_original_emitted_channels':baseline['emitted_channels'],
                'sender_variant_emitted_channels':candidate['emitted_channels'],
                'declared_original_ingress':list(baseline_input),
                'declared_variant_ingress':list(candidate_input),
                'original_receiver_readout':recipient_before,
                'variant_receiver_readout':recipient_after,
                'receiver_output_changed':not equal,
                'receiver_guard_changed':recipient_before['guard']!=recipient_after['guard'],
                'receiver_emission_changed':recipient_before['emitted_channels']!=recipient_after['emitted_channels'],
                'classification':'DIFFERENT' if not equal else 'SAME'})
    require(len(records)==len(EVAL_INDEX)*len(RECEIVER_IDS),'incomplete receiver matrix')
    require(all(snapshot(nodes[n])==src[n] for n in nodes),'original neuron mutated')
    return {'hypothetical_mapping':{'sender':'A','sender_channel':7,
               'conditional_receiver_ids':list(RECEIVER_IDS),'receiver_channel':0,
               'network_route_attested':False,'native_feedback_packet_attested':False,
               'origin':'explicit_shadow_ingress_assumption_not_native_scheduler'},
            'receiver_probe':{'recipient_timestamp':RECEIVER_TIMESTAMP,
                 'recipient_prior_tick':RECEIVER_PRIOR_TICK,
                 'recipient_raw':'each receiver immutable initial_raw',
                 'evaluation_domain_indices':list(EVAL_INDEX),
                 'receiver_pairs':len(records),'different_pairs':sum(r['receiver_output_changed'] for r in records),
                 'guard_different_pairs':sum(r['receiver_guard_changed'] for r in records),
                 'emission_different_pairs':sum(r['receiver_emission_changed'] for r in records),
                 'readouts':records},
            'selected_sender_program_sha256':snapshot(original_program),
            'candidate_sender_program_sha256':snapshot(variant.instructions),
            'native_receiver_kernels_executed':True,
            'frozen_original_nodes_immutable':True,
            'network_event_lineage_attested':False,
            'native_judgments_observed':0,'native_updates_applied':0,
            'native_learning_proven':False,'causal_credit_identified':False}


def build(v1d,v1d_bytes,computed_v1d,native_fixture,admit,compute):
    require(v1d==computed_v1d, 'full v1d native recomputation mismatch')
    original_hash=snapshot(native_fixture)
    require(original_hash==v1d.get('native_fixture_sha256'), 'native fixture hash drift')
    nodes,_=admit(native_fixture[0],native_fixture[1])
    require(snapshot(native_fixture)==original_hash,'native fixture admission mutated input')
    analysis=analyze(nodes,compute,v1d)
    require(snapshot(native_fixture)==original_hash,'native fixture mutated by v1e')
    return {'schema':SCHEMA,'status':STATUS,
            'reference_v1d_sha256':sha256(v1d_bytes).hexdigest(),
            'reference_v1c_sha256':v1d['reference_v1c_file_sha256'],
            'reference_v1b1_sha256':v1d['reference_v1b1_file_sha256'],
            'reference_v0w_sha256':v1d['reference_v0w_file_sha256'],
            'native_fixture_sha256':original_hash,
            'frozen_native_sources':v1d['frozen_native_sources'],
            **analysis,'claims_excluded':EXCLUSIONS}
