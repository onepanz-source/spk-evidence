"""BV v1g: attest *original* native forward routes/occurrences and reverse feedback lineage.

A channel translation present in the frozen static route and observed forward
occurrences is not evidence that v1e's hypothetical modified sender was run in
the network, nor that reverse BV packets contain a receiver's utility judgment.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from hashlib import sha256
from spk_bv_research.off_on_v0t import require, snapshot
from spk_bv_research.receiver_preference_v1f import SCHEMA as F_SCHEMA, STATUS as F_STATUS

SCHEMA='spk-bv-native-original-route-occurrence-lineage/v1g'
STATUS='ORIGINAL_FORWARD_ROUTE_AND_REVERSE_LINEAGE_ATTESTED_NO_VARIANT_NETWORK_REPLAY'
EXCLUSIONS=[
 'route-attestation-covers-only-frozen-original-network-not-v1e-variant',
 'ancestral-C-not-assumed-direct-A-to-C-route',
 'original-forward-occurrence-not-variant-network-counterfactual',
 'feedback-ancestry-evidence-is-not-scored-receiver-judgment',
 'native-independent_receiver-flag-is-not-independent-causal-vote',
 'no-endogenous-utility-or-operator-update-or-learning',
 'no-generalization-or-hardware-metrics-or-architecture-promotion',
]

def _edge(e,owners):
    keys=('source_node','source_channel','target_node','target_channel','target_pe','delay_ticks')
    require(all(hasattr(e,k) for k in keys),'unsupported native route shape')
    d={k:getattr(e,k) for k in keys}
    require(type(d['source_node']) is str and type(d['target_node']) is str and
            d['source_node'] in owners and d['target_node'] in owners and
            all(type(d[k]) is int for k in ('source_channel','target_channel','delay_ticks')) and
            d['delay_ticks']>0 and d['target_pe']==owners[d['target_node']],
            'invalid static route fields')
    d['source_pe']=owners[d['source_node']]
    return d

def _index_forward(forward,edges):
    require(type(forward) is dict and type(forward.get('occurrences')) is list and
            type(forward.get('batches')) is list and type(forward.get('emissions')) is list,
            'missing original native forward records')
    occ=forward['occurrences']; batches=forward['batches'];emissions=forward['emissions']
    require(0<len(occ)<=256 and 0<len(batches)<=128 and len(emissions)<=128,
            'unbounded forward evidence')
    key_to_edges=defaultdict(list)
    for e in edges:
        key=(e['source_node'],e['target_node'],e['target_channel'],e['source_pe'],
             e['target_pe'],e['delay_ticks'])
        key_to_edges[key].append(e)
    # Native row shape is not a proof of a specific Python collection type.
    # A frozen producer can encode parent IDs in a tuple as well as a list.
    grants=forward.get('link_grants')
    require(grants is None or type(grants) is list,
            'malformed original forward grant section')
    grant_by_id={}
    if grants is not None:
        require(len(grants)<=256,'unbounded original forward grants')
        for g in grants:
            require(type(g) is dict and type(g.get('id')) is str and
                    g['id'] not in grant_by_id and
                    all(type(g.get(k)) is int for k in ('tick','delivered_at')) and
                    g['tick']>=0 and g['delivered_at']>=g['tick'],
                    'malformed original forward grant/timing')
            grant_by_id[g['id']]=g
    byid={}; occ_rows=[]
    for o in occ:
        require(type(o) is dict and set(('id','source','target','source_pe','target_pe',
                'channel','emitted_at','delivered_at','parents','delay'))<=set(o),
                'malformed occurrence')
        oid=o['id'];require(type(oid) is str and oid not in byid,'duplicate occurrence id')
        require(all(type(o[k]) is int for k in ('channel','emitted_at','delivered_at','delay'))
                and o['emitted_at']>=0 and o['delivered_at']>=o['emitted_at']
                and type(o['parents']) in (list,tuple),
                'invalid occurrence timing/parent fields at index '+str(len(occ_rows))+
                ': '+str({k:(type(o.get(k)).__name__,o.get(k)) for k in
                          ('emitted_at','delivered_at','delay')})+
                ', parents_type='+type(o.get('parents')).__name__)
        if grants is None:
            # For isolated contract-only fixtures, no grant evidence was supplied.
            # Do not allow an anomalously short transport time without evidence.
            require(o['delivered_at']>=o['emitted_at']+o['delay'],
                    'occurrence arrives before declared route delay without grant evidence')
        else:
            g=grant_by_id.get(oid)
            require(g is not None and
                    all(g.get(k)==o[k] for k in ('source','target','source_pe','target_pe')) and
                    g['delivered_at']==o['delivered_at'] and
                    g['tick']>=o['emitted_at'],
                    'occurrence does not match native forward link grant')
            # Nominal route delay and link-grant schedule are different concepts.
            # For the observed native result, the joined transport record
            # establishes timing; do not infer delivered_at=emitted_at+delay.
        key=(o['source'],o['target'],o['channel'],o['source_pe'],o['target_pe'],o['delay'])
        matches=key_to_edges.get(key,())
        require(len(matches)==1,'occurrence lacks a unique static route')
        edge=matches[0]
        require(any(type(row) is dict and row.get('timestamp')==o['emitted_at'] and
                    row.get('node_id')==o['source'] and row.get('channel')==edge['source_channel']
                    for row in emissions),'occurrence lacks matching sender emission')
        require(all(type(p) is str and p!=oid for p in o['parents']) and
                len(set(o['parents']))==len(o['parents']),'invalid occurrence ancestry')
        byid[oid]=o
        occ_rows.append({'id':oid,'source':o['source'],'target':o['target'],
             'sender_channel':edge['source_channel'],'receiver_channel':o['channel'],
             'emitted_at':o['emitted_at'],'delivered_at':o['delivered_at'],
             'parents':list(o['parents']),'source_pe':o['source_pe'],
             'target_pe':o['target_pe']})
    if grants is not None:
        require(set(grant_by_id)==set(byid),
                'native link grant and forward occurrence identities disagree')
    # Every emitted channel must spawn exactly one occurrence per matching route.
    # Counter multiplicities matter even with repeated same-tick emissions.
    expected=Counter()
    for row in emissions:
        require(type(row) is dict and type(row.get('timestamp')) is int and
                type(row.get('node_id')) is str and type(row.get('channel')) is int,
                'malformed original emission')
        for e in edges:
            if row['node_id']==e['source_node'] and row['channel']==e['source_channel']:
                expected[(row['timestamp'],e['source_node'],e['target_node'],
                          e['source_channel'],e['target_channel'])]+=1
    realized=Counter((o['emitted_at'],o['source'],o['target'],
                     key_to_edges[(o['source'],o['target'],o['channel'],
                     o['source_pe'],o['target_pe'],o['delay'])][0]['source_channel'],
                     o['channel']) for o in occ)
    require(expected==realized, 'route/emission occurrence multiplicity mismatch')
    for o in occ:
        for pid in o['parents']:
            require(pid in byid,'unresolved forward ancestor')
            parent=byid[pid]
            require(parent['target']==o['source'] and parent['delivered_at']<=o['emitted_at']
                    and parent['emitted_at']<o['emitted_at'],
                    'non-causal forward occurrence ancestry')
    used_parents=[]
    for b in batches:
        require(type(b) is dict and type(b.get('parents')) is list and
                type(b.get('tick')) is int and type(b.get('node')) is str and
                type(b.get('channels')) is list,'malformed forward batch')
        for pid in b['parents']:
            require(pid in byid and byid[pid]['target']==b['node'] and
                    byid[pid]['delivered_at']<=b['tick'] and
                    byid[pid]['channel'] in b['channels'],
                    'forward batch parent is not a delivered input')
            used_parents.append(pid)
    require(len(used_parents)==len(set(used_parents)) and set(used_parents)==set(byid),
            'every occurrence must be consumed exactly once')
    return byid,occ_rows

def _ancestors(oid,byid):
    stack=[oid];seen=set(); result=set()
    while stack:
        cur=stack.pop()
        if cur in seen: continue  # convergence is valid; temporal checks reject cycles.
        seen.add(cur)
        for p in byid[cur]['parents']:
            require(p in byid,'unknown causal ancestor')
            result.add(p);stack.append(p)
    return result

def _feedback(feedback,byid):
    require(type(feedback) is dict and
            all(type(feedback.get(k)) is list for k in ('assessments','deliveries','link_grants')),
            'missing native ON feedback records')
    assessment={}
    for a in feedback['assessments']:
        require(type(a) is dict and type(a.get('id')) is str and a['id'] not in assessment
                and type(a.get('tick')) is int and type(a.get('input_occurrences')) is list,
                'malformed native assessment')
        for p in a['input_occurrences']:
            require(p in byid and byid[p]['target']==a['observer'] and
                    byid[p]['delivered_at']<=a['tick'],
                    'assessment cannot cite this original occurrence')
        assessment[a['id']]=a
    deliveries=[]
    for x in feedback['deliveries']:
        require(type(x) is dict and x.get('assessment_id') in assessment and
                type(x.get('evidence_ids')) is list and len(x['evidence_ids'])>0 and
                len(set(x['evidence_ids']))==len(x['evidence_ids']) and
                type(x.get('tick')) is int and type(x.get('independent_receiver')) is bool,
                'invalid reverse feedback record')
        for p in x['evidence_ids']:
            require(p in byid and byid[p]['target']==x.get('sender') and
                    byid[p]['source']==x.get('receiver') and
                    byid[p]['delivered_at']<x['tick'],
                    'reverse packet does not follow causal forward parent')
        deliveries.append({'assessment_id':x['assessment_id'],
                 'sender':x['sender'],'receiver':x['receiver'],
                 'evidence_ids':list(x['evidence_ids']),'delivered_at':x['tick'],
                 'native_independent_receiver_flag':x.get('independent_receiver')})
    return len(assessment),deliveries

def analyze(native,off,on,owners,*,v1f):
    require(type(v1f) is dict and v1f.get('schema')==F_SCHEMA and
            v1f.get('status')==F_STATUS and v1f.get('native_judgments_observed')==0 and
            v1f.get('native_updates_applied')==0 and v1f.get('network_event_lineage_attested') is False,
            'unexpected or forged v1f reference')
    require(type(native) is tuple and len(native)==3 and type(owners) is dict,
            'invalid frozen fixture')
    require(snapshot(native)==v1f.get('native_fixture_sha256'),
            'frozen fixture differs from v1f')
    case,fabric,plans=native
    edges=[_edge(e,owners) for e in fabric.static_routes]
    require(0<len(edges)<=128 and len({tuple(x.values()) for x in edges})==len(edges),
            'duplicate or unbounded static routes')
    require(type(off) is dict and off.get('enabled') is False and
            type(on) is dict and on.get('enabled') is True and
            on.get('policy')=='forward-first', 'OFF/ON policies invalid')
    off_id,off_rows=_index_forward(off.get('forward'),edges)
    on_id,on_rows=_index_forward(on.get('forward'),edges)
    grant_evidence_joined=(type(off['forward'].get('link_grants')) is list and
                           type(on['forward'].get('link_grants')) is list)
    require(off['forward']['states']==on['forward']['states'] and
            Counter((x['node_id'],x['channel']) for x in off['forward']['emissions'])==
            Counter((x['node_id'],x['channel']) for x in on['forward']['emissions']) and
            Counter((x['node_id'],x['channel']) for x in off['forward']['terminal'])==
            Counter((x['node_id'],x['channel']) for x in on['forward']['terminal']),
            'ON/OFF forward outcome changed')
    # Route evidence by tuples, not unstable packet ids or timing guarantees.
    off_routes=Counter((o['source'],o['target'],o['sender_channel'],o['receiver_channel']) for o in off_rows)
    on_routes=Counter((o['source'],o['target'],o['sender_channel'],o['receiver_channel']) for o in on_rows)
    require(off_routes==on_routes,'ON/OFF changed original route occurrence multiset')
    assess_count,feedback_rows=_feedback(on.get('feedback'),on_id)
    reach={nid:set() for nid in owners}
    for oid,rec in off_id.items():
        for a in _ancestors(oid,off_id):
            reach[off_id[a]['source']].add(rec['target'])
        reach[rec['source']].add(rec['target'])
    receivers=[]
    for rid in ('B','C'):
        static=[e for e in edges if e['source_node']=='A' and e['target_node']==rid and
                e['source_channel']==7 and e['target_channel']==0]
        dynamic=sum(n for (src,dst,sc,tc),n in off_routes.items()
                    if (src,dst,sc,tc)==('A',rid,7,0))
        recipients_via_ancestry=rid in reach['A']
        receivers.append({'receiver_id':rid,
               'direct_static_route_7_to_0':len(static)>0,
               'direct_original_forward_occurrences':dynamic,
               'observed_original_forward_ancestry_from_A':recipients_via_ancestry,
               'v1e_variant_network_route_replayed':False,
               'native_criterion_or_judgment_from_receiver':False})
    return {'static_routes':edges,'static_route_count':len(edges),
            'original_forward_transport_grants_joined':grant_evidence_joined,
            'transport_temporal_semantics':('GRANT_JOIN_CONFIRMED_NOT_NOMINAL_DELAY_SUM'
                   if grant_evidence_joined else 'NOMINAL_DELAY_ONLY_NO_GRANT_EVIDENCE'),
            'original_off_occurrences':len(off_rows),'original_on_occurrences':len(on_rows),
            'off_route_multiset_equal_on':True,
            'original_off_occurrence_lineage':off_rows,
            'conditional_receiver_route_audit':receivers,
            'native_feedback_assessment_count':assess_count,
            'native_reverse_deliveries':feedback_rows,
            'native_reverse_delivery_count':len(feedback_rows),
            'native_packet_field_independence_is_not_causal_independence':True,
            'v1e_shadow_mapping_promoted_to_live_variant_route':False,
            'endogenous_receiver_judgments':0,'native_updates_applied':0,
            'learning_or_receiver_utility_identified':False}

def build(v1f,v1f_bytes,recomputed_v1f,native,off,on,owners,source_hashes):
    require(v1f==recomputed_v1f,'full v1f source-bound native recomputation mismatch')
    require(type(v1f_bytes) is bytes and len(v1f_bytes)>0,'invalid reference bytes')
    require(snapshot(native)==v1f['native_fixture_sha256'],
            'fixture reference hash changed before lineage audit')
    report=analyze(native,off,on,owners,v1f=v1f)
    return {'schema':SCHEMA,'status':STATUS,'reference_v1f_sha256':sha256(v1f_bytes).hexdigest(),
            'native_fixture_sha256':v1f['native_fixture_sha256'],
            'frozen_native_sources':source_hashes,
            **report,'claims_excluded':EXCLUSIONS}
