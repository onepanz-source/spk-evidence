"""T8JKL: v1 REFERENCE feedback bus, isolated from frozen BV-v0e.

The original BV scheduler is called first. We subsequently interpret its
A emission + A->B->C structural evidence in a NEW reference event bus.
This is a v1 bus event carrying semantics, not native SPK or a modification
of a v0e packet. The host owns all inputs and can forge every field.
"""
from __future__ import annotations
from copy import deepcopy
from research.spk_v5_t7abc_def_ghi.scheduler_bridge_v0 import verify_source,check
from research.spk_v5_t6abc_def_ghi.loop_v0 import digest

SCHEMA='spk-v1-reference-semantic-feedback/v1'


def _pick(items, node, channel):
    found=[e for e in items if e.get('node_id')==node and e.get('channel')==channel]
    check(len(found)==1,'A_SEMANTIC_SOURCE_NOT_UNIQUE')
    return found[0]


def dispatch(source,issue,*,drop=False):
    """Replay source PE emission as semantic feedback in a NEW v1 event bus.

    Require the frozen structural route and bind A's actual PE output to it.
    Recompute from source; do NOT consume a host-supplied verdict label.
    """
    check(type(issue) is dict and set(issue)=={'id','cue','choice','version','goal'},'ISSUE_FIELDS')
    check(all(type(issue[k]) is int for k in issue),'ISSUE_TYPE')
    verified=verify_source(source,issue['choice'],issue['goal'],drop_forward=drop)
    if drop:
        check(verified['A_outcome']=='ABSENT','DROP_VERDICT')
        return None
    f=source['forward'];bv=source['feedback'];emits=f['emissions']
    channel=verified['A_emission']
    ev=_pick(emits,'A',channel)
    occurrence=f['occurrences'][-1]
    assessment=bv['assessments'][0]
    deliveries=bv['deliveries']
    check(len(deliveries)==2,'STRUCTURAL_DELIVERY_COUNT')
    assert verified['A_outcome'] in ('IMPROVED','WORSENED')
    payload={'issuer':'A','receiver':'C','decision_id':issue['id'],
        'context_id':issue['cue'],'policy_version':issue['version'],
        'choice':issue['choice'], 'verdict':verified['A_outcome'],
        'A_emission_channel':channel,'A_emission_digest':digest(ev),
        'A_assessment_digest':digest(assessment),
        'causal_parent_occurrence_id':occurrence['id'],
        'source_digest':digest(source),
        'authoritativeness':'REFERENCE_HOST_UNATTESTED'}
    a={'schema':SCHEMA,'carrier':'REFERENCE_V1_A_TO_B','payload':payload,
        'structural_delivery_digest':digest(deliveries[0])}
    b={'schema':SCHEMA,'carrier':'REFERENCE_V1_B_TO_C','a':deepcopy(a),
        'a_digest':digest(a),'structural_delivery_digest':digest(deliveries[1])}
    c={'schema':SCHEMA,'carrier':'REFERENCE_V1_C_RECEIPT','b':deepcopy(b),
        'b_digest':digest(b),'payload':deepcopy(payload)}
    return c


def verify(source,issue,packet,*,drop=False):
    expected=dispatch(source,issue,drop=drop)
    check(packet==expected and (drop or type(packet) is dict),'SEMANTIC_BINDING_DRIFT')
    if not drop:
        a=packet['b']['a'];b=packet['b'];p=packet['payload']
        check(b['a_digest']==digest(a) and packet['b_digest']==digest(b),'BUS_CUSTODY_DRIFT')
        check(p==a['payload'] and p['authoritativeness']=='REFERENCE_HOST_UNATTESTED','BUS_PAYLOAD_DRIFT')
    return expected
