"""Pure tests: no imported frozen SPK interpreter or Core."""
from dataclasses import replace

import pytest

from search.spk_24r_dual_limit_plan_v0 import (
    plan_v0, probe_for_case_v0, check_eligibility_v0, summary_v0,
)
from search.spk_24o_semantic_corpus_v0 import catalog_v0
from search.spk_24n_independent_oracle_v0 import execute_v0


def test_full_corpus_dual_limit_plan_and_independent_proofs():
    rows = plan_v0()
    assert len(rows) == 168
    assert len({p.case_id for _, _, p in rows}) == len(rows)
    assert len(catalog_v0()) == 216
    for cid, case, probe in rows:
        assert probe.case_id == cid
        assert check_eligibility_v0(case, probe)['both_eligible'] is True


def test_plan_summary_and_source_corpus_fingerprint():
    summary = summary_v0()
    assert summary['case_count'] == 216
    assert summary['dual_limit_probes'] == 168
    assert summary['corpus_sha256'] == 'cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5'


def test_no_dual_probe_for_zero_and_single_batch_cases():
    no_probes = [(name, case) for name, case in catalog_v0()
                 if probe_for_case_v0(name, case) is None]
    assert len(no_probes) == 216 - 168
    assert all(len(execute_v0(c)['observations']['batches']) < 2
               for _, c in no_probes)


@pytest.mark.parametrize('field,change', (
    ('max_batches', 1), ('max_events', 1), ('prior_events', 1),
    ('prior_batches', 1), ('pending_batch_events', 1),
))
def test_forged_dual_limit_prefix_rejected(field, change):
    _, case, p = plan_v0()[0]
    tampered = replace(p, **{field: getattr(p, field) + change})
    with pytest.raises(AssertionError):
        check_eligibility_v0(case, tampered)


def test_empty_case_identifier_rejected():
    _, case = catalog_v0()[0]
    with pytest.raises(ValueError):
        probe_for_case_v0('', case)


def test_only_allowed_reason_emerges_from_independent_oracle():
    assert {check_eligibility_v0(case, p)['independent_reason']
            for _, case, p in plan_v0()} == {'max_batches'}
