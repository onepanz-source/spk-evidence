"""BV v1r: exact rational accounting of exogenous factorial count effects.

Posthoc producer-side diagnostic, not a native value signal, receiver judgment,
credit assignment, or learning mechanism. No frozen SPK code is changed.
"""
from __future__ import annotations

from fractions import Fraction
from hashlib import sha256
from itertools import permutations

from spk_bv_research.off_on_v0t import require
from spk_bv_research.native_factorial_interaction_v1q import (
    ARMS, METRICS, SCHEMA as Q_SCHEMA, STATUS as Q_STATUS,
    canon, factorial_coefficients,
)

SCHEMA='spk-bv-posthoc-factorial-allocation-nonidentifiability/v1r'
STATUS='EXACT_COUNT_ACCOUNTING_NO_RECEIVER_CREDIT'
NODES=('A','B','C')
MODES=('off','on')
POLICIES={'preserve_activity':1,'suppress_activity':-1}
SOURCE='SOURCE_BOUND_NATIVE_FACTORIAL_POSTHOC_ONLY'
EXCLUDED=[
    'count-allocation-not-utility-credit-or-learning',
    'coalition-order-marginals-not-native-sequential-updates',
    'arithmetic-allocation-requires-complete-producer-side-16-arm-matrix',
    'no-native-receiver-access-to-counterfactuals',
    'policy-polarity-changes-sign-without-changing-any-native-event',
    'no-independent-utility-or-criterion-of-neuron-destination',
    'native-assessments-are-lineage-not-scored-feedback',
    'no-independent-absence-witness-decision-disclosure-or-causal-credit',
    'no-operator-commit-rollback-learning-or-frozen-architecture-promotion',
]


def code(frac):
    require(type(frac) is Fraction,'fraction required')
    return str(frac.numerator) if frac.denominator==1 else f'{frac.numerator}/{frac.denominator}'


def arm_of(nodes):
    require(type(nodes) is tuple and len(set(nodes))==len(nodes) and
            set(nodes)<=set(NODES),'invalid coalition')
    out=''.join(n for n in NODES if n in nodes)
    return out or 'none'


def allocate(values, polarity):
    """Six ordering marginals; arithmetic mean is one declared convention."""
    require(type(values) is dict and set(values)==set(ARMS) and
            all(type(values[x]) is int and values[x]>=0 for x in ARMS) and
            type(polarity) is int and polarity in (-1,1),'invalid allocation inputs')
    paths={}; totals={n:Fraction(0) for n in NODES}
    for order in permutations(NODES):
        active=();partials={}
        for node in order:
            before=arm_of(active)
            active=(*active,node)
            after=arm_of(active)
            delta=Fraction(polarity*(values[after]-values[before]))
            partials[node]=delta
            totals[node]+=delta
        require(sum(partials.values(),Fraction(0))==
                Fraction(polarity*(values['ABC']-values['none'])),
                'ordering telescoping identity violated')
        paths[''.join(order)]={n:code(partials[n]) for n in NODES}
    mean={n:totals[n]/6 for n in NODES}
    delta=Fraction(polarity*(values['ABC']-values['none']))
    require(sum(mean.values(),Fraction(0))==delta,'averaged allocation not conserved')
    variation={n:len({paths[p][n] for p in paths})>1 for n in NODES}
    return {
        'full_coalition_delta':code(delta),
        'order_marginals':paths,
        'equal_permutation_average':{n:code(mean[n]) for n in NODES},
        'order_sensitive':variation,
        'any_order_sensitive':any(variation.values()),
        'equal_permutation_average_is_a_convention_not_credit':True,
    }


def validate_q(q,raw):
    """Validate native v1q custody marker and all auditable numeric identities.

    CLI additionally reproduces full v1q bytes using frozen runtime before calling.
    """
    require(type(q) is dict and type(raw) is bytes and raw==canon(q) and
            q.get('schema')==Q_SCHEMA and q.get('status')==Q_STATUS and
            q.get('source_kind')=='FROZEN_NATIVE_SCHEDULER_EXOGENOUS_FULL_FACTORIAL' and
            q.get('native_v1p_recomputation_verified_in_this_run') is True and
            q.get('native_factorial_repeatability_attested_in_this_run') is True and
            q.get('native_scheduler_executions_in_matrix')==16 and
            q.get('factorial_prefix_negative_control_pairs_verified')==16 and
            q.get('event_count_interaction_present') is True and
            q.get('native_receiver_exposed_to_full_matrix') is False and
            q.get('native_independent_absence_certificates')==0 and
            q.get('native_scored_receiver_judgments')==0 and
            q.get('native_operator_updates')==0 and
            q.get('native_learning_proven') is False and
            q.get('network_utility_identified') is False and
            q.get('interaction_coefficients_are_utility_or_credit') is False,
            'unauthorized v1q source, status or authority')
    require(type(q.get('native_fixture_sha256')) is str and
            len(q['native_fixture_sha256'])==64 and
            all(c in '0123456789abcdef' for c in q['native_fixture_sha256']) and
            type(q.get('frozen_native_sources')) is dict and
            bool(q['frozen_native_sources']) and
            type(q.get('reference_v1p_sha256')) is str and
            len(q['reference_v1p_sha256'])==64,
            'invalid frozen source or upstream pin')
    tables=q.get('factorial_observed_counts');coefs=q.get('factorial_mobius_count_coefficients')
    runs=q.get('factorial_runs'); interventions=q.get('interventions')
    require(type(tables) is dict and set(tables)==set(MODES) and
            type(coefs) is dict and set(coefs)==set(MODES) and
            type(runs) is dict and set(runs)==set(ARMS) and
            type(interventions) is dict and set(interventions)==set(ARMS),
            'incomplete factorial inventory')
    for arm in ARMS:
        expected=[] if arm=='none' else list(arm)
        intervention=interventions[arm]
        require(type(intervention) is dict and
                intervention.get('arm')==arm and
                intervention.get('changed_nodes')==expected and
                type(intervention.get('mutations')) is dict and
                set(intervention['mutations'])==set(expected),
                'factorial intervention scope mismatch')
        r=runs[arm]
        require(type(r) is dict and set(r)==set(MODES),'invalid factorial run modes')
        for mode in MODES:
            result=r[mode]
            require(type(result) is dict and type(result.get('forward')) is dict and
                    type(result.get('edges')) is dict and
                    type(result.get('emissions_by_neuron')) is dict and
                    set(result['emissions_by_neuron'])==set(NODES) and
                    type(result.get('feedback_assessments')) is int and
                    type(result.get('feedback_deliveries')) is int,
                    'invalid native factorial run record')
            f=result['forward'];e=result['edges'];em=result['emissions_by_neuron']
            require(all(type(em[n]) is int and em[n]>=0 for n in NODES) and
                    all(type(f.get(k)) is int and f[k]>=0 for k in
                        ('batches','emissions','occurrences','link_grants','terminal')) and
                    set(e)=={'A->B:7->0','B->C:7->0'} and
                    all(type(v) is int and v>=0 for v in e.values()) and
                    f['emissions']==sum(em.values()) and
                    f['terminal']==em['C'] and
                    e['A->B:7->0']==em['A'] and
                    e['B->C:7->0']==em['B'] and
                    f['occurrences']==sum(e.values()) and
                    f['link_grants']==f['occurrences'] and
                    result['feedback_assessments']==(f['terminal'] if mode=='on' else 0) and
                    result['feedback_deliveries']==2*result['feedback_assessments'],
                    'native count conservation/feedback lineage mismatch')
    for mode in MODES:
        require(type(tables[mode]) is dict and set(tables[mode])==set(METRICS) and
                type(coefs[mode]) is dict and set(coefs[mode])==set(METRICS),
                'incomplete metric tables')
        for metric in METRICS:
            counts=tables[mode][metric]
            require(type(counts) is dict and set(counts)==set(ARMS) and
                    all(type(v) is int and v>=0 for v in counts.values()),
                    'invalid factorial count cell')
            for arm in ARMS:
                r=runs[arm][mode]
                observed=(r['forward']['terminal'] if metric=='terminal' else
                          r['feedback_assessments'] if metric=='feedback_assessments' else
                          r['edges'][metric])
                require(counts[arm]==observed,'count table not native-run derived')
            require(coefs[mode][metric]==factorial_coefficients(counts),
                    'Mobius coefficients tampered or invalid')
    for metric in METRICS:
        if metric!='feedback_assessments':
            require(tables['off'][metric]==tables['on'][metric],
                    'feedback mode modifies native forward readout')
    require(tables['off']['feedback_assessments']=={a:0 for a in ARMS},
            'OFF mode feedback present')
    require(tables['on']['feedback_assessments']==tables['on']['terminal'],
            'feedback lineage inconsistent with terminal trace')
    return True


def analyze(q,raw):
    """Pure posthoc descriptive accounting; never attests a new native replay."""
    validate_q(q,raw)
    count_tables=q['factorial_observed_counts'];mob=q['factorial_mobius_count_coefficients']
    allocations={};diagnostics={};order_variability=False
    for mode in MODES:
        allocations[mode]={};diagnostics[mode]={}
        for metric in METRICS:
            values=count_tables[mode][metric]
            up={policy:allocate(values,polarity) for policy,polarity in POLICIES.items()}
            for n in NODES:
                require(Fraction(up['preserve_activity']['equal_permutation_average'][n])==
                        -Fraction(up['suppress_activity']['equal_permutation_average'][n]),
                        'declared scoring polarity not inverted')
            if any(a['any_order_sensitive'] for a in up.values()):order_variability=True
            allocations[mode][metric]=up
            single_delta=sum(values[n]-values['none'] for n in NODES)
            observed_delta=values['ABC']-values['none']
            interactions=sum(mob[mode][metric][arm] for arm in ('AB','AC','BC','ABC'))
            require(single_delta+interactions==observed_delta,
                    'singletons and interaction coefficients do not reconcile')
            diagnostics[mode][metric]={
                'baseline':values['none'],
                'full_coalition':values['ABC'],
                'sum_of_isolated_deltas':single_delta,
                'observed_full_delta':observed_delta,
                'nonadditive_correction':interactions,
                'nonzero_interaction_terms':{
                    a:mob[mode][metric][a] for a in ('AB','AC','BC','ABC')
                    if mob[mode][metric][a]!=0},
            }
    require(order_variability,'fixture no longer demonstrates ordering ambiguity')
    return {
        'schema':SCHEMA,'status':STATUS,'source_kind':SOURCE,
        'reference_v1q_sha256':sha256(raw).hexdigest(),
        'native_fixture_sha256':q['native_fixture_sha256'],
        'frozen_native_sources':q['frozen_native_sources'],
        'factored_native_matrix_runs_in_source':16,
        'posthoc_rational_allocation':allocations,
        'nonadditivity_diagnostics':diagnostics,
        'allocation_order_variability_present':order_variability,
        'native_v1q_recomputation_verified_in_this_run':False,
        'new_native_scheduler_runs_in_this_module':0,
        'receiver_exposed_to_allocation':False,
        'native_scored_receiver_judgments':0,
        'native_operator_updates':0,
        'native_learning_proven':False,
        'causal_credit_or_utility_identified':False,
        'claims_excluded':EXCLUDED,
    }
