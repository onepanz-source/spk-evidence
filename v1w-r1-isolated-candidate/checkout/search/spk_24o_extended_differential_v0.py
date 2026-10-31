"""24o extended Network v0 differential and noninterference corpus evidence.

24n provides the independent interpreter. This module translates *inputs* to
frozen types and executes the real Network v0. No frozen evaluator contributes
expected oracle output. All comparisons are full-field, with multiplicities.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
import argparse
from pathlib import Path

from search.spk_24n_differential_evidence_v0 import (
    canonical, compare_actual_v0, project_v0, sha, strict_json,
)
from search.spk_24n_independent_oracle_v0 import execute_v0
from search.spk_24o_semantic_corpus_v0 import (
    SCHEMA as CORPUS_SCHEMA, catalog_v0, catalog_fingerprint_v0,
)
from spk_core.isa import (
    CoreAcc, CoreCmp, CoreConfig, CoreEmit, CoreProgram, CoreReset, ShiftDecay,
)
from spk_network.events_v0 import NetworkEventV0
from spk_network.model_v0 import NetworkNodeV0, NetworkEdgeV0, NetworkV0
from spk_network.runtime_v0 import run_network_v0

SCHEMA = 'spk-extended-semantic-differential-evidence/v0'


def _frozen_instruction(op, arg):
    if op == 'ACC':
        return CoreAcc(arg[0], arg[1])
    if op == 'CMP':
        return CoreCmp(arg)
    if op == 'EMIT':
        return CoreEmit(arg)
    if op == 'RESET':
        return CoreReset(arg)
    if op == 'SHIFT':
        return ShiftDecay(arg)
    raise ValueError('unsupported corpus instruction: ' + str(op))


def _admitted_instructions_v0(instructions):
    """Remove only consecutive, overwritten CMP guards at the Core-IR boundary.

    A subsequent CMP replaces the prior guard without modifying neuron state or
    producing an effect. This is an admission normalization, not an evaluation:
    the original primitive program remains unchanged for the independent oracle.
    All other instructions and their order are preserved.
    """
    admitted = []
    for instruction in instructions:
        if (instruction[0] == 'CMP' and admitted and admitted[-1][0] == 'CMP'):
            admitted[-1] = instruction
        else:
            admitted.append(instruction)
    return tuple(admitted)


def to_frozen_v0(case):
    """Construct runtime-normalized frozen inputs; never evaluate expected output."""
    network = NetworkV0(tuple(
        NetworkNodeV0(n.node_id, CoreConfig(n.state_bits, n.fractional_bits),
                      CoreProgram(tuple(_frozen_instruction(op, arg)
                                        for op, arg in _admitted_instructions_v0(n.instructions))),
                      initial_raw=n.initial_raw)
        for n in case.nodes), tuple(
        NetworkEdgeV0(e.source_node, e.source_channel, e.target_node,
                      e.target_channel, e.delay_ticks) for e in case.edges),
    )
    events = tuple(NetworkEventV0(e.timestamp, e.node_id, e.channel)
                   for e in case.events)
    return network, events


@dataclass
class Recorder:
    batches: list
    routes: list

    def on_batch(self, entry):
        self.batches.append(entry)

    def on_route(self, entry):
        self.routes.append(entry)


def evaluate_case_v0(case, *, max_batches=128, max_events=4096):
    net, events = to_frozen_v0(case)
    options = {'max_batches': max_batches, 'max_events': max_events}
    unobserved = run_network_v0(net, events, **options)
    recorder = Recorder([], [])
    observed = run_network_v0(net, events, learning_observer=recorder, **options)
    if observed != unobserved:
        raise AssertionError('observer changed full frozen Network result')
    comparison = compare_actual_v0(net, events, observed,
                                   recorder.batches, recorder.routes, **options)
    assert comparison['status'] == 'PASS'
    projection = project_v0(observed, recorder.batches, recorder.routes)
    if projection != comparison['oracle']:
        raise AssertionError('oracle projection mismatch after successful comparison')
    # The frozen Network IR requires a normal form. Its adapter may remove a
    # redundant guard, but the independent original primitive program must
    # still predict the exact same observable behavior. Comparing only the
    # normalized frozen network would conceal a faulty admission rewrite.
    primitive = execute_v0(case, **options)
    original_projection = project_v0(
        primitive, primitive['observations']['batches'],
        primitive['observations']['routes'],
    )
    if projection != original_projection:
        raise AssertionError('Core-IR admission normalization changed primitive semantics')
    return {
        'result_sha256': sha(canonical(projection)),
        'processed_events': observed.processed_events,
        'processed_batches': observed.processed_batches,
        'emission_count': len(observed.emissions),
        'route_count': len(recorder.routes),
        'observer_noninterference': True,
    }


def report_v0():
    rows = []
    for cid, case in catalog_v0():
        rows.append({'id': cid, **evaluate_case_v0(case)})
    return {
        'schema': SCHEMA,
        'corpus_schema': CORPUS_SCHEMA,
        'corpus_sha256': catalog_fingerprint_v0(),
        'case_count': len(rows),
        'rows': rows,
    }


def seal_v0():
    payload = report_v0()
    return canonical({'schema': SCHEMA, 'payload': payload,
                      'payload_sha256': sha(SCHEMA + '\n' + canonical(payload))})


def verify_v0(document):
    envelope = strict_json(document)
    if (type(envelope) is not dict
            or set(envelope) != {'schema', 'payload', 'payload_sha256'}
            or envelope['schema'] != SCHEMA
            or document != canonical(envelope)):
        raise ValueError('invalid or noncanonical evidence envelope')
    payload = envelope['payload']
    if (envelope['payload_sha256'] != sha(SCHEMA + '\n' + canonical(payload))):
        raise ValueError('evidence digest mismatch')
    reconstructed = report_v0()
    if payload != reconstructed:
        raise ValueError('extended corpus replay mismatch')
    return {'status': 'PASS', 'case_count': reconstructed['case_count'],
            'corpus_sha256': reconstructed['corpus_sha256'],
            'evidence_sha256': sha(document)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    cmd = parser.add_mutually_exclusive_group(required=True)
    cmd.add_argument('--write', type=Path)
    cmd.add_argument('--verify', type=Path)
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
