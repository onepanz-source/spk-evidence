"""BV v0c: sidecar budgeted causal-feedback delivery over validated event evidence.

Research adapter, NOT integration in frozen Network/PE/A3d transport. All messages
consume explicit abstract budgets, but not actual memory/energy in frozen engines.
"""
from __future__ import annotations

from collections import defaultdict, deque

from spk_backvalidation_v0.contract_v0 import canonical, digest, validate_trace

SCHEMA = 'spk-bv-budgeted-feedback/v0c'
DEFAULT_BUDGET = {
    'max_messages': 16,
    'max_paths': 16,
    'max_hops': 4,
    'max_elapsed_ticks': 32,
    'max_feedback_operations': 64,
    'max_memory_accesses': 64,
    'max_inflight': 4,
    'hop_latency': 1,
    'messages_per_link_per_tick': 1,
}


class FeedbackTransportRejected(ValueError):
    pass


def _reject(s):
    raise FeedbackTransportRejected(s)


def _budget(budget):
    if type(budget) is not dict or set(budget) != set(DEFAULT_BUDGET):
        _reject('invalid complete sidecar budget')
    for k, value in budget.items():
        if type(value) is not int or value < 1 or value > 1_000_000:
            _reject('budget values must be positive bounded integers: ' + k)
    return budget


def _paths_for_assessment(occurrences, a, budget):
    """Enumerate evidence paths, not independent credits; capped against explosion."""
    base = a['occurrence_id']
    q = deque([(base,)])
    paths = []
    while q:
        path = q.popleft()
        if len(paths) >= budget['max_paths']:
            _reject('causal path budget exhausted')
        paths.append(path)
        last = occurrences[path[-1]]
        if last['parent_ids']:
            if len(path) >= budget['max_hops']:
                _reject('causal ancestor exceeds hop budget')
            for pid in sorted(last['parent_ids']):
                if pid in path:
                    _reject('causal cycle in one feedback witness')
                q.append(path + (pid,))
    return paths


def transport_v0c(trace, budget=None):
    """Schedule real abstract feedback packets over reversed *observed* causal links.

    A delivered assessment counts once per receiver even if several paths arrive.
    Every actual packet/hop is counted independently; parallel same-hop links
    with identical sender and receiver are bundled with all route IDs retained.
    All admission is all-or-nothing: no returned partial report on exhaustion.
    """
    validate_trace(trace)   # from frozen BV v0; structurally valid is NOT metric truth
    budget = _budget(dict(DEFAULT_BUDGET) if budget is None else budget)
    occ = {x['id']: x for x in trace['occurrences']}
    assessments = {x['id']: x for x in trace['assessments']}
    groups = {}
    for assessment_id, a in sorted(assessments.items()):
        paths = _paths_for_assessment(occ, a, budget)
        for path in paths:
            j = len(path) - 1
            last = occ[path[-1]]
            sender = a['observer'] if j == 0 else occ[path[-2]]['source']
            target = last['source']
            if sender != last['target']:
                _reject('causal reverse-hop endpoints do not match')
            k = (assessment_id, j, sender, target)
            groups.setdefault(k, set()).add(path[-1])
    # Schedule in nondecreasing depth: all prior contributors arrived before forwarding.
    pending = sorted(groups.items(), key=lambda kv: (kv[0][1], kv[0][0], kv[0][2], kv[0][3]))
    packets = []
    arrivals = defaultdict(list)
    link_load = defaultdict(int)
    for (assessment_id, hop, src, dst), routes in pending:
        if hop == 0:
            ready = assessments[assessment_id]['observed_at']
        else:
            inbound = arrivals[(assessment_id, src, hop-1)]
            if not inbound:
                _reject('forwarding without delivered causal predecessor')
            ready = max(inbound)
        t = ready
        while link_load[(src, dst, t)] >= budget['messages_per_link_per_tick']:
            t += 1
        arrival = t + budget['hop_latency']
        if arrival - assessments[assessment_id]['observed_at'] > budget['max_elapsed_ticks']:
            _reject('sidecar feedback elapsed-time budget exceeded')
        link_load[(src, dst, t)] += 1
        packet = {'assessment_id': assessment_id, 'hop': hop + 1,
                  'sender': src, 'receiver': dst, 'causal_route_ids': sorted(routes),
                  'send_at': t, 'delivered_at': arrival}
        packets.append(packet)
        arrivals[(assessment_id, dst, hop)].append(arrival)
        if len(packets) > budget['max_messages']:
            _reject('sidecar feedback message budget exceeded')
    # Simple declared abstract proxy: local assessment = one operation + one
    # memory write; each physical packet = send + receive + route check, one
    # store and one load; no charges silently attributed to frozen Network.
    ops = len(assessments) + 3 * len(packets)
    accesses = len(assessments) + 2 * len(packets)
    if ops > budget['max_feedback_operations'] or accesses > budget['max_memory_accesses']:
        _reject('sidecar compute/memory budget exceeded')
    max_inflight = 0
    for packet in packets:
        active = sum(p['send_at'] <= packet['send_at'] < p['delivered_at'] for p in packets)
        max_inflight = max(max_inflight, active)
    if max_inflight > budget['max_inflight']:
        _reject('sidecar in-flight slot budget exceeded')
    receiver_set = {(p['assessment_id'], p['receiver']) for p in packets}
    return {'schema': SCHEMA, 'trace_sha256': digest(trace), 'budget_sha256': digest(budget),
            'packets': sorted(packets, key=lambda x: (x['send_at'], x['assessment_id'], x['hop'], x['sender'], x['receiver'])),
            'unique_assessment_receiver_pairs': len(receiver_set),
            'total_assessments': len(assessments),
            'resources': {'feedback_messages': len(packets), 'feedback_operations': ops,
                          'feedback_memory_accesses': accesses, 'peak_inflight': max_inflight,
                          'feedback_words': 4 * len(packets)},
            'claims_excluded': ['network-runtime-BV-service', 'A3d-resource-admission',
                                'hardware-energy', 'true-causal-credit', 'autonomous-learning',
                                'verified-feedback-truth', 'program-promotion']}
