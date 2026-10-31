"""Deterministic paired SPK simulator execution for BV contextual-credit v0a.

Real frozen Network v0 and PE A1b are each executed; PE placement is checked
independently against Network output. This is an *offline controlled fixture*,
not a learned policy, factual causal-credit estimator, hardware cost model,
or independent stochastic trial population. Historical sources remain untouched.
"""
from __future__ import annotations

from dataclasses import asdict

from spk_backvalidation_v0.contract_v0 import canonical, digest
from spk_backvalidation_v0.contextual_credit_v0a import evaluate_credit
from search.spk_24n_independent_oracle_v0 import CaseV0, NodeV0, EdgeV0, EventV0
from spk_architecture_v1.pe_fabric_v1a import SCHEMES, plan_v1a
from spk_architecture_v1.pe_execution_v1b import execute_on_pes_v1b
from spk_core.isa import CoreAcc, CoreCmp, CoreConfig, CoreEmit, CoreProgram, CoreReset, ShiftDecay
from spk_network.model_v0 import NetworkV0, NetworkNodeV0, NetworkEdgeV0
from spk_network.events_v0 import NetworkEventV0
from spk_network.runtime_v0 import run_network_v0

SCHEMA = 'spk-bv-simulator-paired-evidence/v0b'
FROZEN_COMMIT = '5af99cd1f4d603bf0c8e1557a6561c107765fdb5'
OLD = (('ACC', (1, 0)), ('SHIFT', 1), ('CMP', 1), ('EMIT', 7), ('RESET', 0))
NEW = (('SHIFT', 1), ('ACC', (1, 0)), ('CMP', 1), ('EMIT', 7), ('RESET', 0))
RELAY = (('ACC', (1, 0)), ('CMP', 1), ('EMIT', 7), ('RESET', 0))
EDGES = (EdgeV0('A', 7, 'B', 0, 1), EdgeV0('A', 7, 'C', 0, 1))
CONTEXTS = ('beneficial', 'consensus-trap')
POLICY = {
    'global_metric_id': 'predeclared-target-terminal-count',
    'global_metric_policy_sha256': digest({'positive_target': 2, 'negative_target': 0, 'score': 'exact-match-binary'}),
    'local_metric_id': 'receiver-terminal-count-presence',
    'local_metric_policy_sha256': digest({'receivers': ['B', 'C'], 'score': 'one-if-terminal-spike-else-zero'}),
    'minimum_pairs': 8, 'alpha_ppm': 50000, 'minimum_mean_gain': 0.1,
    'max_mean_extra_cost': 20.0, 'max_pairs': 16, 'max_receivers': 2,
    'max_cost_per_arm': 64,
    'cost_weights': {'operations': 1.0, 'memory_accesses': 0.1,
                     'spike_messages': 0.1, 'feedback_messages': 0.2,
                     'candidate_eval_operations': 1.0},
}


class SimulatorEvidenceRejected(ValueError):
    pass


def _case(program, tick):
    if program not in (OLD, NEW) or type(tick) is not int or not 1 <= tick <= 16:
        raise SimulatorEvidenceRejected('unadmitted fixture program or tick')
    return CaseV0((NodeV0('A', 8, 0, 0, program),
                   NodeV0('B', 8, 0, 0, RELAY), NodeV0('C', 8, 0, 0, RELAY)),
                  EDGES, (EventV0(tick, 'A', 0),))


def _core_program(instructions):
    ops = []
    for op, arg in instructions:
        if op == 'ACC':
            ops.append(CoreAcc(*arg))
        elif op == 'SHIFT':
            ops.append(ShiftDecay(arg))
        elif op == 'CMP':
            ops.append(CoreCmp(arg))
        elif op == 'EMIT':
            ops.append(CoreEmit(arg))
        elif op == 'RESET':
            ops.append(CoreReset(arg))
        else:
            raise SimulatorEvidenceRejected('unrecognized operator')
    return CoreProgram(tuple(ops))


def _network(case):
    return NetworkV0(tuple(NetworkNodeV0(n.node_id, CoreConfig(n.state_bits, n.fractional_bits),
                                         _core_program(n.instructions), n.initial_raw)
                           for n in case.nodes),
                     tuple(NetworkEdgeV0(*asdict(e).values()) for e in case.edges))


class _Observer:
    def __init__(self):
        self.batches = []
        self.routes = []

    def on_batch(self, x):
        self.batches.append({'timestamp': x.timestamp, 'node_id': x.node_id,
                             'channels': list(x.channels), 'final_raw': x.final_raw,
                             'final_guard': x.final_guard,
                             'output_channels': list(x.output_channels)})

    def on_route(self, x):
        self.routes.append(asdict(x))


def _frozen_projection(result, observer):
    def events(items):
        return [asdict(e) for e in items]
    return {'emissions': events(result.emissions),
            'terminal_outputs': events(result.terminal_outputs),
            'states': [asdict(s) for s in result.states],
            'processed_batches': result.processed_batches,
            'processed_events': result.processed_events,
            'observations': {'batches': observer.batches, 'routes': observer.routes}}


def _run(case):
    observer = _Observer()
    reference = _frozen_projection(run_network_v0(_network(case),
                                 tuple(NetworkEventV0(e.timestamp, e.node_id, e.channel)
                                       for e in case.events), max_batches=32, max_events=64,
                                 learning_observer=observer), observer)
    placements = {}
    for scheme in SCHEMES:
        projected = execute_on_pes_v1b(case, plan_v1a(case, scheme),
                                       max_batches=32, max_events=64)['result']
        if projected != reference:
            raise SimulatorEvidenceRejected('Network/PE observational mismatch: ' + scheme)
        placements[scheme] = digest(projected)
    if len(set(placements.values())) != 1:
        raise SimulatorEvidenceRejected('placement-dependent semantic output')
    return {'source': 'frozen-Network-v0-PE-A1b', 'projection': reference,
            'placement_digests': placements}


def _global_score(context, projection):
    # Target is a declared EXTERNAL task label, not a neuron/observer vote.
    target = 2 if context == 'beneficial' else 0
    return 1.0 if len(projection['terminal_outputs']) == target else 0.0


def _feedback(projection):
    terminal = projection['terminal_outputs']
    return [{'observer': n, 'status': 'OBSERVED',
             'score': 1.0 if any(e['node_id'] == n for e in terminal) else 0.0,
             'reason': None} for n in ('B', 'C')]


def _cost(case, projection):
    nodes = {n.node_id: n for n in case.nodes}
    n_b = projection['processed_batches']
    return {'operations': sum(len(nodes[b['node_id']].instructions)
                              for b in projection['observations']['batches']),
            'memory_accesses': 2 * n_b, # declared abstract reads/writes proxy
            'spike_messages': len(projection['observations']['routes']),
            'feedback_messages': 0, # no BV message is executed in Network v0
            'candidate_eval_operations': 0} # external evaluator not charged here


def _arm(case, context, trace):
    p = trace['projection']
    return {'program_sha256': digest(case.nodes[0].instructions),
            'trace_sha256': digest(trace), 'global_score': _global_score(context, p),
            'feedback': _feedback(p), 'cost': _cost(case, p)}


def capture_v0b():
    """Rebuild the full witness from actual frozen-engine execution."""
    topo = {'nodes': ['A', 'B', 'C'], 'edges': [asdict(e) for e in EDGES]}
    contexts = [{'id': name,
                 'pre_treatment_features_sha256': digest({'label': name, 'target': 2 if name == 'beneficial' else 0}),
                 'extractor_sha256': digest({'type': 'predeclared-external-label-v0b'})}
                for name in CONTEXTS]
    pairs, traces = [], []
    for context in CONTEXTS:
        for tick in (range(1, 9) if context == 'beneficial' else range(9, 17)):
            case0, case1 = _case(OLD, tick), _case(NEW, tick)
            t0, t1 = _run(case0), _run(case1)
            p = {'id': context + '-' + str(tick), 'context_id': context, 'seed': tick,
                 'initial_state_sha256': digest([(n.node_id, n.initial_raw, 0) for n in case0.nodes]),
                 'input_sha256': digest([asdict(e) for e in case0.events]),
                 'baseline': _arm(case0, context, t0),
                 'candidate': _arm(case1, context, t1)}
            pairs.append(p)
            traces.append({'pair_id': p['id'], 'baseline_trace_sha256': digest(t0),
                           'candidate_trace_sha256': digest(t1),
                           'baseline_terminal_count': len(t0['projection']['terminal_outputs']),
                           'candidate_terminal_count': len(t1['projection']['terminal_outputs']),
                           'placement_digests': {'baseline': t0['placement_digests'],
                                                 'candidate': t1['placement_digests']}})
    credit = {'schema': 'spk-bv-contextual-credit/v0a',
              'baseline_tag': 'spk-architecture-bounded-reference-v1',
              'baseline_commit': FROZEN_COMMIT, 'topology_sha256': digest(topo),
              'policy': POLICY, 'program': {'node_id': 'A',
                                           'baseline_sha256': digest(OLD),
                                           'candidate_sha256': digest(NEW)},
              'contexts': contexts, 'trial_pairs': pairs}
    summary = evaluate_credit(credit)
    decisions = {x['context_id']: x['decision'] for x in summary['context_results']}
    if decisions != {'beneficial': 'EVIDENCE_FOR_FURTHER_VERIFICATION',
                     'consensus-trap': 'LOCAL_GLOBAL_CONFLICT'}:
        raise SimulatorEvidenceRejected('unexpected independent-score decisions')
    return {'schema': SCHEMA, 'frozen_commit': FROZEN_COMMIT,
            'experiment_kind': 'deterministic-fixture-not-independent-sampled-trials',
            'pair_count': len(pairs), 'simulator_executions': len(pairs) * 2 * (len(SCHEMES) + 1),
            'traces': traces, 'credit': credit, 'credit_summary': summary,
            'excluded_claims': ['unbiased-randomization', 'independent-trials',
                                'statistical-significance', 'causal-credit-in-real-networks',
                                'in-network-feedback', 'autonomous-program-learning',
                                'measured-hardware-cost', 'promoted-program']}


def seal_v0b():
    report = capture_v0b()
    return canonical({'payload': report, 'payload_sha256': digest(report)})


def verify_v0b(document):
    if type(document) is not str:
        raise SimulatorEvidenceRejected('evidence must be text')
    from spk_backvalidation_v0.contract_v0 import strict_loads
    obj = strict_loads(document)
    if (type(obj) is not dict or set(obj) != {'payload', 'payload_sha256'}
            or canonical(obj) != document or obj['payload_sha256'] != digest(obj['payload'])):
        raise SimulatorEvidenceRejected('invalid or noncanonical witness')
    if obj != __import__('json').loads(seal_v0b()):
        raise SimulatorEvidenceRejected('witness does not match independently rerun simulators')
    return {'status': 'REAL_SIMULATOR_PAIRED_REPLAY_PASS',
            'evidence_sha256': digest(obj), 'pair_count': obj['payload']['pair_count'],
            'simulator_executions': obj['payload']['simulator_executions'],
            'decisions': {x['context_id']: x['decision'] for x in
                          obj['payload']['credit_summary']['context_results']}}
