"""SPK 24q: bounded corpus-wide exact-budget and failure parity evidence.

Runs independent 24n primitive oracle and frozen SPK Network v0 separately.
No result is attributed to Core/Network from a synthetic evaluator.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from search.spk_24n_independent_oracle_v0 import execute_v0, OracleLimitV0
from search.spk_24n_differential_evidence_v0 import (
    canonical, compare_actual_v0, project_v0, sha, strict_json,
)
from search.spk_24o_extended_differential_v0 import Recorder, to_frozen_v0
from search.spk_24q_limit_probe_plan_v0 import plan_v0, plan_summary_v0
from spk_network.runtime_v0 import run_network_v0, NetworkExecutionLimitV0

SCHEMA = 'spk-corpus-failure-parity-evidence/v0'


def _reason(exc):
    # Use exactly the typed failure and reason contract already accepted in 24p.
    from search.spk_24p_network_application_host_v0 import _limit_reason
    return _limit_reason(exc)


def _attempt_frozen(net, events, probe, observed):
    options = dict(max_batches=probe.max_batches, max_events=probe.max_events)
    recorder = Recorder([], [])
    if observed:
        options['learning_observer'] = recorder
    try:
        return 'CLOSED', run_network_v0(net, events, **options), recorder
    except NetworkExecutionLimitV0 as exc:
        return 'LIMIT_REACHED', _reason(exc), recorder


def _attempt_oracle(case, probe):
    try:
        return 'CLOSED', execute_v0(case, max_batches=probe.max_batches,
                                    max_events=probe.max_events)
    except OracleLimitV0 as exc:
        return 'LIMIT_REACHED', _reason(exc)


def evaluate_probe_v0(case, net, events, probe):
    """Fail closed on differing status, exact limit reason or successful output.

    Observer output after an execution limit is partial and not a receipt.
    The comparison intentionally makes no rollback or partial-trace claim.
    """
    off_status, off_value, _ = _attempt_frozen(net, events, probe, False)
    on_status, on_value, recorder = _attempt_frozen(net, events, probe, True)
    oracle_status, oracle_value = _attempt_oracle(case, probe)
    if (off_status != probe.expected_status or
            on_status != probe.expected_status or
            oracle_status != probe.expected_status):
        raise AssertionError(f'{probe.case_id}/{probe.kind}: execution status disagreement')
    if off_status == 'LIMIT_REACHED':
        if not (off_value == on_value == oracle_value == probe.expected_reason):
            raise AssertionError(f'{probe.case_id}/{probe.kind}: limit reason disagreement')
        return {'case_id': probe.case_id, 'kind': probe.kind,
                'max_batches': probe.max_batches, 'max_events': probe.max_events,
                'status': 'LIMIT_REACHED', 'reason': probe.expected_reason,
                'result_sha256': None}
    if off_value != on_value:
        raise AssertionError(f'{probe.case_id}/{probe.kind}: observer altered result')
    proof = compare_actual_v0(net, events, on_value,
                              recorder.batches, recorder.routes,
                              max_batches=probe.max_batches,
                              max_events=probe.max_events)
    frozen_projection = project_v0(on_value, recorder.batches, recorder.routes)
    oracle_projection = project_v0(
        oracle_value,
        oracle_value['observations']['batches'],
        oracle_value['observations']['routes'],
    )
    if (proof['status'] != 'PASS' or frozen_projection != proof['oracle']
            or frozen_projection != oracle_projection):
        raise AssertionError(f'{probe.case_id}/{probe.kind}: independent result disagreement')
    return {'case_id': probe.case_id, 'kind': probe.kind,
            'max_batches': probe.max_batches, 'max_events': probe.max_events,
            'status': 'CLOSED', 'reason': None,
            'result_sha256': sha(canonical(frozen_projection))}


def report_v0():
    summary = plan_summary_v0()
    rows = []
    for cid, case, probes in plan_v0():
        network, events = to_frozen_v0(case)
        for probe in probes:
            assert probe.case_id == cid
            rows.append(evaluate_probe_v0(case, network, events, probe))
    if len(rows) != summary['probe_count']:
        raise AssertionError('probe count mismatch')
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
        raise ValueError('invalid or noncanonical failure-parity envelope')
    payload = envelope['payload']
    if sha(SCHEMA + '\n' + canonical(payload)) != envelope['payload_sha256']:
        raise ValueError('failure-parity payload checksum mismatch')
    if payload != report_v0():
        raise ValueError('failure-parity replay mismatch')
    return {'status': 'PASS', **plan_summary_v0(),
            'evidence_sha256': sha(document)}


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
