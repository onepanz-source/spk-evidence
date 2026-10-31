"""Source-pinned A1d fail-stop prefix evidence vs independently compiled host.

Only the adapter accesses the frozen Compiler/host reference. The new A1d PE
engine itself never calls the frozen stack or the A1c service executor.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from search.spk_24n_differential_evidence_v0 import (
    canonical, sha, strict_json, project_v0,
)
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from spk_architecture_v1.pe_fabric_v1a import SCHEMES, plan_v1a
from spk_architecture_v1.pe_service_v1c import (
    uniform_service_plan_v1c, execute_with_service_v1c,
)
from spk_architecture_v1.pe_fault_v1d import (
    PEFaultPlanV1d, execute_failstop_v1d,
)

SCHEMA = 'spk-architecture-a1d-failstop-evidence/v1d'
SOURCE_SHA256 = 'cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5'
BASE_TAG = 'spk-simulator-bounded-reference-v0'
A1C_EVIDENCE_SHA256 = '9e35bef1a9c7f8b4db89831fdeeb79098f3072618d791cdb02b809eae23a7082'
REGIMES = ('shared_and_pe_limited', 'unconstrained')


def compiled_reference(case_id, case, scheme):
    from search.spk_arch_a1b_pe_local_v1b import evaluate_v1b
    return evaluate_v1b(case_id, case, scheme)


def _project(result):
    return project_v0(result, result['observations']['batches'],
                      result['observations']['routes'])


def _fault_at_second_service(ledger):
    if len(ledger) < 2:
        return None
    second = ledger[1]
    prior_local = sum(r['pe_id'] == second['pe_id'] for r in ledger[:1])
    return PEFaultPlanV1d(second['pe_id'], prior_local)


def _validate_prefix(baseline, fault_out):
    ledger = baseline['service']['ledger']
    if (fault_out['status'] != 'PE_FAULT'
            or 'result' in fault_out or 'receipt' in fault_out
            or 'closed' in fault_out):
        raise AssertionError('fault run exported success or unexpected status')
    prefix = fault_out['committed_prefix']
    if (prefix['processed_batches'] != 1
            or prefix['processed_events'] != ledger[0]['input_occurrences']
            or prefix['service_ledger'] != ledger[:1]
            or prefix['observations']['batches'] != baseline['result']['observations']['batches'][:1]
            or fault_out['fault']['stage'] != 'before_service_grant'
            or fault_out['fault']['node_id'] != ledger[1]['node_id']
            or fault_out['fault']['logical_timestamp'] != ledger[1]['logical_timestamp']):
        raise AssertionError('fault prefix differs from A1c committed work')
    # The first batch may have routes; preserve their occurrence multiplicity.
    batch_zero = baseline['result']['observations']['batches'][0]
    first_routes = [r for r in baseline['result']['observations']['routes']
                    if r['source_node'] == batch_zero['node_id']
                    and r['emission_timestamp'] == batch_zero['timestamp']]
    if prefix['observations']['routes'] != first_routes:
        raise AssertionError('fault prefix route multiplicity mismatch')
    if sum(prefix['pending_event_occurrences_per_pe'].values()) < 1:
        raise AssertionError('fault had no pending batch to quiesce')
    return {'fault_pe': fault_out['fault']['pe_id'],
            'fault_node': fault_out['fault']['node_id'],
            'committed_batches': 1,
            'committed_events': prefix['processed_events'],
            'pending_occurrences': sum(prefix['pending_event_occurrences_per_pe'].values()),
            'prefix_sha256': sha(canonical(prefix))}


def evaluate_v1d(case_id, case, scheme):
    fabric = plan_v1a(case, scheme)
    reference = compiled_reference(case_id, case, scheme)
    summaries = []
    for regime in REGIMES:
        limit = 1 if regime == 'shared_and_pe_limited' else 4096
        plan = uniform_service_plan_v1c(fabric, pe_slots=limit,
                                         fabric_slots_per_tick=limit)
        baseline = execute_with_service_v1c(case, fabric, plan)
        if sha(canonical(_project(baseline['result']))) != reference['canonical_result_sha256']:
            raise AssertionError(case_id + '/' + scheme + ': A1c/frozen mismatch')
        nominal = execute_failstop_v1d(case, fabric, plan)
        if (nominal['status'] != 'CLOSED'
                or {k: nominal[k] for k in ('result', 'transport', 'pe_snapshots', 'service')} != baseline):
            raise AssertionError(case_id + '/' + scheme + ': A1d nominal execution changed A1c')
        fault = _fault_at_second_service(baseline['service']['ledger'])
        witness = None
        if fault is not None:
            witness = _validate_prefix(baseline, execute_failstop_v1d(
                case, fabric, plan, fault))
        summaries.append({'regime': regime, 'nominal_result_sha256':
                          reference['canonical_result_sha256'],
                          'fault': witness})
    return {'case_id': case_id, 'scheme': scheme,
            'manifest_sha256': reference['manifest_sha256'],
            'cross_pe_route_occurrences': reference['cross_pe_route_occurrences'],
            'regimes': summaries}


def report_v1d():
    if catalog_fingerprint_v0() != SOURCE_SHA256:
        raise AssertionError('A1d source corpus fingerprint drift')
    rows = [evaluate_v1d(cid, case, scheme)
            for cid, case in checked_catalog_v0()
            for scheme in SCHEMES]
    if len(rows) != 648:
        raise AssertionError('A1d integration coverage incomplete')
    faults = sum(v['fault'] is not None for row in rows for v in row['regimes'])
    if faults < 600:
        raise AssertionError('A1d corpus has insufficient reachable fail-stop coverage')
    remote = sum(row['cross_pe_route_occurrences'] for row in rows)
    if remote != 768:
        raise AssertionError('A1d source route occurrence drift')
    return {'schema': SCHEMA, 'source_cases': 216,
            'source_sha256': SOURCE_SHA256, 'baseline_tag': BASE_TAG,
            'upstream_a1c_evidence_sha256': A1C_EVIDENCE_SHA256,
            'compiled_reference_comparisons': len(rows),
            'nominal_service_executions': len(rows) * len(REGIMES),
            'eligible_fault_executions': faults,
            'cross_pe_route_occurrences': remote,
            'regimes': list(REGIMES), 'rows': rows,
            'limitations': ['synchronous global quiescence before service grant',
                            'no partial-batch injection, rollback or recovery',
                            'no asynchronous PE execution or physical fault timing']}


def seal_v1d():
    payload = report_v1d()
    return canonical({'schema': SCHEMA, 'payload': payload,
                      'payload_sha256': sha(SCHEMA + '\n' + canonical(payload))})


def verify_v1d(document):
    obj = strict_json(document)
    if (type(obj) is not dict or set(obj) != {'schema', 'payload', 'payload_sha256'}
            or obj['schema'] != SCHEMA or canonical(obj) != document):
        raise ValueError('noncanonical A1d fail-stop evidence')
    if obj['payload_sha256'] != sha(SCHEMA + '\n' + canonical(obj['payload'])):
        raise ValueError('A1d fail-stop checksum mismatch')
    if obj['payload'] != report_v1d():
        raise ValueError('A1d fail-stop evidence replay mismatch')
    p = obj['payload']
    return {'status': 'PASS', 'source_cases': p['source_cases'],
            'compiled_reference_comparisons': p['compiled_reference_comparisons'],
            'nominal_service_executions': p['nominal_service_executions'],
            'eligible_fault_executions': p['eligible_fault_executions'],
            'evidence_sha256': sha(document)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    exclusive = parser.add_mutually_exclusive_group(required=True)
    exclusive.add_argument('--write', type=Path)
    exclusive.add_argument('--verify', type=Path)
    args = parser.parse_args(argv)
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
