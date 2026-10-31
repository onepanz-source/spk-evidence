"""SPK BV v1q: full finite factorial native intervention interactions (research only).

Uses a frozen original A->B->C case and experimenter-created detached program copies.
All output is posthoc producer-side. Contrast of observable counts is not utility,
credit, a receiver-readable judgment, or a neuron-originated update.
"""
from __future__ import annotations

from dataclasses import fields, is_dataclass, replace
from hashlib import sha256
from itertools import combinations

from spk_bv_research.off_on_v0t import require, snapshot
from spk_bv_research.native_causal_locus_v1p import (
    SCHEMA as P_SCHEMA, STATUS as P_STATUS, canon, copy_intervention,
    native_arm, PLAN,
)

SCHEMA='spk-bv-native-exogenous-factorial-interactions/v1q'
STATUS='FROZEN_NATIVE_FULL_FACTORIAL_INTERACTION_NO_ENDOGENOUS_CREDIT'
ARMS=('none','A','B','C','AB','AC','BC','ABC')
NODES=('A','B','C')
EDGES=('A->B:7->0','B->C:7->0')
SINGLE={'none':'sham','A':'A_cmp2','B':'B_cmp2','C':'C_cmp2'}
METRICS=('terminal','A->B:7->0','B->C:7->0','feedback_assessments')
EXCLUDED=[
    'experimenter-imposed-factorial-interventions-not-receiver-driven-operator-choice',
    'finite-network-count-interactions-not-utility-or-causal-credit',
    'interactions-depend-on-fixed-fixture-and-event-distribution',
    'posthoc-producer-traces-not-receiver-accessible-evidence',
    'feedback-counts-not-endogenous-scored-judgments',
    'absence-of-forward-events-not-native-absence-certificate',
    'native-operator-replacement-not-certified-algebra-rewrite',
    'no-authenticated-disclosure-operator-commit-rollback-or-learning',
    'no-hardware-scaling-or-frozen-architecture-promotion',
]


def subsets(bits):
    """All subsets of a nonempty ordered string of distinct A/B/C symbols."""
    require(type(bits) is str and bits and all(c in NODES for c in bits) and
            len(set(bits))==len(bits) and bits==''.join(x for x in NODES if x in bits),
            'invalid factorial node subset')
    return tuple(''.join(x) if x else 'none' for size in range(len(bits)+1)
                 for x in combinations(bits,size))


def factorial_coefficients(values):
    """Boolean-lattice Mobius coefficients: counts only, not credit or value."""
    require(type(values) is dict and set(values)==set(ARMS) and
            all(type(values[k]) is int and values[k]>=0 for k in ARMS),
            'invalid complete nonnegative integer factorial count table')
    out={}
    for arm in ARMS:
        if arm=='none':
            out[arm]=values['none']
            continue
        coeff=0
        for sub in subsets(arm):
            size=0 if sub=='none' else len(sub)
            coeff+=(-1)**(len(arm)-size)*values[sub]
        out[arm]=coeff
    # The zeta sum reproduces each observed value exactly, not merely totals.
    for arm in ARMS:
        parents=('none',) if arm=='none' else subsets(arm)
        require(sum(out[s] for s in parents)==values[arm],
                'factorial inclusion-exclusion failed')
    return out


def clone(native, arm, pins):
    """Detach only the requested native nodes, preserving events/fabric/plans."""
    require(arm in ARMS, 'unknown factorial combination')
    require(type(native) is tuple and len(native)==3,'invalid native case')
    base, fabric, plans=native
    require(is_dataclass(base) and not isinstance(base,type) and
            {'nodes','events'} <= {x.name for x in fields(base)} and
            type(base.nodes) is tuple and len(base.nodes)==3,
            'invalid case object')
    nodes={getattr(n,'node_id',None):n for n in base.nodes}
    require(set(nodes)==set(NODES) and len(nodes)==3 and type(pins) is dict and
            set(pins)==set(NODES) and
            all(snapshot(nodes[n].instructions)==pins[n] for n in NODES),
            'native original instruction pin drift')
    before=snapshot(native)
    changed_nodes=[];mutations={}
    for n in base.nodes:
        id_=n.node_id
        ix=2 if id_=='A' else 1
        require(is_dataclass(n) and not isinstance(n,type) and
                type(n.instructions) is tuple and n.instructions[ix]==('CMP',1),
                'native expected CMP instruction missing')
        if id_ in arm:
            changed_instr=n.instructions[:ix]+(('CMP',2),)+n.instructions[ix+1:]
            changed_nodes.append(replace(n,instructions=changed_instr))
            mutations[id_]={'instruction_index':ix,'before':['CMP',1],
                'after':['CMP',2],'original_program_sha256':pins[id_],
                'modified_program_sha256':snapshot(changed_instr)}
        else:
            changed_nodes.append(n)
    changed=(replace(base,nodes=tuple(changed_nodes)),fabric,plans)
    require(snapshot(native)==before and changed[1] is fabric and
            changed[2] is plans and changed[0].events==base.events and
            snapshot(replace(changed[0],nodes=base.nodes))==snapshot(base) and
            all((a is b)==(a.node_id not in arm)
                for a,b in zip(base.nodes,changed_nodes)) and
            (snapshot(changed)==before)==(arm=='none') and
            all(snapshot(nodes[n].instructions)==pins[n] for n in NODES),
            'non-isolated copy intervention')
    return changed,{'arm':arm,'changed_nodes':list(arm) if arm!='none' else [],
                    'mutations':mutations,'case_sha256':snapshot(changed[0])}


def validate_predecessor(p,raw):
    require(type(p) is dict and type(raw) is bytes and raw==canon(p) and
            p.get('schema')==P_SCHEMA and p.get('status')==P_STATUS and
            p.get('source_kind')=='NATIVE_FROZEN_SCHEDULER_EXOGENOUS_INTERVENTION_MATRIX',
            'v1p canonical source or status mismatch')
    require(p.get('native_v1o_recomputation_verified_in_this_run') is True and
            p.get('native_matrix_repeatability_attested_in_this_run') is True and
            p.get('native_scheduler_executions_in_this_matrix')==8 and
            p.get('causal_prefix_negative_controls_pass') is True and
            p.get('original_and_A_variant_replayed_against_v1h') is True and
            p.get('intervention_selector')=='EXPERIMENTER_PRE_EPISODE_COPY' and
            p.get('native_absence_witnesses')==0 and
            p.get('native_scored_receiver_judgments')==0 and
            p.get('native_operator_updates')==0 and
            p.get('native_learning_proven') is False and
            p.get('native_receiver_decision_disclosure') is False and
            p.get('network_utility_identified') is False,
            'v1p unauthorized provenance or learning claim')
    fixture_pin=p.get('native_fixture_sha256')
    frozen_sources=p.get('frozen_native_sources')
    require(type(fixture_pin) is str and len(fixture_pin)==64 and
            all(c in '0123456789abcdef' for c in fixture_pin) and
            type(frozen_sources) is dict and bool(frozen_sources) and
            all(type(k) is str and k for k in frozen_sources) and
            set(p.get('experiment_arms',{}))==set(SINGLE.values()) and
            set(p.get('intervention_runs',{}))==set(SINGLE.values()) and
            all(type(p['intervention_runs'][key]) is dict and
                set(p['intervention_runs'][key])=={'off','on'}
                for key in SINGLE.values()),
            'v1p matrix inventory missing')
    require(p['intervention_runs']['sham']['off']['forward']['terminal']==2 and
            p['intervention_runs']['A_cmp2']['off']['forward']['terminal']==0 and
            p['intervention_runs']['B_cmp2']['off']['forward']['terminal']==1 and
            p['intervention_runs']['C_cmp2']['off']['forward']['terminal']==1,
            'v1p native singleton terminal controls drift')
    return True


def _counts(r):
    return {
        'terminal':r['forward']['terminal'],
        'A->B:7->0':r['edges']['A->B:7->0'],
        'B->C:7->0':r['edges']['B->C:7->0'],
        'feedback_assessments':r['feedback_assessments'],
    }


def analyze(p,raw,native,owners,sources,runs):
    """Pure validation of supplied run results. Only CLI can attest re-execution."""
    validate_predecessor(p,raw)
    require(type(native) is tuple and len(native)==3 and
            snapshot(native)==p['native_fixture_sha256'] and
            sources==p['frozen_native_sources'] and
            type(owners) is dict and set(owners)==set(NODES),
            'frozen fixture or native source mismatch')
    require(type(runs) is dict and set(runs)==set(ARMS) and
            all(type(x) is dict and set(x)=={'off','on'} for x in runs.values()),
            'incomplete factorial matrix')
    from spk_bv_research.native_route_lineage_v1g import _edge
    from spk_bv_research.native_passive_trace_projection_v1m import ROUTES
    edges=[_edge(r,owners) for r in native[1].static_routes]
    require([(e['source_node'],e['target_node'],e['source_channel'],e['target_channel'])
            for e in edges]==list(ROUTES),'native topology drift')
    pins={n.node_id:snapshot(n.instructions) for n in native[0].nodes}
    require(set(pins)==set(NODES) and
            pins=={n:p['experiment_arms'][n+'_cmp2']['original_program_sha256'] for n in NODES},
            'native program pins differ from v1p')
    initial=snapshot(native);rec={};details={}
    for arm in ARMS:
        cloned,details[arm]=clone(native,arm,pins)
        require(snapshot(native)==initial,'original fixture mutated before replay analysis')
        rec[arm]={}
        for mode in ('off','on'):
            run=runs[arm][mode]
            require(type(run) is dict and run.get('enabled') is (mode=='on') and
                    run.get('policy')=='forward-first', 'invalid enabled/policy')
            rec[arm][mode]=native_arm(run,edges)
        require(snapshot(native)==initial and
                (snapshot(cloned)==initial)==(arm=='none'),
                'native program changed by experiment')
        if arm in SINGLE:
            require(details[arm]['case_sha256']==p['experiment_arms'][SINGLE[arm]]['case_sha256']
                    and all(rec[arm][mode]==p['intervention_runs'][SINGLE[arm]][mode]
                            for mode in ('off','on')),
                    'factorial baseline/singleton does not reproduce v1p native result')
    # Directional prefix invariance in this feed-forward fixture. Comparisons
    # differ by one downstream intervention; no assumption of monotone behavior.
    prefix_checks=0
    for arm in ARMS:
        if 'B' not in arm:
            counterpart=''.join(n for n in NODES if n in arm+'B')
            for mode in ('off','on'):
                a=rec[arm][mode];b=rec[counterpart][mode]
                require(a['emissions_by_neuron']['A']==b['emissions_by_neuron']['A'] and
                        a['edges'][EDGES[0]]==b['edges'][EDGES[0]],
                        'B intervention contaminated upstream A')
                prefix_checks+=1
        if 'C' not in arm:
            counterpart=''.join(n for n in NODES if n in arm+'C')
            for mode in ('off','on'):
                a=rec[arm][mode];b=rec[counterpart][mode]
                require(all(a['emissions_by_neuron'][n]==b['emissions_by_neuron'][n]
                            for n in ('A','B')) and
                        all(a['edges'][e]==b['edges'][e] for e in EDGES),
                        'C intervention contaminated upstream A/B')
                prefix_checks+=1
    require(prefix_checks==16,'factorial prefix coverage incomplete')
    for arm in ARMS:
        require(rec[arm]['off']['forward']==rec[arm]['on']['forward'] and
                rec[arm]['off']['emissions_by_neuron']==rec[arm]['on']['emissions_by_neuron'] and
                rec[arm]['off']['edges']==rec[arm]['on']['edges'] and
                rec[arm]['off']['feedback_assessments']==0 and
                rec[arm]['off']['feedback_deliveries']==0,
                'OFF/ON forward drift or OFF feedback present')
    tables={};coefs={}
    for mode in ('off','on'):
        tables[mode]={};coefs[mode]={}
        for metric in METRICS:
            counts={arm:_counts(rec[arm][mode])[metric] for arm in ARMS}
            require(all(type(c) is int and c>=0 for c in counts.values()),
                    'negative or noninteger event count')
            tables[mode][metric]=counts
            coefs[mode][metric]=factorial_coefficients(counts)
    require(all(tables['off'][m]==tables['on'][m]
                for m in METRICS if m!='feedback_assessments'),
            'OFF/ON changed count of native forward events')
    require(any(coefs['off']['terminal'][arm]!=0 for arm in ('AB','AC','BC','ABC')),
            'fixture no longer demonstrates a terminal count interaction')
    return {
        'schema':SCHEMA,'status':STATUS,
        'source_kind':'FROZEN_NATIVE_SCHEDULER_EXOGENOUS_FULL_FACTORIAL',
        'reference_v1p_sha256':sha256(raw).hexdigest(),
        'native_fixture_sha256':initial,'frozen_native_sources':sources,
        'interventions':details,'factorial_runs':rec,
        'native_scheduler_executions_in_matrix':16,
        'native_v1p_recomputation_verified_in_this_run':False,
        'native_factorial_repeatability_attested_in_this_run':False,
        'factorial_observed_counts':tables,
        'factorial_mobius_count_coefficients':coefs,
        'factorial_prefix_negative_control_pairs_verified':prefix_checks,
        'event_count_interaction_present':True,
        'native_receiver_exposed_to_full_matrix':False,
        'native_independent_absence_certificates':0,
        'native_scored_receiver_judgments':0,
        'native_operator_updates':0,'native_learning_proven':False,
        'network_utility_identified':False,
        'interaction_coefficients_are_utility_or_credit':False,
        'claims_excluded':EXCLUDED,
    }
