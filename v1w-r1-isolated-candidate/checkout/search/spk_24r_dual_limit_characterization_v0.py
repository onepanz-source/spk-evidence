"""SPK 24r: simultaneous-limit characterization on frozen Network v0.

The independent 24n engine proves that *both* limits are eligible at one
pending batch. It does not prescribe which limit Network v0 must report.
This is a bounded, observational characterization, NOT an SPK-wide priority
contract. No successful result or rollback is asserted for failed executions.
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from search.spk_24n_differential_evidence_v0 import canonical, sha, strict_json
from search.spk_24o_extended_differential_v0 import to_frozen_v0
from search.spk_24q_failure_parity_v0 import _attempt_frozen
from search.spk_24q_limit_probe_plan_v0 import BudgetProbeV0
from search.spk_24r_dual_limit_plan_v0 import (
    plan_v0, check_eligibility_v0, summary_v0,
)

SCHEMA = 'spk-dual-limit-characterization-evidence/v0'
KNOWN_REASONS = frozenset(('max_batches', 'max_events'))


def evaluate_v0(case, probe):
    eligibility = check_eligibility_v0(case, probe)
    network, events = to_frozen_v0(case)
    pair = BudgetProbeV0(probe.case_id, 'dual_eligible',
                         probe.max_batches, probe.max_events,
                         'LIMIT_REACHED', None)
    without, reason_without, _ = _attempt_frozen(network, events, pair, False)
    with_obs, reason_with, _ = _attempt_frozen(network, events, pair, True)
    if without != 'LIMIT_REACHED' or with_obs != 'LIMIT_REACHED':
        raise AssertionError(probe.case_id + ': simultaneous exhaustion not reported as limit')
    if (reason_without not in KNOWN_REASONS or
            reason_without != reason_with):
        raise AssertionError(probe.case_id + ': passive observer changed limit priority')
    # The independent reason is retained for transparency but not considered
    # normative precedence when two preconditions hold simultaneously.
    return {
        'case_id': probe.case_id,
        'max_batches': probe.max_batches,
        'max_events': probe.max_events,
        'prior_batches': probe.prior_batches,
        'prior_events': probe.prior_events,
        'pending_batch_events': probe.pending_batch_events,
        'both_eligible': eligibility['both_eligible'],
        'independent_reason': eligibility['independent_reason'],
        'frozen_reason': reason_without,
        'status': 'LIMIT_REACHED',
        'result_sha256': None,
    }


def report_v0():
    rows = [evaluate_v0(case, p) for _, case, p in plan_v0()]
    summary = summary_v0()
    if len(rows) != summary['dual_limit_probes']:
        raise AssertionError('incorrect simultaneous-limit probe count')
    counts = Counter(r['frozen_reason'] for r in rows)
    summary = {**summary, 'frozen_reason_counts': {
        'max_batches': counts.get('max_batches', 0),
        'max_events': counts.get('max_events', 0),
    }}
    return {'schema': SCHEMA, 'summary': summary, 'rows': rows}


def seal_v0():
    payload = report_v0()
    return canonical({'schema': SCHEMA, 'payload': payload,
                      'payload_sha256': sha(SCHEMA + '\n' + canonical(payload))})


def verify_v0(document):
    env = strict_json(document)
    if (type(env) is not dict or set(env) !=
            {'schema', 'payload', 'payload_sha256'} or
            env['schema'] != SCHEMA or document != canonical(env)):
        raise ValueError('noncanonical or invalid dual-limit envelope')
    if env['payload_sha256'] != sha(SCHEMA + '\n' + canonical(env['payload'])):
        raise ValueError('dual-limit payload checksum mismatch')
    replay = report_v0()
    if env['payload'] != replay:
        raise ValueError('dual-limit replay mismatch')
    return {'status': 'PASS', **replay['summary'], 'evidence_sha256': sha(document)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--write', type=Path)
    mode.add_argument('--verify', type=Path)
    args = parser.parse_args(argv)
    if args.write is not None:
        doc = seal_v0()
        args.write.write_text(doc + '\n', encoding='utf-8')
    else:
        doc = args.verify.read_text(encoding='utf-8').rstrip('\n')
    print(canonical(verify_v0(doc)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
