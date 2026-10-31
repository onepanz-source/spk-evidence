"""v2a: bounded independent micro-executor admission, NOT frozen SPK parity.

Compare a new source-owned event loop OFF/ON inside its own implementation.
The label 'native' is deliberately withheld: relay/pair/block are not frozen CMP.
"""
from __future__ import annotations
from hashlib import sha256

from spk_bv_research.off_on_v0t import require
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.native_observer_v2_boundary_v1z import (
    SCHEMA as Z_SCHEMA, STATUS as Z_STATUS, analyze as rebuild_z)
from spk_bv_research.observation_seam_contract_v1w import PORT_OBLIGATIONS
from spk_bv_research.native_capture_v0k import _json_bytes, canonical_fixture
from spk_backvalidation_v2.observed_scheduler_v2a import (
    BoundedCaseV2a, ObserverV2a, ObservationV2a, execute_live_v2a,
    EXECUTOR_VERSION, PORT_VERSION, NODES, PHASES,
)

SCHEMA = 'spk-bv-bounded-source-owned-versioned-executor/v2a'
STATUS = 'BOUNDED_V2A_EXECUTED_NATIVE_SPK_EQUIVALENCE_UNPROVEN'
SOURCE_KIND = 'NEW_INDEPENDENT_RESEARCH_MICRO_EXECUTOR_NOT_FROZEN_NATIVE_SCHEDULER'
EXCLUSIONS = (
    'v2a-micro-relay-pair-block-are-not-frozen-CMP-instruction-implementations',
    'micro-counter-matches-do-not-establish-SPK-forward-state-or-BV-parity',
    'v2a-produced-immutable-events-are-not-cryptographically-authenticated',
    'callback-not-recipient-delivery-no-native-B-control-packets',
    'logical-close-is-not-independent-time-coverage-or-absence-certificate',
    'BV-on-off-is-only-a-label-in-this-bounded-micro-executor',
    'bounded-forward-outcome-parity-is-not-general-timing-noninterference',
    'no-value-criterion-no-endogenous-feedback-no-operator-learning',
    'frozen-SPK-scheduler-Core-Network-Compiler-Architecture-remain-unchanged',
)
OPERATORS = {
    'relay_chain': ('relay', 'relay', 'relay'),
    'block_at_A': ('block', 'relay', 'relay'),
    'pair_at_B': ('relay', 'pair', 'relay'),
    'pair_at_C': ('relay', 'relay', 'pair'),
}
EXPECTED = {
    'relay_chain': (2, 2, 2), 'block_at_A': (0, 0, 0),
    'pair_at_B': (2, 1, 1), 'pair_at_C': (2, 2, 1),
}


def assert_observation_stream(case: BoundedCaseV2a, port: ObserverV2a, result: dict):
    """Cross-check actual emitted events against independently returned decisions."""
    es = port.events
    require(not port.overflow and not port.sink_fault and len(es) > 0 and
            len(es) == result['logical_event_count'], 'micro-events incomplete')
    require(all(type(e) is ObservationV2a and e.version == PORT_VERSION and
                e.episode == case.episode and e.ordinal == i and
                e.logical_tick == i + 1 and e.phase in PHASES
                for i, e in enumerate(es)), 'event clock/identity corrupted')
    require(es[-1].phase == 'interval_coverage_close' and
            sum(e.phase == 'interval_coverage_close' for e in es) == 1,
            'no single local close')
    sent = {n: 0 for n in NODES}
    received = {n: 0 for n in NODES}
    issued = set()
    seen_expectation = set()
    decided = set()
    decision_rows = {d['decision_id']: d for d in result['decisions']}
    require(len(decision_rows) == len(result['decisions']), 'duplicate decision IDs')
    for e in es[:-1]:
        require(e.actor in NODES and e.decision_id in decision_rows,
                'foreign event actor or decision')
        if e.phase != 'receiver_ingress':
            require(decision_rows[e.decision_id]['node'] == e.actor,
                    'event not owned by decision actor')
        if e.phase == 'predecision_expectation':
            require(e.decision_id not in seen_expectation, 'duplicate expectation')
            seen_expectation.add(e.decision_id)
        elif e.phase == 'decision':
            require(e.decision_id in seen_expectation and
                    e.decision_id not in decided, 'decision without local predecision')
            decided.add(e.decision_id)
        elif e.phase == 'sender_port_emission':
            require(e.decision_id in decided and e.event_token not in issued and
                    bool(e.event_token) and decision_rows[e.decision_id]['selected'] is True,
                    'unbound, rejected or duplicate emission')
            issued.add(e.event_token)
            sent[e.actor] += 1
        elif e.phase == 'receiver_ingress':
            require(e.event_token in issued and e.actor in NODES[1:] and
                    e.parent_token == e.event_token and
                    e.target == decision_rows[e.decision_id]['node'],
                    'fabricated micro-ingress')
            received[e.actor] += 1
        else:
            require(False, 'invalid bounded phase')
    require(sent == result['forward_emissions'] and
            received['B'] == result['forward_routes']['A->B'] and
            received['C'] == result['forward_routes']['B->C'] and
            len(decided) == result['forward_decisions'] and
            len(result['decisions']) == len(decided), 'micro-event/result mismatch')
    return True


def paired_case(case: BoundedCaseV2a, sink=None, capacity=512):
    raw_without = _json_bytes(canonical_fixture(execute_live_v2a(case)))
    port = ObserverV2a(sink=sink, capacity=capacity)
    with_observer = execute_live_v2a(case, observation_port=port)
    raw_with = _json_bytes(canonical_fixture(with_observer))
    require(raw_without == raw_with, 'v2a micro forward result differs with observer')
    summary = port.summary()
    if summary['complete']:
        assert_observation_stream(case, port, with_observer)
    return {
        'case': case.episode, 'operator_program': list(case.operators),
        'bv_label_only': case.bv_enabled,
        'typed_result_sha256': sha256(raw_without).hexdigest(),
        'observer_off_on_result_bytes_equal': True,
        'forward_emissions': with_observer['forward_emissions'],
        'forward_arrivals': with_observer['forward_arrivals'],
        'forward_terminal_count': with_observer['forward_terminal_count'],
        'forward_routes': with_observer['forward_routes'],
        'source_owned_micro_events_seen': summary['records_retained'],
        'logical_events': with_observer['logical_event_count'],
        'observer': summary,
    }


def validate_z(z: dict, zb: bytes, y: dict, yb: bytes, x: dict, xb: bytes):
    require(all(type(r) is dict and type(b) is bytes and canon(r) == b
                for r,b in ((z,zb),(y,yb),(x,xb))), 'predecessor canonical bytes bad')
    require(z.get('schema') == Z_SCHEMA and z.get('status') == Z_STATUS and
            z.get('reference_v1y_sha256') == sha256(yb).hexdigest() and
            z.get('reference_v1x_sha256') == sha256(xb).hexdigest() and
            z.get('native_gate_status') == 'BLOCKED_VERSIONED_NATIVE_EXECUTOR_NOT_PRESENT',
            'v1z frozen boundary not attested')
    require(rebuild_z(y,yb,x,xb) == z, 'v1z report does not recompute exactly')
    return True


def analyze(z,zb,y,yb,x,xb, *, frozen_source_custody=False, executor_sha256=''):
    validate_z(z,zb,y,yb,x,xb)
    require(type(frozen_source_custody) is bool and type(executor_sha256) is str and
            len(executor_sha256) == 64 and all(c in '0123456789abcdef' for c in executor_sha256),
            'invalid versioned-source custody')
    rows = []
    for name, ops in OPERATORS.items():
        for mode in ('off', 'on'):
            case = BoundedCaseV2a('micro.v2a.'+name+'.'+mode, (1,1),ops,mode=='on')
            row = paired_case(case)
            require(tuple(row['forward_emissions'][n] for n in NODES) == EXPECTED[name],
                    'bounded micro footprint drift')
            rows.append({'arm':name,'mode':mode,**row})
    require(len(rows) == 8 and sum(r['source_owned_micro_events_seen'] for r in rows) > 0,
            'v2a not executed online')
    return {
        'schema': SCHEMA, 'status': STATUS, 'source_kind': SOURCE_KIND,
        'reference_v1z_sha256': sha256(zb).hexdigest(),
        'reference_v1y_sha256': sha256(yb).hexdigest(),
        'reference_v1x_sha256': sha256(xb).hexdigest(),
        'recomputed_v1z_contract_identically': True,
        'frozen_native_source_pins_rechecked_in_this_run': frozen_source_custody,
        'versioned_executor_file_sha256': executor_sha256,
        'executor_version': EXECUTOR_VERSION, 'observer_port_version': PORT_VERSION,
        'micro_executor_installed_and_invoked': True,
        'micro_observer_created_during_execution': True,
        'micro_executor_pairs': 8, 'micro_results': rows,
        'micro_off_on_return_parity': True,
        'micro_event_origin_belongs_to_new_executor': True,
        'frozen_native_forward_equivalence_proven': False,
        'frozen_native_BV_equivalence_proven': False,
        'native_frozen_scheduler_observer_connected': False,
        'native_recipient_B_received_control_messages': 0,
        'native_authenticated_emission_observation': False,
        'native_independent_absence_certificates': 0,
        'native_scored_receiver_judgments': 0,
        'native_operator_updates': 0, 'native_learning_proven': False,
        'ten_native_promotion_obligations_unmet': [
            {'id': k, 'verified': False} for k,_ in PORT_OBLIGATIONS
        ],
        'claims_excluded': list(EXCLUSIONS),
    }
