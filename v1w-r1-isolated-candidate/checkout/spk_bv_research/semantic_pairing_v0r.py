"""SPK BV v0r. Offline signature-based pairing of two feedback-enabled runs.

Proof domain: native typed *records*, not simulator causal-event equivalence.
Requires existing v0q within-run packet/grant/assessment checks. Never infers
cross-run identity from the same auto-generated packet_id.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from .native_capture_v0k import _sha
from .feedback_lineage_v0q import run_extract, get, deny

SCHEMA = 'spk-bv-native-semantic-packet-pairing/v0r'
STATUS = 'STRUCTURAL_SEMANTIC_SIGNATURE_COMPARISON_ONLY'


def _canonical(fields, excluded):
    return {k: v for k, v in sorted(fields.items()) if k not in excluded}


def _strict_nonnegative(value, name):
    if type(value) is not int or value < 0:
        deny('invalid nonnegative tick/wait: ' + name)
    return value


def _signature_rows(run):
    deliveries, grants, assessments = run_extract(run)
    signatures = defaultdict(list)
    assessment_signatures = Counter()
    for assessment in assessments.values():
        s = _sha(_canonical(assessment, {'id', 'tick'}))
        assessment_signatures[s] += 1
    for packet_id in sorted(deliveries):
        delivery, grant = deliveries[packet_id], grants[packet_id]
        aid = delivery['assessment_id']
        assessment = assessments[aid]
        stamp = {
            'assessment': _canonical(assessment, {'id', 'tick'}),
            'delivery': _canonical(delivery, {'packet_id', 'assessment_id', 'tick'}),
            'grant': _canonical(grant, {'packet_id', 'assessment_id', 'tick', 'delivered_at', 'wait'}),
        }
        sig = _sha(stamp)
        signatures[sig].append({
            'packet_id': packet_id,
            'assessment_id': aid,
            'delivery_tick': _strict_nonnegative(delivery['tick'], 'delivery'),
            'grant_tick': _strict_nonnegative(grant['tick'], 'grant'),
            'delivered_at': _strict_nonnegative(grant['delivered_at'], 'delivered_at'),
            'native_reported_wait': _strict_nonnegative(grant['wait'], 'wait'),
        })
    return signatures, assessment_signatures, len(deliveries), len(assessments)


def compare(native_root, fixture_sha):
    if type(native_root) is not dict or native_root.get('$t') != 'tuple' or len(native_root.get('items', [])) != 5:
        deny('unexpected five-element native fixture')
    first, second = native_root['items'][3:5]
    if (get(first, 'enabled'), get(second, 'enabled')) != (True, True):
        deny('v0r only accepts two feedback-enabled runs')
    if (get(first, 'policy'), get(second, 'policy')) != ('forward-first', 'feedback-first'):
        deny('unexpected policy pairing')
    sig_a, ass_a, packets_a, total_a = _signature_rows(first)
    sig_b, ass_b, packets_b, total_b = _signature_rows(second)
    count_a = Counter({s: len(v) for s, v in sig_a.items()})
    count_b = Counter({s: len(v) for s, v in sig_b.items()})
    if packets_a == 0 or packets_b == 0:
        deny('empty feedback packet set cannot establish semantic correspondence')
    sig_match = count_a == count_b
    ass_match = ass_a == ass_b
    groups = []
    unique = []
    for signature in sorted(set(sig_a) | set(sig_b)):
        a = sorted(sig_a.get(signature, []), key=lambda x: x['packet_id'])
        b = sorted(sig_b.get(signature, []), key=lambda x: x['packet_id'])
        one_to_one = len(a) == len(b) == 1
        group = {
            'signature_sha256': signature,
            'first_count': len(a),
            'second_count': len(b),
            'first_packet_ids': [x['packet_id'] for x in a],
            'second_packet_ids': [x['packet_id'] for x in b],
            'per_packet_identity_resolved': one_to_one,
        }
        if one_to_one:
            pa, pb = a[0], b[0]
            deltas = {k: pb[k] - pa[k] for k in ('delivery_tick', 'grant_tick', 'delivered_at', 'native_reported_wait')}
            group['identity_pair'] = {
                'first_packet_id': pa['packet_id'],
                'second_packet_id': pb['packet_id'],
                'first_assessment_id': pa['assessment_id'],
                'second_assessment_id': pb['assessment_id'],
                'deltas_second_minus_first': deltas,
            }
            unique.append(group['identity_pair'])
        groups.append(group)
    ambiguous = sum(1 for g in groups if g['first_count'] > 1 or g['second_count'] > 1)
    unmatched_a = sum((count_a - count_b).values())
    unmatched_b = sum((count_b - count_a).values())
    bijective = sig_match and ass_match and not ambiguous
    return {
        'schema': SCHEMA,
        'status': STATUS,
        'native_fixture_sha256': fixture_sha,
        'comparison': 'forward-first_vs_feedback-first_both_feedback_enabled',
        'first_packets': packets_a,
        'second_packets': packets_b,
        'first_assessments': total_a,
        'second_assessments': total_b,
        'assessment_payload_multisets_equal': ass_match,
        'feedback_record_signature_multisets_equal': sig_match,
        'unmatched_signatures_first': unmatched_a,
        'unmatched_signatures_second': unmatched_b,
        'ambiguous_signature_groups': ambiguous,
        'unique_cross_policy_pair_count': len(unique),
        'complete_unambiguous_structural_pairing': bijective,
        'signature_policy': {
            'assessment_omitted': ['id', 'tick'],
            'delivery_omitted': ['packet_id', 'assessment_id', 'tick'],
            'grant_omitted': ['packet_id', 'assessment_id', 'tick', 'delivered_at', 'wait'],
            'other_fields_retained': True,
            'lists_order_and_multiplicity_retained': True,
        },
        'relabelled_packet_pairs': [p for p in unique if p['first_packet_id'] != p['second_packet_id']],
        'signature_groups': groups,
        'claims_excluded': [
            'packet-ids-are-global-identities',
            'distinct-semantic-signatures-prove-distinct-causal-events',
            'same-payload-proves-same-runtime-event',
            'feedback-on-off-comparison',
            'equal-effective-workload-proof',
            'causal-benefit-or-learning',
            'hardware-energy-or-latency',
            'v0h-528-stress-equivalence',
            'architecture-promotion',
        ],
    }
