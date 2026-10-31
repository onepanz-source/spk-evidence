"""BV v1w: source-pinned feasibility contract for an ADDITIVE native observer port.

This module is intentionally incapable of connecting to the frozen scheduler.
AST call-site candidates are NOT live callbacks, authenticated observations,
or independent coverage witnesses. Research-owned code never mutates native source.
"""
from __future__ import annotations

import ast
from hashlib import sha256
from pathlib import Path

from spk_bv_research.off_on_v0t import require
from spk_bv_research.native_allocation_boundary_v1r import canon
from spk_bv_research.frozen_observation_surface_v1v import (
    SCHEMA as PREV_SCHEMA, STATUS as PREV_STATUS, SCHED, PRODUCER, TEST, ARCH,
    PINS, REQUIRED_BOUNDARY, _function, _signature,
)

SCHEMA = 'spk-bv-additive-native-observation-seam-feasibility/v1w'
STATUS = 'SOURCE_PINNED_RESEARCH_SEAM_PROPOSAL_NO_NATIVE_STREAM'
SOURCE_KIND_NATIVE = 'FROZEN_NATIVE_AST_READONLY_CANDIDATES_NO_EVENT_TAP'
SOURCE_KIND_OFFLINE = 'PREDECESSOR_BOUND_DESIGN_ONLY'
EXPECTED_PINS = {
    PRODUCER: '1e93f1a71c1099a3ce3c5e14d2cb9cfa47b8bfa9027832785d9f09af0c2bbc70',
    SCHED: '2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9',
    TEST: '6de34cd1ff6c85c96faad3dc047066406cf49d9675ac87fc77b260814f18dfa8',
    ARCH: '8e9d08ddc165e0c6e307ca16cc849feb7eabad33c148c26f4faa436c890d752c',
}
EXPECTED_COMPUTE_AST = '2e5ca7822becfeddf8a7d18dc2797eb643e957ce164a153f33efa22c3eb2b2ce'
CLAIMS_EXCLUDED = (
    'ast-identifier-hints-are-not-executed-event-taps',
    'frozen-entrypoint-without-callback-does-not-prove-no-other-hook-exists',
    'postreturn-producer-traces-not-online-native-events',
    'proposed-versioned-interface-not-installed-or-native-invoked',
    'producer-content-sha-not-authenticated-messaging-or-independent-coverage',
    'research-shadow-mailbox-not-native-receiver-B',
    'no-independent-native-absence-certificate-or-value-criterion',
    'no-native-receiver-scored-judgment-or-credit-or-update-or-learning',
    'no-frozen-core-network-compiler-architecture-modification',
)
# These are proof obligations, NOT an accepted architecture change.
PORT_OBLIGATIONS = (
    ('source_event_origin', 'producer-owned event identity bound to episode and source port'),
    ('online_happens_before', 'observation produced before native episode return, with bounded native event order'),
    ('receiver_delivery', 'receiver actually obtains the specific control record over a separate route'),
    ('provenance_authority', 'trust anchor establishes native producer and recipient identity, not only SHA'),
    ('expectation_before_decision', 'receiver knows an authenticated predecision commitment before evaluation'),
    ('coverage_and_clock', 'independent finite-interval coverage, closure and fault-awareness, not trace absence'),
    ('bounded_backpressure', 'control overflow/drop/replay/order faults fail closed without changing forward scheduling'),
    ('read_only_noninterference', 'native forward/BV behavior and result bytes equal with observer disabled/enabled'),
    ('local_value_criterion', 'native recipient declares its own verifiable evaluation criterion'),
    ('decision_causal_binding', 'an event or missingness bound to the actual sender decision, not a copied label'),
)
NAME_HINTS = {
    'sender_emission': ('emit', 'emission', 'outgoing'),
    'forward_route': ('route', 'routed', 'occurrence', 'grant'),
    'receiver_ingress': ('ingress', 'deliver', 'consume', 'admit'),
    'back_validation': ('feedback', 'assess', 'backward'),
    'scheduler_batch': ('batch', 'schedule', 'dispatch'),
}


def validate_predecessor(v: dict, raw: bytes):
    require(type(v) is dict and type(raw) is bytes and canon(v) == raw,
            'v1v report not canonical')
    required = {
        'schema': PREV_SCHEMA,
        'status': PREV_STATUS,
        'source_kind': 'NATIVE_FROZEN_SOURCE_SHA256_AST_READONLY_AUDIT',
        'frozen_source_bytes_rechecked_in_this_run': True,
        'inherited_native_v1u_recomputation_verified_in_this_run': True,
        'public_live_event_hook_semantics_verified': False,
        'native_per_event_callback_invoked': False,
        'native_source_to_B_control_delivery_verified': False,
        'native_independent_absence_certificate_verified': False,
        'native_clock_or_coverage_certified': False,
        'native_scored_receiver_judgments': 0,
        'native_operator_updates': 0,
        'native_learning_proven': False,
        'no_new_scheduler_executions_in_v1v': True,
    }
    require(all(type(v.get(k)) is type(e) and v[k] == e for k, e in required.items()),
            'v1v has missing or promoted native authority')
    require(v.get('integration_requirements_not_yet_satisfied') == list(REQUIRED_BOUNDARY),
            'v1v integration gate lost an obligation')
    frozen = v.get('frozen_native_sources')
    require(type(frozen) is dict and
            frozen.get('frozen_producer_sha256') == {k: EXPECTED_PINS[k] for k in PINS} and
            frozen.get('frozen_a1_compute_source_sha256') == EXPECTED_PINS[ARCH] and
            frozen.get('compute_function_ast_sha256') ==
                EXPECTED_COMPUTE_AST and
            frozen.get('compute_function_positional_args') == ['node','state','timestamp','channels'] and
            frozen.get('compute_function_name') == '_compute_local',
            'v1v frozen source provenance differs from attested identity')
    actual = v.get('actual_native_API_surface')
    require(type(actual) is dict and actual.get('plan_class_found') is True and
            actual.get('observation_class') == 'SOURCE_SIGNATURE_HINTS_ONLY_NOT_EXECUTION_PROOF' and
            actual.get('producer_files_sha256') == {k: EXPECTED_PINS[k] for k in sorted(EXPECTED_PINS)},
            'v1v has no verified source API inventory')
    signatures = {
        'scheduler_entrypoint': ('execute_live_v0e', ['case','fabric','tplan','pplan','mplan','lplan','bv']),
        'fixture_entrypoint': ('fixture', ['program','ticks']),
        'neuron_compute_entrypoint': ('_compute_local', ['node','state','timestamp','channels']),
    }
    for field, (name, pos) in signatures.items():
        item = actual.get(field)
        require(type(item) is dict and item.get('name') == name and
                item.get('positional') == pos and item.get('keyword_only') == [] and
                item.get('possible_callback_name_hints') == [] and
                item.get('async_function') is False and
                item.get('generator_body_has_yield') is False,
                'unverified live API signature: '+field)
    for key in ('reference_v1t_sha256', 'reference_v1u_sha256'):
        digest = v.get(key)
        require(type(digest) is str and len(digest) == 64 and
                all(c in '0123456789abcdef' for c in digest),
                'bad predecessor reference '+key)
    return actual


def read_pinned_sources(root: Path):
    """Source custody: no relative redirection and no symlink components."""
    root = Path(root).resolve(strict=True)
    result = {}
    for rel, expected in EXPECTED_PINS.items():
        p = root / rel
        require(p.resolve(strict=True) == p and p.is_file() and not p.is_symlink() and
                0 < p.stat().st_size <= 600_000, 'unsafe frozen source '+rel)
        blob = p.read_bytes()
        require(sha256(blob).hexdigest() == expected, 'source SHA256 mismatch '+rel)
        result[rel] = blob
    return result


def _call_names(function):
    """Shallow, bounded, static candidate discovery. Not executed event semantics."""
    results = {key: [] for key in NAME_HINTS}
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        callee = node.func
        name = callee.id if isinstance(callee, ast.Name) else (
            callee.attr if isinstance(callee, ast.Attribute) else '')
        if not name:
            continue
        low = name.lower()
        for category, hints in NAME_HINTS.items():
            if any(h in low for h in hints):
                results[category].append({'line': int(node.lineno), 'callee': name})
    return results


def source_candidate_inventory(v: dict, blobs: dict[str, bytes]):
    actual = validate_predecessor(v, canon(v))
    require(type(blobs) is dict and set(blobs) == set(EXPECTED_PINS),
            'all frozen sources required for static inventory')
    trees = {}
    for rel, expected in EXPECTED_PINS.items():
        blob = blobs[rel]
        require(type(blob) is bytes and 0 < len(blob) <= 600_000 and
                sha256(blob).hexdigest() == expected,
                'changed frozen source '+rel)
        trees[rel] = ast.parse(blob, filename=rel)
    compute = _function(trees[ARCH], '_compute_local')
    require(sha256(ast.dump(compute, include_attributes=False).encode('utf8')).hexdigest()
            == EXPECTED_COMPUTE_AST, 'compute body AST drift')
    _function(trees[ARCH], '_admit')
    require(sum(isinstance(x, ast.ClassDef) and x.name == 'LiveBVPlanV0e'
                for x in trees[SCHED].body) == 1, 'native BV plan missing or ambiguous')
    functions = (
        (SCHED, _function(trees[SCHED], 'execute_live_v0e'), 'scheduler_entrypoint'),
        (PRODUCER, _function(trees[PRODUCER], 'fixture'), 'fixture_entrypoint'),
        (ARCH, _function(trees[ARCH], '_compute_local'), 'neuron_compute_entrypoint'),
    )
    samples = {category: [] for category in NAME_HINTS}
    totals = {category: 0 for category in NAME_HINTS}
    for rel, node, label in functions:
        require(_signature(node) == actual[label], 'native API changed: '+label)
        for category, sites in _call_names(node).items():
            totals[category] += len(sites)
            for site in sites:
                if len(samples[category]) < 8:
                    samples[category].append({'file': rel, 'function': node.name,
                                               **site, 'verified_hook': False})
    return {
        'candidate_extraction': 'STATIC_CALL_NAME_MATCHES_NOT_EXECUTION_OR_DATA_FLOW',
        'candidate_count_by_category': totals,
        'bounded_callsite_examples': samples,
        'native_event_semantics_established': False,
        'native_listener_or_callback_installed': False,
        'source_file_sha256': {k: EXPECTED_PINS[k] for k in sorted(EXPECTED_PINS)},
    }


def analyze(v: dict, raw: bytes, *, blobs: dict[str, bytes] | None = None):
    actual = validate_predecessor(v, raw)
    verified = blobs is not None
    candidates = source_candidate_inventory(v, blobs) if verified else None
    require(len(PORT_OBLIGATIONS) == len({name for name, _ in PORT_OBLIGATIONS}),
            'duplicate design obligations')
    return {
        'schema': SCHEMA, 'status': STATUS,
        'source_kind': SOURCE_KIND_NATIVE if verified else SOURCE_KIND_OFFLINE,
        'reference_v1v_sha256': sha256(raw).hexdigest(),
        'reference_v1u_sha256': v['reference_v1u_sha256'],
        'native_source_readonly_bytes_rechecked_in_this_run': verified,
        'inherited_native_v1v_recomputation_verified_in_this_run': False,
        'confirmed_frozen_scheduler_signature': actual['scheduler_entrypoint'],
        'source_pinned_static_candidate_inventory': candidates,
        'integration_path_selection': 'VERSIONED_ADDITIVE_SOURCE_OWNED_OBSERVER_PORT_REQUIRED_NOT_INSTALLED',
        'design_port_name_only': 'spk-bv-observation-port/v1-proposal',
        'proposed_event_phases': [
            'predecision_expectation', 'decision', 'sender_port_emission',
            'receiver_ingress', 'interval_coverage_close', 'receiver_receipt',
            'local_value_judgment', 'bounded_reverse_feedback',
        ],
        'proof_obligations_unmet': [
            {'id': name, 'requirement': requirement, 'verified': False}
            for name, requirement in PORT_OBLIGATIONS
        ],
        'current_boundary_requirements_unmet': list(REQUIRED_BOUNDARY),
        'postreturn_trace_is_online_native_evidence': False,
        'static_candidate_is_runtime_event_hook': False,
        'native_event_callback_invoked': False,
        'native_observation_message_delivered_to_B': False,
        'native_authenticated_absence_coverage': False,
        'native_receiver_scored_judgments': 0,
        'native_operator_updates': 0,
        'native_learning_proven': False,
        'source_files_modified': False,
        'new_native_scheduler_executions_in_this_module': 0,
        'claims_excluded': list(CLAIMS_EXCLUDED),
    }
