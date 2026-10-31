"""Cross-layer A2a P/S/E/O memory projection against frozen compiled host.

Compiles each of the 216 canonical cases at three A1 PE placements.  This
adapter alone imports frozen host/Compiler references; the memory module does
not.  Nominal A1d execution and fault-prefix projection are checked separately.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from search.spk_24n_differential_evidence_v0 import canonical, sha, strict_json, project_v0
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from search.spk_arch_a1d_fault_conformance_v1d import compiled_reference
from spk_architecture_v1.pe_fabric_v1a import SCHEMES, plan_v1a
from spk_architecture_v1.pe_fault_v1d import execute_failstop_v1d, PEFaultPlanV1d
from spk_architecture_v1.pe_service_v1c import uniform_service_plan_v1c
from spk_architecture_v1.memory_projection_v1a import (
    uniform_memory_plan_v1a, admit_memory_v1a, project_execution_memory_v1a,
)

SCHEMA = 'spk-architecture-memory-evidence/v1a'
SOURCE_SHA256 = 'cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5'
BASE_TAG = 'spk-simulator-bounded-reference-v0'


def evaluate_v1a(cid, case, scheme):
    fabric = plan_v1a(case, scheme)
    service = uniform_service_plan_v1c(fabric, pe_slots=4096,
                                        fabric_slots_per_tick=4096)
    memory = uniform_memory_plan_v1a(fabric)
    admitted = admit_memory_v1a(case, fabric, service, memory)
    frozen = compiled_reference(cid, case, scheme)
    nominal = execute_failstop_v1d(case, fabric, service)
    if nominal['status'] != 'CLOSED':
        raise AssertionError('A2a nominal A1d execution did not close')
    actual = project_v0(nominal['result'], nominal['result']['observations']['batches'],
                        nominal['result']['observations']['routes'])
    if sha(canonical(actual)) != frozen['canonical_result_sha256']:
        raise AssertionError(cid + '/' + scheme + ': PE-local/frozen mismatch')
    proj = project_execution_memory_v1a(case, fabric, admitted, nominal)
    fault_sha = None
    ledger = nominal['service']['ledger']
    if len(ledger) >= 2:
        second = ledger[1]
        prior = sum(x['pe_id'] == second['pe_id'] for x in ledger[:1])
        fault = execute_failstop_v1d(case, fabric, service,
                                    PEFaultPlanV1d(second['pe_id'], prior))
        fault_proj = project_execution_memory_v1a(case, fabric, admitted, fault)
        if (fault_proj['status'] != 'PE_FAULT'
                or fault_proj['conservation']['pending_occurrences'] == 0):
            raise AssertionError('A2a fault-prefix projection incomplete')
        fault_sha = sha(canonical(fault_proj))
    return {'id': cid, 'placement': scheme,
            'manifest_sha256': frozen['manifest_sha256'],
            'memory_reservation_sha256': sha(canonical(admitted)),
            'memory_projection_sha256': sha(canonical(proj)),
            'fault_projection_sha256': fault_sha,
            'cross_pe_routes': frozen['cross_pe_route_occurrences'],
            'event_peak_sum': sum(p['E_peak'] for p in proj['pe_usage'].values()),
            'observation_records': sum(p['O_records'] for p in proj['pe_usage'].values())}


def report_v1a():
    if catalog_fingerprint_v0() != SOURCE_SHA256:
        raise AssertionError('pinned source catalog drift')
    rows = [evaluate_v1a(cid, case, scheme)
            for cid, case in checked_catalog_v0()
            for scheme in SCHEMES]
    if len(rows) != 648:
        raise AssertionError('incomplete A2a compiled reference coverage')
    faults = sum(row['fault_projection_sha256'] is not None for row in rows)
    if faults != 504:
        raise AssertionError('A2a eligible fault prefix count changed')
    if sum(row['cross_pe_routes'] for row in rows) != 768:
        raise AssertionError('A2a cross PE route count changed')
    return {'schema': SCHEMA, 'baseline_tag': BASE_TAG,
            'source_sha256': SOURCE_SHA256, 'source_cases': 216,
            'compiled_host_comparisons': len(rows),
            'projected_fault_prefixes': faults,
            'total_cross_pe_route_occurrences': 768,
            'rows': rows,
            'limitations': ['logical P/S/E/O projection and conservative admission',
                            'no physical transaction counts, bandwidth or permissions',
                            'no PE fault recovery or hot-swap']}


def seal_v1a():
    payload = report_v1a()
    return canonical({'schema': SCHEMA, 'payload': payload,
                      'payload_sha256': sha(SCHEMA + '\n' + canonical(payload))})


def verify_v1a(document):
    obj = strict_json(document)
    if (type(obj) is not dict or set(obj) != {'schema', 'payload', 'payload_sha256'}
            or obj['schema'] != SCHEMA or canonical(obj) != document):
        raise ValueError('noncanonical A2a memory evidence')
    if obj['payload_sha256'] != sha(SCHEMA + '\n' + canonical(obj['payload'])):
        raise ValueError('A2a memory evidence checksum mismatch')
    if obj['payload'] != report_v1a():
        raise ValueError('A2a memory evidence replay mismatch')
    return {'status': 'PASS', 'source_cases': 216, 'compiled_host_comparisons': 648,
            'projected_fault_prefixes': 504,
            'total_cross_pe_route_occurrences': 768,
            'evidence_sha256': sha(document)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    exclusive = parser.add_mutually_exclusive_group(required=True)
    exclusive.add_argument('--write', type=Path)
    exclusive.add_argument('--verify', type=Path)
    args = parser.parse_args(argv)
    if args.write is not None:
        doc = seal_v1a()
        args.write.write_text(doc + '\n', encoding='utf-8')
        print(canonical({'status':'WRITTEN', 'evidence_sha256':sha(doc)}))
    else:
        doc = args.verify.read_text(encoding='utf-8').rstrip('\n')
        print(canonical(verify_v1a(doc)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
