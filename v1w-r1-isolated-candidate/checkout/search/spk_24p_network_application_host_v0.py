"""SPK 24p: bounded single-shot multineuron network *reference* host.

Separate from 24j single-root / no-output host. Requires a caller-pinned
compilation manifest. Never replaces the frozen Compiler, Core or Network.
The accepted error domain is NetworkExecutionLimitV0, not all runtime errors.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock

from search.spk_24n_differential_evidence_v0 import (
    adapt_frozen_v0, canonical, compare_actual_v0, project_v0, sha, strict_json,
)
from search.spk_24n_independent_oracle_v0 import execute_v0, OracleLimitV0
from spk_compiler.compilation_manifest_v0 import loads_compilation_manifest_v0
from spk_network.runtime_v0 import run_network_v0, NetworkExecutionLimitV0

SCHEMA = 'spk-multineuron-reference-host-evidence/v0'


def _positive(value, name):
    if type(value) is not int or value < 1:
        raise ValueError(name + ' requires a positive integer')
    return value


def _digest(value):
    if (type(value) is not str or len(value) != 64 or
            any(ch not in '0123456789abcdef' for ch in value)):
        raise ValueError('expected_manifest_sha256 must be lowercase SHA-256')
    return value


def _limit_reason(error):
    message = str(error)
    matches = [x for x in ('max_batches', 'max_events') if x in message]
    if len(matches) != 1:
        raise AssertionError('unclassifiable or ambiguous Network execution limit') from error
    return matches[0]


@dataclass
class _PassiveRecorder:
    batches: list = field(default_factory=list)
    routes: list = field(default_factory=list)

    def on_batch(self, entry):
        self.batches.append(entry)

    def on_route(self, entry):
        self.routes.append(entry)


def _attempt(network, events, budget, *, observed):
    recorder = _PassiveRecorder()
    args = dict(max_batches=budget['max_batches'], max_events=budget['max_events'])
    if observed:
        args['learning_observer'] = recorder
    try:
        return ('CLOSED', run_network_v0(network, events, **args), recorder)
    except NetworkExecutionLimitV0 as error:
        return ('LIMIT_REACHED', _limit_reason(error), recorder)


def execute_manifest_v0(manifest_json, expected_manifest_sha256, *,
                        max_batches=128, max_events=4096):
    """One finite execution. Checks full success/limit parity with independent 24n.

    An exception outside the declared limit category propagates, with no
    result envelope. Partial work before a limit is NOT promised to rollback.
    """
    if type(manifest_json) is not str:
        raise TypeError('manifest_json must be text')
    digest = _digest(expected_manifest_sha256)
    if sha(manifest_json) != digest:
        raise ValueError('manifest source-pin mismatch')
    budgets = {'max_batches': _positive(max_batches, 'max_batches'),
               'max_events': _positive(max_events, 'max_events')}
    compiled = loads_compilation_manifest_v0(manifest_json)
    network, events = compiled.network, compiled.initial_events

    plain_status, plain_value, _ = _attempt(network, events, budgets, observed=False)
    watched_status, watched_value, watcher = _attempt(network, events, budgets, observed=True)
    if plain_status != watched_status:
        raise AssertionError('observer changed execution outcome')

    case = adapt_frozen_v0(network, events)
    if plain_status == 'LIMIT_REACHED':
        if plain_value != watched_value:
            raise AssertionError('observer changed execution limit reason')
        try:
            execute_v0(case, **budgets)
        except OracleLimitV0 as independent_error:
            if _limit_reason(independent_error) != plain_value:
                raise AssertionError('oracle and frozen limit reasons differ') from independent_error
        else:
            raise AssertionError('frozen runtime reached a limit absent in independent oracle')
        return {'status': 'LIMIT_REACHED', 'reason': plain_value, 'result': None,
                'comparison': None, 'observations': None,
                'note': 'No successful receipt or atomic rollback claim'}

    if plain_value != watched_value:
        raise AssertionError('observer changed full successful execution result')
    proof = compare_actual_v0(network, events, watched_value,
                              watcher.batches, watcher.routes, **budgets)
    projection = project_v0(watched_value, watcher.batches, watcher.routes)
    if projection != proof['oracle']:
        raise AssertionError('independent oracle and runtime projection differ')
    return {'status': 'CLOSED', 'reason': None, 'result': projection,
            'comparison': 'INDEPENDENT_PASS', 'observations': {
                'batch_count': len(watcher.batches), 'route_count': len(watcher.routes),
            }, 'note': None}


def _payload(manifest_json, expected_manifest_sha256, max_batches, max_events):
    result = execute_manifest_v0(manifest_json, expected_manifest_sha256,
                                 max_batches=max_batches, max_events=max_events)
    return {'manifest_json': manifest_json, 'manifest_sha256': expected_manifest_sha256,
            'max_batches': max_batches, 'max_events': max_events,
            'execution': result}


def seal_v0(manifest_json, expected_manifest_sha256, *,
            max_batches=128, max_events=4096):
    payload = _payload(manifest_json, expected_manifest_sha256, max_batches, max_events)
    return canonical({'schema': SCHEMA, 'payload': payload,
                      'payload_sha256': sha(SCHEMA + '\n' + canonical(payload))})


def verify_v0(document):
    obj = strict_json(document)
    if (type(obj) is not dict or set(obj) != {'schema', 'payload', 'payload_sha256'}
            or obj['schema'] != SCHEMA or canonical(obj) != document):
        raise ValueError('invalid or noncanonical host evidence envelope')
    payload = obj['payload']
    if type(payload) is not dict or set(payload) != {
        'manifest_json', 'manifest_sha256', 'max_batches', 'max_events', 'execution'
    }:
        raise ValueError('invalid host evidence fields')
    if sha(SCHEMA + '\n' + canonical(payload)) != obj['payload_sha256']:
        raise ValueError('host evidence checksum mismatch')
    expected = _payload(payload['manifest_json'], payload['manifest_sha256'],
                        payload['max_batches'], payload['max_events'])
    if expected != payload:
        raise ValueError('host evidence replay mismatch')
    return {'status': payload['execution']['status'], 'reason': payload['execution']['reason'],
            'manifest_sha256': payload['manifest_sha256'], 'evidence_sha256': sha(document)}


class NetworkReferenceHostV0:
    """One manifest, one run, no reset. Serializes cooperative callers.

    This is not a process-unique authority or a replacement for 24j custody.
    """
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
            # Even an invalid attempt irreversibly consumes this reference host;
            # the caller can create a new instance after correcting its request.
            self._phase = 'FAILED'
            receipt = seal_v0(self._manifest, self._digest,
                              max_batches=max_batches, max_events=max_events)
            status = strict_json(receipt)['payload']['execution']['status']
            self._receipt = receipt
            self._phase = status
            return receipt


def _demo_manifest():
    from spk_compiler.compile_pipeline_v0 import compile_network_ir_v0
    from spk_compiler.compilation_manifest_v0 import dumps_compilation_manifest_v0
    from search.spk_24m_compiler_network_evidence_v0 import reference_scenario_v0
    compiled = compile_network_ir_v0(**reference_scenario_v0())
    manifest = dumps_compilation_manifest_v0(compiled)
    return manifest, sha(manifest)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--write-demo', type=Path)
    mode.add_argument('--verify', type=Path)
    parser.add_argument('--max-batches', type=int, default=128)
    parser.add_argument('--max-events', type=int, default=4096)
    args = parser.parse_args(argv)
    if args.write_demo is not None:
        manifest, pinned = _demo_manifest()
        document = NetworkReferenceHostV0(manifest, pinned).run(
            max_batches=args.max_batches, max_events=args.max_events)
        args.write_demo.write_text(document + '\n', encoding='utf-8')
    else:
        document = args.verify.read_text(encoding='utf-8').rstrip('\n')
    print(canonical(verify_v0(document)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
