"""24w primitive-only metamorphic corpus tests, no frozen modules imported."""
import pytest
from collections import Counter
from dataclasses import asdict
from search.spk_24n_independent_oracle_v0 import CaseV0
from search.spk_24n_differential_evidence_v0 import canonical, project_v0, sha
from search.spk_24o_semantic_corpus_v0 import catalog_fingerprint_v0
from search.spk_24w_metamorphic_plan_v0 import (
    SOURCE_SHA256, VARIANTS, checked_catalog_v0, renaming_v0,
    transform_v0, inverse_projection_v0, oracle_projection_v0,
    assert_pure_equivalence_v0, identity_v0, plan_v0, summary_v0,
)

CASES = checked_catalog_v0()


def test_exact_pinned_216_by_3():
    assert catalog_fingerprint_v0() == SOURCE_SHA256
    assert len(CASES) == 216 and len(plan_v0()) == 648
    assert len({k for k, _ in CASES}) == 216
    assert tuple(summary_v0()[key] for key in ('source_cases', 'variants', 'metamorphic_cases')) == (216, 3, 648)


def test_plan_fingerprint_stable():
    assert identity_v0() == '91dda6289f29b38a12a7672c36169003c3eddc27ff3d4b8abfd923d9f0565d0f'


def test_mappings_are_bijections_and_include_nontrivial_permutations():
    for variant in VARIANTS:
        m = renaming_v0(variant)
        assert set(m) == set(m.values()) == set('ABC')
    assert renaming_v0('cycle_and_reverse') != renaming_v0('reverse_order')


def test_transform_refuses_unsupported_id():
    case = CASES[0][1]
    from dataclasses import replace
    wrong = replace(case, nodes=(replace(case.nodes[0], node_id='X'),) + case.nodes[1:])
    with pytest.raises(ValueError, match='domain'):
        transform_v0(wrong, 'swap_ac')


def test_refuse_unknown_variant():
    with pytest.raises(ValueError, match='unknown'):
        renaming_v0('delete_A')


def test_no_loss_of_parallel_edges_or_duplicate_inputs():
    selected = next(case for cid, case in CASES if cid == 'relays/parallel/duplicate')
    for v in VARIANTS:
        t = transform_v0(selected, v)
        assert len(t.edges) == len(selected.edges) == 3
        assert len(t.events) == len(selected.events) == 2
        assert sum(Counter(asdict(e).__repr__() for e in t.edges).values()) == 3
        assert sum(Counter(asdict(e).__repr__() for e in t.events).values()) == 2


def test_transformation_does_not_mutate_source():
    case = CASES[3][1]
    before = canonical(asdict(case))
    for variant in VARIANTS:
        out = transform_v0(case, variant)
        assert type(out) is CaseV0
    assert canonical(asdict(case)) == before


@pytest.mark.parametrize('profile', sorted({cid.split('/')[0] for cid, _ in CASES}))
def test_full_648_case_pure_oracle_invariance_by_profile(profile):
    n = 0
    for cid, case in CASES:
        if cid.split('/')[0] == profile:
            for variant in VARIANTS:
                assert len(assert_pure_equivalence_v0(case, variant)) == 64
                n += 1
    assert n == 108


def test_normalization_refuses_unexpected_projection():
    with pytest.raises(ValueError, match='structure'):
        inverse_projection_v0({'not_a_projection': 1}, 'swap_ac')


def test_all_6_instructions_profiles_remain_present():
    assert {cid.split('/')[0] for cid, _ in CASES} == {
        'relays','threshold','decay','double_emit','guard_overwrite','fractional'
    }
