"""Independent, read-only closure audit of N-node BV v0h identified traces.

This does not execute neurons or award causal credit: it checks that a
*CLOSED* trace has coherent event ancestry, actual return-path custody,
per-assessment vote deduplication, and shared per-tick resource use.
Not an A3d verifier or a proof of counterfactual influence.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from spk_backvalidation_v0.identified_scheduler_v0h import SCHEMA as LIVE_SCHEMA

SCHEMA = 'spk-bv-identified-causal-audit/v0h'


class CausalAuditRejected(ValueError):
    pass


def _check(ok, msg):
    if not ok:
        raise CausalAuditRejected(msg)


def audit_identified_v0h(case, fabric, result, tplan, pplan, mplan, lplan):
    """Verify a fully completed N-node research run with independent accounting.

    Incoming occurrences are *batch inputs*, not proven causal influence.
    Feedback observations remain untrusted as estimates of global benefit.
    """
    _check(isinstance(result, dict) and result.get('schema') == LIVE_SCHEMA,
           'not an identified N-node BV v0h trace')
    fwd = result['forward']; fb = result['feedback']; res = result['resources']
    owner = {p.node_id: p.pe_id for p in fabric.placement}
    nodes = {n.node_id for n in case.nodes}
    _check(set(owner) == nodes and len(nodes) == result['population']['neurons'],
           'invalid neuron/PE custody')
    _check(len(fabric.pe_ids) == result['population']['pe_count'],
           'inconsistent PE count')
    routes = Counter((e.source_node, e.source_channel, e.target_node,
                      e.target_channel, e.delay_ticks) for e in case.edges)

    # Batch identity must be unique even for two executions of the same neuron
    # in the same logical tick. No ambiguous (node, tick) surrogate key.
    batches = {}
    batch_parents = Counter()
    for b in fwd['batches']:
        bid=b.get('batch_id')
        _check(type(bid) is str and bid and bid not in batches,
               'missing/duplicate batch identity')
        _check(b['node'] in nodes and b['parents'] == sorted(set(b['parents'])),
               'invalid neuron batch/ancestry')
        batches[bid]=b
        batch_parents.update(b['parents'])
    _check(set(batches)=={f'b{i}' for i in range(1,len(batches)+1)},
           'noncanonical batch identity sequence')

    # Each output instruction occurrence has its own identity. An output
    # channel may occur multiple times in one batch; a neuron may process
    # multiple batches at the same tick.
    em = {}
    observed_outputs = Counter()
    for e in fwd['emissions']:
        eid=e.get('emission_id'); bid=e.get('batch_id')
        _check(type(eid) is str and eid and eid not in em and bid in batches,
               'missing/duplicate emission identity')
        b=batches[bid]
        _check(e['timestamp']==b['tick'] and e['node_id']==b['node'],
               'emission/batch custody mismatch')
        em[eid]=e
        observed_outputs[(bid,e['channel'])]+=1
    _check(set(em)=={f'e{i}' for i in range(1,len(em)+1)},
           'noncanonical emission identity sequence')
    expected_outputs=Counter((bid,ch) for bid,b in batches.items()
                             for ch in b['outputs'])
    _check(observed_outputs==expected_outputs,
           'emission differs from its identified computation batch')

    terminals={}
    for t in fwd['terminal']:
        eid=t.get('emission_id'); bid=t.get('batch_id')
        _check(eid in em and eid not in terminals and bid==em[eid]['batch_id'] and
               (t['timestamp'],t['node_id'],t['channel'])==
               (em[eid]['timestamp'],em[eid]['node_id'],em[eid]['channel']),
               'terminal identity/custody mismatch')
        terminals[eid]=t
    expected_terminals={eid for eid,e in em.items() if not any(
        src==e['node_id'] and sc==e['channel']
        for src,sc,_,_,_ in routes)}
    _check(set(terminals)==expected_terminals,
           'terminal emission not derived from route table')

    occ = {}
    observed_routes = Counter()
    for o in fwd['occurrences']:
        oid=o['id']; bid=o.get('batch_id'); eid=o.get('emission_id')
        _check(oid not in occ, 'duplicate routed occurrence')
        _check(eid in em and bid in batches and em[eid]['batch_id']==bid and
               o['emitted_at']==em[eid]['timestamp'] and
               o['source']==em[eid]['node_id'],
               'routed occurrence without identified source emission')
        _check(o['source'] in nodes and o['target'] in nodes and
               o['source_pe']==owner[o['source']] and
               o['target_pe']==owner[o['target']],
               'occurrence PE custody forged')
        _check(list(o['parents'])==batches[bid]['parents'],
               'source batch ancestry mismatch')
        _check(type(o['delivered_at']) is int and
               o['delivered_at']>o['emitted_at'] and
               type(o['delay']) is int and o['delay']>0,
               'noncausal occurrence timing')
        _check(batch_parents[oid]==1,
               'occurrence missing or multiply consumed')
        occ[oid]=o
        observed_routes[(eid,o['target'],o['channel'],o['delay'])]+=1
    for b in batches.values():
        for oid in b['parents']:
            _check(oid in occ and occ[oid]['target']==b['node'] and
                   occ[oid]['delivered_at']<=b['tick'],
                   'batch parent not delivered or from wrong neuron')

    # All consumed input groups must be accounted for, independently of
    # which service tick accepted them. A ready group can execute at most once.
    expected_inputs=defaultdict(list)
    expected_parents=defaultdict(list)
    for e in case.events:
        expected_inputs[(e.timestamp,e.node_id)].append(e.channel)
    for oid,o in occ.items():
        key=(o['delivered_at'],o['target'])
        expected_inputs[key].append(o['channel'])
        expected_parents[key].append(oid)
    seen_ready=set()
    for b in batches.values():
        key=(b['ready'],b['node'])
        _check(key not in seen_ready and b['ready']<=b['tick'],
               'invalid/duplicated scheduled ready group')
        _check(sorted(b['channels'])==sorted(expected_inputs[key]) and
               b['parents']==sorted(expected_parents[key]),
               'scheduled neuron inputs not reconstructable from actual events')
        seen_ready.add(key)
    _check(seen_ready==set(expected_inputs),
           'unconsumed external or routed event ready group')

    expected_routes=Counter()
    for eid,e in em.items():
        for (src,sc,dst,dc,delay),multiplicity in routes.items():
            if src==e['node_id'] and sc==e['channel']:
                expected_routes[(eid,dst,dc,delay)]+=multiplicity
    _check(observed_routes==expected_routes,
           'routed emission/edge multiplicity differs from graph')

    fg_by_id = {}
    for g in fwd['link_grants']:
        oid = g['id']
        _check(oid in occ and oid not in fg_by_id, 'unmatched/duplicate forward link grant')
        o = occ[oid]
        _check(o['source_pe'] != o['target_pe'] and
               all(g[k] == o[k] for k in ('source', 'target', 'source_pe', 'target_pe')),
               'forward link custody wrong')
        _check(g['tick'] >= o['emitted_at'] and
               g['delivered_at'] == o['delivered_at'], 'forward grant timing wrong')
        _check(g['delivered_at'] > g['tick'], 'noncausal forward link grant')
        fg_by_id[oid] = g
    for oid, o in occ.items():
        if o['source_pe'] == o['target_pe']:
            _check(oid not in fg_by_id and
                   o['delivered_at'] == o['emitted_at'] + o['delay'],
                   'local route incorrectly granted or delayed')
        else:
            _check(oid in fg_by_id and
                   o['delivered_at'] == fg_by_id[oid]['tick'] +
                   o['delay'] + tplan.cross_pe_extra_ticks,
                   'cross-PE grant/route timing wrong')

    assessment={}
    assessed_emissions=set()
    for a in fb['assessments']:
        aid=a['id']; bid=a.get('batch_id'); eid=a.get('terminal_emission_id')
        _check(aid not in assessment and eid not in assessed_emissions and bid in batches and eid in terminals,
               'assessment missing identified terminal emission')
        b=batches[bid]; t=terminals[eid]
        _check(t['batch_id']==bid and
               (a['tick'],a['observer'])==(t['timestamp'],t['node_id']) and
               a['input_occurrences']==b['parents'],
               'assessment input ancestry/custody forged')
        assessment[aid]=a
        assessed_emissions.add(eid)
    ancestors = {}
    for aid, a in assessment.items():
        visited = set(); stack = list(a['input_occurrences'])
        while stack:
            oid = stack.pop()
            _check(oid in occ, 'assessment references unknown ancestor')
            if oid in visited:
                continue
            visited.add(oid)
            stack.extend(occ[oid]['parents'])
        ancestors[aid] = visited

    grants = {}
    for g in fb['link_grants']:
        pid = g['packet_id']
        _check(pid not in grants and g['assessment_id'] in assessment,
               'unknown/duplicate feedback packet')
        _check(g['sender'] in nodes and g['receiver'] in nodes and
               g['source_pe'] == owner[g['sender']] and
               g['target_pe'] == owner[g['receiver']],
               'feedback neuron/PE custody forged')
        _check(g['cross_pe'] == (g['source_pe'] != g['target_pe']) and
               g['delivered_at'] > g['tick'], 'feedback delay/PE locality forged')
        _check(g['tick'] >= assessment[g['assessment_id']]['tick'],
               'feedback predates its assessment')
        grants[pid] = g
    deliveries = fb['deliveries']
    _check(len(deliveries) == len(grants), 'lost or multiply delivered feedback packet')
    received = set()
    received_before = defaultdict(dict)
    for d in deliveries:
        pid = d['packet_id']
        _check(pid in grants and pid not in received, 'duplicate/missing BV delivery grant')
        g = grants[pid]; aid = d['assessment_id']
        _check(aid == g['assessment_id'] and
               d['sender'] == g['sender'] and d['receiver'] == g['receiver'] and
               d['tick'] == g['delivered_at'], 'feedback grant/delivery mismatch')
        _check(d['evidence_ids'] == sorted(set(d['evidence_ids'])) and
               bool(d['evidence_ids']), 'invalid BV evidence set')
        for oid in d['evidence_ids']:
            _check(oid in ancestors[aid] and
                   occ[oid]['target'] == d['sender'] and
                   occ[oid]['source'] == d['receiver'],
                   'BV evidence is not a real reverse causal link')
        prior = {oid for oid, receipt_tick in received_before[(aid, d['sender'])].items()
                 if receipt_tick <= g['tick']}
        if d['sender'] == assessment[aid]['observer']:
            allowed = set(assessment[aid]['input_occurrences'])
        else:
            allowed = {parent for incoming in prior for parent in occ[incoming]['parents']}
        _check(set(d['evidence_ids']).issubset(allowed),
               'feedback did not originate from a prior contextual reception')
        received_before[(aid, d['receiver'])].update({oid:d['tick'] for oid in d['evidence_ids']})
        received.add(pid)
    _check(len(received) == len(grants), 'unmatched BV transmissions')
    votes = set()
    for d in deliveries:
        key = (d['assessment_id'], d['receiver'])
        expected = key not in votes
        _check(d['independent_receiver'] is expected,
               'path multiplicity inflated independent receivers')
        votes.add(key)
    _check(fb['unique_receiver_votes'] == len(votes),
           'feedback unique-receiver count forged')

    # Reconstruct the shared slot accounting from grants and batches rather
    # than trusting the totals provided by the producing scheduler.
    by_tick = {x['tick']: x for x in res['timeline']}
    _check(len(by_tick) == len(res['timeline']), 'duplicate resource timeline tick')
    for tick, record in by_tick.items():
        fs = [g for g in fwd['link_grants'] if g['tick'] == tick]
        bs = [g for g in fb['link_grants'] if g['tick'] == tick]
        batch = [b for b in fwd['batches'] if b['tick'] == tick]
        links = Counter((g['source_pe'], g['target_pe']) for g in fs)
        links.update((g['source_pe'], g['target_pe']) for g in bs if g['cross_pe'])
        uses = Counter(owner[b['node']] for b in batch)
        uses.update(g['source_pe'] for g in bs)
        _check(record['forward_computations'] == len(batch) and
               record['feedback_sends'] == len(bs), 'per-tick class accounting differs')
        _check(record['pe_service_total'] == sum(uses.values()) and
               record['pe_service_by_pe'] == dict(sorted(uses.items())),
               'per-tick PE capacity accounting differs')
        _check(record['link_total'] == sum(links.values()) and
               record['link_by_direction'] == [[src,dst,n] for (src,dst),n in sorted(links.items())],
               'per-tick link capacity accounting differs')
        _check(record['link_total'] <= lplan.fabric_slots_per_tick and
               all(v <= lplan.link_slots_per_tick for v in links.values()),
               'shared link slots oversubscribed')
        _check(record['pe_service_total'] <= pplan.fabric_slots_per_tick and
               all(v <= dict(pplan.pe_slots)[pe] for pe, v in uses.items()),
               'shared PE service slots oversubscribed')
        _check(record['memory_total'] <= mplan.fabric_slots_per_tick and
               record['memory_total'] == sum(record['memory_by_pe'].values()) and
               record['memory_total'] == sum(record['memory_by_domain'].values()) and
               all(v <= dict(mplan.pe_slots)[p] for p,v in record['memory_by_pe'].items()) and
               all(v <= dict(mplan.domain_slots)[d] for d,v in record['memory_by_domain'].items()),
               'shared memory accounting/quota mismatch')
    _check(all(g['tick'] in by_tick for g in list(fwd['link_grants']) + list(fb['link_grants'])) and
           all(b['tick'] in by_tick for b in fwd['batches']),
           'grant or computation outside accounted timeline')
    _check(sum(row['memory_total'] for row in by_tick.values()) ==
           res['forward_reserved_memory_units'] + 2 * len(grants),
           'forward/BV memory usage cannot be reconciled')
    _check(res['forward_link_grants'] == len(fg_by_id) and
           res['bv_link_grants'] == sum(g['cross_pe'] for g in grants.values()) and
           res['bv_local_sends'] == sum(not g['cross_pe'] for g in grants.values()) and
           res['bv_service_units'] == len(grants) and
           res['bv_memory_units'] == 2 * len(grants),
           'aggregate feedback/forward resource accounting differs')
    return {'schema':SCHEMA, 'status':'IDENTIFIED_CAUSAL_AUDIT_PASS',
            'neurons':len(nodes),'batches':len(batches),'emissions':len(em),
            'occurrences':len(occ),'assessments':len(assessment),
            'feedback_packets':len(grants),'deliveries':len(deliveries),
            'unique_receiver_votes':len(votes),
            'duplicate_path_receptions':len(deliveries)-len(votes),
            'shared_link_grants':len(fg_by_id)+res['bv_link_grants']}
