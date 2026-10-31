"""BV v1i: report-bound native feedback-silence and objective-polarity audit.

This is an epistemic *boundary*, not negative feedback, receiver utility,
learned updating, or an endogenous score. An original/variant counterfactual
is admitted only after the v1h native CLI has been replayed and byte-compared.
"""
from __future__ import annotations
from hashlib import sha256
from spk_bv_research.off_on_v0t import require
from spk_bv_research.native_network_counterfactual_v1h import SCHEMA as H_SCHEMA, STATUS as H_STATUS

SCHEMA='spk-bv-native-feedback-silence-polarity/v1i'
STATUS='REPLAY_BOUND_NO_FEEDBACK_IS_NOT_A_RECEIVER_VOTE'
EXCLUSIONS=[
    'structural-no-downstream-occurrences-not-receiver-approval',
    'zero-native-assessments-not-a-negative-or-positive-judgment',
    'missing-feedback-mechanism-is-not-identified-from-a-single-counterfactual',
    'terminal-count-scores-are-experimenter-declared-illustrations-not-external-truth',
    'different-totals-are-not-independent-episodes-or-generalization',
    'sender-operator-choice-not-originated-in-feedback',
    'no-scored-native-judgment-or-local-commit-or-rollback-or-learning',
    'not-a-certified-algebra-rewrite-or-hardware-or-architecture-promotion',
]


def _natural(v):
    return type(v) is int and 0 <= v <= 100000


def _footprint(x,label):
    require(type(x) is dict and set(x)=={
        'batches','emissions','link_grants','occurrences','terminal','edges','states_sha256'},
        f'{label} native footprint inventory drift')
    require(all(_natural(x[k]) for k in ('batches','emissions','link_grants','occurrences','terminal')),
            f'{label} invalid nonnegative native counter')
    require(type(x['states_sha256']) is str and len(x['states_sha256'])==64 and
            all(c in '0123456789abcdef' for c in x['states_sha256']),
            f'{label} invalid state SHA-256')
    require(type(x['edges']) is dict and all(type(k) is str and _natural(v)
            for k,v in x['edges'].items()),f'{label} invalid route map')
    require(sum(x['edges'].values())==x['occurrences'],f'{label} route count != occurrences')
    require(x['terminal']<=x['emissions'] and x['occurrences']==x['link_grants'],
            f'{label} native transport accounting broken')
    return x


def audit(report, report_bytes, *, g_bytes, d_bytes):
    """Only admit the frozen original A->B->C / isolated A variant v1h fixture."""
    require(type(report) is dict and report.get('schema')==H_SCHEMA and
            report.get('status')==H_STATUS and report.get('real_variant_full_fabric_replay') is True and
            report.get('experiment_kind')=='PRE_EPISODE_COPY_INTERVENTION' and
            report.get('conditional_direct_A_to_C') is False and
            report.get('v1e_hypothetical_A_to_C_direct_promoted') is False and
            report.get('variant_off_on_forward_outcomes_equal') is True,
            'v1h is not the attested source-bound frozen network counterfactual')
    require(type(report_bytes) is bytes and type(g_bytes) is bytes and type(d_bytes) is bytes and
            all(len(v)>0 for v in (report_bytes,g_bytes,d_bytes)),
            'missing source bytes')
    require(sha256(g_bytes).hexdigest()==report.get('reference_v1g1_file_sha256') and
            sha256(d_bytes).hexdigest()==report.get('reference_v1d_file_sha256'),
            'v1h reference SHA-256 mismatch')
    intervention=report.get('intervention')
    require(type(intervention) is dict and
            intervention.get('sender')=='A' and intervention.get('instruction_index')==2 and
            intervention.get('original_instruction')==['CMP',1] and
            intervention.get('variant_instruction')==['CMP',2] and
            intervention.get('original_nodes_unchanged') is True and
            intervention.get('static_fabric_shared_immutable') is True and
            intervention.get('external_events_preserved') is True,
            'not the isolated native A intervention')
    require(report.get('native_scored_receiver_judgments')==0 and
            report.get('native_updates_applied')==0 and
            report.get('native_learning_proven') is False and
            report.get('network_utility_identified') is False,
            'v1h unjustified receiver-value or learning claim')
    origin=report.get('original'); variant=report.get('variant')
    require(type(origin) is dict and type(variant) is dict,
            'missing original/variant run families')
    for fam,obj in (('original',origin),('variant',variant)):
        for arm in ('off','on'):
            _footprint(obj.get(arm),f'{fam}.{arm}')
            s=obj.get(f'{arm}_result_sha256')
            require(type(s) is str and len(s)==64 and
                    all(c in '0123456789abcdef' for c in s),
                    f'{fam}.{arm} whole result SHA missing')
    r={'A->B:7->0':2,'B->C:7->0':2}
    expected_original={'batches':6,'emissions':6,'occurrences':4,'terminal':2,'link_grants':4,'edges':r}
    expected_variant={'batches':2,'emissions':0,'occurrences':0,'terminal':0,'link_grants':0,'edges':{}}
    for fam, expected in ((origin,expected_original),(variant,expected_variant)):
        for arm in ('off','on'):
            require(all(fam[arm][key]==value for key,value in expected.items()),
                    'native network footprint differs from v1h bounded baseline/variant')
    for arm in ('off','on'):
        deltas=report.get(f'{arm}_variant_minus_original')
        require(type(deltas) is dict and set(deltas)=={
            'batches','emissions','link_grants','occurrences','terminal'} and
            all(type(v) is int and v==variant[arm][k]-origin[arm][k]
                for k,v in deltas.items()),'native counterfactual delta mismatch')
    fb_a=report.get('native_feedback_assessments')
    fb_d=report.get('native_feedback_deliveries')
    require(fb_a=={'original_on':2,'variant_on':0} and
            fb_d=={'original_on':4,'variant_on':0},
            'native evidence feedback inventory drift')
    # These are observed run counters, *not* inferred independent votes.
    start=origin['off']['terminal']; end=variant['off']['terminal']
    require(start==origin['on']['terminal'] and end==variant['on']['terminal'],
            'BV state altered original/variant terminal count')
    policies=(
      ('maximize_terminal_emissions','EXPERIMENTER_DECLARED_TERMINAL_ACTIVITY',start,end),
      ('minimize_terminal_emissions','EXPERIMENTER_DECLARED_TERMINAL_SPARSE',-start,-end),
      ('match_two_terminal_emissions','EXPERIMENTER_DECLARED_TARGET_TWO',-abs(start-2),-abs(end-2)),
    )
    rows=[]
    for ident,origin_type,x,y in policies:
        rows.append({'criterion_id':ident,'criterion_origin':origin_type,
                     'original_score':x,'variant_score':y,'variant_minus_original_score':y-x,
                     'preferred':'VARIANT' if y>x else 'ORIGINAL' if y<x else 'TIE',
                     'independent_utility_oracle':False})
    require(rows[0]['preferred']=='ORIGINAL' and rows[1]['preferred']=='VARIANT',
            'criterion polarity not observed')
    return {
      'schema':SCHEMA,'status':STATUS,
      'reference_v1h_sha256':sha256(report_bytes).hexdigest(),
      'reference_v1g1_sha256':sha256(g_bytes).hexdigest(),
      'reference_v1d_sha256':sha256(d_bytes).hexdigest(),
      'frozen_native_sources':report.get('frozen_native_sources'),
      'native_fixture_sha256':report.get('native_fixture_sha256'),
      'original_to_variant_network':{
          'terminal_emissions':[start,end],
          'forward_occurrences':[origin['off']['occurrences'],variant['off']['occurrences']],
          'A_to_B_occurrences':[origin['off']['edges']["A->B:7->0"],variant['off']['edges'].get('A->B:7->0',0)],
          'B_to_C_occurrences':[origin['off']['edges']["B->C:7->0"],variant['off']['edges'].get('B->C:7->0',0)],
          'processed_batches':[origin['off']['batches'],variant['off']['batches']],
          'feedback_assessments_on':[fb_a['original_on'],fb_a['variant_on']],
          'feedback_deliveries_on':[fb_d['original_on'],fb_d['variant_on']],
      },
      'variant_feedback_availability':'NO_ASSESSMENT_GENERATED_WITH_ZERO_ROUTED_OCCURRENCES',
      'variant_receiver_judgment_sign':'UNOBSERVED_NOT_NEUTRAL_OR_POSITIVE',
      'recipient_exposure_zero_on_variant':True,
      'native_scored_receiver_judgments':0,'native_updates_applied':0,
      'network_utility_identified':False,'learning_proven':False,
      'declared_policy_demonstrations':rows,
      'policy_origin':'DECLARED_EXPERIMENTER_SCORE_NOT_RECEIVER_ORACLE',
      'claims_excluded':EXCLUSIONS,
    }
