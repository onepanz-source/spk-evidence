"""A3c pinned evidence: causal PE memory reservations before actual computation.

Frozen Compiler/host anchors zero-latency ideal cases, A3b anchors the causal
PE-grant baseline for both latencies; bounded-memory runs are independent.
"""
from __future__ import annotations
import argparse
from pathlib import Path

from search.spk_24n_differential_evidence_v0 import canonical, sha, strict_json
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from spk_architecture_v1.pe_fabric_v1a import SCHEMES, plan_v1a
from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
from spk_architecture_v1.temporal_service_v1b import (
    execute_causal_service_v1b, uniform_causal_service_plan_v1b,
)
from spk_architecture_v1.causal_memory_v1c import (
    execute_causal_memory_v1c, uniform_causal_memory_plan_v1c,
)
from search.spk_arch_a3b_causal_service_conformance_v1b import (
    compiled_reference, projected_hash,
)

SCHEMA = 'spk-architecture-a3c-memory-timing-evidence/v1c'
SOURCE_SHA256 = 'cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5'
LATENCIES = (0, 2)
MODES = ('ideal', 'memory_limited')


def evaluate_v1c(cid, case, scheme):
    fabric = plan_v1a(case, scheme)
    frozen = compiled_reference(cid, case, scheme)
    plan = uniform_causal_service_plan_v1b(
        fabric, pe_slots=128, fabric_slots_per_tick=128)
    rows = []
    for latency in LATENCIES:
        transport = TransportPlanV1a(latency)
        baseline = execute_causal_service_v1b(case, fabric, transport, plan)
        baseline_sha = projected_hash(baseline['result'])
        if latency == 0 and baseline_sha != frozen['canonical_result_sha256']:
            raise AssertionError(cid + '/' + scheme + ': frozen compiled host differs')
        for mode in MODES:
            quotas = dict(pe_slots=1024, domain_slots=1024, fabric_slots_per_tick=1024)
            if mode == 'memory_limited':
                quotas = dict(pe_slots=1, domain_slots=1, fabric_slots_per_tick=1)
            mem = uniform_causal_memory_plan_v1c(fabric, **quotas)
            actual = execute_causal_memory_v1c(case, fabric, transport, plan, mem)
            result = actual['result']
            digest = projected_hash(result)
            if mode == 'ideal' and digest != baseline_sha:
                raise AssertionError(cid + '/' + scheme + ': ideal memory changed A3b')
            if result['processed_events'] != len(case.events) + len(actual['transport']['transfers']):
                raise AssertionError('event count conservation')
            if (actual['memory']['actual_units'] > actual['memory']['reserved_units']
                    or actual['transport']['remaining_inflight_occurrences']):
                raise AssertionError('memory reserve or transport conservation')
            rows.append({'latency_ticks': latency, 'mode': mode,
                         'result_sha256': digest, 'baseline_sha256': baseline_sha,
                         'changed_from_a3b': digest != baseline_sha,
                         'memory_reserved_units': actual['memory']['reserved_units'],
                         'memory_actual_units': actual['memory']['actual_units'],
                         'memory_weighted_wait': actual['service']['event_weighted_wait_ticks'],
                         'memory_ledger_sha256': sha(canonical(actual['memory']['reservation_ledger'])),
                         'actual_ledger_sha256': sha(canonical(actual['memory']['actual_accesses'])),
                         'cross_pe_occurrences': actual['transport']['cross_pe_occurrences']})
    return {'id': cid, 'scheme': scheme, 'manifest_sha256': frozen['manifest_sha256'],
            'runs': rows}


def report_v1c():
    if catalog_fingerprint_v0() != SOURCE_SHA256:
        raise AssertionError('A3c source fingerprint drift')
    rows = [evaluate_v1c(cid, case, scheme)
            for cid, case in checked_catalog_v0() for scheme in SCHEMES]
    if len(rows) != 648 or sum(len(x['runs']) for x in rows) != 2592:
        raise AssertionError('A3c incomplete coverage')
    totals = {}
    for mode in MODES:
        runs = [r for row in rows for r in row['runs'] if r['mode'] == mode]
        totals[mode] = {'executions': len(runs),
                        'changed_from_a3b': sum(r['changed_from_a3b'] for r in runs),
                        'memory_reserved_units': sum(r['memory_reserved_units'] for r in runs),
                        'memory_actual_units': sum(r['memory_actual_units'] for r in runs),
                        'event_weighted_wait': sum(r['memory_weighted_wait'] for r in runs)}
    if totals['ideal']['changed_from_a3b'] or not totals['memory_limited']['changed_from_a3b']:
        raise AssertionError('A3c ideal parity or contention effects missing')
    return {'schema': SCHEMA, 'source_cases': 216,
            'source_sha256': SOURCE_SHA256, 'compiled_host_comparisons': 648,
            'a3b_ideal_comparisons': 1296, 'causal_memory_executions': 2592,
            'totals': totals, 'rows': rows,
            'limitations': ['controller-trusted conservative access envelopes',
                            'logical permits before PE execution, not physical RAM transactions',
                            'no causal link congestion or distributed clock']}


def seal_v1c():
    payload = report_v1c()
    return canonical({'schema': SCHEMA, 'payload': payload,
                      'payload_sha256': sha(SCHEMA + '\n' + canonical(payload))})


def verify_v1c(document):
    obj = strict_json(document)
    if (type(obj) is not dict or set(obj) != {'schema', 'payload', 'payload_sha256'}
            or obj['schema'] != SCHEMA or canonical(obj) != document):
        raise ValueError('noncanonical A3c evidence')
    if obj['payload_sha256'] != sha(SCHEMA + '\n' + canonical(obj['payload'])):
        raise ValueError('A3c evidence checksum mismatch')
    if obj['payload'] != report_v1c():
        raise ValueError('A3c evidence replay mismatch')
    return {'status': 'PASS', 'source_cases': 216,
            'compiled_host_comparisons': obj['payload']['compiled_host_comparisons'],
            'a3b_ideal_comparisons': obj['payload']['a3b_ideal_comparisons'],
            'causal_memory_executions': obj['payload']['causal_memory_executions'],
            'limited_changed': obj['payload']['totals']['memory_limited']['changed_from_a3b'],
            'evidence_sha256': sha(document)}


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--write', type=Path)
    group.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.write:
        document = seal_v1c()
        args.write.write_text(document + '\n')
        print(canonical({'status': 'WRITTEN', 'evidence_sha256': sha(document)}))
    else:
        print(canonical(verify_v1c(args.verify.read_text().rstrip('\n'))))

if __name__ == '__main__':
    main()
