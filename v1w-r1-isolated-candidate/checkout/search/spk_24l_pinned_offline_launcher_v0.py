"""SPK 24l: cooperative pinned-source offline launcher with live POSIX lease.

This wraps the already-gated 24k launcher. Source pinning is a local operator
configuration check, NOT producer authentication. The lease only excludes
concurrent cooperating executions in the same trusted local namespace.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from typing import Sequence

from search.spk_application_runtime_launcher_v0 import (
    run_offline_epoch_v0, OfflineEpochResultV0, EXIT_COMPLETED,
    EXIT_FAILURE, EXIT_INCOMPLETE,
)
from spk_simulator.application_trust_boundary_v0 import (
    LocalEpochLeaseV0, SourcePinErrorV0, resolve_pinned_factory_v0,
    result_fingerprint_v0, _hex_sha256,
)


class OfflineResultDriftV0(RuntimeError):
    """Actual public-result fingerprint differs from an explicit golden one."""


@dataclass(frozen=True, slots=True)
class PinnedOfflineExecutionV0:
    result: OfflineEpochResultV0
    result_sha256: str
    source_sha256: str


def run_pinned_offline_epoch_v0(
    *, provider: str, expected_source_sha256: str, epoch_id: str,
    lock_dir: str, max_actions: int, chunk_size: int,
    expected_result_sha256: str | None = None,
) -> PinnedOfflineExecutionV0:
    """Pin one explicitly trusted module and exclude overlapping local runs.

    Never attempts restart/resume/replay of a previous authority. A second
    sequential invocation creates a new execution, even for the same epoch.
    """
    if type(epoch_id) is not str or not epoch_id:
        raise ValueError('epoch_id must be a nonempty exact string')
    for name, n in (('max_actions', max_actions), ('chunk_size', chunk_size)):
        if type(n) is not int or n < 1:
            raise ValueError(f'{name} must be an exact positive integer')
    if expected_result_sha256 is not None and not _hex_sha256(expected_result_sha256):
        raise SourcePinErrorV0('expected result SHA256 must be lowercase hex')
    # Always acquire lease BEFORE importing the provider or calling its factory.
    with LocalEpochLeaseV0(epoch_id, lock_dir):
        factory = resolve_pinned_factory_v0(provider, expected_source_sha256)
        result = run_offline_epoch_v0(
            factory=factory, provider_id=provider, epoch_id=epoch_id,
            max_actions=max_actions, chunk_size=chunk_size,
        )
        digest = result_fingerprint_v0(result)
        if expected_result_sha256 is not None and digest != expected_result_sha256:
            raise OfflineResultDriftV0('offline public-result digest mismatch')
        return PinnedOfflineExecutionV0(result, digest, expected_source_sha256)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description='SPK offline pinned-source reference launcher (trusted local code only)')
    parser.add_argument('--provider', required=True, help='operator-approved module.path:factory')
    parser.add_argument('--provider-sha256', required=True, help='expected SHA256 of module .py bytes')
    parser.add_argument('--lock-dir', required=True, help='pre-existing private local directory (0700)')
    parser.add_argument('--epoch-id', required=True)
    parser.add_argument('--max-actions', required=True, type=int)
    parser.add_argument('--chunk-size', type=int, default=8)
    parser.add_argument('--expected-result-sha256')
    args = parser.parse_args(argv)
    try:
        run = run_pinned_offline_epoch_v0(
            provider=args.provider, expected_source_sha256=args.provider_sha256,
            lock_dir=args.lock_dir, epoch_id=args.epoch_id,
            max_actions=args.max_actions, chunk_size=args.chunk_size,
            expected_result_sha256=args.expected_result_sha256,
        )
    except Exception as exc:
        # No success-shaped record is ever produced for an exception.
        print(json.dumps({'status': 'ERROR', 'error_type': type(exc).__name__,
                          'detail': str(exc)}, sort_keys=True))
        return EXIT_FAILURE
    record = asdict(run.result)
    record.update(source_sha256=run.source_sha256, result_sha256=run.result_sha256)
    print(json.dumps(record, sort_keys=True))
    return EXIT_COMPLETED if run.result.completed else EXIT_INCOMPLETE


if __name__ == '__main__':
    raise SystemExit(main())
