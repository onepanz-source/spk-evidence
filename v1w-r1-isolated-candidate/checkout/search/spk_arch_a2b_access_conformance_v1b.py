"""A2b logical authorization conformance over real Compiler -> A1d -> A2a.

Authority is prepared before execution and checked against the independent
A2a logical ledger afterwards. Neither priority nor physical service is here.
"""
from __future__ import annotations
import argparse
from pathlib import Path

from search.spk_24n_differential_evidence_v0 import canonical, sha, strict_json
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from search.spk_arch_a2a_memory_conformance_v1a import evaluate_v1a
from spk_architecture_v1.pe_fabric_v1a import SCHEMES, plan_v1a
from spk_architecture_v1.pe_fault_v1d import execute_failstop_v1d, PEFaultPlanV1d
from spk_architecture_v1.pe_service_v1c import uniform_service_plan_v1c
from spk_architecture_v1.memory_projection_v1a import (
    uniform_memory_plan_v1a, admit_memory_v1a, project_execution_memory_v1a,
)
from spk_architecture_v1.memory_access_v1b import (
    issue_authority_v1b, authorize_projection_v1b,
)

SCHEMA = 'spk-architecture-memory-access-evidence/v1b'
SOURCE_SHA256 = 'cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5'
A2A_SHA256 = 'c7164a8abdf27e747f3522ec29b0449574aee219ab525b7f9cc1aff4acc80082'
BASE_TAG = 'spk-simulator-bounded-reference-v0'


def evaluate_v1b(cid, case, scheme):
    # Real frozen Compiler/host integration, also checks PE-local reference.
    original = evaluate_v1a(cid, case, scheme)
    fabric = plan_v1a(case, scheme)
    service = uniform_service_plan_v1c(fabric, pe_slots=4096,
                                        fabric_slots_per_tick=4096)
    admission = admit_memory_v1a(case, fabric, service, uniform_memory_plan_v1a(fabric))
    authority = issue_authority_v1b(admission)  # issued before execution
    if authority.epoch_id != admission['epoch_id']:
        raise AssertionError('A2b controller epoch mismatch')
    nominal = execute_failstop_v1d(case, fabric, service)
    projected = project_execution_memory_v1a(case, fabric, admission, nominal)
    if sha(canonical(projected)) != original['memory_projection_sha256']:
        raise AssertionError('A2b nominal projection drift')
    auth = authorize_projection_v1b(admission, projected)
    if auth['status'] != 'AUTHORIZED':
        raise AssertionError('A2b unauthorized nominal trace')
    fault_auth = None
    ledger = nominal['service']['ledger']
    if len(ledger) >= 2:
        second = ledger[1]
        prior = sum(row['pe_id'] == second['pe_id'] for row in ledger[:1])
        fault = execute_failstop_v1d(case, fabric, service,
                                    PEFaultPlanV1d(second['pe_id'], prior))
        fault_projection = project_execution_memory_v1a(case, fabric, admission, fault)
        if sha(canonical(fault_projection)) != original['fault_projection_sha256']:
            raise AssertionError('A2b fault-prefix projection drift')
        fault_auth = authorize_projection_v1b(admission, fault_projection)
    elif original['fault_projection_sha256'] is not None:
        raise AssertionError('A2b missing fault-prefix proof')
    return {
        'id': cid, 'scheme': scheme,
        'manifest_sha256': original['manifest_sha256'],
        'authority_sha256': sha(canonical({'epoch': authority.epoch_id,
            'grants': [vars(g) for g in authority.grants]})),
        'nominal_authorization_sha256': sha(canonical(auth)),
        'fault_authorization_sha256': (sha(canonical(fault_auth))
                                       if fault_auth is not None else None),
        'nominal_logical_units': auth['logical_units'],
        'nominal_access_requests': auth['request_count'],
    }


def report_v1b():
    if catalog_fingerprint_v0() != SOURCE_SHA256:
        raise AssertionError('A2b pinned source catalog drift')
    rows = [evaluate_v1b(cid, case, scheme)
            for cid, case in checked_catalog_v0()
            for scheme in SCHEMES]
    faults = sum(row['fault_authorization_sha256'] is not None for row in rows)
    if len(rows) != 648 or faults != 504:
        raise AssertionError('A2b source coverage or fail-stop count changed')
    return {
        'schema': SCHEMA, 'baseline_tag': BASE_TAG,
        'source_sha256': SOURCE_SHA256,
        'upstream_a2a_evidence_sha256': A2A_SHA256,
        'source_cases': 216, 'compiled_host_comparisons': len(rows),
        'authorized_fault_prefixes': faults, 'rows': rows,
        'limitations': ['only verified A2a logical access intents',
                        'no authentication of runtime principals',
                        'no memory-service arbitration or physical transactions',
                        'no candidate program writes or epoch transitions'],
    }


def seal_v1b():
    payload = report_v1b()
    return canonical({'schema': SCHEMA, 'payload': payload,
                      'payload_sha256': sha(SCHEMA + '\n' + canonical(payload))})


def verify_v1b(document):
    obj = strict_json(document)
    if (type(obj) is not dict or set(obj) != {'schema', 'payload', 'payload_sha256'}
            or obj['schema'] != SCHEMA or canonical(obj) != document):
        raise ValueError('noncanonical A2b memory access evidence')
    if obj['payload_sha256'] != sha(SCHEMA + '\n' + canonical(obj['payload'])):
        raise ValueError('A2b memory access checksum mismatch')
    if obj['payload'] != report_v1b():
        raise ValueError('A2b memory access replay mismatch')
    return {'status': 'PASS', 'source_cases': 216, 'compiled_host_comparisons': 648,
            'authorized_fault_prefixes': 504, 'evidence_sha256': sha(document)}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--write', type=Path)
    g.add_argument('--verify', type=Path)
    a = p.parse_args(argv)
    if a.write is not None:
        doc = seal_v1b()
        a.write.write_text(doc + '\n', encoding='utf-8')
        print(canonical({'status': 'WRITTEN', 'evidence_sha256': sha(doc)}))
    else:
        doc = a.verify.read_text(encoding='utf-8').rstrip('\n')
        print(canonical(verify_v1b(doc)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
