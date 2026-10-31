"""BV v1h: source-bound, isolated pre-episode change of A and full native scheduler replay.

The native scheduler runs an experimental *copy* of the A/B/C fixture, not a
feedback-generated choice, an online commit, a certified algebra rewrite or a
claim of utility.  In particular C is only A's *descendant*, never a direct
A -> C connection in this frozen fixture.
"""
from __future__ import annotations
from collections import Counter
from dataclasses import fields, is_dataclass, replace
from hashlib import sha256

from spk_bv_research.off_on_v0t import require, snapshot, summarize
from spk_bv_research.native_sensitivity_v1c import CANDIDATES
from spk_bv_research.native_criterion_v1d import SCHEMA as D_SCHEMA, STATUS as D_STATUS
from spk_bv_research.native_route_lineage_v1g import (
    SCHEMA as G_SCHEMA, STATUS as G_STATUS, _edge, _index_forward,
)

SCHEMA = 'spk-bv-source-bound-isolated-network-counterfactual/v1h'
STATUS = 'NATIVE_FROZEN_SCHEDULER_VARIANT_NETWORK_REPLAY_NO_JUDGMENT_OR_LEARNING'
EXCLUSIONS = [
    'variant-cmp-operand-was-experimenter-selected-on-synthetic-local-criterion',
    'pre-episode-copy-intervention-not-feedback-originated-neuron-update',
    'not-a-certified-SPK-algebra-rewrite',
    'native-scheduler-bounded-A-B-C-fixture-not-independent-heldout',
    'network-emission-loss-or-gain-not-a-utility-value',
    'native-feedback-is-evidence-lineage-not-scored-receiver-judgment',
    'no-causal-credit-or-learned-controller-or-online-rollback',
    'no-hardware-performance-generalization-or-architecture-promotion',
]


def variant_fixture(original, v1d):
    """Change exactly one instruction on a detached A neuron, with lossless revert."""
    require(type(original) is tuple and len(original)==3, 'native fixture shape changed')
    case, fabric, plans=original
    require(is_dataclass(case) and not isinstance(case,type) and
            {'nodes','events'} <= {f.name for f in fields(case)},
            'native case is not an admitted dataclass')
    require(type(case.nodes) is tuple and len(case.nodes)==3,
            'unexpected bounded native node tuple')
    require(type(v1d) is dict and v1d.get('schema')==D_SCHEMA and
            v1d.get('status')==D_STATUS and v1d.get('selected_candidate_position')==2 and
            v1d.get('selected_was_training_improvement') is True and
            v1d.get('native_updates_applied')==0 and
            v1d.get('native_judgments_observed')==0,
            'v1d intervention is not the frozen selected shadow proposal')
    selected=CANDIDATES[2]
    require(selected==('A',2,('CMP',2)), 'selected intervention drift')
    mapped={getattr(n,'node_id',None):n for n in case.nodes}
    require(set(mapped)=={'A','B','C'} and len(mapped)==len(case.nodes),
            'admitted node inventory mismatch')
    a=mapped['A']
    require(is_dataclass(a) and not isinstance(a,type) and type(a.instructions) is tuple
            and len(a.instructions)==5 and a.instructions[2]==('CMP',1),
            'native original A/CMP instruction drift')
    require(snapshot(a.instructions)==v1d['training'][2]['original_program_sha256'] and
            v1d['training'][2].get('candidate_position')==2 and
            v1d['training'][2].get('candidate_program_sha256')==snapshot(
                 a.instructions[:2]+(('CMP',2),)+a.instructions[3:]),
            'v1d selected program SHA does not match fixture')
    base=snapshot(original)
    candidate_a=replace(a,instructions=a.instructions[:2]+(('CMP',2),)+a.instructions[3:])
    nodes=tuple(candidate_a if n.node_id=='A' else n for n in case.nodes)
    candidate_case=replace(case,nodes=nodes)
    require(snapshot(candidate_case)!=snapshot(case) and
            snapshot(replace(candidate_case,nodes=case.nodes))==snapshot(case) and
            snapshot((case,fabric,plans))==base and
            candidate_case.events==case.events and
            all(x is y for x,y in zip(case.nodes,nodes) if x.node_id!='A'),
            'intervention changed something other than one detached A instruction')
    return (candidate_case,fabric,plans), {
        'sender':'A','instruction_index':2,
        'original_instruction':['CMP',1], 'variant_instruction':['CMP',2],
        'original_program_sha256':snapshot(a.instructions),
        'variant_program_sha256':snapshot(candidate_a.instructions),
        'original_case_sha256':snapshot(case),
        'variant_case_sha256':snapshot(candidate_case),
        'external_events_preserved':True, 'static_fabric_shared_immutable':True,
        'original_nodes_unchanged':True,
    }


def _routes(edges):
    return Counter((e['source_node'],e['target_node'],e['source_channel'],
                    e['target_channel']) for e in edges)


def variant_forward_audit(forward,edges):
    """Verify causal routing of the *variant*, including the legal zero-spike case.

    _index_forward (v1g) deliberately requires a nonempty original trace.
    No delivered spikes is a meaningful counterfactual; validate it separately.
    """
    require(type(forward) is dict and all(type(forward.get(k)) is list
            for k in ('batches','emissions','terminal','occurrences','link_grants')),
            'malformed variant forward evidence')
    require(type(forward.get('states')) is dict and set(forward['states'])=={'A','B','C'},
            'variant native state inventory changed')
    emissions=forward['emissions'];terminals=forward['terminal']
    require(all(type(r) is dict and type(r.get('timestamp')) is int and
                type(r.get('node_id')) is str and type(r.get('channel')) is int
                for r in emissions+terminals),
            'malformed native emission/terminal row')
    def no_outgoing(r):
        return not any(r['node_id']==e['source_node'] and
                       r['channel']==e['source_channel'] for e in edges)
    exp=Counter((r['timestamp'],r['node_id'],r['channel'])
                for r in emissions if no_outgoing(r))
    actual=Counter((r['timestamp'],r['node_id'],r['channel']) for r in terminals)
    require(actual==exp, 'native terminal emission reconciliation failed')
    occ=forward['occurrences']
    require(len(occ)<=256, 'variant occurrence bound')
    if occ:
        _,rows=_index_forward(forward,edges)
    else:
        require(not forward['link_grants'] and
                all(type(b) is dict and b.get('parents')==[] for b in forward['batches']),
                'zero occurrence variant contains grants/causal consumers')
        require(all(type(e) is dict and type(e.get('node_id')) is str and
                type(e.get('channel')) is int and
                not any((e['node_id'],e['channel'])==
                        (r['source_node'],r['source_channel']) for r in edges)
                for e in forward['emissions']),
                'unaccounted routed emission in zero-occurrence branch')
        rows=[]
    return {'occurrences':len(rows),
            'edges':dict(sorted((f'{a}->{b}:{c}->{d}',n) for (a,b,c,d),n in
                     Counter((o['source'],o['target'],o['sender_channel'],
                              o['receiver_channel']) for o in rows).items())),
            'batches':len(forward['batches']),
            'emissions':len(forward['emissions']),
            'terminal':len(forward['terminal']),
            'link_grants':len(forward['link_grants']),
            'states_sha256':snapshot(forward['states'])}


def evaluate(native,v1d,v1g,orig_off,orig_on,modified,variant_off,variant_on,owners):
    """Compare complete native executions without imposing a favorable result."""
    original_hash=snapshot(native)
    require(type(v1g) is dict and v1g.get('schema')==G_SCHEMA and
            v1g.get('status')==G_STATUS and
            v1g.get('native_fixture_sha256')==original_hash and
            v1g.get('original_forward_transport_grants_joined') is True and
            v1g.get('off_route_multiset_equal_on') is True and
            v1g.get('endogenous_receiver_judgments')==0 and
            v1g.get('native_updates_applied')==0,
            'v1g.1 native lineage attestation invalid')
    require(type(owners) is dict and set(owners)=={'A','B','C'},
            'native node ownership drift')
    expected_routes=[_edge(e,owners) for e in native[1].static_routes]
    require(expected_routes==v1g.get('static_routes') and
            _routes(expected_routes)==Counter({('A','B',7,0):1,('B','C',7,0):1}),
            'frozen network route changed')
    require(snapshot(modified[1])==snapshot(native[1]) and
            snapshot(modified[2])==snapshot(native[2]),
            'variant used a different fabric or resource plan')
    original_summary_off=summarize(orig_off,enabled=False,priority='forward-first')
    original_summary_on=summarize(orig_on,enabled=True,priority='forward-first')
    orig_audit=variant_forward_audit(orig_off['forward'],expected_routes)
    on_orig_audit=variant_forward_audit(orig_on['forward'],expected_routes)
    require(orig_audit['occurrences']==v1g['original_off_occurrences'] and
            on_orig_audit['occurrences']==v1g['original_on_occurrences'],
            'v1g original occurrence reference mismatch')
    modified_summary_off=summarize(variant_off,enabled=False,priority='forward-first')
    modified_summary_on=summarize(variant_on,enabled=True,priority='forward-first')
    var_audit_off=variant_forward_audit(variant_off['forward'],expected_routes)
    var_audit_on=variant_forward_audit(variant_on['forward'],expected_routes)
    # This tests the same variant under BV OFF and ON, not "BV caused learning".
    require(variant_off['forward']['batches'] and variant_on['forward']['batches'],
            'variant did not execute any native neuron')
    require(len(variant_off['feedback']['assessments'])==0 and
            len(variant_off['feedback']['deliveries'])==0,
            'BV OFF variant emitted feedback')
    output={
       'original':{'off':orig_audit,'on':on_orig_audit,
                   'off_result_sha256':original_summary_off['whole_result_sha256'],
                   'on_result_sha256':original_summary_on['whole_result_sha256']},
       'variant':{'off':var_audit_off,'on':var_audit_on,
                  'off_result_sha256':modified_summary_off['whole_result_sha256'],
                  'on_result_sha256':modified_summary_on['whole_result_sha256']},
       'off_variant_minus_original':{
            k:var_audit_off[k]-orig_audit[k] for k in
            ('batches','emissions','terminal','occurrences','link_grants')},
       'on_variant_minus_original':{
            k:var_audit_on[k]-on_orig_audit[k] for k in
            ('batches','emissions','terminal','occurrences','link_grants')},
       'variant_off_on_forward_outcomes_equal':(
            variant_off['forward']['states']==variant_on['forward']['states'] and
            Counter((z['node_id'],z['channel']) for z in variant_off['forward']['emissions'])==
            Counter((z['node_id'],z['channel']) for z in variant_on['forward']['emissions']) and
            Counter((z['node_id'],z['channel']) for z in variant_off['forward']['terminal'])==
            Counter((z['node_id'],z['channel']) for z in variant_on['forward']['terminal'])),
       'native_feedback_assessments':{'original_on':len(orig_on['feedback']['assessments']),
                                       'variant_on':len(variant_on['feedback']['assessments'])},
       'native_feedback_deliveries':{'original_on':len(orig_on['feedback']['deliveries']),
                                     'variant_on':len(variant_on['feedback']['deliveries'])},
       'native_scored_receiver_judgments':0,
       'native_updates_applied':0,'native_learning_proven':False,
       'network_utility_identified':False,'experiment_kind':'PRE_EPISODE_COPY_INTERVENTION',
       'conditional_direct_A_to_C':False,
       'real_variant_full_fabric_replay':True,
       'v1e_hypothetical_A_to_C_direct_promoted':False,
    }
    require(snapshot(native)==original_hash,'original fixture mutated during comparison')
    return output


def build(native,v1g,v1g_bytes,v1d,v1d_bytes,orig_off,orig_on,variant_off,
          variant_on,owners,source_hashes):
    require(type(v1g_bytes) is bytes and len(v1g_bytes)>0 and
            type(v1d_bytes) is bytes and len(v1d_bytes)>0,
            'invalid source-bound reference')
    variant,identity=variant_fixture(native,v1d)
    result=evaluate(native,v1d,v1g,orig_off,orig_on,variant,variant_off,
                    variant_on,owners)
    require(v1g.get('frozen_native_sources')==source_hashes and
            v1d.get('frozen_native_sources')==source_hashes,
            'frozen source identity differs from references')
    return {'schema':SCHEMA,'status':STATUS,
        'reference_v1g1_file_sha256':sha256(v1g_bytes).hexdigest(),
        'reference_v1d_file_sha256':sha256(v1d_bytes).hexdigest(),
        'native_fixture_sha256':snapshot(native),
        'frozen_native_sources':source_hashes,
        'intervention':identity,**result,'claims_excluded':EXCLUSIONS}
