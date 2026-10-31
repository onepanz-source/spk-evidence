"""A1b: compare independently executed PE-local batches against compiled v0 host.

This integration adapter may use frozen Compiler/host through A1a. The new PE
engine cannot and does not import or execute frozen Network or oracle methods.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from spk_architecture_v1.pe_fabric_v1a import SCHEMES, plan_v1a
from spk_architecture_v1.pe_execution_v1b import execute_on_pes_v1b
from search.spk_24n_differential_evidence_v0 import (
    canonical, sha, strict_json, project_v0,
)
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
SOURCE_SHA256 = 'cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5'
BASE_COMMIT = 'a76ebaae49373a4c6b66f94465d78dbf1cf19f80'
BASE_TAG = 'spk-simulator-bounded-reference-v0'


def evaluate_v1a(*args, **kwargs):
    # Deferred frozen import: primitive engine and artifact schema are testable
    # in isolation; the real integration gate always loads A1a here.
    from search.spk_arch_a1_pe_fabric_v1a import evaluate_v1a as frozen_reference
    return frozen_reference(*args, **kwargs)


SCHEMA = 'spk-architecture-pe-local-execution/v1b'


def _projection(result):
    return project_v0(result, result['observations']['batches'],
                      result['observations']['routes'])


def evaluate_v1b(case_id, case, scheme):
    """The reference is independently compiled and executed, not reused as PE work."""
    fabric = plan_v1a(case, scheme)
    local = execute_on_pes_v1b(case, fabric)
    projection = _projection(local['result'])
    digest = sha(canonical(projection))
    # A1a recompiles source, admits PE capacities, verifies manifest, and
    # checks frozen Network/24t host against independent 24n oracle.
    reference = evaluate_v1a(case_id, case, scheme)
    if digest != reference['result_sha256']:
        raise AssertionError(case_id + '/' + scheme + ': PE-local / frozen-host mismatch')
    if local['transport']['cross_pe_occurrences'] != reference['cross_pe_route_occurrences']:
        raise AssertionError(case_id + '/' + scheme + ': PE transport cross-PE multiplicity mismatch')
    if local['transport']['local_occurrences'] != reference['local_route_occurrences']:
        raise AssertionError(case_id + '/' + scheme + ': PE transport local multiplicity mismatch')
    if len(local['transport']['transfers']) != reference['logical_route_count']:
        raise AssertionError(case_id + '/' + scheme + ': PE transport occurrence count mismatch')
    return {'case_id': case_id, 'scheme': scheme, 'manifest_sha256': reference['manifest_sha256'],
            'canonical_result_sha256': digest,
            'processed_batches': local['result']['processed_batches'],
            'processed_events': local['result']['processed_events'],
            'cross_pe_route_occurrences': local['transport']['cross_pe_occurrences'],
            'local_route_occurrences': local['transport']['local_occurrences'],
            'pe_snapshots': local['pe_snapshots']}


def report_v1b():
    if catalog_fingerprint_v0() != SOURCE_SHA256:
        raise AssertionError('A1b source pin drift')
    cases = checked_catalog_v0()
    rows = []
    for name, case in cases:
        for scheme in SCHEMES:
            rows.append(evaluate_v1b(name, case, scheme))
        if len({r['canonical_result_sha256'] for r in rows[-3:]}) != 1:
            raise AssertionError(name + ': local PE mapping changed the computation')
    if len(rows) != 648:
        raise AssertionError('incomplete A1b compiled-host coverage')
    remote = sum(r['cross_pe_route_occurrences'] for r in rows)
    if remote != 768:
        raise AssertionError('A1b transport cross-PE count drift')
    return {'schema': SCHEMA, 'baseline_tag': BASE_TAG, 'baseline_commit': BASE_COMMIT,
            'source_sha256': SOURCE_SHA256, 'source_cases': len(cases),
            'pe_schemes': list(SCHEMES), 'compiled_host_comparisons': len(rows),
            'cross_pe_route_occurrences': remote, 'rows': rows,
            'limitations': ['one global logical arbitration clock',
                            'PE-owned state and event queues, synchronous host process',
                            'ideal zero extra inter-PE latency', 'no PE contention',
                            'no durable mailbox', 'bounded admitted Core fragment']}


def seal_v1b():
    payload = report_v1b()
    return canonical({'schema': SCHEMA, 'payload': payload,
                      'payload_sha256': sha(SCHEMA + '\n' + canonical(payload))})


def verify_v1b(document):
    obj = strict_json(document)
    if (type(obj) is not dict or set(obj) != {'schema', 'payload', 'payload_sha256'}
            or obj['schema'] != SCHEMA or canonical(obj) != document):
        raise ValueError('noncanonical PE-local evidence')
    if obj['payload_sha256'] != sha(SCHEMA + '\n' + canonical(obj['payload'])):
        raise ValueError('PE-local evidence checksum mismatch')
    if obj['payload'] != report_v1b():
        raise ValueError('PE-local evidence replay mismatch')
    payload = obj['payload']
    return {'status': 'PASS', 'source_cases': payload['source_cases'],
            'compiled_host_comparisons': payload['compiled_host_comparisons'],
            'cross_pe_route_occurrences': payload['cross_pe_route_occurrences'],
            'source_sha256': SOURCE_SHA256, 'evidence_sha256': sha(document)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--write', type=Path)
    group.add_argument('--verify', type=Path)
    args = parser.parse_args(argv)
    if args.write is not None:
        doc = seal_v1b()
        args.write.write_text(doc + '\n', encoding='utf-8')
        print(canonical({'status': 'WRITTEN', 'evidence_sha256': sha(doc)}))
    else:
        doc = args.verify.read_text(encoding='utf-8').rstrip('\n')
        print(canonical(verify_v1b(doc)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
