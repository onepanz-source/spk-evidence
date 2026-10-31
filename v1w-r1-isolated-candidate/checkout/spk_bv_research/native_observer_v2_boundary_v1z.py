"""SPK BV v1z: source-owned *versioned executor* admission contract (research only).

The frozen v0e scheduler has no verified semantic observation port.  The tiny
reference emitter here exists solely to test a future v2 interface's negative
boundary.  It is NOT an instrumentation of v0e, a native callback, or an
independent witness, and it cannot issue absence certificates or B judgments.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Callable

from spk_bv_research.off_on_v0t import require
from spk_bv_research.native_capture_v0k import _json_bytes, canonical_fixture
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_external_probe_v1y import SCHEMA as Y_SCHEMA, STATUS as Y_STATUS
from spk_bv_research.observation_seam_contract_v1w import PORT_OBLIGATIONS

SCHEMA = 'spk-bv-versioned-native-observer-admission-contract/v1z'
STATUS = 'NATIVE_V1Y_PROBE_ACCEPTED_VERSIONED_EXECUTOR_NOT_INSTALLED'
PROPOSED_PORT = 'spk-bv-native-observer-port/v2a-proposal'
CAP = 64
PHASES = ('predecision_expectation', 'decision', 'sender_port_emission',
          'receiver_ingress', 'interval_coverage_close')

NATIVE_EXCLUSIONS = (
    'v1y-python-trace-is-not-semantic-source-owned-event-stream',
    'reference-v2a-emitter-is-not-frozen-native-scheduler',
    'v2a-proposal-is-not-installed-or-invoked-by-frozen-scheduler',
    'python-process-capability-is-not-cryptographic-authentication',
    'reference-close-is-not-independent-coverage-or-absence-witness',
    'observer-callback-is-not-receiver-delivery',
    'source-owned-event-requires-actual-versioned-executor-under-test',
    'reference-forward-result-parity-is-not-native-v2a-parity',
    'no-native-receiver-value-criterion-judgment-credit-update-or-learning',
    'no-core-network-compiler-architecture-freeze-modification',
)


def verify_native_y(y: dict, y_raw: bytes, x: dict, x_raw: bytes):
    """Bind to canonical, complete native v1y report and unchanged v1x baseline.

    This verifies a *reported prior experiment*, not a new native invocation.
    """
    require(type(y) is dict and type(x) is dict and type(y_raw) is bytes and
            type(x_raw) is bytes and y_raw == canon(y) and x_raw == canon(x),
            'noncanonical predecessor')
    required = {
        'schema': Y_SCHEMA, 'status': Y_STATUS,
        'source_kind': 'FROZEN_NATIVE_EXECUTION_EXTERNAL_PYTHON_PROBE',
        'source_pins_rechecked_in_this_run': True,
        'source_files_modified': False,
        'inherited_native_v1x_recomputation_verified_in_this_run': True,
        'interpreter_tracing_observed_scheduler_during_native_execution': True,
        'native_scheduler_executions_without_trace_in_this_module': 4,
        'native_scheduler_executions_with_trace_in_this_module': 4,
        'native_source_callback_invoked': False,
        'runtime_listener_interface_installed': False,
        'native_observer_ON_source_owned_mode_executed': False,
        'native_receiver_B_control_messages': 0,
        'native_producer_owned_observer_callback_calls': 0,
        'native_authenticated_producer_evidence': 0,
        'native_independent_absence_certificates': 0,
        'native_scored_receiver_judgments': 0,
        'native_operator_updates': 0,
        'native_learning_proven': False,
        'native_value_criterion_identified': False,
        'probe_has_independent_clock_or_coverage': False,
        'source_owned_native_semantic_events_attested': 0,
    }
    for key, val in required.items():
        require(type(y.get(key)) is type(val) and y[key] == val,
                'v1y native authority/integrity mismatch: ' + key)
    require(type(y.get('reference_v1x_sha256')) is str and
            y['reference_v1x_sha256'] == sha256(x_raw).hexdigest(),
            'v1y/v1x digest mismatch')
    require(y.get('reference_v1w_sha256') == x.get('reference_v1w_sha256'),
            'v1y/v1x source pin lineage mismatch')
    expected_obligations = [{'id': k, 'verified': False} for k, _ in PORT_OBLIGATIONS]
    require(y.get('native_proof_obligations_unmet') == expected_obligations,
            'native proof boundary promoted')
    expected = {'original': {'off': 2, 'on': 2},
                'variant': {'off': 0, 'on': 0}}
    matrix = y.get('native_probe_parity_matrix')
    reference = x.get('native_run_reference_matrix')
    require(type(matrix) is dict and type(reference) is dict and
            set(matrix) == set(reference) == set(expected),
            'native matrix shape drift')
    for arm, modes in expected.items():
        require(type(matrix[arm]) is dict and type(reference[arm]) is dict and
                set(matrix[arm]) == set(reference[arm]) == set(modes),
                'native mode matrix shape drift')
        for mode, count in modes.items():
            row, base = matrix[arm][mode], reference[arm][mode]
            require(type(row) is dict and type(base) is dict and
                    set(row) == {'no_probe_result_sha256', 'probe_result_sha256',
                                 'native_return_bytes_equal', 'trace'} and
                    type(base.get('sender')) is int and base['sender'] == count and
                    type(base.get('ingress')) is int and base['ingress'] == count and
                    base.get('repeatability_identical') is True and
                    row.get('native_return_bytes_equal') is True and
                    row['no_probe_result_sha256'] == row['probe_result_sha256'] ==
                    base.get('result_sha256'),
                    'native OFF/ON return parity drift')
            trace = row['trace']
            require(type(trace) is dict and
                    trace.get('scope') == 'PYTHON_INTERPRETER_FUNCTION_CODE_OBJECT_ONLY' and
                    trace.get('python_target_call_events') == 1 and
                    trace.get('python_return_events') == 1 and
                    type(trace.get('python_line_events')) is int and
                    trace['python_line_events'] > 0 and
                    trace.get('trace_events_seen') == 2 + trace['python_line_events'] and
                    trace.get('trace_error') is False and
                    trace.get('trace_overflow') is False and
                    trace.get('trace_restored') is True and
                    trace.get('semantic_spike_events_attested') == 0 and
                    trace.get('native_B_packets_delivered') == 0,
                    'invalid Python trace evidence')
            hits = trace.get('candidate_line_hits')
            require(type(hits) is dict and set(hits) == {'49', '50', '150', '206'} and
                    all(type(v) is int and 0 <= v <= trace['python_line_events']
                        for v in hits.values()) and
                    hits['49'] == hits['50'] == 1 and
                    (hits['150'] > 0 and hits['206'] > 0) ==
                    (arm == 'original' and mode == 'on'),
                    'candidate trace callsite count inconsistent')
    return True


@dataclass(frozen=True)
class ProposalEvent:
    """Immutable local reference record, never authority for native receiver B."""
    episode: str
    source: str
    target: str
    ordinal: int
    tick: int
    phase: str
    decision: str


class ReferenceProposalPort:
    """Bounded phase/identity/order checker for a FUTURE versioned executor.

    A local callback can see reference events but does not attest delivery to B.
    No quantity here is an independent native silence or timing certificate.
    """
    def __init__(self, episode: str, sink: Callable | None = None, capacity: int = CAP):
        require(type(episode) is str and 1 <= len(episode) <= 96 and
                type(capacity) is int and 1 <= capacity <= CAP and
                (sink is None or callable(sink)), 'invalid reference port')
        self.episode = episode
        self.sink = sink
        self.capacity = capacity
        self.events = []
        self.sink_fault = False
        self.overflow = False
        self._last_tick = -1
        self._last_phase = -1
        self._decision = None
        self._closed = False

    def emit(self, *, source: str, target: str, tick: int,
             phase: str, decision: str):
        require(not self._closed and type(source) is str and source == 'A' and
                type(target) is str and target == 'B' and
                type(tick) is int and 0 <= tick <= 1000000 and
                type(decision) is str and 1 <= len(decision) <= 96 and
                phase in PHASES and type(phase) is str,
                'malformed or closed reference event')
        idx = PHASES.index(phase)
        require(idx >= self._last_phase and tick > self._last_tick,
                'nonmonotonic reference phase/tick')
        if not self.events:
            require(idx == 0, 'predecision event missing')
        if idx == 1:
            require(self._last_phase == 0, 'decision has no prior expectation')
        if idx >= 2:
            require(self._last_phase >= 1, 'sender decision missing')
        if idx == 3:
            require(self._last_phase in (2, 3), 'ingress without source emission')
        if idx == 4:
            require(self._last_phase in (1, 2, 3), 'coverage closure without decision')
        if self._decision is not None:
            require(decision == self._decision, 'cross-decision message')
        require(len(self.events) < self.capacity, 'reference port capacity exhausted')
        if self._decision is None: self._decision = decision
        rec = ProposalEvent(self.episode, source, target, len(self.events), tick, phase, decision)
        self.events.append(rec)
        self._last_phase, self._last_tick = idx, tick
        if idx == 4: self._closed = True
        if self.sink is not None and not self.sink_fault:
            try:
                self.sink(rec)
            except Exception:
                self.sink_fault = True
        return rec

    def seal(self):
        require(self._closed and self.events[-1].phase == PHASES[-1],
                'reference execution incomplete')
        return {
            'events': len(self.events),
            'phase_names': [ev.phase for ev in self.events],
            'ordinal_contiguous': all(ev.ordinal == n for n, ev in enumerate(self.events)),
            'listener_failed': self.sink_fault,
            'is_native_source_observer': False,
            'native_receiver_packets': 0,
            'native_absence_certificates': 0,
        }


def execute_reference_v2a(*, seed: int, port: ReferenceProposalPort | None = None):
    """Explicitly NONNATIVE reference executor; emitted records are not SPK spikes.

    A future v2 executor must be independently versioned, source-pinned and
    byte-matched against frozen baseline; this function cannot substitute for it.
    """
    require(type(seed) is int and seed in (0, 1, 2), 'invalid reference seed')
    decision = 'ref.decision.0'
    if port is not None:
        port.emit(source='A', target='B', tick=0,
                  phase='predecision_expectation', decision=decision)
        port.emit(source='A', target='B', tick=1,
                  phase='decision', decision=decision)
    total = 0
    for i in range(seed):
        total += i + 1
        if port is not None:
            port.emit(source='A', target='B', tick=2 + i,
                      phase='sender_port_emission', decision=decision)
    if port is not None:
        for i in range(seed):
            port.emit(source='A', target='B', tick=8 + i,
                      phase='receiver_ingress', decision=decision)
        port.emit(source='A', target='B', tick=16,
                  phase='interval_coverage_close', decision=decision)
    return {'accumulator': (total, seed), 'emissions': seed}


def reference_pair(seed: int, sink: Callable | None = None, capacity=CAP):
    """Pure reference OFF/ON experiment. NEVER a native scheduler parity claim."""
    without = _json_bytes(canonical_fixture(execute_reference_v2a(seed=seed)))
    port = ReferenceProposalPort('ref.v2a.' + str(seed), sink=sink, capacity=capacity)
    with_observer = _json_bytes(canonical_fixture(execute_reference_v2a(seed=seed, port=port)))
    require(without == with_observer, 'reference observer changed result')
    return {'reference_seed': seed, 'typed_return_sha256': sha256(without).hexdigest(),
            'reference_result_bytes_equal': True, 'port': port.seal()}


def analyze(y, y_raw, x, x_raw):
    verify_native_y(y, y_raw, x, x_raw)
    examples = [reference_pair(n) for n in (0, 1, 2)]
    require([e['port']['events'] for e in examples] == [3, 5, 7],
            'reference port example count mismatch')
    return {
        'schema': SCHEMA, 'status': STATUS,
        'source_kind': 'CANONICAL_NATIVE_V1Y_PREDECESSOR_PLUS_NONNATIVE_V2A_REFERENCE_CONTRACT',
        'reference_v1y_sha256': sha256(y_raw).hexdigest(),
        'reference_v1x_sha256': sha256(x_raw).hexdigest(),
        'native_v1y_report_consistency_verified': True,
        'inherited_native_v1y_recomputation_verified_in_this_run': False,
        'new_native_scheduler_executions_in_this_module': 0,
        'source_owned_native_semantic_events_attested': 0,
        'native_producer_owned_observer_callback_calls': 0,
        'native_B_control_messages_received': 0,
        'native_absence_certificates': 0,
        'native_scored_receiver_judgments': 0,
        'native_operator_updates': 0,
        'native_learning_proven': False,
        'native_runtime_versioned_v2a_installed': False,
        'frozen_source_files_modified': False,
        'proposed_port_version': PROPOSED_PORT,
        'proposed_phases': list(PHASES),
        'reference_executor_examples': examples,
        'native_promotion_obligations_unmet': [
            {'id': k, 'verified': False} for k, _ in PORT_OBLIGATIONS
        ],
        'native_gate_status': 'BLOCKED_VERSIONED_NATIVE_EXECUTOR_NOT_PRESENT',
        'claims_excluded': list(NATIVE_EXCLUSIONS),
    }
