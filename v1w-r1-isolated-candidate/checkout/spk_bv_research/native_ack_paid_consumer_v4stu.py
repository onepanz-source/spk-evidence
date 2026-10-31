"""v4s-v4u: causal native reexecution with paid *derived actor* consumption.

The fixed native v0e scheduler and the v4m causal source are SHA-pinned and
untouched. ACKs are generated from real receiver computations and transported
with v4m O/E/link/PE costs. Only after physical-simulator delivery can a
separate actor-local consumption turn reserve its owner PE and S memory.
This is a research counterfactual, not a native learner or a hardware cost.
"""
from __future__ import annotations

from dataclasses import asdict
from hashlib import sha256
from pathlib import Path

from spk_bv_research.native_ack_causal_replay_v4mno import (
    CausalProbeRejected, SyntheticACKRequest,
)
from spk_bv_research.native_ack_actor_loop_v4pqr import ActorJudgment, _sha_receipt

SCHEMA = 'spk-bv-paid-derived-actor-ACK-consumer/research-v4s-v4u'
STATUS = 'CAUSAL_NATIVE_REEXECUTION_PAID_DERIVED_ACTOR_CONSUMER_NO_NATIVE_LEARNING'
PARENT_SHA = 'b256c82f6452eb39789481d265d6e79bbcb5527e4c8155b66524a0e8d8680261'
ZERO_ROOT = '0' * 64


def _pinned_executable():
    source_path = Path(__file__).with_name('native_ack_causal_replay_v4mno.py')
    raw = source_path.read_bytes()
    if sha256(raw).hexdigest() != PARENT_SHA:
        raise CausalProbeRejected('v4stu pinned native parent source SHA drift')
    source = raw.decode('utf-8')
    begin = source.index('class CausalProbeRejected(ValueError):')
    end = source.index('def _validate_requests(requests, fabric, start, bv):')
    if source[begin:end].count('class SyntheticACKRequest:') != 1:
        raise CausalProbeRejected('v4stu pinned dataclass anchor drift')
    source = source[:begin] + source[end:]
    substitutions = (
        ('    ready_acks = []\n', '''    ready_acks = []
    _v4s_requests, _v4s_judgments, _v4s_receipts = [], [], []
    _v4s_consumer_queue, _v4s_service_grants, _v4s_unserved = [], [], []
    _v4s_seen = set()
    _v4s_balances = {nid: 0 for nid in nodes}
    _v4s_roots = {nid: '0' * 64 for nid in nodes}
'''),
        ('ready_acks or ack_cursor < len(requests)):',
         'ready_acks or _v4s_consumer_queue or ack_cursor < len(requests)):'),
        ("                                       'actor_credit_applied': False})\n", '''                                       'actor_credit_applied': False})
                _v4s_enqueue(item, now, ack_grants, _v4s_requests,
                              _v4s_judgments, _v4s_consumer_queue,
                              _v4s_unserved, ack_deliveries)
'''),
        ('        link_fabric_used = 0\n', '''        link_fabric_used = 0
        if _v4s_policy == 'consumer-first':
            pe_total, mem_total = _v4s_service(
                now, _v4s_consumer_queue, _v4s_receipts,
                _v4s_service_grants, _v4s_balances, _v4s_roots,
                pe_total, mem_total, service_used, mem_pe_used, mem_dom_used,
                pe_caps, mem_pe_caps, mem_domain_caps, pplan, mplan,
                ack_deliveries)
'''),
        ('                for ch in outs:\n', '''                _v4s_generate(now, nid, parents, outs, occurrences, owners,
                              _v4s_requests, _v4s_judgments, _v4s_seen,
                              ready_acks)
                for ch in outs:
'''),
        ('        if (pe_total > pplan.fabric_slots_per_tick or', '''        if _v4s_policy == 'native-first':
            pe_total, mem_total = _v4s_service(
                now, _v4s_consumer_queue, _v4s_receipts,
                _v4s_service_grants, _v4s_balances, _v4s_roots,
                pe_total, mem_total, service_used, mem_pe_used, mem_dom_used,
                pe_caps, mem_pe_caps, mem_domain_caps, pplan, mplan,
                ack_deliveries)
        if (pe_total > pplan.fabric_slots_per_tick or'''),
        ("            'synthetic_ack_sends': sum(a['tick'] == now for a in ack_grants),",
         "            'synthetic_ack_sends': sum(a['tick'] == now for a in ack_grants),\n"
         "            'derived_actor_consumer_services': sum(s['tick'] == now for s in _v4s_service_grants),"),
        ("                          'forward_reserved_memory_units': reserved_memory,",
         "                          'forward_reserved_memory_units': reserved_memory,\n"
         "                          'derived_actor_consumer_PE_units': len(_v4s_service_grants),\n"
         "                          'derived_actor_consumer_S_memory_units': len(_v4s_service_grants),"),
        ('len(ack_deliveries) != len(requests)',
         'len(ack_deliveries) != len(_v4s_requests)'),
        ("'requests': len(requests)", "'requests': len(_v4s_requests)"),
        ("'applied_actor_credits': 0", "'applied_actor_credits': len(_v4s_receipts)"),
        ("'owner_ACK_FIFOs_decremented': 0", "'owner_ACK_FIFOs_decremented': len(_v4s_receipts)"),
        ("'synthetic_ack': {'requests'", "'derived_actor_ack': {'requests'"),
        ("'synthetic_ack_sends'", "'derived_actor_ACK_sends'"),
        ("'synthetic_ack_transport_blocked'", "'derived_actor_ACK_transport_blocked'"),
        ("'real_actor_ACK_evidence': False", "'real_actor_ACK_evidence': True"),
        ("        'native_source_timeline_frozen': False,", '''        'derived_actor': {
            'judgments': [asdict(j) for j in _v4s_judgments],
            'applied_receipts': _v4s_receipts,
            'consumer_service_grants': _v4s_service_grants,
            'unserved_deliveries': _v4s_unserved,
            'pending_consumer_queue_end': len(_v4s_consumer_queue),
            'applied_credit_by_actor': dict(sorted(_v4s_balances.items())),
            'receipt_roots': dict(sorted(_v4s_roots.items())),
            'native_learner_mutations': 0,
        },
        'native_source_timeline_frozen': False,'''),
    )
    for anchor, replacement in substitutions:
        if source.count(anchor) != 1:
            raise CausalProbeRejected('v4stu pinned source anchor drift: ' + anchor[:55])
        source = source.replace(anchor, replacement, 1)
    return compile(source, '<v4stu-pinned-native-causal-fork>', 'exec')


_EXECUTABLE = _pinned_executable()


def execute_paid_consumer_probe(case, fabric, tplan, pplan, mplan, lplan, bv,
                                *, consumer_policy='consumer-first',
                                feedback=True, max_judgments=128,
                                max_abs_actor_credit=256):
    """Charge each actor-credit consumption against native-clock PE and S.

    `consumer-first` reserves PE/S before ACK sends and native computations;
    `native-first` uses same-tick slack after native service; `consumer-off`
    records actual transport as delivered-but-unconsumed. There is no native
    learning and no assumption about real-world hardware instructions.
    """
    if (consumer_policy not in ('consumer-first', 'native-first', 'consumer-off') or
            type(feedback) is not bool or type(max_judgments) is not int or
            not 0 <= max_judgments <= 128 or
            type(max_abs_actor_credit) is not int or
            not 0 <= max_abs_actor_credit <= 512):
        raise CausalProbeRejected('invalid paid derived actor consumer policy')
    seen_delivery = set()
    if not feedback:
        max_judgments = 0

    def generate(now, nid, parents, outs, occurrences, owners,
                 requests, judgments, seen, ready):
        for oid in parents:
            if oid in seen or oid not in occurrences:
                raise CausalProbeRejected('paid consumer native parent forged/duplicated')
            occ = occurrences[oid]
            if (occ['target'] != nid or occ['delivered_at'] is None or
                    occ['delivered_at'] > now or occ['emitted_at'] >= now or
                    owners.get(nid) != occ['target_pe'] or
                    owners.get(occ['source']) != occ['source_pe']):
                raise CausalProbeRejected('paid consumer lacks native ingress provenance')
            seen.add(oid)
            if not feedback:
                continue
            if len(judgments) >= max_judgments:
                raise CausalProbeRejected('paid consumer judgment quota exhausted')
            if occ['source_pe'] == occ['target_pe']:
                raise CausalProbeRejected('local actor ACK unmodeled')
            identity = f'j{len(judgments) + 1}'
            request = SyntheticACKRequest(identity, now + 1,
                                          occ['target_pe'], occ['source_pe'])
            judgment = ActorJudgment(identity, oid, nid, occ['source'],
                                     1 if outs else -1,
                                     occ['emitted_at'], occ['delivered_at'],
                                     now, now + 1,
                                     request.source_pe, request.target_pe)
            judgments.append(judgment)
            requests.append(request)
            ready.append(request)

    def enqueue(request, now, grants, requests, judgments, queue,
                unserved, delivery_rows):
        index = next((i for i, r in enumerate(requests)
                      if r.identity == request.identity), None)
        if (index is None or request.identity in seen_delivery or
                len(requests) != len(judgments)):
            raise CausalProbeRejected('paid consumer duplicate or fabricated receipt')
        j = judgments[index]
        match = [g for g in grants if g['identity'] == j.identity]
        if (len(match) != 1 or match[0]['delivered_at'] != now or
                match[0]['tick'] < j.ready_tick or
                match[0]['source_pe'] != j.source_pe or
                match[0]['target_pe'] != j.target_pe or now <= j.created_tick):
            raise CausalProbeRejected('paid consumer invalid transport custody')
        seen_delivery.add(j.identity)
        if consumer_policy == 'consumer-off':
            delivery_rows[-1]['consumer_disabled'] = True
            unserved.append({'identity': j.identity, 'delivery_tick': now,
                             'reason': 'CONSUMER_DISABLED',
                             'negative_judgment': False})
        else:
            queue.append((j, match[0], now))

    def service(now, queue, receipts, grants, balances, roots,
                pe_total, mem_total, service_used, mem_pe_used, mem_dom_used,
                pe_caps, mem_pe_caps, mem_domain_caps, pplan, mplan,
                ack_deliveries):
        if not queue:
            return pe_total, mem_total
        j, ack_grant, delivered = queue[0]
        owner = j.target_pe
        if (service_used[owner] >= pe_caps[owner] or
                pe_total >= pplan.fabric_slots_per_tick or
                mem_pe_used[owner] >= mem_pe_caps[owner] or
                mem_total >= mplan.fabric_slots_per_tick or
                mem_dom_used['S'] >= mem_domain_caps['S']):
            return pe_total, mem_total
        queue.pop(0)
        before = balances[j.recipient]
        after = before + j.response
        row = next((x for x in ack_deliveries if x['identity'] == j.identity), None)
        if row is None or row['tick'] != delivered or delivered > now:
            raise CausalProbeRejected('consumer paid without prior delivered ACK')
        # Credit policy evaluation itself is not represented as a PE-consuming
        # native computation. Denial records are not lost/negative ACKs.
        if abs(after) > max_abs_actor_credit:
            row['actor_credit_denied_by_policy'] = True
            return pe_total, mem_total
        pe_total += 1
        service_used[owner] += 1
        mem_total += 1
        mem_pe_used[owner] += 1
        mem_dom_used['S'] += 1
        seq = 1 + sum(x['actor'] == j.recipient for x in receipts)
        grant = {'identity': j.identity, 'tick': now, 'owner_pe': owner,
                 'memory_domain': 'S', 'memory_units': 1, 'PE_units': 1,
                 'delivery_tick': delivered, 'wait': now - delivered}
        grants.append(grant)
        receipt = {
            'actor': j.recipient, 'owner_pe': owner, 'issuer': j.issuer,
            'source_emission': j.source_emission, 'judgment_id': j.identity,
            'response': j.response, 'seq': seq,
            'created_tick': j.created_tick, 'grant_tick': ack_grant['tick'],
            'delivery_tick': delivered, 'consumer_tick': now,
            'credit_before': before, 'credit_after': after,
            'consumer_PE_units': 1, 'consumer_S_memory_units': 1,
            'chain_prev': roots[j.recipient],
        }
        receipt['chain_digest'] = _sha_receipt(receipt)
        receipts.append(receipt)
        balances[j.recipient] = after
        roots[j.recipient] = receipt['chain_digest']
        row['actor_credit_applied'] = True
        row['consumer_tick'] = now
        return pe_total, mem_total

    namespace = {
        '__name__': 'spk_bv_research.v4stu_fork',
        '_v4s_policy': consumer_policy,
        '_v4s_generate': generate, '_v4s_enqueue': enqueue,
        '_v4s_service': service,
        'asdict': asdict, 'CausalProbeRejected': CausalProbeRejected,
        'SyntheticACKRequest': SyntheticACKRequest,
    }
    exec(_EXECUTABLE, namespace)
    result = namespace['execute_causal_probe'](
        case, fabric, tplan, pplan, mplan, lplan, bv, ())
    derived = result['derived_actor']
    ack = result['derived_actor_ack']
    if (ack['requests'] != len(derived['judgments']) or
            ack['requests'] != len(ack['transport_deliveries']) or
            ack['requests'] != len(seen_delivery) or
            derived['pending_consumer_queue_end'] or
            len(derived['consumer_service_grants']) != len(derived['applied_receipts'])):
        raise CausalProbeRejected('paid consumer not causally closed')
    result['schema'] = SCHEMA
    result['status'] = STATUS
    result['derived_actor']['consumer_policy'] = consumer_policy
    result['derived_actor']['feedback_enabled'] = feedback
    result['derived_actor']['max_abs_actor_credit'] = max_abs_actor_credit
    result['native_actor_credit_applied'] = False
    result['native_learning_implemented'] = False
    return result
