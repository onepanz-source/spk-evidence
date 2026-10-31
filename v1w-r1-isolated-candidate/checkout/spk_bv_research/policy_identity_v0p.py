"""SPK BV v0p: source-bound, read-only identity-aware native scheduler policy audit.

This compares feedback-enabled *policies*, not feedback ON versus OFF.
The source fixture is typed data captured by BV v0o; no runtime invocation.
"""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
from typing import Any
from .native_capture_v0k import _sha
from .native_dossier_v0l import typed_path
from .paired_runs_v0o import PairError

SCHEMA = 'spk-bv-native-policy-identity-audit/v0p'
STATUS = 'NATIVE_FEEDBACK_ENABLED_POLICY_IDENTITY_AUDIT_ONLY'
EXPECTED_NATIVE_SHA = '887ad94cc89d91083950d9a99fff10007edc160df370c6bdef5b1d9048167fb4'


def reject(m: str):
    raise PairError(m)


def at(x: Any, *path):
    return typed_path(x, path)


def rows(x: Any, *path) -> list:
    v = at(x, *path)
    if type(v) is not dict or v.get('$t') not in ('tuple','list'):
        reject(f'expected typed sequence at {path!r}')
    return v['items']


def integer(x: Any, *path) -> int:
    v = at(x, *path)
    if type(v) is not int or v < 0:
        reject(f'invalid nonnegative integer at {path!r}')
    return v


def scalar(x: Any, *path, typ=str):
    v = at(x,*path)
    if type(v) is not typ:
        reject(f'invalid scalar at {path!r}')
    return v


def content_fields(row: Any, excluded: frozenset[str]) -> dict:
    if type(row) is not dict or row.get('$t') not in ('dict','dataclass'):
        reject('record not typed dict/dataclass')
    fieldset = row['pairs'] if row['$t']=='dict' else row['fields']
    return {k:v for k,v in fieldset if k not in excluded}


def multiset_report(a: list, b: list, excluded: frozenset[str]) -> dict:
    ca=Counter(_sha(content_fields(x,excluded)) for x in a)
    cb=Counter(_sha(content_fields(x,excluded)) for x in b)
    return {'same_multiset':ca==cb, 'count_first':len(a),'count_second':len(b),
            'duplicate_content_groups_first':sum(n>1 for n in ca.values()),
            'duplicate_content_groups_second':sum(n>1 for n in cb.values()),
            'unmatched_first':sum((ca-cb).values()),'unmatched_second':sum((cb-ca).values())}


def identity_report(a: list, b: list, *, key: str, time_fields: tuple[str,...], ignored: frozenset[str]=frozenset()) -> dict:
    def indexed(source):
        d={}
        for record in source:
            k=scalar(record,key)
            if not k or len(k)>256 or k in d:
                reject('missing, oversized or duplicate identity '+key)
            d[k]=record
        return d
    x,y=indexed(a),indexed(b)
    missing_a=sorted(set(x)-set(y))
    missing_b=sorted(set(y)-set(x))
    mismatched=[]
    matching=[]
    for ident in sorted(set(x)&set(y)):
        excluded=frozenset((*time_fields,*ignored))
        if content_fields(x[ident],excluded)!=content_fields(y[ident],excluded):
            mismatched.append(ident)
            continue
        shifts={f:integer(y[ident],f)-integer(x[ident],f) for f in time_fields}
        matching.append((ident,shifts))
    shifts={f:sorted(v[f] for _,v in matching) for f in time_fields}
    result={'identity_field':key, 'count_first':len(x), 'count_second':len(y),
            'missing_in_second':missing_a,'missing_in_first':missing_b,
            'payload_mismatches':mismatched,'matched_immutable_payload_count':len(matching),
            'timestamp_shift_distributions':shifts,
            'all_identities_and_payloads_match':not(missing_a or missing_b or mismatched)}
    # No per-event identity inference when an ID is absent or payload changes.
    return result


def timestamp_report(a:list,b:list, field:str)->dict:
    before=sorted(integer(row,field) for row in a)
    after=sorted(integer(row,field) for row in b)
    return {'first':before,'second':after,'first_max':max(before) if before else None,
            'second_max':max(after) if after else None,
            'last_tick_delta':(max(after)-max(before)) if before and after else None,
            'count_equal':len(before)==len(after)}


def compute(native_root:dict, fixture_sha:str=EXPECTED_NATIVE_SHA)->dict:
    if not isinstance(native_root,dict) or native_root.get('$t')!='tuple' or len(native_root['items'])!=5:
        reject('expected original five-item typed native fixture')
    one,two=native_root['items'][3:5]
    ep=(scalar(one,'enabled',typ=bool),scalar(two,'enabled',typ=bool))
    pol=(scalar(one,'policy'),scalar(two,'policy'))
    if ep != (True, True) or pol!=('forward-first','feedback-first'):
        reject('not the intended feedback-enabled policy comparison')

    base={k:_sha(native_root['items'][k]) for k in range(3)}
    bo=rows(one,'forward','batches'); bt=rows(two,'forward','batches')
    eo=rows(one,'forward','emissions'); et=rows(two,'forward','emissions')
    to=rows(one,'forward','terminal'); tt=rows(two,'forward','terminal')
    fo=rows(one,'forward','occurrences'); ft=rows(two,'forward','occurrences')
    do=rows(one,'feedback','deliveries'); dt=rows(two,'feedback','deliveries')
    go=rows(one,'feedback','link_grants'); gt=rows(two,'feedback','link_grants')
    lo=rows(one,'forward','link_grants'); lt=rows(two,'forward','link_grants')
    identity={
        'feedback_delivery': identity_report(do,dt,key='packet_id',time_fields=('tick',)),
        'feedback_grant':identity_report(go,gt,key='packet_id',time_fields=('tick','delivered_at'),ignored=frozenset({'wait'})),
        'forward_occurrence':identity_report(fo,ft,key='id',time_fields=('emitted_at','delivered_at')),
        'forward_grant':identity_report(lo,lt,key='id',time_fields=('tick','delivered_at'),ignored=frozenset({'wait'})),
    }
    payload={
        'forward_batches':multiset_report(bo,bt,frozenset({'tick','ready'})),
        'forward_emissions':multiset_report(eo,et,frozenset({'timestamp'})),
        'forward_terminal':multiset_report(to,tt,frozenset({'timestamp'})),
    }
    tick={
        'forward_batches':timestamp_report(bo,bt,'tick'),
        'forward_emissions':timestamp_report(eo,et,'timestamp'),
        'forward_terminal':timestamp_report(to,tt,'timestamp'),
        'feedback_deliveries':timestamp_report(do,dt,'tick'),
    }
    states_match=at(one,'forward','states')==at(two,'forward','states')
    conserved={
        'processed_batches':integer(one,'forward','processed_batches')==integer(two,'forward','processed_batches'),
        'processed_events':integer(one,'forward','processed_events')==integer(two,'forward','processed_events'),
        'forward_states':states_match,
        'forward_emission_payload':payload['forward_emissions']['same_multiset'],
        'forward_terminal_payload':payload['forward_terminal']['same_multiset'],
    }
    waits = {
        'forward_feedback_grant_wait_sum': {
            'first': sum(integer(x,'wait') for x in go),
            'second': sum(integer(x,'wait') for x in gt),
            'second_minus_first': sum(integer(x,'wait') for x in gt)-sum(integer(x,'wait') for x in go),
        }
    }
    differences={name:{'first':integer(one,*p),'second':integer(two,*p),
                       'second_minus_first':integer(two,*p)-integer(one,*p)}
                 for name,p in {
                   'fabric_link_contention':('resources','contention','fabric_link'),
                   'bv_link_grants':('resources','bv_link_grants'),
                   'bv_service_units':('resources','bv_service_units'),
                   'bv_memory_units':('resources','bv_memory_units'),
                   'forward_link_grants':('resources','forward_link_grants'),
                   'forward_reserved_memory_units':('resources','forward_reserved_memory_units'),
                 }.items()}
    structural_parity=all(conserved.values())
    return {'schema':SCHEMA,'status': STATUS, 'native_fixture_sha256':fixture_sha,
            'policies':list(pol),'both_feedback_enabled':True,'shared_base_source_sha256':base,
            'resource_comparison':{**differences,**waits},'conserved_outcomes':conserved,
            'conserved_outcomes_all':structural_parity,
            'payload_multisets':payload,'identity_joins':identity,'time_distributions':tick,
            'restrictions':[
                'both-runs-feedback-enabled-not-ON-OFF',
                'shared-fixture-base-not-proof-of-equal-effective-inputs',
                'immutable-payload-joins-not-causal-attribution',
                'duplicate-payload-groups-not-identifiable-event-matches',
                'tick-counts-not-hardware-time-or-energy',
                'native-scheduler-policy-not-hardware-or-learning-promotion',
            ]}
