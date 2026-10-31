"""Independent, read-only closure audit of N-node BV v0f research traces.

This does not execute neurons or award causal credit: it checks that a
*CLOSED* trace has coherent event ancestry, actual return-path custody,
per-assessment vote deduplication, and shared per-tick resource use.
Not an A3d verifier or a proof of counterfactual influence.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from spk_backvalidation_v0.n_node_scheduler_v0f import SCHEMA as LIVE_SCHEMA

SCHEMA = 'spk-bv-causal-closure-audit/v0g'


class CausalAuditRejected(ValueError):
    pass


def _check(ok, msg):
    if not ok:
        raise CausalAuditRejected(msg)


def audit_closed_v0g(case, fabric, result, tplan, pplan, mplan, lplan):
    """Verify a fully completed N-node research run with independent accounting.

    Incoming occurrences are *batch inputs*, not proven causal influence.
    Feedback observations remain untrusted as estimates of global benefit.
    """
    _check(isinstance(result, dict) and result.get('schema') == LIVE_SCHEMA,
           'not a closed N-node BV v0f trace')
    fwd = result['forward']; fb = result['feedback']; res = result['resources']
    owner = {p.node_id: p.pe_id for p in fabric.placement}
    nodes = {n.node_id for n in case.nodes}
    _check(set(owner) == nodes and len(nodes) == result['population']['neurons'],
           'invalid neuron/PE custody')
    _check(len(fabric.pe_ids) == result['population']['pe_count'],
           'inconsistent PE count')
    routes = Counter((e.source_node, e.source_channel, e.target_node,
                      e.target_channel, e.delay_ticks) for e in case.edges)

    batches = {}
    batch_parents = Counter()
    expected_emissions = []
    for b in fwd['batches']:
        key = (b['node'], b['tick'])
        _check(b['node'] in nodes, 'invalid neuron batch')
        _check(key not in batches, 'batch identity ambiguity: same neuron/tick')
        _check(b['parents'] == sorted(set(b['parents'])), 'duplicated/unsorted batch parent')
        batches[key] = b
        batch_parents.update(b['parents'])
        expected_emissions.extend((b['tick'], b['node'], ch) for ch in b['outputs'])
    emissions = [(e['timestamp'], e['node_id'], e['channel']) for e in fwd['emissions']]
    _check(Counter(expected_emissions) == Counter(emissions), 'emission differs from computed batches')
    no_routes = {(nid, ch) for _, nid, ch in emissions
                 if not any(src == nid and source_ch == ch
                            for src, source_ch, _, _, _ in routes)}
    expected_terminal = Counter((tick, nid, ch) for tick, nid, ch in emissions
                                if (nid, ch) in no_routes)
    terminal = Counter((e['timestamp'], e['node_id'], e['channel']) for e in fwd['terminal'])
    _check(terminal == expected_terminal, 'terminal emission not derived from route table')

    occ = {}
    observed_routes = Counter()
    for o in fwd['occurrences']:
        oid = o['id']
        _check(oid not in occ, 'duplicate routed occurrence')
        _check(o['source'] in nodes and o['target'] in nodes, 'unknown occurrence neuron')
        _check(o['source_pe'] == owner[o['source']] and
               o['target_pe'] == owner[o['target']], 'occurrence PE custody forged')
        key = (o['source'], o['emitted_at'])
        _check(key in batches, 'occurrence without source batch')
        _check(list(o['parents']) == batches[key]['parents'], 'source batch ancestry mismatch')
        _check(isinstance(o['delivered_at'], int) and
               o['delivered_at'] > o['emitted_at'], 'noncausal occurrence timing')
        _check(isinstance(o['delay'], int) and o['delay'] > 0,
               'invalid occurrence edge delay')
        _check(batch_parents[oid] == 1, 'occurrence missing or multiply consumed')
        occ[oid] = o
        observed_routes[(o['source'], o['emitted_at'], o['target'],
                         o['channel'], o['delay'])] += 1
    for b in batches.values():
        for oid in b['parents']:
            _check(oid in occ and occ[oid]['target'] == b['node'] and
                   occ[oid]['delivered_at'] <= b['tick'],
                   'batch parent not delivered or from wrong neuron')
    # A batch's ready timestamp must be traceable to actual external events
    # and routed deliveries, not just to plausible-looking parent IDs.
    expected_inputs = defaultdict(list)
    expected_parents = defaultdict(list)
    for e in case.events:
        expected_inputs[(e.timestamp, e.node_id)].append(e.channel)
    for oid, o in occ.items():
        ready_key = (o['delivered_at'], o['target'])
        expected_inputs[ready_key].append(o['channel'])
        expected_parents[ready_key].append(oid)
    seen_ready = set()
    for b in batches.values():
        ready_key = (b['ready'], b['node'])
        _check(ready_key not in seen_ready and b['ready'] <= b['tick'],
               'invalid/duplicated scheduled ready group')
        _check(sorted(b['channels']) == sorted(expected_inputs[ready_key]) and
               b['parents'] == sorted(expected_parents[ready_key]),
               'scheduled neuron inputs not reconstructable from actual events')
        seen_ready.add(ready_key)
    _check(seen_ready == set(expected_inputs),
           'unconsumed external or routed event ready group')
    # Source-channel information is reconstructed from emitted output and
    # route multiplicity. Distinct parallel edge occurrences remain distinct.
    expected_routes = Counter()
    for tick, src, ch in emissions:
        for (s, sc, dst, dc, delay), multiplicity in routes.items():
            if s == src and sc == ch:
                expected_routes[(src, tick, dst, dc, delay)] += multiplicity
    _check(observed_routes == expected_routes, 'routed occurrence multiplicity differs from emitted graph')

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

    assessment = {}
    terminal_pairs = {(e['timestamp'], e['node_id']) for e in fwd['terminal']}
    for a in fb['assessments']:
        aid = a['id']
        _check(aid not in assessment and (a['tick'], a['observer']) in terminal_pairs,
               'assessment not anchored to actual terminal event')
        key = (a['observer'], a['tick'])
        _check(key in batches and a['input_occurrences'] == batches[key]['parents'],
               'assessment input ancestry forged')
        assessment[aid] = a
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
    return {'schema':SCHEMA, 'status':'CAUSAL_CLOSURE_AUDIT_PASS',
            'neurons':len(nodes),'occurrences':len(occ),'assessments':len(assessment),
            'feedback_packets':len(grants),'deliveries':len(deliveries),
            'unique_receiver_votes':len(votes),
            'duplicate_path_receptions':len(deliveries)-len(votes),
            'shared_link_grants':len(fg_by_id)+res['bv_link_grants']}
