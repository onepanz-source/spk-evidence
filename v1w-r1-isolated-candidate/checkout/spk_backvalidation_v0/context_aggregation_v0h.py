"""BV v0h: *read-only* contextual accumulation after verified scheduler replay.

An assessment/receiver is ONE recipient, not one vote per routed path.
All path witnesses are retained; this does not reduce live packet traffic,
measure credit, calibrate quality, or trigger program promotion.
"""
from collections import defaultdict
from spk_backvalidation_v0.identified_audit_v0h import audit_identified_v0h
from spk_backvalidation_v0.contract_v0 import digest

SCHEMA='spk-bv-contextual-receptions/v0h'


def aggregate_context_v0h(case, fabric, result, tplan, pplan, mplan, lplan):
    audit=audit_identified_v0h(case, fabric, result, tplan, pplan, mplan, lplan)
    groups=defaultdict(list)
    for d in result['feedback']['deliveries']:
        groups[(d['assessment_id'],d['receiver'])].append(d)
    rows=[]
    for (aid,receiver),packets in sorted(groups.items()):
        evidence=sorted({oid for p in packets for oid in p['evidence_ids']})
        rows.append({'assessment_id':aid,'receiver':receiver,
            'packets':len(packets),'first_tick':min(p['tick'] for p in packets),
            'last_tick':max(p['tick'] for p in packets),
            'senders':sorted({p['sender'] for p in packets}),
            'packet_ids':sorted(p['packet_id'] for p in packets),
            'causal_evidence_ids':evidence,
            'path_evidence_sets':[{'packet_id':p['packet_id'],
                    'evidence_ids':list(p['evidence_ids'])} for p in
                  sorted(packets,key=lambda p:p['packet_id'])]})
    if len(rows)!=audit['unique_receiver_votes'] or sum(row['packets'] for row in rows)!=audit['feedback_packets']:
        raise ValueError('aggregation must conserve audited packet and receiver cardinality')
    summary={'schema':SCHEMA,'audit_schema':audit['schema'],
        'assessment_receiver_groups':len(rows),'transport_packets':audit['feedback_packets'],
        'duplicate_path_receptions':audit['duplicate_path_receptions'],
        'rows':rows,'claims_excluded':['causal credit','independence between recipients',
            'communication savings','metric calibration','autonomous learning','promotion']}
    return {'summary':summary,'sha256':digest(summary)}
