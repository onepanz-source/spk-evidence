"""BV v0q: read-only per-field provenance diagnostic for the TWO native v0o policies.

An identifier is only a join candidate, not evidence of stable cross-run identity.
No new simulator executions, source changes, causal or learning claims.
"""
from __future__ import annotations

from hashlib import sha256
from collections import Counter
from typing import Any

from .native_capture_v0k import _sha
from .native_dossier_v0l import typed_path
from .paired_runs_v0o import PairError

SCHEMA='spk-bv-native-feedback-lineage-differential/v0q'
STATUS='NATIVE_FIELD_DIFFERENCES_ONLY_NOT_CAUSAL_EQUIVALENCE'
EXPECTED_NATIVE_SHA='887ad94cc89d91083950d9a99fff10007edc160df370c6bdef5b1d9048167fb4'
MAX_RECORDS=10000
MAX_FIELD=256


def deny(reason):
    raise PairError(reason)


def get(obj,*p):
    return typed_path(obj,p)


def fields(node):
    if type(node) is not dict or node.get('$t') not in ('dict','dataclass'):
        deny('expected typed mapping')
    pairs=node['pairs'] if node['$t']=='dict' else node['fields']
    if not isinstance(pairs,list) or len(pairs)>MAX_FIELD:
        deny('record field bound')
    d={}
    for k,v in pairs:
        if type(k) is not str or not k or k in d:
            deny('invalid or repeated field')
        d[k]=v
    return d


def seq(obj,*p):
    node=get(obj,*p)
    if type(node) is not dict or node.get('$t') not in ('list','tuple'):
        deny('expected typed sequence')
    vals=node['items']
    if type(vals) is not list or len(vals)>MAX_RECORDS:
        deny('sequence size invalid')
    return vals


def index(rows,key):
    result={}
    for row in rows:
        x=fields(row)
        k=x.get(key)
        if type(k) is not str or not 0<len(k)<=MAX_FIELD or k in result:
            deny('invalid/duplicate '+key)
        result[k]=x
    return result


def display(v):
    if v is None or type(v) in (int,str,bool):
        if type(v) is str and len(v)>MAX_FIELD:
            return {'sha256':_sha(v),'type':'long-string'}
        return v
    if type(v) is dict and v.get('$t') in ('tuple','list') and len(v.get('items',[]))<=30:
        items=v['items']
        if all(type(x) in (str,int,bool) for x in items) and all(type(x) is not str or len(x)<=MAX_FIELD for x in items):
            return {'container':v['$t'],'items':items}
    return {'typed_value_sha256':_sha(v),'tag':v.get('$t') if type(v) is dict else type(v).__name__}


def compare_fields(x,y,excluded=frozenset()):
    diffs={}
    for k in sorted(set(x)|set(y)):
        if k in excluded: continue
        a=x.get(k,{'missing':True})
        b=y.get(k,{'missing':True})
        if a!=b:
            diffs[k]={'first':display(a),'second':display(b)}
    return diffs


def run_extract(run):
    fb_del=index(seq(run,'feedback','deliveries'),'packet_id')
    fb_gr=index(seq(run,'feedback','link_grants'),'packet_id')
    fb_ass=index(seq(run,'feedback','assessments'),'id')
    if set(fb_del)!=set(fb_gr):
        deny('within-run feedback packet/grant not bijective')
    for ident in sorted(fb_del):
        d,g=fb_del[ident],fb_gr[ident]
        for k in ('packet_id','assessment_id','sender','receiver'):
            if d.get(k)!=g.get(k):
                deny('within-run delivery/grant discrepancy '+ident+':'+k)
        a=d.get('assessment_id')
        if type(a) is not str or a not in fb_ass:
            deny('within-run dangling assessment reference '+ident)
        if type(d.get('tick')) is not int or type(g.get('delivered_at')) is not int or d['tick']!=g['delivered_at']:
            deny('within-run delivery tick mismatch '+ident)
        if type(g.get('tick')) is not int or type(g.get('wait')) is not int or g['wait']<0:
            deny('within-run grant invalid tick or wait')
    return fb_del,fb_gr,fb_ass


def audit(root:dict,fixture_sha:str)->dict:
    if type(root) is not dict or root.get('$t')!='tuple' or len(root.get('items',[]))!=5:
        deny('unexpected native fixture root')
    one,two=root['items'][3:5]
    if (get(one,'enabled'),get(two,'enabled'))!=(True,True):
        deny('both fixture runs must have feedback enabled')
    if (get(one,'policy'),get(two,'policy'))!=('forward-first','feedback-first'):
        deny('unexpected scheduler policies')
    d1,g1,a1=run_extract(one)
    d2,g2,a2=run_extract(two)
    packet_ids=sorted(set(d1)|set(d2))
    assessment_ids=sorted(set(a1)|set(a2))
    observations=[]
    divergent_delivery=[]
    divergent_grant=[]
    for p in packet_ids:
        if p not in d1 or p not in d2:
            observations.append({'packet_id':p,'presence':('first-only' if p in d1 else 'second-only')})
            continue
        dd=compare_fields(d1[p],d2[p],frozenset({'tick'}))
        gg=compare_fields(g1[p],g2[p],frozenset({'tick','delivered_at','wait'}))
        if dd:divergent_delivery.append(p)
        if gg:divergent_grant.append(p)
        shifts={k:g2[p][k]-g1[p][k] for k in ('tick','delivered_at','wait') if type(g1[p].get(k)) is int and type(g2[p].get(k)) is int}
        shifts['delivery_tick']=d2[p]['tick']-d1[p]['tick']
        observations.append({'packet_id':p,'presence':'both','delivery_non_temporal_differences':dd,
                             'grant_non_temporal_differences':gg,'observed_tick_and_reported_wait_delta':shifts,
                             'same_non_temporal_delivery_payload':not dd,'same_non_temporal_grant_payload':not gg})
    assessment_changes=[]
    for aid in assessment_ids:
        if aid in a1 and aid in a2:
            changes=compare_fields(a1[aid],a2[aid],frozenset({'tick'}))
            if changes:assessment_changes.append({'assessment_id':aid,'non_temporal_differences':changes})
    nonident=set(divergent_delivery)|set(divergent_grant)
    return {'schema':SCHEMA,'status':STATUS,'native_fixture_sha256':fixture_sha,
            'policies':['forward-first','feedback-first'],
            'source_kind':'native-v0o-typed-fixture-not-simulator-rerun',
            'runs':{'first':{'feedback_deliveries':len(d1),'feedback_grants':len(g1),'assessments':len(a1)},
                    'second':{'feedback_deliveries':len(d2),'feedback_grants':len(g2),'assessments':len(a2)}},
            'within_run_packet_grant_bijection_and_assessment_references':True,
            'packet_ids_both':sum(p in d1 and p in d2 for p in packet_ids),
            'delivery_payload_divergent_ids':divergent_delivery,
            'grant_payload_divergent_ids':divergent_grant,
            'packet_ids_not_semantically_equivalent_by_same_id':sorted(nonident),
            'assessment_non_temporal_changes':assessment_changes,
            'packet_diagnostics':observations,
            'restrictions':['identifiers-are-only-within-run-until-cross-policy-semantics-proven',
                            'no-evidence-that-packet-id-reuse-is-a-bug',
                            'time-fields-and-native-wait-not-hardware-cost',
                            'no-feedback-off-control','no-causal-credit-or-learning',
                            'no-architecture-promotion']}
