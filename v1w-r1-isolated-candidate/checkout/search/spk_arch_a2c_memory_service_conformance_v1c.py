"""A2c conformance: frozen compiled host -> A1d -> A2a -> A2b -> finite memory service.

Only the adapter imports frozen runtime dependencies. The memory service module
operates strictly on verified A2b aggregate intents, not live memory accesses.
"""
from __future__ import annotations
import argparse
from pathlib import Path

from search.spk_24n_differential_evidence_v0 import canonical, sha, strict_json
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from search.spk_arch_a2b_access_conformance_v1b import evaluate_v1b
from spk_architecture_v1.pe_fabric_v1a import SCHEMES, plan_v1a
from spk_architecture_v1.pe_service_v1c import uniform_service_plan_v1c
from spk_architecture_v1.pe_fault_v1d import execute_failstop_v1d, PEFaultPlanV1d
from spk_architecture_v1.memory_projection_v1a import (
    admit_memory_v1a, project_execution_memory_v1a, uniform_memory_plan_v1a,
)
from spk_architecture_v1.memory_access_v1b import authorize_projection_v1b
from spk_architecture_v1.memory_service_v1c import (
    memory_service_plan_v1c, serve_projection_v1c,
)

SCHEMA = 'spk-architecture-memory-service-evidence/v1c'
SOURCE_SHA256 = 'cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5'
BASE_TAG = 'spk-simulator-bounded-reference-v0'


def evaluate_v1c(cid, case, scheme):
    frozen = evaluate_v1b(cid, case, scheme)  # genuine Compiler/host proof
    fabric = plan_v1a(case, scheme)
    pe_service = uniform_service_plan_v1c(fabric, pe_slots=4096,
                                            fabric_slots_per_tick=4096)
    admitted = admit_memory_v1a(case, fabric, pe_service,
                                uniform_memory_plan_v1a(fabric))
    nominal = execute_failstop_v1d(case, fabric, pe_service)
    projected = project_execution_memory_v1a(case, fabric, admitted, nominal)
    auth = authorize_projection_v1b(admitted, projected)
    if (auth['logical_units'] != frozen['nominal_logical_units']
            or auth['request_count'] != frozen['nominal_access_requests']):
        raise AssertionError('A2c upstream compiled memory access drift: ' + cid)
    limited_plan = memory_service_plan_v1c(admitted, pe_slots=2,
                              fabric_slots_per_tick=3, domain_slots_per_tick=2)
    abundant_plan = memory_service_plan_v1c(admitted, pe_slots=65536,
                              fabric_slots_per_tick=65536, domain_slots_per_tick=65536)
    served_limited = serve_projection_v1c(admitted, projected, limited_plan)
    served_abundant = serve_projection_v1c(admitted, projected, abundant_plan)
    if (served_limited['logical_units'] != served_abundant['logical_units']
            or served_abundant['weighted_wait_ticks'] != 0
            or served_limited['execution_status'] != 'CLOSED'):
        raise AssertionError('A2c service conservation / logical closure mismatch')
    fault_limited_sha = None
    fault_units = None
    ledger = nominal['service']['ledger']
    if len(ledger) >= 2:
        second = ledger[1]
        prior = sum(row['pe_id'] == second['pe_id'] for row in ledger[:1])
        fault = execute_failstop_v1d(case, fabric, pe_service,
                                    PEFaultPlanV1d(second['pe_id'], prior))
        fault_projection = project_execution_memory_v1a(case, fabric, admitted, fault)
        auth_fault = authorize_projection_v1b(admitted, fault_projection)
        if (auth_fault['status'] != 'AUTHORIZED'
                or frozen['fault_authorization_sha256'] is None):
            raise AssertionError('A2c unaccounted fail-stop prefix')
        fault_limited = serve_projection_v1c(admitted, fault_projection, limited_plan)
        if (fault_limited['execution_status'] != 'PE_FAULT'
                or fault_limited['logical_units'] != auth_fault['logical_units']):
            raise AssertionError('A2c fail-stop service projection drift')
        fault_limited_sha = sha(canonical(fault_limited))
        fault_units = fault_limited['logical_units']
    elif frozen['fault_authorization_sha256'] is not None:
        raise AssertionError('A2c missing compiled fault-prefix witness')
    return {
        'id': cid, 'placement': scheme,
        'manifest_sha256': frozen['manifest_sha256'],
        'limited_service_sha256': sha(canonical(served_limited)),
        'unconstrained_service_sha256': sha(canonical(served_abundant)),
        'fault_service_sha256': fault_limited_sha,
        'nominal_units': served_limited['logical_units'],
        'fault_units': fault_units,
        'limited_service_ticks': served_limited['service_ticks'],
        'limited_weighted_wait': served_limited['weighted_wait_ticks'],
        'unconstrained_service_ticks': served_abundant['service_ticks'],
    }


def report_v1c():
    if catalog_fingerprint_v0() != SOURCE_SHA256:
        raise AssertionError('A2c source corpus drift')
    rows = [evaluate_v1c(cid, case, scheme)
            for cid, case in checked_catalog_v0() for scheme in SCHEMES]
    count = sum(row['fault_service_sha256'] is not None for row in rows)
    if len(rows) != 648 or count != 504:
        raise AssertionError('A2c incomplete nominal / fail-stop coverage')
    return {
        'schema': SCHEMA, 'source_sha256': SOURCE_SHA256,
        'baseline_tag': BASE_TAG, 'source_cases': 216,
        'compiled_host_comparisons': len(rows),
        'projected_fault_prefixes': count,
        'nominal_service_regimes': 2,
        'nominal_service_runs': 2*len(rows),
        'fault_service_runs': count,
        'limited_total_weighted_wait': sum(x['limited_weighted_wait'] for x in rows),
        'rows': rows,
        'limitations': [
            'A2b-derived aggregate authorized demand, not live RAM accesses',
            'service tick zero releases all demands notionally',
            'no causality, mode-aware scheduling, physical banks or backpressure',
            'fault prefix remains PE_FAULT, not a successful neuron execution',
        ],
    }


def seal_v1c():
    payload = report_v1c()
    return canonical({'schema': SCHEMA, 'payload': payload,
                      'payload_sha256': sha(SCHEMA + '\n' + canonical(payload))})


def verify_v1c(document):
    obj = strict_json(document)
    if (type(obj) is not dict or set(obj) != {'schema','payload','payload_sha256'}
            or obj['schema'] != SCHEMA or canonical(obj) != document):
        raise ValueError('noncanonical A2c memory service evidence')
    if obj['payload_sha256'] != sha(SCHEMA + '\n' + canonical(obj['payload'])):
        raise ValueError('A2c memory service checksum mismatch')
    if obj['payload'] != report_v1c():
        raise ValueError('A2c memory service replay mismatch')
    return {'status': 'PASS', 'source_cases': 216,
            'compiled_host_comparisons': obj['payload']['compiled_host_comparisons'],
            'nominal_service_runs': obj['payload']['nominal_service_runs'],
            'fault_service_runs': obj['payload']['fault_service_runs'],
            'limited_total_weighted_wait': obj['payload']['limited_total_weighted_wait'],
            'evidence_sha256': sha(document)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument('--write', type=Path)
    g.add_argument('--verify', type=Path)
    args = parser.parse_args(argv)
    if args.write is not None:
        document = seal_v1c()
        args.write.write_text(document + '\n', encoding='utf-8')
        print(canonical({'status': 'WRITTEN', 'evidence_sha256': sha(document)}))
    else:
        document = args.verify.read_text(encoding='utf-8').rstrip('\n')
        print(canonical(verify_v1c(document)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
