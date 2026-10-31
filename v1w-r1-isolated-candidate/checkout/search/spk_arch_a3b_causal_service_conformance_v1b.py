"""A3b evidence: PE service grants alter *causal* spike times under fixed quotas.

An independent frozen Compiler/host witnesses every zero-latency ideal case;
A3a witnesses both ideal latency variants. The finite variants are genuine
PE-local re-executions and are never falsely claimed to match frozen v0.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from search.spk_24n_differential_evidence_v0 import canonical, sha, strict_json, project_v0
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from spk_architecture_v1.pe_fabric_v1a import SCHEMES, plan_v1a
from spk_architecture_v1.temporal_transport_v1a import (
    TransportPlanV1a, execute_temporal_v1a,
)
from spk_architecture_v1.temporal_service_v1b import (
    execute_causal_service_v1b, uniform_causal_service_plan_v1b,
)

SCHEMA = 'spk-architecture-a3b-causal-service-evidence/v1b'
SOURCE_SHA256 = 'cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5'
BASE_TAG = 'spk-simulator-bounded-reference-v0'
LATENCIES = (0, 2)
REGIMES = (
    ('ideal', 128, 128),
    ('pe_limited', 1, 128),
    ('fabric_limited', 128, 1),
    ('joint_limited', 1, 1),
)


def compiled_reference(cid, case, scheme):
    from search.spk_arch_a1b_pe_local_v1b import evaluate_v1b
    return evaluate_v1b(cid, case, scheme)


def projected_hash(result):
    return sha(canonical(project_v0(result, result['observations']['batches'],
                                    result['observations']['routes'])))


def evaluate_v1b(cid, case, scheme):
    fabric = plan_v1a(case, scheme)
    witness = compiled_reference(cid, case, scheme)
    rows = []
    for latency in LATENCIES:
        transport_plan = TransportPlanV1a(latency)
        ideal_a3a = execute_temporal_v1a(case, fabric, transport_plan)
        target_hash = projected_hash(ideal_a3a['result'])
        if latency == 0 and target_hash != witness['canonical_result_sha256']:
            raise AssertionError(cid + '/' + scheme + ': frozen compiled host differs')
        for name, local_cap, fabric_cap in REGIMES:
            plan = uniform_causal_service_plan_v1b(
                fabric, pe_slots=local_cap, fabric_slots_per_tick=fabric_cap)
            actual = execute_causal_service_v1b(case, fabric, transport_plan, plan)
            result, service, routed = actual['result'], actual['service'], actual['transport']
            digest = projected_hash(result)
            if name == 'ideal' and digest != target_hash:
                raise AssertionError(cid + '/' + scheme + ': ideal A3a service parity')
            if len(service['grants']) != result['processed_batches']:
                raise AssertionError('unaccounted service grant')
            if routed['remaining_inflight_occurrences'] or (
                    routed['cross_pe_occurrences'] != routed['delivered_cross_pe_occurrences']):
                raise AssertionError('remote transfer lost')
            if result['processed_events'] != len(case.events) + len(routed['transfers']):
                raise AssertionError('event occurrence conservation')
            rows.append({'latency_ticks': latency, 'regime': name,
                         'result_sha256': digest,
                         'matches_ideal': digest == target_hash,
                         'processed_events': result['processed_events'],
                         'processed_batches': result['processed_batches'],
                         'cross_pe_occurrences': routed['cross_pe_occurrences'],
                         'batch_wait_ticks': service['batch_wait_ticks'],
                         'event_weighted_wait_ticks': service['event_weighted_wait_ticks'],
                         'fabric_stall_incidents': service['fabric_stall_incidents'],
                         'pe_stall_incidents': service['pe_stall_incidents'],
                         'grant_ledger_sha256': sha(canonical(service['grants'])),
                         'transport_ledger_sha256': sha(canonical(routed['transfers'])),
                         'terminal_outputs_sha256': sha(canonical(result['terminal_outputs']))})
    if len(rows) != len(LATENCIES) * len(REGIMES):
        raise AssertionError('A3b incomplete service regimes')
    return {'id': cid, 'scheme': scheme, 'manifest_sha256': witness['manifest_sha256'],
            'timings': rows}


def report_v1b():
    if catalog_fingerprint_v0() != SOURCE_SHA256:
        raise AssertionError('A3b pinned corpus drift')
    rows = [evaluate_v1b(cid, case, scheme) for cid, case in checked_catalog_v0()
            for scheme in SCHEMES]
    if len(rows) != 648 or sum(len(x['timings']) for x in rows) != 5184:
        raise AssertionError('A3b coverage incomplete')
    totals = {}
    for name, _, _ in REGIMES:
        items = [timing for row in rows for timing in row['timings']
                 if timing['regime'] == name]
        totals[name] = {
            'executions': len(items),
            'changed_from_ideal': sum(not x['matches_ideal'] for x in items),
            'event_weighted_wait_ticks': sum(x['event_weighted_wait_ticks'] for x in items),
            'fabric_stall_incidents': sum(x['fabric_stall_incidents'] for x in items),
            'pe_stall_incidents': sum(x['pe_stall_incidents'] for x in items),
        }
    if totals['ideal']['changed_from_ideal'] or totals['ideal']['event_weighted_wait_ticks']:
        raise AssertionError('ideal causal service diverged from A3a')
    if totals['joint_limited']['changed_from_ideal'] == 0:
        raise AssertionError('finite grants produced no causal effect')
    return {'schema': SCHEMA, 'base_tag': BASE_TAG,
            'source_sha256': SOURCE_SHA256, 'source_cases': 216,
            'compiled_host_comparisons': 648,
            'a3a_ideal_comparisons': 1296,
            'causal_service_executions': 5184,
            'latencies': list(LATENCIES),
            'regimes': [{'name': name, 'pe_slots': local, 'fabric_slots': shared}
                        for name, local, shared in REGIMES],
            'totals': totals, 'rows': rows,
            'limitations': ['positive transport latency and finite PE grant capacity',
                            'service timestamp enters Core time, emissions and routes',
                            'single global deterministic arbiter with per-PE quotas',
                            'no concurrent hardware execution or distributed clock',
                            'A2c aggregate memory service not coupled to timeline',
                            'no link bandwidth, backpressure, dynamic failover or recovery',
                            'bounded three-node acyclic source corpus']}


def seal_v1b():
    payload = report_v1b()
    return canonical({'schema': SCHEMA, 'payload': payload,
                      'payload_sha256': sha(SCHEMA + '\n' + canonical(payload))})


def verify_v1b(document):
    obj = strict_json(document)
    if (type(obj) is not dict or set(obj) != {'schema', 'payload', 'payload_sha256'}
            or obj['schema'] != SCHEMA or canonical(obj) != document):
        raise ValueError('noncanonical A3b causal service evidence')
    if obj['payload_sha256'] != sha(SCHEMA + '\n' + canonical(obj['payload'])):
        raise ValueError('A3b evidence checksum mismatch')
    if obj['payload'] != report_v1b():
        raise ValueError('A3b evidence replay mismatch')
    payload = obj['payload']
    return {'status': 'PASS', 'source_cases': payload['source_cases'],
            'compiled_host_comparisons': payload['compiled_host_comparisons'],
            'a3a_ideal_comparisons': payload['a3a_ideal_comparisons'],
            'causal_service_executions': payload['causal_service_executions'],
            'regime_totals': payload['totals'],
            'evidence_sha256': sha(document)}


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
        print(canonical(verify_v1b(args.verify.read_text(encoding='utf-8').rstrip('\n'))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
