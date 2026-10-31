"""A2d finite memory failure evidence across frozen Compiler/host and A1d/A2a/A2b/A2c."""
from __future__ import annotations
import argparse
from pathlib import Path

from search.spk_24n_differential_evidence_v0 import canonical, sha, strict_json
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from search.spk_arch_a2c_memory_service_conformance_v1c import evaluate_v1c
from spk_architecture_v1.pe_fabric_v1a import SCHEMES, plan_v1a
from spk_architecture_v1.pe_service_v1c import uniform_service_plan_v1c
from spk_architecture_v1.pe_fault_v1d import execute_failstop_v1d, PEFaultPlanV1d
from spk_architecture_v1.memory_projection_v1a import (
    admit_memory_v1a, project_execution_memory_v1a, uniform_memory_plan_v1a,
)
from spk_architecture_v1.memory_access_v1b import authorize_projection_v1b
from spk_architecture_v1.memory_service_v1c import memory_service_plan_v1c
from spk_architecture_v1.memory_exhaustion_v1d import (
    CAP_FIELDS, preflight_memory_v1d, execute_after_admission_v1d,
    shortfall_plan_v1d, exact_and_short_v1d, projection_digest_v1d,
)

SCHEMA = 'spk-architecture-memory-exhaustion-evidence/v1d'
SOURCE_SHA256 = 'cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5'
BASE_TAG = 'spk-simulator-bounded-reference-v0'


def _short_summary(outcome):
    return None if outcome is None else {
        'status': outcome['status'], 'reason': outcome['reason'],
        'execution_status': outcome['execution_status'],
        'logical_units': outcome['logical_units'],
        'max_service_ticks': outcome['max_service_ticks'],
        'complete_service': outcome['complete_service'],
    }


def evaluate_v1d(cid, case, scheme):
    compiled = evaluate_v1c(cid, case, scheme)  # actual frozen Compiler/host witness
    fabric = plan_v1a(case, scheme)
    pe_plan = uniform_service_plan_v1c(fabric, pe_slots=4096,
                                        fabric_slots_per_tick=4096)
    memory = uniform_memory_plan_v1a(fabric)
    baseline = preflight_memory_v1d(case, fabric, pe_plan, memory)
    if baseline['status'] != 'ADMITTED':
        raise AssertionError('A2d nominal A2a capacity admission drift: ' + cid)
    admission = baseline['admission']

    # Every mutated one-unit shortage must be rejected before any PE batch.
    capacity_rejections = {}
    for domain in CAP_FIELDS:
        deficient = shortfall_plan_v1d(admission, memory, domain)
        def forbidden():
            raise AssertionError('A2d invoked executor after denied capacity')
        rejected = execute_after_admission_v1d(case, fabric, pe_plan,
                                                deficient, forbidden)
        if (rejected['status'] != 'ADMISSION_REJECTED' or rejected['execution'] is not None
                or f'/{domain}:' not in rejected['detail']):
            raise AssertionError('A2d capacity rejection drift: ' + cid + '/' + domain)
        capacity_rejections[domain] = rejected['detail']

    admitted = execute_after_admission_v1d(
        case, fabric, pe_plan, memory,
        lambda: execute_failstop_v1d(case, fabric, pe_plan))
    if admitted['status'] != 'EXECUTED' or admitted['execution']['status'] != 'CLOSED':
        raise AssertionError('A2d nominal PE closure drift')
    projection = project_execution_memory_v1a(case, fabric, admission,
                                               admitted['execution'])
    authorization = authorize_projection_v1b(admission, projection)
    plan = memory_service_plan_v1c(admission, pe_slots=2,
                                    fabric_slots_per_tick=3, domain_slots_per_tick=2)
    boundary = exact_and_short_v1d(admission, projection, plan,
                         expected_projection_sha256=projection_digest_v1d(projection))
    if (boundary['required_service_ticks'] != compiled['limited_service_ticks']
            or authorization['logical_units'] != compiled['nominal_units']
            or boundary['exact']['complete_service']['weighted_wait_ticks'] !=
               compiled['limited_weighted_wait']):
        raise AssertionError('A2d compiled A2c service mismatch: ' + cid)

    fault = None
    ledger = admitted['execution']['service']['ledger']
    if len(ledger) >= 2:
        second = ledger[1]
        prior = sum(row['pe_id'] == second['pe_id'] for row in ledger[:1])
        interrupted = execute_failstop_v1d(case, fabric, pe_plan,
                              PEFaultPlanV1d(second['pe_id'], prior))
        fault_projection = project_execution_memory_v1a(case, fabric, admission,
                                                         interrupted)
        fault_boundary = exact_and_short_v1d(admission, fault_projection, plan,
                         expected_projection_sha256=projection_digest_v1d(fault_projection))
        if (fault_boundary['exact']['execution_status'] != 'PE_FAULT'
                or fault_boundary['exact']['complete_service']['execution_status'] != 'PE_FAULT'
                or fault_boundary['exact']['logical_units'] != compiled['fault_units']):
            raise AssertionError('A2d fault-prefix status was lost: ' + cid)
        fault = {
            'status': 'PE_FAULT',
            'required_service_ticks': fault_boundary['required_service_ticks'],
            'exact_service_sha256': sha(canonical(fault_boundary['exact']['complete_service'])),
            'short': _short_summary(fault_boundary['short']),
        }
    elif compiled['fault_units'] is not None:
        raise AssertionError('A2d missing PE fault prefix witness')

    short = _short_summary(boundary['short'])
    return {'id': cid, 'scheme': scheme, 'manifest_sha256': compiled['manifest_sha256'],
            'admission_rejections': capacity_rejections,
            'nominal_execution_status': admitted['execution']['status'],
            'required_service_ticks': boundary['required_service_ticks'],
            'exact_service_sha256': sha(canonical(boundary['exact']['complete_service'])),
            'short': short, 'fault': fault}


def report_v1d():
    if catalog_fingerprint_v0() != SOURCE_SHA256:
        raise AssertionError('A2d pinned source corpus drift')
    rows = [evaluate_v1d(cid, case, scheme)
            for cid, case in checked_catalog_v0() for scheme in SCHEMES]
    faults = sum(row['fault'] is not None for row in rows)
    nominal_short = sum(row['short'] is not None for row in rows)
    fault_short = sum(row['fault'] is not None and row['fault']['short'] is not None
                      for row in rows)
    cap = sum(len(row['admission_rejections']) for row in rows)
    if len(rows) != 648 or faults != 504 or cap != 2592:
        raise AssertionError('A2d finite resource failure coverage incomplete')
    if any(row['short'] is not None and
           (row['short']['status'] != 'MEMORY_SERVICE_EXHAUSTED'
            or row['short']['complete_service'] is not None) for row in rows):
        raise AssertionError('A2d short budget emitted completed receipt')
    return {'schema': SCHEMA, 'source_sha256': SOURCE_SHA256,
            'baseline_tag': BASE_TAG, 'source_cases': 216,
            'compiled_host_comparisons': 648,
            'capacity_admission_rejections': cap,
            'nominal_service_exact_passes': len(rows),
            'nominal_service_short_failures': nominal_short,
            'fault_prefix_exact_passes': faults,
            'fault_prefix_short_failures': fault_short,
            'short_budget_nonprobeable': len(rows) + faults - nominal_short - fault_short,
            'rows': rows,
            'limitations': ['memory service uses post-execution aggregate A2b demands',
                            'no live memory access interception or causal stall',
                            'A2c supplies the exact boundary reference, not independent timing',
                            'no recovery, rollback, physical memory or transaction atomicity']}


def seal_v1d():
    payload = report_v1d()
    return canonical({'schema': SCHEMA, 'payload': payload,
                      'payload_sha256': sha(SCHEMA + '\n' + canonical(payload))})


def verify_v1d(document):
    obj = strict_json(document)
    if (type(obj) is not dict or set(obj) != {'schema', 'payload', 'payload_sha256'}
            or obj['schema'] != SCHEMA or canonical(obj) != document):
        raise ValueError('noncanonical A2d memory failure evidence')
    if obj['payload_sha256'] != sha(SCHEMA + '\n' + canonical(obj['payload'])):
        raise ValueError('A2d memory failure checksum mismatch')
    if obj['payload'] != report_v1d():
        raise ValueError('A2d memory failure replay mismatch')
    payload = obj['payload']
    return {'status': 'PASS', 'source_cases': payload['source_cases'],
            'compiled_host_comparisons': payload['compiled_host_comparisons'],
            'capacity_admission_rejections': payload['capacity_admission_rejections'],
            'nominal_service_exact_passes': payload['nominal_service_exact_passes'],
            'nominal_service_short_failures': payload['nominal_service_short_failures'],
            'fault_prefix_exact_passes': payload['fault_prefix_exact_passes'],
            'fault_prefix_short_failures': payload['fault_prefix_short_failures'],
            'short_budget_nonprobeable': payload['short_budget_nonprobeable'],
            'evidence_sha256': sha(document)}


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--write', type=Path)
    g.add_argument('--verify', type=Path)
    args = p.parse_args(argv)
    if args.write is not None:
        doc = seal_v1d()
        args.write.write_text(doc + '\n', encoding='utf-8')
        print(canonical({'status': 'WRITTEN', 'evidence_sha256': sha(doc)}))
    else:
        doc = args.verify.read_text(encoding='utf-8').rstrip('\n')
        print(canonical(verify_v1d(doc)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
