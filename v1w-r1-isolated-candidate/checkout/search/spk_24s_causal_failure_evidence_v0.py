"""SPK 24s: isolated-limit control evidence around each dual-exhaustion tie.

Empirical, bounded classification. A frozen choice in a tie is a diagnostic,
not a new SPK precedence rule; singleton cases require exact reason parity.
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from search.spk_24n_differential_evidence_v0 import canonical, sha, strict_json
from search.spk_24o_extended_differential_v0 import to_frozen_v0
from search.spk_24q_failure_parity_v0 import _attempt_frozen
from search.spk_24s_budget_triads_v0 import plan_v0, summary_v0

SCHEMA = 'spk-causal-budget-failure-evidence/v0'
REASONS = frozenset(('max_events', 'max_batches'))


def evaluate_one_v0(network, events, ctrl):
    off_status, off_reason, _ = _attempt_frozen(network, events, ctrl, False)
    on_status, on_reason, _ = _attempt_frozen(network, events, ctrl, True)
    if off_status != 'LIMIT_REACHED' or on_status != 'LIMIT_REACHED':
        raise AssertionError(ctrl.case_id + '/' + ctrl.condition + ': incomplete run reported success')
    if off_reason not in REASONS or off_reason != on_reason:
        raise AssertionError(ctrl.case_id + '/' + ctrl.condition + ': observer changed failure reason')
    if off_reason not in ctrl.expected_violated:
        raise AssertionError(ctrl.case_id + '/' + ctrl.condition + ': noneligible failure reason')
    if len(ctrl.expected_violated) == 1 and off_reason != ctrl.independent_reason:
        raise AssertionError(ctrl.case_id + '/' + ctrl.condition + ': isolated-budget differential failure')
    return {
        'case_id': ctrl.case_id,
        'condition': ctrl.condition,
        'max_batches': ctrl.max_batches,
        'max_events': ctrl.max_events,
        'violated_at_same_batch': list(ctrl.expected_violated),
        'independent_reason': ctrl.independent_reason,
        'frozen_reason': off_reason,
        'independent_selection_differs': off_reason != ctrl.independent_reason,
        'status': 'LIMIT_REACHED',
        'result_sha256': None,
    }


def evaluate_triad_v0(case, controls):
    if tuple(c.condition for c in controls) != ('both', 'events_only', 'batches_only'):
        raise AssertionError('invalid causal triplet order')
    net, events = to_frozen_v0(case)
    rows = tuple(evaluate_one_v0(net, events, c) for c in controls)
    # Both control cases must isolate their corresponding error.
    if (rows[1]['frozen_reason'] != 'max_events' or
            rows[2]['frozen_reason'] != 'max_batches'):
        raise AssertionError('isolated controls did not discriminate failure sources')
    return rows


def report_v0():
    plan = plan_v0()
    rows = [row for _, case, cs in plan for row in evaluate_triad_v0(case, cs)]
    summary = summary_v0()
    if len(rows) != summary['control_probes']:
        raise AssertionError('incorrect control count')
    tie_rows = [r for r in rows if r['condition'] == 'both']
    counts = Counter(r['frozen_reason'] for r in tie_rows)
    summary = {
        **summary,
        'observed_tie_reason_counts': {
            'max_batches': counts.get('max_batches', 0),
            'max_events': counts.get('max_events', 0),
        },
        'ties_differing_from_independent_choice': sum(
            r['independent_selection_differs'] for r in tie_rows
        ),
        'singleton_exact_agreement': sum(
            r['frozen_reason'] == r['independent_reason'] for r in rows
            if r['condition'] != 'both'
        ),
    }
    if summary['singleton_exact_agreement'] != summary['triad_count'] * 2:
        raise AssertionError('isolated controls failed exact agreement')
    return {'schema': SCHEMA, 'summary': summary, 'rows': rows}


def seal_v0():
    payload = report_v0()
    return canonical({'schema': SCHEMA, 'payload': payload,
                      'payload_sha256': sha(SCHEMA + '\n' + canonical(payload))})


def verify_v0(document):
    envelope = strict_json(document)
    if (type(envelope) is not dict or set(envelope) !=
            {'schema', 'payload', 'payload_sha256'} or
            envelope['schema'] != SCHEMA or document != canonical(envelope)):
        raise ValueError('invalid or noncanonical causal-budget envelope')
    if envelope['payload_sha256'] != sha(SCHEMA + '\n' + canonical(envelope['payload'])):
        raise ValueError('causal-budget checksum mismatch')
    if envelope['payload'] != report_v0():
        raise ValueError('causal-budget replay mismatch')
    return {'status': 'PASS', **envelope['payload']['summary'],
            'evidence_sha256': sha(document)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--write', type=Path)
    modes.add_argument('--verify', type=Path)
    args = parser.parse_args(argv)
    if args.write:
        document = seal_v0()
        args.write.write_text(document + '\n', encoding='utf-8')
    else:
        document = args.verify.read_text(encoding='utf-8').rstrip('\n')
    print(canonical(verify_v0(document)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
