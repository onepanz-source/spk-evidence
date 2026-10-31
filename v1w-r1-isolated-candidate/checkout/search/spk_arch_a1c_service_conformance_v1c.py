"""A1c: certify finite virtual PE service capacity against A1b and frozen host.

Each source (216) x placement (3) is independently compiled/executed by
A1b's integration reference exactly once; then four resource regimes are
executed by the new independent capacity-bearing PE-local service engine.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from spk_architecture_v1.pe_fabric_v1a import SCHEMES, plan_v1a
from spk_architecture_v1.pe_service_v1c import (
    execute_with_service_v1c, uniform_service_plan_v1c,
)
from search.spk_24n_differential_evidence_v0 import (
    canonical, sha, strict_json, project_v0,
)
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0

SCHEMA = 'spk-architecture-service-conformance/v1c'
SOURCE_SHA256 = 'cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5'
BASE_TAG = 'spk-simulator-bounded-reference-v0'
REGIMES = ('shared_and_pe_limited', 'pe_limited',
           'shared_limited', 'unconstrained')


def reference_v1b(case_id, case, scheme):
    # Deferred import: new capacity engine cannot depend on frozen runtime.
    from search.spk_arch_a1b_pe_local_v1b import evaluate_v1b
    return evaluate_v1b(case_id, case, scheme)


def plan_for_regime_v1c(fabric, regime):
    if regime == 'shared_and_pe_limited':
        return uniform_service_plan_v1c(fabric, pe_slots=1, fabric_slots_per_tick=1)
    if regime == 'pe_limited':
        return uniform_service_plan_v1c(fabric, pe_slots=1, fabric_slots_per_tick=4096)
    if regime == 'shared_limited':
        return uniform_service_plan_v1c(fabric, pe_slots=4096, fabric_slots_per_tick=1)
    if regime == 'unconstrained':
        return uniform_service_plan_v1c(fabric, pe_slots=4096, fabric_slots_per_tick=4096)
    raise ValueError('unknown A1c service regime')


def _projection(result):
    return project_v0(result, result['observations']['batches'],
                      result['observations']['routes'])


def evaluate_v1c(case_id, case, scheme):
    fabric = plan_v1a(case, scheme)
    baseline = reference_v1b(case_id, case, scheme)
    out = []
    for regime in REGIMES:
        plan = plan_for_regime_v1c(fabric, regime)
        actual = execute_with_service_v1c(case, fabric, plan)
        result_hash = sha(canonical(_projection(actual['result'])))
        if result_hash != baseline['canonical_result_sha256']:
            raise AssertionError(f'{case_id}/{scheme}/{regime}: PE service changed logical computation')
        if (actual['transport']['cross_pe_occurrences'] != baseline['cross_pe_route_occurrences']
                or actual['transport']['local_occurrences'] != baseline['local_route_occurrences']):
            raise AssertionError(f'{case_id}/{scheme}/{regime}: PE service lost transport multiplicity')
        svc = actual['service']
        if len(svc['ledger']) != baseline['processed_batches'] or svc['batches'] != len(svc['ledger']):
            raise AssertionError('service ledger/processed batches mismatch')
        if regime == 'unconstrained' and (svc['fabric_stall_ticks'] != 0
                                          or svc['pe_stall_ticks'] != 0
                                          or any(row['service_wait_ticks'] for row in svc['ledger'])):
            raise AssertionError('unconstrained service incurred contention')
        out.append({'regime': regime, 'result_sha256': result_hash,
                    'fabric_stalls': svc['fabric_stall_ticks'],
                    'pe_stalls': svc['pe_stall_ticks'],
                    'service_wait_ticks': sum(row['service_wait_ticks'] for row in svc['ledger']),
                    'service_ledger_sha256': sha(canonical(svc['ledger']))})
    if len({row['result_sha256'] for row in out}) != 1:
        raise AssertionError('capacity settings changed logical result')
    return {'case_id': case_id, 'scheme': scheme,
            'manifest_sha256': baseline['manifest_sha256'],
            'result_sha256': baseline['canonical_result_sha256'],
            'cross_pe_route_occurrences': baseline['cross_pe_route_occurrences'],
            'service_regimes': out}


def report_v1c():
    if catalog_fingerprint_v0() != SOURCE_SHA256:
        raise AssertionError('A1c source corpus changed')
    rows = [evaluate_v1c(cid, case, scheme)
            for cid, case in checked_catalog_v0()
            for scheme in SCHEMES]
    if len(rows) != 648:
        raise AssertionError('missing compiled source/placement comparisons')
    totals = {regime: {'fabric_stalls': 0, 'pe_stalls': 0, 'service_wait_ticks': 0}
              for regime in REGIMES}
    for r in rows:
        for v in r['service_regimes']:
            for key in ('fabric_stalls', 'pe_stalls', 'service_wait_ticks'):
                totals[v['regime']][key] += v[key]
    if not (totals['shared_and_pe_limited']['fabric_stalls'] > 0
            and totals['pe_limited']['pe_stalls'] > 0
            and totals['shared_limited']['fabric_stalls'] > 0
            and totals['unconstrained'] == {
                'fabric_stalls': 0, 'pe_stalls': 0, 'service_wait_ticks': 0}):
        raise AssertionError('A1c planned service contention has no meaningful coverage')
    return {'schema': SCHEMA, 'source_sha256': SOURCE_SHA256,
            'frozen_reference_tag': BASE_TAG,
            'source_cases': 216, 'placements': list(SCHEMES),
            'compiled_reference_comparisons': len(rows),
            'pe_service_executions': len(rows) * len(REGIMES),
            'regimes': list(REGIMES), 'regime_totals': totals, 'rows': rows,
            'limitations': ['finite virtual service slots, one central logical arbiter',
                            'service clock separate from spike timestamp',
                            'no physical latency feedback to logical events',
                            'no active backpressure, persistent queue or rollback',
                            'no PE workers in parallel, no hardware timing']}


def seal_v1c():
    payload = report_v1c()
    return canonical({'schema': SCHEMA, 'payload': payload,
                      'payload_sha256': sha(SCHEMA + '\n' + canonical(payload))})


def verify_v1c(document):
    obj = strict_json(document)
    if (type(obj) is not dict or set(obj) != {'schema', 'payload', 'payload_sha256'}
            or obj['schema'] != SCHEMA or canonical(obj) != document):
        raise ValueError('noncanonical A1c service evidence')
    if obj['payload_sha256'] != sha(SCHEMA + '\n' + canonical(obj['payload'])):
        raise ValueError('A1c evidence checksum mismatch')
    if obj['payload'] != report_v1c():
        raise ValueError('A1c service evidence replay mismatch')
    p = obj['payload']
    return {'status': 'PASS', 'source_cases': p['source_cases'],
            'compiled_reference_comparisons': p['compiled_reference_comparisons'],
            'pe_service_executions': p['pe_service_executions'],
            'regime_totals': p['regime_totals'],
            'evidence_sha256': sha(document)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--write', type=Path)
    group.add_argument('--verify', type=Path)
    args = parser.parse_args(argv)
    if args.write is not None:
        doc = seal_v1c()
        args.write.write_text(doc + '\n', encoding='utf-8')
        print(canonical({'status': 'WRITTEN', 'evidence_sha256': sha(doc)}))
    else:
        text = args.verify.read_text(encoding='utf-8').rstrip('\n')
        print(canonical(verify_v1c(text)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
