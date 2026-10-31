"""Independent source-bound accounting for paid derived actor ACK consumption."""
from __future__ import annotations

from collections import Counter
from dataclasses import replace
from hashlib import sha256

from search.spk_bv_v0e_live_evidence import fixture
from spk_architecture_v1.causal_memory_v1c import _reservation, _valid_memory
from spk_architecture_v1.temporal_service_v1b import _valid_plan
from spk_backvalidation_v0.live_dual_scheduler_v0e import LiveBVPlanV0e, execute_live_v0e
from spk_bv_research.grant_rank_integration_v3tuv import ARMS, CAPACITIES, NEW_SCHEDULES
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.off_on_v0t import snapshot
from spk_bv_research.native_ack_actor_loop_v4pqr import _sha_receipt
from spk_bv_research.native_ack_paid_consumer_v4stu import (
    SCHEMA, STATUS, CausalProbeRejected, execute_paid_consumer_probe,
)

SIGNED_V3TUV_SHA = 'f783be9952613aa98eafef59d24c19eb64ccc09d29265017eabb675fe0155827'
SIGNED_V4PQR_SHA = '9e33e4257cfb660861afcfb6f46efc6ee6893e78d060490faaefbd47d0dc5872'
INTERVENTIONS = (
    ('consumer_first', 'consumer-first', True, 256),
    ('native_first', 'native-first', True, 256),
    ('consumer_disabled', 'consumer-off', True, 256),
    ('feedback_disabled', 'consumer-first', False, 256),
    ('zero_credit_policy', 'native-first', True, 0),
)


def require(ok, message):
    if not ok:
        raise CausalProbeRejected(message)


def _native_conservation(replay, case, fabric, pplan, mplan):
    """Reconstruct every PE/domain/link allocation from native event records."""
    nat = replay['native']
    rows = nat['resources']['timeline']
    pe_caps = _valid_plan(fabric, pplan)
    mem_pe_caps, mem_domains = _valid_memory(fabric, mplan)
    batches = nat['forward']['batches']
    bv = nat['feedback']['link_grants']
    ack = replay['derived_actor_ack']['transport_grants']
    services = replay['derived_actor']['consumer_service_grants']
    f_links = nat['forward']['link_grants']
    require(len(rows) == len(set(r['tick'] for r in rows)) and
            all(rows[i]['tick'] == rows[i - 1]['tick'] + 1 for i in range(1, len(rows))),
            'paid-consumer native tick gap/duplicate')
    require(len(services) == nat['resources']['derived_actor_consumer_PE_units'] ==
            nat['resources']['derived_actor_consumer_S_memory_units'] and
            sum(r['derived_actor_consumer_services'] for r in rows) == len(services),
            'paid-consumer PE and S units not recorded')
    require(sum(r['pe_service_total'] for r in rows) ==
            len(batches) + len(bv) + len(ack) + len(services) and
            sum(r['link_total'] for r in rows) == len(f_links) + len(bv) + len(ack) and
            sum(r['memory_total'] for r in rows) ==
            nat['resources']['forward_reserved_memory_units'] + 2 * len(bv) +
            2 * len(ack) + len(services),
            'paid-consumer aggregate PE/link/memory conservation')
    # Independently derive per-PE accounting and O/E/S charges (native forward
    # reservation itself is checked against the frozen memory contract).
    owners = {n.node_id: n.pe_id for n in fabric.placement}
    outgoing = {}
    for edge in fabric.static_routes:
        outgoing.setdefault((edge.source_node, edge.source_channel), []).append(edge)
    for row in rows:
        t = row['tick']
        pe = Counter()
        mem_pe = Counter()
        dom = Counter()
        links = Counter()
        for batch in batches:
            if batch['tick'] != t:
                continue
            nid = batch['node']
            pe[owners[nid]] += 1
            node = next(n for n in case.nodes if n.node_id == nid)
            reserved = _reservation(node, batch['channels'], owners[nid], outgoing)
            for target, domain, _, units in reserved:
                mem_pe[target] += units
                dom[domain] += units
        for grant in bv + ack:
            if grant['tick'] != t:
                continue
            src, dst = grant['source_pe'], grant['target_pe']
            pe[src] += 1
            mem_pe[src] += 1
            mem_pe[dst] += 1
            dom['O'] += 1
            dom['E'] += 1
            links[(src, dst)] += 1
        for grant in services:
            if grant['tick'] != t:
                continue
            owner = grant['owner_pe']
            require(grant['PE_units'] == 1 and grant['memory_domain'] == 'S' and
                    grant['memory_units'] == 1,
                    'paid-consumer grant lacks owner PE/S reservation')
            pe[owner] += 1
            mem_pe[owner] += 1
            dom['S'] += 1
        for grant in f_links:
            if grant['tick'] == t:
                links[(grant['source_pe'],grant['target_pe'])] += 1
        require(dict(sorted(pe.items())) == row['pe_service_by_pe'] and
                dict(sorted(mem_pe.items())) == row['memory_by_pe'] and
                dict(sorted(dom.items())) == row['memory_by_domain'] and
                sum(pe.values()) == row['pe_service_total'] and
                sum(mem_pe.values()) == row['memory_total'] and
                sum(links.values()) == row['link_total'] and
                [[a,b,n] for (a,b),n in sorted(links.items())] ==
                   row['link_by_direction'] and
                row['derived_actor_ACK_sends'] == sum(a['tick'] == t for a in ack) and
                row['derived_actor_consumer_services'] == sum(s['tick'] == t for s in services),
                'paid-consumer per-tick resource or service ledger forged')
        require(sum(pe.values()) <= pplan.fabric_slots_per_tick and
                all(pe[pid] <= cap for pid, cap in pe_caps.items()) and
                sum(dom.values()) <= mplan.fabric_slots_per_tick and
                all(mem_pe[pid] <= cap for pid, cap in mem_pe_caps.items()) and
                all(dom[d] <= cap for d, cap in mem_domains.items()),
                'paid-consumer resource overcommit')


def conservation(replay, case, fabric, pplan, mplan):
    _native_conservation(replay, case, fabric, pplan, mplan)
    derived = replay['derived_actor']
    ack = replay['derived_actor_ack']
    judgments = derived['judgments']
    grants = ack['transport_grants']
    deliveries = ack['transport_deliveries']
    receipts = derived['applied_receipts']
    services = derived['consumer_service_grants']
    require(len(judgments) == ack['requests'] == len(grants) == len(deliveries) and
            [j['identity'] for j in judgments] ==
            [g['identity'] for g in grants] ==
            [d['identity'] for d in deliveries] and
            derived['pending_consumer_queue_end'] == 0 and
            replay['native_actor_credit_applied'] is False and
            replay['native_learning_implemented'] is False,
            'paid-consumer ACK custody/completion or native boundary broken')
    source_occ = {o['id']:o for o in replay['native']['forward']['occurrences']}
    batches = {(b['node'],b['tick']):b for b in replay['native']['forward']['batches']}
    for j, g, d in zip(judgments, grants, deliveries):
        occ = source_occ.get(j['source_emission'])
        batch = batches.get((j['issuer'],j['created_tick']))
        require(occ is not None and batch is not None and
                occ['source'] == j['recipient'] and occ['target'] == j['issuer'] and
                occ['delivered_at'] == j['ingress_tick'] and
                j['source_emission'] in batch['parents'] and
                j['response'] == (1 if batch['outputs'] else -1) and
                j['emitted_tick'] < j['ingress_tick'] <= j['created_tick'] <
                    j['ready_tick'] <= g['tick'] < g['delivered_at'] == d['tick'] and
                (g['source_pe'],g['target_pe']) == (j['source_pe'],j['target_pe']) and
                d['target_pe'] == j['target_pe'],
                'paid-consumer ACK semantic source, time or owner forged')
    roots = {n:'0'*64 for n in derived['receipt_roots']}
    balances = {n:0 for n in roots}
    seq = Counter()
    seen = set()
    by_j = {j['identity']:j for j in judgments}
    by_d = {d['identity']:d for d in deliveries}
    require([s['identity'] for s in services] == [r['judgment_id'] for r in receipts] and
            len(services) == ack['applied_actor_credits'] ==
            ack['owner_ACK_FIFOs_decremented'] and
            len(services) == sum(bool(d['actor_credit_applied']) for d in deliveries),
            'paid-consumer service is disconnected from credits')
    for service, receipt in zip(services, receipts):
        oid = receipt['judgment_id']
        j = by_j.get(oid)
        d = by_d.get(oid)
        require(j is not None and d is not None and oid not in seen and
                service['tick'] == receipt['consumer_tick'] == d['consumer_tick'] and
                service['delivery_tick'] == receipt['delivery_tick'] == d['tick'] and
                service['tick'] >= d['tick'] and
                service['wait'] == service['tick'] - service['delivery_tick'] and
                service['owner_pe'] == j['target_pe'] == receipt['owner_pe'] and
                receipt['actor'] == j['recipient'] and
                receipt['issuer'] == j['issuer'] and
                receipt['source_emission'] == j['source_emission'] and
                receipt['response'] == j['response'] and
                receipt['credit_before'] == balances[j['recipient']] and
                receipt['credit_after'] == balances[j['recipient']] + j['response'] and
                receipt['chain_prev'] == roots[j['recipient']] and
                receipt['seq'] == seq[j['recipient']] + 1 and
                abs(receipt['credit_after']) <= derived['max_abs_actor_credit'] and
                receipt['consumer_PE_units'] == 1 and
                receipt['consumer_S_memory_units'] == 1,
                'paid-consumer receipt fabricated/unpaid/reordered')
        event = dict(receipt)
        digest = event.pop('chain_digest')
        require(_sha_receipt(event) == digest,
                'paid-consumer receipt hash forgery')
        seen.add(oid)
        roots[j['recipient']] = digest
        balances[j['recipient']] = receipt['credit_after']
        seq[j['recipient']] += 1
    require(roots == derived['receipt_roots'] and
            balances == derived['applied_credit_by_actor'] and
            all(d['identity'] not in seen for d in deliveries
                if d.get('actor_credit_denied_by_policy') or d.get('consumer_disabled')) and
            len(receipts) + len(derived['unserved_deliveries']) +
              sum(d.get('actor_credit_denied_by_policy') is True for d in deliveries)
              == len(judgments),
            'paid-consumer chains/unserved ACK custody not closed')
    require(derived['consumer_policy'] != 'consumer-off' or not receipts,
            'disabled paid-consumer incorrectly adopted actor credit')


def null_native_parity(native, replay):
    own = replay['native']
    rows = [{k:v for k,v in row.items()
             if k not in ('derived_actor_ACK_sends','derived_actor_consumer_services')}
            for row in own['resources']['timeline']]
    resources = {k:v for k,v in own['resources'].items()
                 if k not in ('derived_actor_consumer_PE_units',
                              'derived_actor_consumer_S_memory_units')}
    resources['timeline'] = rows
    return (own['forward'] == native['forward'] and
            own['feedback'] == native['feedback'] and
            resources == native['resources'] and
            replay['derived_actor_ack']['requests'] == 0 and
            not replay['derived_actor']['applied_receipts'])


def evaluate(v3, raw3, v4p, raw4p, *, fixture_fn=fixture,
             native_executor=execute_live_v0e,
             derived_executor=execute_paid_consumer_probe):
    require(type(v3) is dict and type(raw3) is bytes and
            canon(v3) == raw3 and sha256(raw3).hexdigest() == SIGNED_V3TUV_SHA and
            type(v4p) is dict and type(raw4p) is bytes and
            canon(v4p) == raw4p and sha256(raw4p).hexdigest() == SIGNED_V4PQR_SHA and
            v4p['signed_v3tuv_sha256'] == SIGNED_V3TUV_SHA and
            v4p['totals']['original_native_replays'] == 18 and
            v4p['totals']['derived_scenarios'] == 72 and
            v4p['native_learning_implemented'] is False and
            v4p['native_actor_ACK_consumer_implemented'] is False,
            'v4stu signed predecessors/canonical SHA invalid')
    totals = Counter()
    scenarios = []
    for source, (schedule,ticks) in zip(v3['source_matrix'], NEW_SCHEDULES):
        require(source['schedule'] == schedule and
                source['source_external_ticks'] == list(ticks),
                'v4stu signed native schedule drift')
        case,fabric,plans = fixture_fn(ticks=ticks)
        for mode, (name,enabled,priority) in zip(source['modes'], ARMS):
            require(mode['mode'] == name, 'v4stu source BV mode drift')
            for capacity,cap in zip(mode['capacities'],CAPACITIES):
                require(capacity['native_PE_capacity'] == cap,
                        'v4stu native source capacity drift')
                pplan = replace(plans[1],fabric_slots_per_tick=cap)
                bv = LiveBVPlanV0e(enabled=enabled,priority=priority)
                native = native_executor(case,fabric,plans[0],pplan,plans[2],plans[3],bv)
                require(snapshot(native) == capacity['original_native_sha256'],
                        'v4stu frozen native source trace drift')
                totals['original_native_replays'] += 1
                for variant,consumer_policy,feedback,credit_bound in INTERVENTIONS:
                    r = derived_executor(case,fabric,plans[0],pplan,plans[2],
                                         plans[3],bv,consumer_policy=consumer_policy,
                                         feedback=feedback,
                                         max_abs_actor_credit=credit_bound)
                    conservation(r,case,fabric,pplan,plans[2])
                    d = r['derived_actor']
                    a = r['derived_actor_ack']
                    n = r['native']
                    require(a['requests'] == (16 if feedback else 0),
                            'v4stu signed native source judgments mismatch')
                    if variant == 'feedback_disabled':
                        require(null_native_parity(native,r),
                                'v4stu zero-intervention native bitwise parity failed')
                        totals['null_native_exact_parity'] += 1
                    if variant == 'consumer_disabled':
                        require(not d['applied_receipts'] and
                                len(d['unserved_deliveries']) == a['requests'],
                                'v4stu consumer-disabled did not preserve real delivery')
                    if variant == 'zero_credit_policy':
                        require(not d['applied_receipts'] and
                                all(x.get('actor_credit_denied_by_policy')
                                    for x in a['transport_deliveries']),
                                'v4stu zero actor-credit denial is not explicit')
                    if variant in ('consumer_first','native_first'):
                        require(len(d['applied_receipts']) == a['requests'] and
                                all(not x.get('actor_credit_denied_by_policy')
                                    for x in a['transport_deliveries']),
                                'v4stu paid consumer normal receipts missing')
                    totals['derived_scenarios'] += 1
                    totals['generated_judgments'] += a['requests']
                    totals['actual_ACK_transport_deliveries'] += len(a['transport_deliveries'])
                    totals['paid_consumer_services'] += len(d['consumer_service_grants'])
                    totals['consumer_disabled_deliveries'] += len(d['unserved_deliveries'])
                    totals['credit_policy_denials'] += sum(
                        x.get('actor_credit_denied_by_policy') is True
                        for x in a['transport_deliveries'])
                    totals['native_forward_changed_scenarios'] += int(
                        n['forward'] != native['forward'])
                    scenarios.append({
                        'schedule':schedule,'mode':name,
                        'native_global_PE_capacity':cap,'variant':variant,
                        'originated_judgments':a['requests'],
                        'transport_delivered':len(a['transport_deliveries']),
                        'paid_consumer_services':len(d['consumer_service_grants']),
                        'maximum_consumer_wait_ticks':max(
                            [s['wait'] for s in d['consumer_service_grants']],default=0),
                        'native_forward_equal':n['forward'] == native['forward'],
                        'native_BV_equal':n['feedback'] == native['feedback'],
                        'native_final_states_equal':n['forward']['states'] ==
                            native['forward']['states'],
                    })
    require(len(v3['source_matrix']) == 3 and
            totals['original_native_replays'] == 18 and
            totals['derived_scenarios'] == 18*len(INTERVENTIONS) and
            totals['null_native_exact_parity'] == 18 and
            totals['actual_ACK_transport_deliveries'] == totals['generated_judgments'] ==
              18*4*16 and
            totals['paid_consumer_services'] == 18*2*16 and
            totals['consumer_disabled_deliveries'] == 18*16 and
            totals['credit_policy_denials'] == 18*16 and
            totals['native_forward_changed_scenarios'] > 0,
            'v4stu finite source matrix causal consumer study incomplete')
    return {
        'schema':SCHEMA, 'status':STATUS,
        'signed_v3tuv_sha256':sha256(raw3).hexdigest(),
        'signed_v4pqr_sha256':sha256(raw4p).hexdigest(),
        'native_reference':'PINNED_V0E_AND_CAUSAL_V4MNO',
        'causal_actor_source':'ACTUAL_REEXECUTED_RECEIVER_BATCH',
        'credit_target':'DERIVED_ACTOR_REGISTER_ONLY',
        'consumer_hypothesis':'ONE_OWNER_PE_AND_ONE_OWNER_S_MEMORY_SERVICE_PER_APPLIED_RECEIPT',
        'policies':list(x[0] for x in INTERVENTIONS),
        'totals':dict(sorted(totals.items())),
        'scenarios':scenarios,
        'native_v0e_modified':False,
        'native_Architecture_v1_modified':False,
        'native_learning_implemented':False,
        'native_actor_consumer_implemented':False,
        'claims_excluded':[
            'a charged derived-actor consumption turn is a modeling assumption, not a measured hardware cost',
            'derived consumer FIFO/hash chain is not frozen-native learner authority or adaptive weight update',
            'one-PE/one-S policy denies represent policy, not negative judgments or lost transport',
            'credit-denial policy checks are not separately charged native computations',
            'hash receipts do not authenticate physical mesh peers',
            'no general liveness guarantees, topology generalization, hardware power or energy claims',
        ],
        'next_gate':'NATIVE_LEARNING_AUTHORITY_NOT_IMPLEMENTED',
    }
