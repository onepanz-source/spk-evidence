"""24w real frozen Compiler->manifest->24t observer host, bounded isomorphism."""
import json
import pytest
from search.spk_24n_differential_evidence_v0 import canonical, sha
from search.spk_24w_metamorphic_plan_v0 import (
    VARIANTS, checked_catalog_v0, transform_v0, oracle_projection_v0,
    inverse_projection_v0, identity_v0,
)
from search import spk_24w_cross_layer_metamorphic_v0 as audit

CASES = checked_catalog_v0()


@pytest.fixture(scope='module')
def document():
    return audit.seal_v0()


@pytest.mark.parametrize('variant', VARIANTS)
def test_frozen_compiler_and_host_all_216_sources(variant, document):
    payload = json.loads(document)['payload']
    rows = [r for r in payload['rows'] if r['variant'] == variant]
    assert len(rows) == 216
    assert all(len(r['manifest_sha256']) == len(r['result_sha256']) == 64 for r in rows)
    assert all(r['case_id'] for r in rows)


def test_entire_plan_admitted_no_silent_skip(document):
    payload = json.loads(document)['payload']
    assert payload['source_cases'] == 216
    assert payload['compiled_host_runs'] == 648
    assert payload['variant_counts'] == {v: 216 for v in VARIANTS}
    assert payload['plan_sha256'] == identity_v0()
    assert len(payload['rows']) == 648
    assert len({(r['case_id'], r['variant']) for r in payload['rows']}) == 648


def test_result_hashes_equivalent_across_variants(document):
    rows = json.loads(document)['payload']['rows']
    bycase = {}
    for row in rows:
        bycase.setdefault(row['case_id'], set()).add(row['result_sha256'])
    assert len(bycase) == 216 and all(len(values) == 1 for values in bycase.values())


def test_live_manifest_matches_original_primitive_reference_on_parallel_duplicate():
    from search.spk_24u_cross_layer_v0 import compile_case_v0
    from search.spk_24t_diagnostic_manifest_host_v0 import execute_manifest_v0
    cid, case = next((cid, c) for cid, c in CASES if cid == 'relays/parallel/duplicate')
    original = oracle_projection_v0(case)
    for v in VARIANTS:
        transformed = transform_v0(case, v)
        manifest, pin = compile_case_v0(transformed)
        result = execute_manifest_v0(manifest, pin)
        assert result['status'] == 'CLOSED'
        assert inverse_projection_v0(result['result'], v) == original


def test_canonical_cross_process_receipt_replays_complete_execution(document):
    result = audit.verify_v0(document)
    assert result['status'] == 'PASS'
    assert result['compiled_host_runs'] == 648
    assert result['evidence_sha256'] == sha(document)


def test_resealed_modified_manifest_digest_does_not_pass_full_replay(document):
    obj = json.loads(document)
    obj['payload']['rows'][0]['manifest_sha256'] = '0' * 64
    obj['payload_sha256'] = sha(audit.SCHEMA + '\n' + canonical(obj['payload']))
    with pytest.raises(ValueError, match='replay mismatch'):
        audit.verify_v0(canonical(obj))


def test_corrupt_hash_rejected_without_execution(document):
    obj = json.loads(document)
    obj['payload_sha256'] = 'f' * 64
    with pytest.raises(ValueError, match='checksum'):
        audit.verify_v0(canonical(obj))


def test_noncanonical_or_duplicate_json_keys_are_rejected(document):
    with pytest.raises(ValueError, match='noncanonical'):
        audit.verify_v0(' ' + document)
    with pytest.raises(ValueError, match='duplicate JSON'):
        audit.verify_v0(document[:-1] + ',"schema":"forged"}')
