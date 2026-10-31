"""Authoritative fwork cross-layer: 216 separately compiled 3-node cases."""
import json
from pathlib import Path

import pytest

from search import spk_24u_cross_layer_v0 as bridge
from search.spk_24u_conformance_plan_v0 import entries_v0, summary_v0
from search.spk_24o_semantic_corpus_v0 import catalog_v0
from search.spk_24n_differential_evidence_v0 import canonical, sha

CASES = catalog_v0()
PLAN = entries_v0()
from search.spk_24s_budget_triads_v0 import plan_v0 as causal_plan
CAUSAL = {n: controls for n, _, controls in causal_plan()}


@pytest.fixture(scope="module")
def document():
    return bridge.seal_v0()


@pytest.mark.parametrize('profile', summary_v0()['profiles'])
def test_every_compiled_case_reaches_versioned_host_and_oracle(profile):
    seen = 0
    for (cid, case), selected in zip(CASES, PLAN):
        if selected.profile != profile:
            continue
        record = bridge.evaluate_case_v0(cid, case, selected,
                                         CAUSAL.get(cid, ()))
        assert record['case_id'] == cid
        assert record['compiled_nodes'] == 3
        assert record['host_runs'] == 1 + len(selected.boundary_kinds) + len(selected.dual_controls)
        seen += 1
    assert seen == 36


def test_three_node_manifest_roundtrips_for_each_profile():
    for cid, case in CASES:
        if not cid.endswith('/duplicate'):
            continue
        manifest, pin = bridge.compile_case_v0(case)
        assert pin == sha(manifest)
        assert manifest and manifest[0] == '{'


def test_host_rejects_wrong_compiled_manifest_pin():
    cid, case = CASES[0]
    manifest, pin = bridge.compile_case_v0(case)
    with pytest.raises(ValueError, match='source-pin mismatch'):
        bridge.execute_manifest_v0(manifest + '\n', pin)


def test_evidence_full_replay_and_deterministic_summary(document):
    doc = document
    verified = bridge.verify_v0(doc)
    assert verified['status'] == 'PASS'
    assert verified['admitted_cases'] == 216
    assert verified['host_runs'] == 408
    assert verified['exact_adjudications'] == 378
    assert verified['ambiguous_adjudications'] == 30
    payload = json.loads(doc)['payload']
    assert payload['plan_summary'] == summary_v0()
    assert len(payload['rows']) == 216
    assert all(r['manifest_sha256'] != '' for r in payload['rows'])


def test_even_resealed_replay_forgery_is_rejected(document):
    doc = document
    obj = json.loads(doc)
    obj['payload']['rows'][0]['result_sha256'] = '0' * 64
    obj['payload_sha256'] = sha(bridge.SCHEMA + '\n' + canonical(obj['payload']))
    with pytest.raises(ValueError, match='replay mismatch'):
        bridge.verify_v0(canonical(obj))


def test_checksum_and_noncanonical_forms_are_rejected_before_replay(document):
    doc = document
    obj = json.loads(doc)
    obj['payload_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='checksum'):
        bridge.verify_v0(canonical(obj))
    with pytest.raises(ValueError, match='noncanonical'):
        bridge.verify_v0(' ' + doc)
