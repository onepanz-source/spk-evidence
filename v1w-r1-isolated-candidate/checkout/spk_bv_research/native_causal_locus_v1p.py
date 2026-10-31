"""BV v1p: exogenous native operator intervention loci, not endogenous credit.

Read-only research extension. Three isolated program replacements (one at a time)
and a sham on the frozen A->B->C fixture. No intervention selected by feedback.
No recipient obtains simulator-side trace data; no utility or learning claim.
"""
from __future__ import annotations
from dataclasses import fields, is_dataclass, replace
from hashlib import sha256
import json
from collections import Counter

from spk_bv_research.off_on_v0t import require, snapshot, summarize
from spk_bv_research.native_network_counterfactual_v1h import variant_forward_audit
from spk_bv_research.native_passive_trace_projection_v1m import _extract, ROUTES
from spk_bv_research.decision_disclosure_boundary_v1o import SCHEMA as O_SCHEMA, STATUS as O_STATUS
from spk_bv_research.native_network_counterfactual_v1h import SCHEMA as H_SCHEMA, STATUS as H_STATUS
from spk_bv_research.native_passive_trace_projection_v1m import SCHEMA as M_SCHEMA, STATUS as M_STATUS

SCHEMA='spk-bv-exogenous-native-causal-locus-audit/v1p'
STATUS='SOURCE_BOUND_NATIVE_EXOGENOUS_LOCUS_CONTRAST_NO_RECEIVER_CREDIT'
PLAN=(('sham','A',2,('CMP',1)),('A_cmp2','A',2,('CMP',2)),
      ('B_cmp2','B',1,('CMP',2)),('C_cmp2','C',1,('CMP',2)))
CLAIMS_EXCLUDED=[
 'interventions-experimenter-imposed-not-feedback-selected',
 'native-local-operator-change-not-certified-algebra-rewrite',
 'single-fixed-A-B-C-fixture-no-independent-generalization',
 'posthoc-scheduler-causal-contrast-not-receiver-readable-evidence',
 'upstream-prefix-invariance-not-utility-or-endogenous-judgment',
 'no-receiver-scored-feedback-no-decision-authentication',
 'no-neuron-update-commit-rollback-or-learning',
 'no-hardware-distribution-or-frozen-architecture-promotion',
]


def canon(doc):
    return (json.dumps(doc,sort_keys=True,indent=2,ensure_ascii=True,allow_nan=False)+'\n').encode()


def bounded_sources(o,ob,h,hb,m,mb,d,db):
    """Reject report/pin drift before attributing an interventional contrast."""
    for name,doc,raw,schema,status in (
        ('v1o',o,ob,O_SCHEMA,O_STATUS),('v1h',h,hb,H_SCHEMA,H_STATUS),
        ('v1m',m,mb,M_SCHEMA,M_STATUS)):
        require(type(doc) is dict and type(raw) is bytes and raw==canon(doc)
                and doc.get('schema')==schema and doc.get('status')==status,
                'invalid canonical reference '+name)
    require(type(d) is dict and type(db) is bytes and db==canon(d),
            'invalid native operator criterion')
    require(o.get('native_v1n_recomputation_verified_in_this_run') is True and
            o.get('native_scheduler_arms_inherited')==4 and
            o.get('reference_v1m_sha256')==sha256(mb).hexdigest() and
            h.get('reference_v1d_file_sha256')==sha256(db).hexdigest() and
            m.get('reference_v1d_sha256')==sha256(db).hexdigest() and
            m.get('reference_v1h_sha256')==sha256(hb).hexdigest() and
            m.get('full_native_scheduler_runs_recomputed_in_this_run')==4 and
            h.get('real_variant_full_fabric_replay') is True and
            o.get('native_fixture_sha256')==h.get('native_fixture_sha256')==m.get('native_fixture_sha256') and
            o.get('frozen_native_sources')==h.get('frozen_native_sources')==m.get('frozen_native_sources'),
            'source bound native chain mismatch')
    require(o.get('native_original_A_to_B')=={'sender_emissions':2,'receiver_ingress':2} and
            o.get('native_variant_A_to_B')=={'sender_emissions':0,'receiver_ingress':0} and
            o.get('native_authenticated_decision_records')==0 and
            o.get('native_receiver_judgments')==0 and
            o.get('native_sender_operator_updates')==0 and
            o.get('native_learning_proven') is False and
            h.get('native_updates_applied')==0 and h.get('native_learning_proven') is False and
            m.get('sender_operator_updates')==0 and m.get('recipient_access_to_sender_trace_demonstrated') is False,
            'unsupported native authority promotion')
    require(d.get('selected_candidate_position')==2 and
            d.get('selected_was_training_improvement') is True and
            d.get('native_updates_applied')==0 and d.get('native_judgments_observed')==0,
            'selected synthetic candidate drift')
    return True


def copy_intervention(native, locus, program_pins):
    """Construct only a detached node instruction copy, never mutate native input."""
    require(type(native) is tuple and len(native)==3,'invalid frozen fixture')
    case,fabric,plans=native
    require(is_dataclass(case) and not isinstance(case,type) and
            {'nodes','events'} <= {x.name for x in fields(case)} and
            type(case.nodes) is tuple and len(case.nodes)==3,'non-native case')
    require(locus in (x[0] for x in PLAN),'unknown experiment arm')
    arm,node_id,index,new_instruction=next(x for x in PLAN if x[0]==locus)
    nodes={getattr(x,'node_id',None):x for x in case.nodes}
    require(set(nodes)=={'A','B','C'} and len(nodes)==3,'unexpected neuron inventory')
    node=nodes[node_id]
    require(is_dataclass(node) and not isinstance(node,type) and
            type(node.instructions) is tuple and
            type(node.instructions[index]) is tuple and
            node.instructions[index]==('CMP',1) and
            type(program_pins) is dict and set(program_pins)=={'A','B','C'} and
            all(snapshot(nodes[n].instructions)==program_pins[n] for n in nodes),
            'native program pin or instruction mismatch')
    original_hash=snapshot(native)
    changed_program=node.instructions[:index]+(new_instruction,)+node.instructions[index+1:]
    replacement=replace(node,instructions=changed_program)
    new_nodes=tuple(replacement if x.node_id==node_id else x for x in case.nodes)
    changed=(replace(case,nodes=new_nodes),fabric,plans)
    require(snapshot(native)==original_hash and
            changed[0].events==case.events and changed[1] is fabric and changed[2] is plans and
            snapshot(replace(changed[0],nodes=case.nodes))==snapshot(case) and
            all(x is y for x,y in zip(case.nodes,new_nodes) if x.node_id!=node_id) and
            (snapshot(changed)==original_hash)==(arm=='sham'),
            'intervention was not isolated')
    return changed,{'arm':arm,'node':node_id,'instruction_index':index,
                    'before':['CMP',1],'after':list(new_instruction),
                    'original_program_sha256':program_pins[node_id],
                    'modified_program_sha256':snapshot(changed_program),
                    'case_sha256':snapshot(changed[0]),
                    'sham':arm=='sham'}


def native_arm(run, native_edges):
    """Reconcile every produced spike with delivery, consumption and route."""
    require(type(run) is dict and run.get('policy')=='forward-first' and
            type(run.get('forward')) is dict,'invalid native run contract')
    audit,rows,occ=_extract(run['forward'],native_edges)
    counts={r['edge']:r['sender_trace_emission_count'] for r in rows}
    require(set(counts)=={'A->B:7->0','B->C:7->0'},'edge drift')
    emissions=run['forward']['emissions']
    by_neuron=Counter(x['node_id'] for x in emissions)
    require(set(by_neuron) <= {'A','B','C'} and
            sum(by_neuron.values())==audit['emissions'], 'emission inventory drift')
    return {'forward':audit,
            'edges':counts,
            'emissions_by_neuron':{k:by_neuron[k] for k in ('A','B','C')},
            'native_result_sha256':summarize(run,enabled=run['enabled'],
                                            priority='forward-first')['whole_result_sha256'],
            'feedback_assessments':len(run['feedback']['assessments']),
            'feedback_deliveries':len(run['feedback']['deliveries'])}


def analyze(o,ob,h,hb,m,mb,d,db,native,owners,source_hashes,runs):
    """Only calls executed by native producer are labelled native (CLI enforces)."""
    bounded_sources(o,ob,h,hb,m,mb,d,db)
    require(type(native) is tuple and len(native)==3 and
            snapshot(native)==o['native_fixture_sha256'] and
            type(source_hashes) is dict and source_hashes==o['frozen_native_sources'] and
            type(owners) is dict and set(owners)=={'A','B','C'},
            'invalid native fixture or frozen provenance')
    require(type(runs) is dict and set(runs)=={x[0] for x in PLAN} and
            all(type(x) is dict and set(x)=={'off','on'} for x in runs.values()),
            'incomplete intervention matrix')
    from spk_bv_research.native_route_lineage_v1g import _edge
    edges=[_edge(e,owners) for e in native[1].static_routes]
    require([(e['source_node'],e['target_node'],e['source_channel'],e['target_channel'])
            for e in edges]==list(ROUTES),'native route topology drift')
    programs={n.node_id:snapshot(n.instructions) for n in native[0].nodes}
    require(set(programs)=={'A','B','C'},'program identity drift')
    require(programs['A']==h['intervention']['original_program_sha256'] and
            programs['A']==d['training'][2]['original_program_sha256'] and
            programs['B']==d['training'][3]['original_program_sha256'] and
            programs['C']==d['training'][4]['original_program_sha256'],
            'source-bound instruction pins mismatch')
    before=snapshot(native);byarm={};details={}
    for arm,_,_,_ in PLAN:
        clone,info=copy_intervention(native,arm,programs)
        details[arm]=info
        byarm[arm]={}
        for mode in ('off','on'):
            run=runs[arm][mode]
            require(type(run) is dict and run.get('enabled') is (mode=='on') and
                    run.get('policy')=='forward-first','invalid BV arm')
            byarm[arm][mode]=native_arm(run,edges)
        require(snapshot(native)==before,'native original fixture changed during comparison')
    require(details['A_cmp2']['modified_program_sha256']==h['intervention']['variant_program_sha256'],
            'A branch program not the established v1h variant')
    for mode in ('off','on'):
        sham=byarm['sham'][mode]; a=byarm['A_cmp2'][mode]
        original=h['original'][mode];variant=h['variant'][mode]
        require(sham['forward']==original and a['forward']==variant and
                sham['native_result_sha256']==h['original'][mode+'_result_sha256'] and
                a['native_result_sha256']==h['variant'][mode+'_result_sha256'],
                'native reference or sham drift')
        require(sham['edges']=={'A->B:7->0':2,'B->C:7->0':2} and
                a['edges']=={'A->B:7->0':0,'B->C:7->0':0},
                'A intervention causal transport contrast lost')
        # Negative controls on upstream paths in the static feed-forward fabric.
        for other in ('B_cmp2','C_cmp2'):
            require(byarm[other][mode]['emissions_by_neuron']['A']==sham['emissions_by_neuron']['A'] and
                    byarm[other][mode]['edges']['A->B:7->0']==sham['edges']['A->B:7->0'],
                    'downstream intervention altered upstream A->B prefix')
        require(byarm['C_cmp2'][mode]['emissions_by_neuron']['B']==sham['emissions_by_neuron']['B'] and
                byarm['C_cmp2'][mode]['edges']['B->C:7->0']==sham['edges']['B->C:7->0'],
                'C intervention altered upstream B->C prefix')
    require(all(byarm[arm]['off']['forward']==byarm[arm]['on']['forward']
                for arm in byarm),
            'forward path depends on enabled feedback despite no operator update')
    require(all(byarm[arm]['off']['feedback_assessments']==0 and
                byarm[arm]['off']['feedback_deliveries']==0 for arm in byarm),
            'BV OFF unexpectedly generated feedback')
    comparisons=[]
    for arm in ('A_cmp2','B_cmp2','C_cmp2'):
        baseline=byarm['sham']['off'];r=byarm[arm]['off']
        comparisons.append({'arm':arm,'changed_neuron':details[arm]['node'],
          'delta_emissions_by_neuron':{n:r['emissions_by_neuron'][n]-baseline['emissions_by_neuron'][n]
                                        for n in ('A','B','C')},
          'delta_edge_occurrences':{e:r['edges'][e]-baseline['edges'][e]
                                    for e in ('A->B:7->0','B->C:7->0')},
          'delta_terminal_emissions':r['forward']['terminal']-baseline['forward']['terminal'],
          'causal_scope':'EXOGENOUS_PAIRWISE_NATIVE_INTERVENTION_ONLY',
          'utility_or_credit_inferred':False})
    return {'schema':SCHEMA,'status':STATUS,
        'source_kind':'NATIVE_FROZEN_SCHEDULER_EXOGENOUS_INTERVENTION_MATRIX',
        'reference_v1o_sha256':sha256(ob).hexdigest(),
        'reference_v1h_sha256':sha256(hb).hexdigest(),
        'reference_v1m_sha256':sha256(mb).hexdigest(),
        'reference_v1d_sha256':sha256(db).hexdigest(),
        'native_fixture_sha256':before,'frozen_native_sources':source_hashes,
        'experiment_arms':details,'intervention_runs':byarm,
        'paired_contrasts_off':comparisons,
        'native_scheduler_executions_in_this_matrix':8,
        'native_v1o_recomputation_verified_in_this_run':False,
        'native_matrix_repeatability_attested_in_this_run':False,
        'original_and_A_variant_replayed_against_v1h':True,
        'causal_prefix_negative_controls_pass':True,
        'intervention_selector':'EXPERIMENTER_PRE_EPISODE_COPY',
        'native_receiver_decision_disclosure':False,
        'native_absence_witnesses':0,'native_scored_receiver_judgments':0,
        'native_operator_updates':0,'native_learning_proven':False,
        'network_utility_identified':False,
        'claims_excluded':CLAIMS_EXCLUDED}
