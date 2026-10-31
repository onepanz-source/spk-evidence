"""SPK 24w: compile, manifest, bounded host and oracle graph isomorphism.

The expected metamorphic result comes from *primitive source* interpretation.
The frozen compiler and Network are used only to produce the actual result.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from search.spk_24n_differential_evidence_v0 import canonical, sha, strict_json
from search.spk_24w_metamorphic_plan_v0 import (
    SCHEMA as PLAN_SCHEMA, VARIANTS, checked_catalog_v0, transform_v0,
    oracle_projection_v0, inverse_projection_v0, identity_v0, summary_v0,
)
from search.spk_24u_cross_layer_v0 import compile_case_v0
from search.spk_24t_diagnostic_manifest_host_v0 import execute_manifest_v0

SCHEMA = 'spk-cross-layer-structural-metamorphism-evidence/v0'


def evaluate_v0(case_id, case, variant, *, original=None):
    if variant not in VARIANTS:
        raise ValueError('unknown metamorphism')
    reference = original if original is not None else oracle_projection_v0(case)
    transformed = transform_v0(case, variant)
    expected = inverse_projection_v0(oracle_projection_v0(transformed), variant)
    if expected != reference:
        raise AssertionError(case_id + ': primitive metamorphic oracle mismatch')
    # Mandatory Compiler admission and versioned manifest round-trip. No fallback
    # to a direct frozen Network run on Compiler rejection.
    manifest, pin = compile_case_v0(transformed)
    receipt = execute_manifest_v0(manifest, pin)
    if (receipt['status'] != 'CLOSED' or receipt['adjudication'] != 'EXACT_PASS'
            or receipt['selected_reason'] is not None or receipt['eligible_reasons']
            or receipt['result'] is None):
        raise AssertionError(case_id + '/' + variant + ': compiled host did not close')
    normalized = inverse_projection_v0(receipt['result'], variant)
    if normalized != reference:
        raise AssertionError(case_id + '/' + variant + ': cross-layer isomorphism mismatch')
    return {'case_id': case_id, 'variant': variant,
            'manifest_sha256': pin, 'result_sha256': sha(canonical(normalized))}


def report_v0():
    rows = []
    for case_id, case in checked_catalog_v0():
        original = oracle_projection_v0(case)
        for variant in VARIANTS:
            rows.append(evaluate_v0(case_id, case, variant, original=original))
    if len(rows) != 648:
        raise AssertionError('incomplete metamorphic integration plan')
    return {'schema': SCHEMA, 'plan_sha256': identity_v0(),
            'plan_summary': summary_v0(),
            'source_cases': 216, 'compiled_host_runs': len(rows),
            'variant_counts': {v: sum(r['variant'] == v for r in rows)
                               for v in VARIANTS},
            'rows': rows}


def seal_v0():
    payload = report_v0()
    return canonical({'schema': SCHEMA, 'payload': payload,
                      'payload_sha256': sha(SCHEMA + '\n' + canonical(payload))})


def verify_v0(document):
    obj = strict_json(document)
    if (type(obj) is not dict or set(obj) != {'schema', 'payload', 'payload_sha256'}
            or obj['schema'] != SCHEMA or canonical(obj) != document):
        raise ValueError('noncanonical metamorphic evidence envelope')
    if sha(SCHEMA + '\n' + canonical(obj['payload'])) != obj['payload_sha256']:
        raise ValueError('metamorphic evidence checksum mismatch')
    if report_v0() != obj['payload']:
        raise ValueError('metamorphic full replay mismatch')
    return {'status': 'PASS', 'source_cases': 216, 'compiled_host_runs': 648,
            'plan_sha256': identity_v0(), 'evidence_sha256': sha(document)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--write', type=Path)
    group.add_argument('--verify', type=Path)
    args = parser.parse_args(argv)
    if args.write is not None:
        document = seal_v0()
        args.write.write_text(document + '\n', encoding='utf-8')
    else:
        document = args.verify.read_text(encoding='utf-8').rstrip('\n')
    print(canonical(verify_v0(document)))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
