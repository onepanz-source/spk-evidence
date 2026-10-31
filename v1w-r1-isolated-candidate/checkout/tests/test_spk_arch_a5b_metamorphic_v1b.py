"""A5b: independently executed, nontrivial cross-subsystem metamorphic laws."""
from dataclasses import replace
import pytest
from search.spk_24o_semantic_corpus_v0 import catalog_v0
from search.spk_24n_differential_evidence_v0 import canonical
from spk_architecture_v1.pe_fabric_v1a import SCHEMES
from search.spk_arch_a4c_candidate_conformance_v1c import args_v1c
from spk_architecture_v1.causal_transport_v1d import execute_causal_transport_v1d
from spk_architecture_v1.operating_modes_v1a import (
    ModeControllerV1a, OperatingModeDeniedV1a, context_fingerprint_v1a,
)
from spk_architecture_v1.metamorphic_v1b import (
    alpha_rename_v1b, normalize_pe_names_v1b, MetamorphicDeniedV1b,
)
from search.spk_arch_a5b_conformance_v1b import (
    metamorphic_case_v1b, ideal_args_v1b, conservation_v1b,
)


@pytest.mark.parametrize('scheme', SCHEMES)
def test_every_case_pe_rename_capacity_and_locality(scheme):
    rows = [metamorphic_case_v1b(cid, case, scheme) for cid, case in catalog_v0()]
    assert len(rows) == 216
    assert len({row['id'] for row in rows}) == 216
    assert all(row['original_context_sha256'] != row['renamed_context_sha256'] for row in rows)
    assert all(row['nonbinding_result_sha256'] == row['nonbinding_expanded_result_sha256'] for row in rows)
    if scheme == 'single':
        assert all(row['remote_occurrences'] == 0 for row in rows)
        assert all(row['single_remote_inert_result_sha256'] == row['original_result_sha256'] for row in rows)
    else:
        assert sum(row['remote_occurrences'] for row in rows) > 0
        assert all(row['single_remote_inert_result_sha256'] is None for row in rows)


def test_renaming_is_a_real_change_of_controller_context():
    case = dict(catalog_v0())['relays/parallel/at_zero']
    args = args_v1c(case, 'spread')
    new, mapping = alpha_rename_v1b(args)
    assert set(mapping) == {'PE0','PE1','PE2'}
    base = execute_causal_transport_v1d(*args)
    renamed = execute_causal_transport_v1d(*new)
    assert canonical(base) == canonical(normalize_pe_names_v1b(renamed, mapping))
    controller = ModeControllerV1a(context_fingerprint_v1a(*args))
    controller.transition('EXECUTE')
    with pytest.raises(OperatingModeDeniedV1a,match='context drift'):
        controller.run(*new)
    assert controller.status == 'QUIESCENT'


def test_normalization_rejects_nonbijective_names():
    with pytest.raises(MetamorphicDeniedV1b):
        normalize_pe_names_v1b({}, {'PE0':'X','PE1':'X'})


def test_rename_rejects_wrong_signature():
    with pytest.raises(MetamorphicDeniedV1b):
        alpha_rename_v1b(('wrong',))


def test_preflight_rejects_missing_pe_quota():
    case = catalog_v0()[0][1]
    args = args_v1c(case,'spread')
    bad = args[:3] + (replace(args[3], pe_slots=args[3].pe_slots[:1]),) + args[4:]
    with pytest.raises(MetamorphicDeniedV1b,match='quota population'):
        alpha_rename_v1b(bad)


def test_conservation_rejects_unaccounted_remote_grant():
    case = dict(catalog_v0())['relays/parallel/at_zero']
    out = execute_causal_transport_v1d(*args_v1c(case,'spread'))
    assert conservation_v1b(out,len(case.events)) > 0
    forged = dict(out)
    forged['transport'] = dict(out['transport'])
    forged['transport']['delivered_cross_pe_occurrences'] -= 1
    with pytest.raises(AssertionError, match='lost, duplicated'):
        conservation_v1b(forged,len(case.events))


def test_capacity_growth_from_binding_quotas_is_not_an_invariance_claim():
    # A saturated finite link and a nonbinding link need not yield identical
    # timestamps or states, so A5b must never assert unconditional monotonicity.
    case = dict(catalog_v0())['relays/chain/separated']
    finite = execute_causal_transport_v1d(*args_v1c(case,'spread'))
    nonbinding = execute_causal_transport_v1d(*ideal_args_v1b(case,'spread',256))
    assert canonical(finite['result']) != canonical(nonbinding['result'])
