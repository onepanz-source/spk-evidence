"""A3a transport-timing evidence against independently compiled bounded SPK v0.

All three modes re-execute on PE-owned queues. The ideal mode must match the
frozen compiled host. Positive cross-PE latency is checked causally but has no
unjustified equality obligation with the zero-latency reference.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from search.spk_24n_differential_evidence_v0 import canonical, sha, strict_json, project_v0
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from spk_architecture_v1.pe_fabric_v1a import SCHEMES, plan_v1a
from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a, execute_temporal_v1a

SCHEMA = 'spk-architecture-a3a-causal-transport-evidence/v1a'
SOURCE_SHA256 = 'cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5'
LATENCIES = (0, 1, 3)
BASE_TAG = 'spk-simulator-bounded-reference-v0'


def compiled_reference(cid, case, scheme):
    from search.spk_arch_a1b_pe_local_v1b import evaluate_v1b
    return evaluate_v1b(cid, case, scheme)


def projected_digest(result):
    return sha(canonical(project_v0(result, result['observations']['batches'],
                                    result['observations']['routes'])))


def evaluate_v1a(cid, case, scheme):
    fabric = plan_v1a(case, scheme)
    witness = compiled_reference(cid, case, scheme)
    rows = []
    for extra in LATENCIES:
        execution = execute_temporal_v1a(case, fabric, TransportPlanV1a(extra))
        result = execution['result']
        transfers = execution['transport']['transfers']
        for transfer in transfers:
            required = transfer['emission_timestamp'] + transfer['declared_delay_ticks']
            required += extra if transfer['cross_pe'] else 0
            if transfer['delivery_timestamp'] != required:
                raise AssertionError('transport noncausal timestamp for ' + cid)
        if result['processed_events'] != len(case.events) + len(transfers):
            raise AssertionError('transport occurrence conservation: ' + cid)
        if execution['transport']['delivered_cross_pe_occurrences'] != sum(
                t['cross_pe'] for t in transfers):
            raise AssertionError('cross-PE delivery loss: ' + cid)
        digest = projected_digest(result)
        if extra == 0 and digest != witness['canonical_result_sha256']:
            raise AssertionError(cid + '/' + scheme + ': zero-latency compiled reference mismatch')
        if scheme == 'single' and digest != witness['canonical_result_sha256']:
            raise AssertionError(cid + ': local-only transfer altered by remote latency')
        rows.append({'extra_latency_ticks': extra, 'result_sha256': digest,
                     'processed_events': result['processed_events'],
                     'processed_batches': result['processed_batches'],
                     'cross_pe_route_occurrences': execution['transport']['cross_pe_occurrences'],
                     'local_route_occurrences': execution['transport']['local_occurrences'],
                     'peak_inflight_occurrences': execution['transport']['peak_inflight_occurrences'],
                     'terminal_outputs_sha256': sha(canonical(result['terminal_outputs']))})
    if (rows[0]['cross_pe_route_occurrences'] != witness['cross_pe_route_occurrences']
            or rows[0]['local_route_occurrences'] != witness['local_route_occurrences']):
        raise AssertionError('zero-latency route custody mismatch: ' + cid)
    return {'id': cid, 'scheme': scheme,
            'manifest_sha256': witness['manifest_sha256'], 'timings': rows}


def report_v1a():
    if catalog_fingerprint_v0() != SOURCE_SHA256:
        raise AssertionError('A3a pinned source drift')
    rows = [evaluate_v1a(cid, case, scheme) for cid, case in checked_catalog_v0()
            for scheme in SCHEMES]
    if len(rows) != 648 or sum(len(x['timings']) for x in rows) != 1944:
        raise AssertionError('A3a incomplete compiled/latency coverage')
    remote0 = sum(row['timings'][0]['cross_pe_route_occurrences'] for row in rows)
    if remote0 != 768:
        raise AssertionError('A3a zero-latency route count drift')
    return {'schema': SCHEMA, 'base_tag': BASE_TAG,
            'source_sha256': SOURCE_SHA256, 'source_cases': 216,
            'compiled_reference_comparisons': 648,
            'temporal_executions': 1944, 'ideal_cross_pe_route_occurrences': remote0,
            'latencies': list(LATENCIES), 'rows': rows,
            'limitations': ['zero-latency behavior compared to frozen compiled v0',
                            'positive remote latency intentionally changes logical timestamps',
                            'one global chronological arbiter, PE-local state and queues',
                            'no causal PE/memory service contention, backpressure or recovery',
                            'bounded finite acyclic source corpus']}


def seal_v1a():
    payload = report_v1a()
    return canonical({'schema': SCHEMA, 'payload': payload,
                      'payload_sha256': sha(SCHEMA + '\n' + canonical(payload))})


def verify_v1a(document):
    obj = strict_json(document)
    if (type(obj) is not dict or set(obj) != {'schema', 'payload', 'payload_sha256'}
            or obj['schema'] != SCHEMA or canonical(obj) != document):
        raise ValueError('noncanonical A3a evidence')
    if obj['payload_sha256'] != sha(SCHEMA + '\n' + canonical(obj['payload'])):
        raise ValueError('A3a checksum mismatch')
    if obj['payload'] != report_v1a():
        raise ValueError('A3a evidence replay mismatch')
    payload = obj['payload']
    return {'status': 'PASS', 'source_cases': payload['source_cases'],
            'compiled_reference_comparisons': payload['compiled_reference_comparisons'],
            'temporal_executions': payload['temporal_executions'],
            'ideal_cross_pe_route_occurrences': payload['ideal_cross_pe_route_occurrences'],
            'evidence_sha256': sha(document)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--write', type=Path)
    choice.add_argument('--verify', type=Path)
    args = parser.parse_args(argv)
    if args.write is not None:
        doc = seal_v1a()
        args.write.write_text(doc + '\n', encoding='utf-8')
        print(canonical({'status': 'WRITTEN', 'evidence_sha256': sha(doc)}))
    else:
        print(canonical(verify_v1a(args.verify.read_text(encoding='utf-8').rstrip('\n'))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
