"""BV v1f: non-endogenous receiver preference polarity, bounded by v1e.

Policies are declared by the experimenter, NOT learned or voted by B/C.
The source of each conditional observation is the same upstream A branch.
Opposite policy polarities on identical native local readouts illustrate that
receiver sensitivity alone cannot identify the utility sign of a change.
"""
from __future__ import annotations
from hashlib import sha256
from spk_bv_research.off_on_v0t import InterventionError, require
from spk_bv_research.receiver_impact_v1e import SCHEMA as E_SCHEMA, STATUS as E_STATUS, ingress

SCHEMA='spk-bv-conditional-receiver-preference-polarity/v1f'
STATUS='SOURCE_BOUND_SHADOW_PREFERENCE_POLARITY_NO_ENDOGENOUS_JUDGMENT'
POLICIES=('maximize_receiver_emission_count','minimize_receiver_emission_count')
EXPECTED_EVAL=(3,4,5)
EXPECTED_RECEIVERS=('B','C')
EXCLUSIONS=[
    'receiver-emission-count-is-experimenter-declared-preference-not-utility-truth',
    'preference-signs-derived-counterfactually-not-generated-by-neurons',
    'B-and-C-records-share-the-same-declared-sender-branch-per-case',
    'no-independent-causal-votes-proven',
    'declared-channel-7-to-0-mapping-is-not-route-attested',
    'no-native-feedback-judgments-or-delivered-feedback-packets',
    'no-operator-commit-rollback-or-learning',
    'no-end-to-end-scheduler-intervention-or-network-utility',
    'not-certified-algebra-rewrite-not-independent-heldout',
    'no-hardware-performance-or-architecture-promotion',
]

def _sha(v):
    require(type(v) is str and len(v)==64 and all(c in '0123456789abcdef' for c in v),
            'invalid SHA-256')
    return v

def _readout(data):
    require(type(data) is dict and set(data)=={'emitted_channels','guard','post_raw','result_sha256'},
            'invalid native receiver readout fields')
    require(type(data['guard']) is bool and type(data['post_raw']) is int,
            'invalid native receiver guard/state')
    emitted=data['emitted_channels']
    require(type(emitted) is list and emitted in ([],[7]), 'unsupported native recipient emission')
    _sha(data['result_sha256'])
    return data

def _record(e, rid, idx):
    require(type(e) is dict, 'invalid receiver pair')
    require(e.get('sender_id')=='A' and e.get('receiver_id')==rid and
            type(e.get('evaluation_domain_index')) is int and
            e['evaluation_domain_index']==idx, 'reordered or altered receiver source')
    before=_readout(e.get('original_receiver_readout'))
    after=_readout(e.get('variant_receiver_readout'))
    sender_orig=e.get('sender_original_emitted_channels')
    sender_variant=e.get('sender_variant_emitted_channels')
    require(type(sender_orig) is list and type(sender_variant) is list,
            'sender emission representation invalid')
    require(e.get('declared_original_ingress')==list(ingress(sender_orig)) and
            e.get('declared_variant_ingress')==list(ingress(sender_variant)),
            'shadow channel mapping mismatch')
    diff=before!=after
    require(type(e.get('receiver_output_changed')) is bool and
            e['receiver_output_changed']==diff and
            type(e.get('receiver_guard_changed')) is bool and
            e['receiver_guard_changed']==(before['guard']!=after['guard']) and
            type(e.get('receiver_emission_changed')) is bool and
            e['receiver_emission_changed']==(before['emitted_channels']!=after['emitted_channels']) and
            e.get('classification')==('DIFFERENT' if diff else 'SAME'),
            'recipient readout classification inconsistent')
    return before,after

def analyze(e):
    """Validate and contrast two explicitly *hypothetical* preference policies.

    The CLI recomputes v1e from the frozen native kernel before invoking this.
    Direct use on a caller-supplied dict only validates the declared structure.
    """
    require(type(e) is dict and e.get('schema')==E_SCHEMA and e.get('status')==E_STATUS,
            'unexpected v1e experiment')
    flags={'native_receiver_kernels_executed':True,
           'frozen_original_nodes_immutable':True,
           'native_judgments_observed':0,'native_updates_applied':0,
           'native_learning_proven':False,'causal_credit_identified':False,
           'network_event_lineage_attested':False}
    require(all(type(e.get(k)) is type(v) and e.get(k)==v for k,v in flags.items()),
            'v1e safety boundary changed')
    mapping=e.get('hypothetical_mapping')
    require(type(mapping) is dict and mapping.get('sender')=='A' and
            type(mapping.get('sender_channel')) is int and mapping['sender_channel']==7 and
            type(mapping.get('receiver_channel')) is int and mapping['receiver_channel']==0 and
            mapping.get('conditional_receiver_ids')==list(EXPECTED_RECEIVERS) and
            mapping.get('network_route_attested') is False and
            mapping.get('native_feedback_packet_attested') is False and
            mapping.get('origin')=='explicit_shadow_ingress_assumption_not_native_scheduler',
            'v1e hypothetical mapping changed')
    probe=e.get('receiver_probe')
    require(type(probe) is dict and probe.get('evaluation_domain_indices')==list(EXPECTED_EVAL)
            and type(probe.get('receiver_pairs')) is int and probe['receiver_pairs']==6,
            'v1e evaluation domain mismatch')
    require(probe.get('recipient_timestamp')==12 and probe.get('recipient_prior_tick')==11,
            'v1e recipient time drift')
    entries=probe.get('readouts')
    require(type(entries) is list and len(entries)==6,'incomplete recipient matrix')
    pairs=[]
    for k,idx in enumerate(EXPECTED_EVAL):
        for j,rid in enumerate(EXPECTED_RECEIVERS):
            item=entries[2*k+j]
            before,after=_record(item,rid,idx)
            pairs.append((idx,rid,item,before,after))
    require(all(type(probe.get(key)) is int for key in
                ('different_pairs','guard_different_pairs','emission_different_pairs')) and
            probe['different_pairs']==sum(bool(p[2]['receiver_output_changed']) for p in pairs) and
            probe['guard_different_pairs']==sum(bool(p[2]['receiver_guard_changed']) for p in pairs) and
            probe['emission_different_pairs']==sum(bool(p[2]['receiver_emission_changed']) for p in pairs),
            'v1e aggregate mismatch')
    require(probe.get('different_pairs')>0,
            'uninformative receiver evidence for preference polarity study')
    policies=[]
    for name in POLICIES:
        signs=[]
        for idx,rid,item,before,after in pairs:
            old_count=len(before['emitted_channels'])
            new_count=len(after['emitted_channels'])
            delta=new_count-old_count
            sign=(delta>0)-(delta<0)
            if name==POLICIES[1]:sign=-sign
            signs.append({'evaluation_domain_index':idx,'receiver_id':rid,
                          'declared_shared_sender_origin':'A.evaluation.'+str(idx),
                          'baseline_receiver_emission_count':old_count,
                          'candidate_receiver_emission_count':new_count,
                          'candidate_minus_baseline_count':delta,
                          'declared_policy_preference_sign':sign,
                          'endogenous_receiver_judgment':False})
        policies.append({'policy_id':name,'criterion_origin':'experimenter_predeclared_not_receiver',
                         'sign_convention':'positive_means_candidate_preferred',
                         'positive':sum(x['declared_policy_preference_sign']==1 for x in signs),
                         'negative':sum(x['declared_policy_preference_sign']==-1 for x in signs),
                         'neutral':sum(x['declared_policy_preference_sign']==0 for x in signs),
                         'observations':signs})
    a,b=policies
    require(all(i['declared_policy_preference_sign']==-j['declared_policy_preference_sign']
                for i,j in zip(a['observations'],b['observations'])),
            'policy inversion invariant violated')
    # Two readouts per case share one *declared* sender branch, not two proven votes.
    return {'native_conditional_pairs':len(pairs),
            'receiver_readout_difference_pairs':probe['different_pairs'],
            'declared_shared_sender_origin_groups':len(EXPECTED_EVAL),
            'observations_per_declared_origin':len(EXPECTED_RECEIVERS),
            'independent_causal_votes_proven':0,
            'policy_conditioned_shadow_preferences':policies,
            'preference_polarity_reversed_on_different_pairs':sum(
                x['declared_policy_preference_sign']!=0 for x in a['observations']),
            'native_judgments_observed':0,'native_updates_applied':0,
            'native_learning_proven':False,'network_event_lineage_attested':False,
            'receiver_utility_identified':False}

def build(v1e,v1e_bytes,recomputed_v1e):
    require(type(v1e_bytes) is bytes and len(v1e_bytes)>0, 'missing bytes')
    require(v1e==recomputed_v1e,'full v1e frozen-native recomputation mismatch')
    for name in ('reference_v1d_sha256','reference_v1c_sha256',
                 'reference_v1b1_sha256','reference_v0w_sha256'):
        _sha(v1e.get(name))
    return {'schema':SCHEMA,'status':STATUS,
            'reference_v1e_sha256':sha256(v1e_bytes).hexdigest(),
            'reference_v1d_sha256':v1e['reference_v1d_sha256'],
            'reference_v1c_sha256':v1e['reference_v1c_sha256'],
            'reference_v1b1_sha256':v1e['reference_v1b1_sha256'],
            'reference_v0w_sha256':v1e['reference_v0w_sha256'],
            'native_fixture_sha256':_sha(v1e.get('native_fixture_sha256')),
            'frozen_native_sources':v1e.get('frozen_native_sources'),
            **analyze(v1e), 'claims_excluded':EXCLUSIONS}
