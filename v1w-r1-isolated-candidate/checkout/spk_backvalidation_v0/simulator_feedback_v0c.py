"""Capture/independently replay *real* frozen Network/PE traces, sidecar BV transport.

The spike route observations come from Network v0 and three independent A1b
placements. Only the feedback sidecar (not the frozen runtime) sends BV packets.
"""
from __future__ import annotations

from dataclasses import asdict

from search.spk_24n_independent_oracle_v0 import CaseV0, NodeV0, EdgeV0, EventV0
from spk_backvalidation_v0.contract_v0 import canonical, digest, strict_loads, validate_trace
from spk_backvalidation_v0.budgeted_feedback_v0c import DEFAULT_BUDGET, FeedbackTransportRejected, transport_v0c
from spk_backvalidation_v0.simulator_evidence_v0b import (OLD, NEW, RELAY,
                                                        FROZEN_COMMIT, _run)

SCHEMA = 'spk-bv-simulator-feedback/v0c'
CHAIN = (EdgeV0('A', 7, 'B', 0, 1), EdgeV0('B', 7, 'C', 0, 1))


def _case(program, tick):
    if program not in (OLD, NEW) or type(tick) is not int or not 1 <= tick <= 16:
        raise FeedbackTransportRejected('inadmissible paired intervention')
    nodes = (NodeV0('A', 8, 0, 0, program), NodeV0('B', 8, 0, 0, RELAY),
             NodeV0('C', 8, 0, 0, RELAY))
    return CaseV0(nodes, CHAIN, (EventV0(tick, 'A', 0),))


def build_trace_v0c(case, run):
    p = run['projection']
    expected_edges = [
        {'id': 'edge' + str(i+1), 'source': e.source_node if hasattr(e, 'source_node') else e.source,
         'target': e.target_node if hasattr(e, 'target_node') else e.target,
         'source_channel': e.source_channel, 'target_channel': e.target_channel,
         'delay_ticks': e.delay_ticks}
        for i, e in enumerate(case.edges)]
    contexts = [{'id': 'ctx-' + n.node_id, 'node_id': n.node_id,
                 'program_sha256': digest(n.instructions),
                 'features_sha256': digest({'reset_state': n.initial_raw}),
                 'extractor_sha256': digest('reset-context-v0c'),
                 'window_start': 0, 'window_end': 0} for n in case.nodes]
    batches = p['observations']['batches']
    routes = p['observations']['routes']
    occurrences = []
    for i, r in enumerate(routes):
        matches = [e for e in expected_edges if
                   (e['source'], e['source_channel'], e['target'], e['target_channel'], e['delay_ticks']) ==
                   (r['source_node'], r['source_channel'], r['target_node'], r['target_channel'], r['delay_ticks'])]
        if len(matches) != 1 or r['delivery_timestamp'] != r['emission_timestamp'] + r['delay_ticks']:
            raise FeedbackTransportRejected('observed route does not match uniquely declared edge')
        source_batches = [b for b in batches if b['node_id'] == r['source_node'] and
                          b['timestamp'] == r['emission_timestamp'] and
                          r['source_channel'] in b['output_channels']]
        target_batches = [b for b in batches if b['node_id'] == r['target_node'] and
                          b['timestamp'] == r['delivery_timestamp'] and
                          r['target_channel'] in b['channels']]
        if len(source_batches) != 1 or len(target_batches) != 1:
            raise FeedbackTransportRejected('route source/delivery lacks frozen batch observation')
        parents = [o['id'] for o in occurrences if o['target'] == r['source_node'] and
                   o['delivered_at'] == r['emission_timestamp']]
        occurrence = {'id': 'r' + str(i+1), 'source': r['source_node'], 'target': r['target_node'],
                      'emitted_at': r['emission_timestamp'], 'delivered_at': r['delivery_timestamp'],
                      'parent_ids': parents, 'source_context_id': 'ctx-' + r['source_node'],
                      'source_program_sha256': next(c['program_sha256'] for c in contexts if c['node_id'] == r['source_node']),
                      'edge_id': matches[0]['id'], 'source_channel': r['source_channel'],
                      'target_channel': r['target_channel']}
        occurrences.append(occurrence)
    # We only claim an unambiguous causal chain for this admitted fixture.
    if occurrences and not (len(occurrences) == 2 and
                            occurrences[0]['source'] == 'A' and occurrences[0]['target'] == 'B' and
                            occurrences[1]['source'] == 'B' and occurrences[1]['target'] == 'C' and
                            occurrences[1]['parent_ids'] == [occurrences[0]['id']]):
        raise FeedbackTransportRejected('fixture is not an unambiguous two-hop causal chain')
    terminal = p['terminal_outputs']
    if occurrences and (len(terminal) != 1 or terminal[0]['node_id'] != 'C' or
                        terminal[0]['timestamp'] != occurrences[-1]['delivered_at']):
        raise FeedbackTransportRejected('terminal observer does not match delivered chain')
    if not occurrences and terminal:
        raise FeedbackTransportRejected('terminal output without witnessed source route')
    assessments = []
    propagations = []
    if occurrences:
        assessments.append({'id': 'assessment-C', 'occurrence_id': occurrences[-1]['id'],
                            'observer': 'C', 'observed_at': terminal[0]['timestamp'],
                            'observer_context_id': 'ctx-C', 'metric_id': 'terminal-emission-present',
                            'metric_policy_sha256': digest('terminal-emission-present-v0c'),
                            'evidence_sha256': digest(terminal), 'status': 'OBSERVED',
                            'value': 1.0, 'confidence': 1.0, 'reason': None})
        propagations.append({'id': 'prop-C-to-A', 'assessment_id': 'assessment-C',
                             'path': [occurrences[1]['id'], occurrences[0]['id']]})
    doc = {'schema': 'spk-back-validation-trace/v0', 'epoch': 1,
           'topology_sha256': digest({'nodes': ['A', 'B', 'C'], 'edges': sorted(expected_edges, key=lambda e: e['id'])}),
           'budgets': {'max_nodes': 4, 'max_edges': 4, 'max_contexts': 4, 'max_occurrences': 4,
                       'max_assessments': 4, 'max_propagations': 4, 'max_proposals': 4,
                       'max_hops': 4, 'max_parents': 4},
           'contexts': contexts, 'edges': expected_edges, 'occurrences': occurrences,
           'assessments': assessments, 'propagations': propagations, 'proposals': []}
    validate_trace(doc)
    return doc


def capture_v0c():
    rows = []
    for context, ticks in (('beneficial', range(1, 9)), ('consensus-trap', range(9, 17))):
        for t in ticks:
            row = {'context_id': context, 'tick': t, 'arms': {}}
            for name, program in (('baseline', OLD), ('candidate', NEW)):
                case = _case(program, t)
                observed = _run(case)  # real Network + three A1b mappings, raises on mismatch
                trace = build_trace_v0c(case, observed)
                transport = transport_v0c(trace)
                # Frozen observable execution costs are distinct from *sidecar* costs.
                p = observed['projection']
                row['arms'][name] = {
                    'program_sha256': digest(program),
                    'frozen_projection_sha256': digest(p),
                    'placements_sha256': observed['placement_digests'],
                    'trace': trace, 'feedback': transport,
                    'terminal_count': len(p['terminal_outputs']),
                    'frozen_spike_messages': len(p['observations']['routes'])}
            assert row['arms']['baseline']['terminal_count'] == 0
            assert row['arms']['candidate']['terminal_count'] == 1
            rows.append(row)
    return {'schema': SCHEMA, 'frozen_commit': FROZEN_COMMIT,
            'execution_count': len(rows) * 2 * 4,
            'pair_count': len(rows), 'sidecar_kind': 'causal-feedback-posthoc-separate-from-frozen-scheduler',
            'rows': rows,
            'excluded_claims': ['integrated-A3d-transport', 'runtime-feedback-service',
                                'physical-resource-consumption', 'statistical-significance',
                                'true-causal-credit', 'autonomous-program-learning',
                                'program-promotion']}


def seal_v0c():
    payload = capture_v0c()
    return canonical({'payload': payload, 'payload_sha256': digest(payload)})


def verify_v0c(text):
    item = strict_loads(text)
    if (type(item) is not dict or set(item) != {'payload', 'payload_sha256'} or
            canonical(item) != text or digest(item['payload']) != item['payload_sha256']):
        raise FeedbackTransportRejected('invalid or noncanonical sealed sidecar witness')
    if item != strict_loads(seal_v0c()):
        raise FeedbackTransportRejected('witness differs from independent frozen-engine replay')
    counts = [x['arms']['candidate']['feedback']['resources']['feedback_messages'] for x in item['payload']['rows']]
    return {'status': 'SIMULATOR_ANCHORED_SIDECAR_REPLAY_PASS',
            'pair_count': item['payload']['pair_count'],
            'simulator_executions': item['payload']['execution_count'],
            'sidecar_packets': sum(counts),
            'feedback_sha256': digest(item),
            'note': 'feedback executed in budgeted sidecar, not frozen simulator'}
