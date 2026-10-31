"""A3d canonical evidence: bounded inter-PE link credits and sender backpressure.

Zero-contention A3c parity is exact. Bounded-link traces are independently
recomputed with real PE-local execution; frozen host anchors only the ideal
latency-zero semantics, never the deliberately delayed results.
"""
from __future__ import annotations
import argparse
from pathlib import Path
from search.spk_24n_differential_evidence_v0 import canonical, sha, strict_json
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from search.spk_arch_a3b_causal_service_conformance_v1b import (
    compiled_reference, projected_hash,
)
from spk_architecture_v1.pe_fabric_v1a import SCHEMES, plan_v1a
from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
from spk_architecture_v1.temporal_service_v1b import uniform_causal_service_plan_v1b
from spk_architecture_v1.causal_memory_v1c import (
    execute_causal_memory_v1c, uniform_causal_memory_plan_v1c,
)
from spk_architecture_v1.causal_transport_v1d import (
    CausalLinkPlanV1d, execute_causal_transport_v1d,
)

SCHEMA = 'spk-architecture-a3d-causal-link-evidence/v1d'
SOURCE_SHA256 = 'cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5'
LATENCIES = (0, 2)
REGIMES = ('ideal', 'link_limited', 'inflight_limited')


def evaluate_v1d(cid, case, scheme):
    fabric = plan_v1a(case, scheme)
    frozen = compiled_reference(cid, case, scheme)
    pe = uniform_causal_service_plan_v1b(fabric, pe_slots=128,
                                            fabric_slots_per_tick=128)
    mem = uniform_causal_memory_plan_v1c(fabric)
    rows = []
    for latency in LATENCIES:
        ideal_transport = TransportPlanV1a(latency)
        baseline = execute_causal_memory_v1c(case, fabric, ideal_transport, pe, mem)
        baseline_sha = projected_hash(baseline['result'])
        if latency == 0 and baseline_sha != frozen['canonical_result_sha256']:
            raise AssertionError(cid + '/' + scheme + ': frozen compiled host differs')
        for mode in REGIMES:
            link = CausalLinkPlanV1d()
            transport = ideal_transport
            if mode == 'link_limited':
                link = CausalLinkPlanV1d(1, 1, 128, 4096)
            elif mode == 'inflight_limited':
                transport = TransportPlanV1a(latency, 1)
            actual = execute_causal_transport_v1d(case, fabric, transport, pe, mem, link)
            result, routed = actual['result'], actual['transport']
            digest = projected_hash(result)
            if mode == 'ideal' and (digest != baseline_sha
                                    or routed['transfers'] != baseline['transport']['transfers']):
                raise AssertionError('unbounded link changed A3c reference')
            if (result['processed_events'] != len(case.events) + len(routed['transfers'])
                    or routed['cross_pe_occurrences'] != routed['delivered_cross_pe_occurrences']
                    or routed['cross_pe_occurrences'] != len(routed['link_grants'])
                    or routed['remaining_inflight_occurrences']
                    or routed['outstanding_outbox_occurrences']):
                raise AssertionError('A3d event/outbox/inflight conservation')
            if (actual['memory']['actual_units'] > actual['memory']['reserved_units']
                    or any(t['link_grants'] > link.fabric_slots_per_tick
                           for t in routed['outbox_timeline'])
                    or any(t['inflight'] > transport.max_inflight_occurrences
                           for t in routed['outbox_timeline'])):
                raise AssertionError('A3d grant capacity or memory reserve violated')
            rows.append({'latency_ticks': latency, 'regime': mode,
                         'result_sha256': digest, 'baseline_sha256': baseline_sha,
                         'changed_from_a3c': digest != baseline_sha,
                         'processed_events': result['processed_events'],
                         'cross_pe_occurrences': routed['cross_pe_occurrences'],
                         'link_grants': len(routed['link_grants']),
                         'source_blocked_ticks': routed['source_blocked_ticks'],
                         'link_congestion_wait_ticks': routed['link_congestion_wait_ticks'],
                         'max_outbox_occupancy': routed['max_outbox_occupancy'],
                         'link_grants_sha256': sha(canonical(routed['link_grants'])),
                         'routes_sha256': sha(canonical(routed['transfers'])),
                         'memory_reservations_sha256': sha(canonical(
                             actual['memory']['reservation_ledger']))})
    return {'id': cid, 'scheme': scheme, 'manifest_sha256': frozen['manifest_sha256'],
            'runs': rows}


def report_v1d():
    if catalog_fingerprint_v0() != SOURCE_SHA256:
        raise AssertionError('A3d source fingerprint drift')
    rows = [evaluate_v1d(cid, case, scheme)
            for cid, case in checked_catalog_v0() for scheme in SCHEMES]
    if len(rows) != 648 or sum(len(r['runs']) for r in rows) != 3888:
        raise AssertionError('incomplete A3d evidence population')
    totals = {}
    for regime in REGIMES:
        runs = [r for row in rows for r in row['runs'] if r['regime'] == regime]
        totals[regime] = {'executions': len(runs),
                          'changed_from_a3c': sum(r['changed_from_a3c'] for r in runs),
                          'source_blocked_ticks': sum(r['source_blocked_ticks'] for r in runs),
                          'link_congestion_wait_ticks': sum(r['link_congestion_wait_ticks'] for r in runs),
                          'remote_occurrences': sum(r['cross_pe_occurrences'] for r in runs)}
    if totals['ideal']['changed_from_a3c'] or totals['ideal']['source_blocked_ticks']:
        raise AssertionError('A3d ideal parity failure')
    if not totals['link_limited']['changed_from_a3c']:
        raise AssertionError('A3d finite link effect missing')
    if not totals['inflight_limited']['changed_from_a3c']:
        raise AssertionError('A3d finite in-flight effect missing')
    return {'schema': SCHEMA, 'source_sha256': SOURCE_SHA256,
            'source_cases': 216, 'compiled_host_comparisons': 648,
            'a3c_ideal_comparisons': 1296, 'causal_link_executions': 3888,
            'totals': totals, 'rows': rows,
            'limitations': ['sender FIFO and global deterministic link-credit arbiter',
                            'bounded in-flight slots and sender outboxes, no silent drops',
                            'A3c memory reservation occurs before computation and link injection',
                            'no receiver-side ingress quotas or distributed NoC/clock',
                            'no rollback/recovery after explicit capacity/horizon failure']}


def seal_v1d():
    payload = report_v1d()
    return canonical({'schema': SCHEMA, 'payload': payload,
                      'payload_sha256': sha(SCHEMA + '\n' + canonical(payload))})


def verify_v1d(document):
    obj = strict_json(document)
    if (type(obj) is not dict or set(obj) != {'schema', 'payload', 'payload_sha256'}
            or obj['schema'] != SCHEMA or canonical(obj) != document):
        raise ValueError('noncanonical A3d evidence')
    if obj['payload_sha256'] != sha(SCHEMA + '\n' + canonical(obj['payload'])):
        raise ValueError('A3d evidence checksum mismatch')
    if obj['payload'] != report_v1d():
        raise ValueError('A3d evidence replay mismatch')
    return {'status': 'PASS', 'source_cases': 216,
            'compiled_host_comparisons': obj['payload']['compiled_host_comparisons'],
            'a3c_ideal_comparisons': obj['payload']['a3c_ideal_comparisons'],
            'causal_link_executions': obj['payload']['causal_link_executions'],
            'regime_totals': obj['payload']['totals'],
            'evidence_sha256': sha(document)}


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--write', type=Path)
    group.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.write:
        doc = seal_v1d()
        args.write.write_text(doc + '\n')
        print(canonical({'status': 'WRITTEN', 'evidence_sha256': sha(doc)}))
    else:
        print(canonical(verify_v1d(args.verify.read_text().rstrip('\n'))))


if __name__ == '__main__':
    main()
