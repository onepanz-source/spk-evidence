"""SPK 24t: versioned bounded multineuron diagnostic-equivalence reference host.

The 24p host and frozen engine are unchanged. This contract avoids rejecting
an actually eligible tie diagnostic solely because another interpreter tests
its limits in a different order. It is fail-closed outside its finite domain.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from threading import RLock

from search.spk_24n_differential_evidence_v0 import (
    adapt_frozen_v0, canonical, compare_actual_v0, project_v0, sha, strict_json,
)
from search.spk_24p_network_application_host_v0 import (
    _attempt, _positive, _digest, _demo_manifest,
)
from search.spk_24t_diagnostic_contract_v0 import adjudicate_v0, classify_v0
from spk_compiler.compilation_manifest_v0 import loads_compilation_manifest_v0

SCHEMA = 'spk-diagnostic-equivalence-reference-host/v0'


def execute_manifest_v0(manifest_json, expected_manifest_sha256, *,
                        max_batches=128, max_events=4096):
    if type(manifest_json) is not str:
        raise TypeError('manifest_json must be text')
    pin = _digest(expected_manifest_sha256)
    if sha(manifest_json) != pin:
        raise ValueError('manifest source-pin mismatch')
    budgets = {'max_batches': _positive(max_batches, 'max_batches'),
               'max_events': _positive(max_events, 'max_events')}
    compiled = loads_compilation_manifest_v0(manifest_json)
    net, events = compiled.network, compiled.initial_events
    case = adapt_frozen_v0(net, events)
    # Bounded independent admission happens BEFORE the frozen run, so an
    # unsupported/too-large program never receives a completion receipt.
    proof = classify_v0(case, **budgets)
    off_status, off_value, _ = _attempt(net, events, budgets, observed=False)
    on_status, on_value, watcher = _attempt(net, events, budgets, observed=True)
    if off_status != on_status:
        raise AssertionError('observer changed execution status')
    if off_status == 'LIMIT_REACHED':
        if off_value != on_value:
            raise AssertionError('observer changed selected failure reason')
        verdict = adjudicate_v0(proof, observed_status=off_status,
                                observed_reason=off_value)
        return {'status': 'LIMIT_REACHED', 'selected_reason': off_value,
                'eligible_reasons': list(proof.eligible),
                'independent_choice': proof.independent_choice,
                'adjudication': verdict, 'result': None,
                'observations': None,
                'note': 'No successful result or rollback is claimed'}
    if off_status != 'CLOSED':
        raise AssertionError('unsupported frozen status')
    adjudicate_v0(proof, observed_status='CLOSED', observed_reason=None)
    if off_value != on_value:
        raise AssertionError('passive observer changed successful execution')
    check = compare_actual_v0(net, events, on_value,
                              watcher.batches, watcher.routes, **budgets)
    proj = project_v0(on_value, watcher.batches, watcher.routes)
    if check['status'] != 'PASS' or proj != check['oracle']:
        raise AssertionError('frozen and independent successful results differ')
    return {'status': 'CLOSED', 'selected_reason': None,
            'eligible_reasons': [], 'independent_choice': None,
            'adjudication': 'EXACT_PASS', 'result': proj,
            'observations': {'batch_count': len(watcher.batches),
                             'route_count': len(watcher.routes)}, 'note': None}


def _payload(manifest_json, expected_manifest_sha256, max_batches, max_events):
    return {'manifest_json': manifest_json,
            'manifest_sha256': expected_manifest_sha256,
            'max_batches': max_batches, 'max_events': max_events,
            'execution': execute_manifest_v0(
                manifest_json, expected_manifest_sha256,
                max_batches=max_batches, max_events=max_events)}


def seal_v0(manifest_json, expected_manifest_sha256, *,
            max_batches=128, max_events=4096):
    payload = _payload(manifest_json, expected_manifest_sha256,
                       max_batches, max_events)
    return canonical({'schema': SCHEMA, 'payload': payload,
                      'payload_sha256': sha(SCHEMA + '\n' + canonical(payload))})


def verify_v0(document):
    obj = strict_json(document)
    if (type(obj) is not dict or set(obj) !=
            {'schema', 'payload', 'payload_sha256'} or
            obj['schema'] != SCHEMA or canonical(obj) != document):
        raise ValueError('noncanonical diagnostic-equivalence host envelope')
    payload = obj['payload']
    if type(payload) is not dict or set(payload) != {
        'manifest_json', 'manifest_sha256', 'max_batches', 'max_events', 'execution'
    }:
        raise ValueError('invalid diagnostic-equivalence host fields')
    if sha(SCHEMA + '\n' + canonical(payload)) != obj['payload_sha256']:
        raise ValueError('diagnostic-equivalence host checksum mismatch')
    recalculated = _payload(payload['manifest_json'], payload['manifest_sha256'],
                            payload['max_batches'], payload['max_events'])
    if recalculated != payload:
        raise ValueError('diagnostic-equivalence host replay mismatch')
    return {'status': payload['execution']['status'],
            'selected_reason': payload['execution']['selected_reason'],
            'adjudication': payload['execution']['adjudication'],
            'eligible_reasons': payload['execution']['eligible_reasons'],
            'manifest_sha256': payload['manifest_sha256'],
            'evidence_sha256': sha(document)}


class DiagnosticReferenceHostV0:
    """Cooperatively single-shot reference object. Not durable authority."""
    def __init__(self, manifest_json, expected_manifest_sha256):
        if type(manifest_json) is not str:
            raise TypeError('manifest_json must be text')
        self._manifest = manifest_json
        self._digest = _digest(expected_manifest_sha256)
        self._lock = RLock()
        self._phase = 'NEW'
        self._receipt = None

    @property
    def phase(self):
        with self._lock:
            return self._phase

    def run(self, *, max_batches=128, max_events=4096):
        with self._lock:
            if self._phase != 'NEW':
                raise RuntimeError('single-shot host already consumed')
            self._phase = 'FAILED'
            receipt = seal_v0(self._manifest, self._digest,
                              max_batches=max_batches, max_events=max_events)
            self._phase = strict_json(receipt)['payload']['execution']['status']
            self._receipt = receipt
            return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--write-demo', type=Path)
    mode.add_argument('--verify', type=Path)
    parser.add_argument('--max-batches', type=int, default=128)
    parser.add_argument('--max-events', type=int, default=4096)
    args = parser.parse_args(argv)
    if args.write_demo is not None:
        manifest, pin = _demo_manifest()
        document = DiagnosticReferenceHostV0(manifest, pin).run(
            max_batches=args.max_batches, max_events=args.max_events)
        args.write_demo.write_text(document + '\n', encoding='utf-8')
    else:
        document = args.verify.read_text(encoding='utf-8').rstrip('\n')
    print(canonical(verify_v0(document)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
