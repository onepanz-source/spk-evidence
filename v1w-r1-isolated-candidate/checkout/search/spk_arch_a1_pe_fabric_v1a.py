"""SPK Architecture A1a: compiled reference placement conformance.

This performs three admissions/manifest host runs per 24o source case.
No PE scheduler is claimed: frozen Network executes the logical computation.
"""
from __future__ import annotations
import argparse
from pathlib import Path

from spk_architecture_v1.pe_fabric_v1a import (
    SCHEMES, plan_v1a, classify_routes_v1a,
)
from search.spk_24n_differential_evidence_v0 import (
    canonical, sha, strict_json, project_v0,
)
from search.spk_24n_independent_oracle_v0 import execute_v0
from search.spk_24o_extended_differential_v0 import to_frozen_v0
from search.spk_24w_metamorphic_plan_v0 import checked_catalog_v0
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24t_diagnostic_manifest_host_v0 import execute_manifest_v0
from spk_architecture.profile_v0 import ProcessingElementV0, ArchitectureProfileV0
from spk_compiler.pe_admission_v0 import NodePlacementV0
from spk_compiler.network_ir_v0 import dumps_network_ir_v0
from spk_compiler.compile_pipeline_v0 import compile_network_ir_v0
from spk_compiler.compilation_manifest_v0 import (
    dumps_compilation_manifest_v0, loads_compilation_manifest_v0,
)
from spk_compiler.resource_admission_v0 import ResourceProfileV0

SCHEMA = 'spk-architecture-a1-pe-placement-evidence/v1a'
SOURCE_SHA256 = 'cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5'
BASE_TAG = 'spk-simulator-bounded-reference-v0'
BASE_COMMIT = 'a76ebaae49373a4c6b66f94465d78dbf1cf19f80'


def _machine(fabric):
    # Frozen PE Profile v0 requires homogeneous capacities. Overprovisioned
    # budgets eliminate admission-driven resource contention in A1a.
    pes = tuple(ProcessingElementV0(
        pe_id=pid, program_slots=32, state_slots=4, event_slots=64,
        output_slots=64, observation_slots=64, accesses_per_service_tick=8,
    ) for pid in fabric.pe_ids)
    return ArchitectureProfileV0('spk-arch-v1a-' + fabric.scheme, pes)


def _expected(case):
    result = execute_v0(case, max_batches=128, max_events=4096)
    return project_v0(result, result['observations']['batches'],
                      result['observations']['routes'])


def evaluate_v1a(case_id, case, scheme, *, expected=None):
    fabric = plan_v1a(case, scheme)
    frozen, events = to_frozen_v0(case)
    compiled = compile_network_ir_v0(
        network_ir_json=dumps_network_ir_v0(frozen), initial_events=events,
        resource_profile=ResourceProfileV0(), architecture=_machine(fabric),
        placements=tuple(NodePlacementV0(p.node_id, p.pe_id) for p in fabric.placement),
    )
    manifest = dumps_compilation_manifest_v0(compiled)
    if loads_compilation_manifest_v0(manifest) != compiled:
        raise AssertionError(case_id + ': manifest roundtrip mismatch')
    if compiled.pe_admission.cross_pe_edges != fabric.profile()['cross_pe_edges']:
        raise AssertionError(case_id + ': frozen PE admission lost cross-PE edge multiplicity')
    receipt = execute_manifest_v0(manifest, sha(manifest))
    expected = _expected(case) if expected is None else expected
    if (receipt['status'] != 'CLOSED' or receipt['adjudication'] != 'EXACT_PASS'
            or receipt['result'] != expected):
        raise AssertionError(case_id + ': placement changed logical computation')
    logical_routes = [strict_json(s) for s in receipt['result']['observations']['routes']]
    classified = classify_routes_v1a(fabric, logical_routes)
    if classified['occurrences'] != len(logical_routes):
        raise AssertionError(case_id + ': route multiplicity lost')
    return {'case_id': case_id, 'scheme': scheme,
            'manifest_sha256': sha(manifest), 'result_sha256': sha(canonical(expected)),
            'profile': fabric.profile(), 'logical_route_count': classified['occurrences'],
            'cross_pe_route_occurrences': classified['cross_pe_occurrences'],
            'local_route_occurrences': classified['local_occurrences']}


def report_v1a():
    if catalog_fingerprint_v0() != SOURCE_SHA256:
        raise AssertionError('frozen source corpus changed')
    rows = []
    cases = checked_catalog_v0()
    for case_id, case in cases:
        expected = _expected(case)
        for scheme in SCHEMES:
            rows.append(evaluate_v1a(case_id, case, scheme, expected=expected))
        # Strong pairwise invariant. Checks outputs/states, not just terminal spikes.
        if len({r['result_sha256'] for r in rows[-3:]}) != 1:
            raise AssertionError(case_id + ': result depends on PE mapping')
    if len(rows) != 648:
        raise AssertionError('expected exactly 216x3 compiled runs')
    return {'schema': SCHEMA, 'baseline_tag': BASE_TAG, 'baseline_commit': BASE_COMMIT,
            'source_sha256': SOURCE_SHA256, 'source_cases': len(cases),
            'placement_variants': list(SCHEMES), 'compiled_runs': len(rows),
            'cross_pe_route_occurrences': sum(r['cross_pe_route_occurrences'] for r in rows),
            'rows': rows, 'limitations': ['static ownership only',
                'no PE scheduler', 'no inter-PE transport simulation',
                'no service contention', 'no physical timing or backpressure']}


def seal_v1a():
    payload = report_v1a()
    return canonical({'schema': SCHEMA, 'payload': payload,
                      'payload_sha256': sha(SCHEMA + '\n' + canonical(payload))})


def verify_v1a(document):
    obj = strict_json(document)
    if (type(obj) is not dict or set(obj) != {'schema', 'payload', 'payload_sha256'}
            or obj['schema'] != SCHEMA or canonical(obj) != document):
        raise ValueError('noncanonical PE fabric evidence')
    if obj['payload_sha256'] != sha(SCHEMA + '\n' + canonical(obj['payload'])):
        raise ValueError('PE fabric evidence checksum mismatch')
    if obj['payload'] != report_v1a():
        raise ValueError('PE fabric evidence replay mismatch')
    return {'status': 'PASS', 'source_cases': 216, 'compiled_runs': 648,
            'cross_pe_route_occurrences': obj['payload']['cross_pe_route_occurrences'],
            'source_sha256': SOURCE_SHA256, 'evidence_sha256': sha(document)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--write', type=Path)
    modes.add_argument('--verify', type=Path)
    args = parser.parse_args(argv)
    if args.write is not None:
        doc = seal_v1a()
        args.write.write_text(doc + '\n', encoding='utf-8')
    else:
        doc = args.verify.read_text(encoding='utf-8').rstrip('\n')
    print(canonical(verify_v1a(doc)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
