"""SPK 24n: independent Core/network oracle adapter and evidence verification.

The independent interpreter lives in spk_24n_independent_oracle_v0 and imports
nothing from the frozen SPK modules. This adapter imports frozen codecs only to
translate admitted inputs and obtain actual results in its CLI/test harness.
"""
from __future__ import annotations

from dataclasses import asdict, is_dataclass
from hashlib import sha256
import argparse
import json
from pathlib import Path

from search.spk_24n_independent_oracle_v0 import (
    CaseV0, EdgeV0, EventV0, NodeV0, OracleDomainErrorV0, execute_v0,
)

SCHEMA = 'spk-independent-network-differential/v0'


class DifferentialMismatchV0(AssertionError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False)


def sha(text):
    return sha256(text.encode('utf-8')).hexdigest()


def _reject_dup(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError('duplicate JSON key')
        out[k] = v
    return out


def _reject_const(s):
    raise ValueError('nonfinite constant: ' + s)


def strict_json(s):
    if type(s) is not str:
        raise TypeError('JSON must be text')
    return json.loads(s, object_pairs_hook=_reject_dup, parse_constant=_reject_const)


def _instruction(ins):
    name = type(ins).__name__
    if name == 'CoreAcc':
        return ('ACC', (ins.weight, ins.channel))
    if name == 'CoreCmp':
        return ('CMP', ins.threshold_raw)
    if name == 'CoreEmit':
        return ('EMIT', ins.channel_out)
    if name == 'CoreReset':
        return ('RESET', ins.value_raw)
    if name == 'ShiftDecay':
        return ('SHIFT', ins.bits_per_tick)
    raise OracleDomainErrorV0('unsupported frozen instruction: ' + name)


def adapt_frozen_v0(network, events):
    """Mechanical data extraction. No frozen evaluator or helper is invoked."""
    return CaseV0(
        nodes=tuple(NodeV0(n.node_id, n.config.state_bits,
                           n.config.fractional_bits, n.initial_raw,
                           tuple(_instruction(x) for x in n.program.instructions))
                    for n in network.nodes),
        edges=tuple(EdgeV0(e.source_node, e.source_channel,
                           e.target_node, e.target_channel, e.delay_ticks)
                    for e in network.edges),
        events=tuple(EventV0(e.timestamp, e.node_id, e.channel)
                     for e in events),
    )


def _fields(item):
    if is_dataclass(item) and not isinstance(item, type):
        return asdict(item)
    if type(item) is dict:
        return item
    raise TypeError('expected observation/result dataclass or dict')


def _multiset(rows):
    return sorted(canonical(_fields(row)) for row in rows)


def project_v0(result, batches, routes):
    """Compare canonical observable multisets, not incidental tuple/list form.

    Same-timestamp events and routes have observable multiplicity but no
    semantically significant ordering; node states are matched by identity.
    """
    r = _fields(result)
    o = {
        'emissions': _multiset(r['emissions']),
        'terminal_outputs': _multiset(r['terminal_outputs']),
        'states': sorted([str(x['node_id']), x['raw'], x['last_timestamp']]
                         for x in map(_fields, r['states'])),
        'processed_batches': r['processed_batches'],
        'processed_events': r['processed_events'],
        'observations': {
            'batches': _multiset(batches),
            'routes': _multiset(routes),
        },
    }
    return o


def compare_actual_v0(network, events, actual_result, batches, routes,
                      *, max_batches=128, max_events=4096):
    """Compare separately computed expected result against frozen actual.

    This function never calls the frozen runtime. The caller supplies actual.
    """
    case = adapt_frozen_v0(network, events)
    expected = execute_v0(case, max_batches=max_batches, max_events=max_events)
    e = project_v0(expected, expected['observations']['batches'],
                   expected['observations']['routes'])
    a = project_v0(actual_result, batches, routes)
    if e != a:
        for field in ('emissions', 'terminal_outputs', 'states',
                      'processed_batches', 'processed_events', 'observations'):
            if e[field] != a[field]:
                if field == 'observations':
                    for sub in ('batches', 'routes'):
                        if e[field][sub] != a[field][sub]:
                            raise DifferentialMismatchV0(
                                'differential ' + field + '.' + sub + ' mismatch: '
                                + 'expected=' + repr(e[field][sub][:4])
                                + ' actual=' + repr(a[field][sub][:4]))
                raise DifferentialMismatchV0('differential ' + field + ' mismatch: '
                                             + 'expected=' + repr(e[field])[:700]
                                             + ' actual=' + repr(a[field])[:700])
    return {'status': 'PASS', 'oracle': e, 'oracle_sha256': sha(canonical(e))}


def verify_receipt_differential_v0(receipt):
    """Independently interpret a 24m compiled-manifest receipt.

    24m envelope verification is additive; it is not used to calculate the
    oracle expectation. The manifest decoder is shared input parsing only.
    """
    from search.spk_24m_compiler_network_evidence_v0 import verify_and_replay_v0
    from spk_compiler.compilation_manifest_v0 import loads_compilation_manifest_v0

    payload = verify_and_replay_v0(receipt)
    compiled = loads_compilation_manifest_v0(payload['manifest_json'])
    actual = payload['result']
    obs = payload['observations']
    report = compare_actual_v0(
        compiled.network, compiled.initial_events, actual,
        obs['batches'], obs['routes'],
        max_batches=payload['max_batches'], max_events=payload['max_events'],
    )
    report['receipt_sha256'] = sha(receipt)
    report['manifest_sha256'] = payload['manifest_sha256']
    return report


def seal_differential_v0(receipt):
    proof = verify_receipt_differential_v0(receipt)
    payload = {'receipt': receipt, 'comparison': proof}
    return canonical({'schema': SCHEMA, 'payload': payload,
                      'payload_sha256': sha(SCHEMA + '\n' + canonical(payload))})


def verify_differential_artifact_v0(document):
    obj = strict_json(document)
    if type(obj) is not dict or set(obj) != {'schema', 'payload', 'payload_sha256'}:
        raise ValueError('invalid artifact envelope')
    if obj['schema'] != SCHEMA or document != canonical(obj):
        raise ValueError('invalid schema or canonical encoding')
    if obj['payload_sha256'] != sha(SCHEMA + '\n' + canonical(obj['payload'])):
        raise ValueError('artifact checksum mismatch')
    payload = obj['payload']
    if type(payload) is not dict or set(payload) != {'receipt', 'comparison'}:
        raise ValueError('invalid artifact payload')
    result = verify_receipt_differential_v0(payload['receipt'])
    if payload['comparison'] != result:
        raise ValueError('differential artifact replay mismatch')
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--write', type=Path)
    group.add_argument('--verify', type=Path)
    args = p.parse_args(argv)
    if args.write is not None:
        from search.spk_24m_compiler_network_evidence_v0 import (
            compile_and_run_v0, reference_scenario_v0,
        )
        artifact = seal_differential_v0(compile_and_run_v0(**reference_scenario_v0()))
        args.write.write_text(artifact + '\n', encoding='utf-8')
    else:
        artifact = args.verify.read_text(encoding='utf-8').rstrip('\n')
    result = verify_differential_artifact_v0(artifact)
    print(canonical({k: v for k, v in result.items() if k != 'oracle'}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
