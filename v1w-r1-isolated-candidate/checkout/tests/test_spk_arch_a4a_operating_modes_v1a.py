"""A4a independent in-process mode and quiescent boundary tests."""
from dataclasses import replace
import pytest
from search.spk_24o_semantic_corpus_v0 import catalog_v0
from spk_architecture_v1.pe_fabric_v1a import plan_v1a
from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
from spk_architecture_v1.temporal_service_v1b import uniform_causal_service_plan_v1b
from spk_architecture_v1.causal_memory_v1c import uniform_causal_memory_plan_v1c
from spk_architecture_v1.causal_transport_v1d import (
    CausalLinkPlanV1d, CausalLinkHorizonV1d,
)
from spk_architecture_v1.operating_modes_v1a import (
    ModeControllerV1a, OperatingModeDeniedV1a, OperatingModeFaultV1a,
    context_fingerprint_v1a,
)


def setup(case_id='relays/parallel/at_zero', scheme='spread', link=None):
    case = next(case for ident, case in catalog_v0() if ident == case_id)
    f = plan_v1a(case, scheme)
    t = TransportPlanV1a(2)
    p = uniform_causal_service_plan_v1b(f, pe_slots=128, fabric_slots_per_tick=128)
    m = uniform_causal_memory_plan_v1c(f)
    l = link or CausalLinkPlanV1d(1, 1, 128, 4096)
    c = ModeControllerV1a(context_fingerprint_v1a(case, f, t, p, m, l))
    return c, (case, f, t, p, m, l)


def test_every_mode_has_explicit_rights_and_no_direct_training_execute():
    c, args = setup()
    for mode in ('TRAINING', 'REMODEL'):
        c.transition(mode)
        with pytest.raises(OperatingModeDeniedV1a, match='forbidden'):
            c.run(*args)
        assert c.stage('a' * 64).status == 'QUIESCENT'
        with pytest.raises(OperatingModeDeniedV1a, match='transition'):
            c.transition('EXECUTE')
        c.transition('VERIFY')
    c.transition('EXECUTE')
    with pytest.raises(OperatingModeDeniedV1a, match='forbidden'):
        c.stage('a' * 64)
    with pytest.raises(OperatingModeDeniedV1a, match='transition'):
        c.transition('TRAINING')


def test_mode_epoch_count_quiescent_six_transitions():
    c, args = setup()
    for mode in ('TRAINING', 'VERIFY', 'REMODEL', 'VERIFY', 'EXECUTE'):
        c.transition(mode)
    live = c.run(*args)
    c.transition('VERIFY')
    replay = c.run(*args, expected_sha256=live['result_sha256'])
    assert replay['boundary'].epoch == 6
    assert replay['boundary'].status == 'QUIESCENT'
    assert c.audit[-1]['kind'] == 'REPLAY'


def test_cannot_change_mode_during_run_lease():
    c, args = setup()
    c.transition('EXECUTE')
    lease = c._start('RUN', c.context_sha256)
    with pytest.raises(OperatingModeDeniedV1a, match='nonquiescent'):
        c.transition('VERIFY')
    with pytest.raises(OperatingModeDeniedV1a, match='not quiescent'):
        c.run(*args)
    with pytest.raises(OperatingModeFaultV1a, match='lease'):
        c._finish(lease + 1, 'RUN', 'a' * 64)
    c._fault()
    with pytest.raises(OperatingModeDeniedV1a, match='nonquiescent'):
        c.transition('VERIFY')


def test_change_to_bound_program_is_rejected_before_engine():
    c, args = setup()
    c.transition('EXECUTE')
    changed = list(args)
    changed[4] = replace(args[4], fabric_slots_per_tick=1)
    with pytest.raises(OperatingModeDeniedV1a, match='context drift'):
        c.run(*changed)
    assert c.status == 'QUIESCENT'  # no run lease was acquired


@pytest.mark.parametrize('where', [0, 1, 2, 3, 4, 5])
def test_each_frozen_context_dimension_is_bound(where):
    c, args = setup()
    changed = list(args)
    if where == 0:
        changed[0] = replace(args[0], events=())
    elif where == 1:
        changed[1] = plan_v1a(args[0], 'single')
    elif where == 2:
        changed[2] = TransportPlanV1a(1)
    elif where == 3:
        changed[3] = replace(args[3], fabric_slots_per_tick=1)
    elif where == 4:
        changed[4] = replace(args[4], fabric_slots_per_tick=1)
    else:
        changed[5] = CausalLinkPlanV1d(1, 2, 128, 4096)
    c.transition('EXECUTE')
    with pytest.raises(OperatingModeDeniedV1a, match='context drift'):
        c.run(*changed)


def test_verify_needs_independent_expected_digest():
    c, args = setup()
    with pytest.raises(OperatingModeDeniedV1a, match='pinned'):
        c.run(*args)
    with pytest.raises(OperatingModeDeniedV1a, match='pinned'):
        c.run(*args, expected_sha256='000')
    assert c.status == 'QUIESCENT'


def test_failed_replay_does_not_claim_quiescence():
    c, args = setup()
    with pytest.raises(OperatingModeDeniedV1a, match='replay mismatch'):
        c.run(*args, expected_sha256='f' * 64)
    assert c.status == 'FAULTED'
    with pytest.raises(OperatingModeDeniedV1a, match='nonquiescent'):
        c.transition('EXECUTE')


def test_runtime_failure_faults_authority_without_claiming_rollback():
    c, args = setup(link=CausalLinkPlanV1d(1, 1, 128, 1))
    c.transition('EXECUTE')
    with pytest.raises(CausalLinkHorizonV1d):
        c.run(*args)
    assert c.status == 'FAULTED'
    assert all(x['kind'] != 'RUN' for x in c.audit)


def test_bad_mode_epoch_and_candidate_values_fail_closed():
    with pytest.raises(OperatingModeDeniedV1a):
        ModeControllerV1a('0' * 64, 'EXPLOIT')
    with pytest.raises(OperatingModeDeniedV1a):
        ModeControllerV1a('x' * 64)
    c, args = setup()
    with pytest.raises(OperatingModeDeniedV1a):
        c.transition('NONSENSE')
    c.transition('TRAINING')
    for bad in ('f' * 63, 'G' * 64, True, ''):
        with pytest.raises(OperatingModeDeniedV1a):
            c.stage(bad)


def test_no_mode_elevation_by_self_supplied_action():
    c, args = setup()
    with pytest.raises(OperatingModeDeniedV1a, match='forbidden'):
        c._start('RUN', c.context_sha256)
    with pytest.raises(OperatingModeDeniedV1a, match='forbidden'):
        c._start('STAGE', c.context_sha256)
    c.transition('TRAINING')
    with pytest.raises(OperatingModeDeniedV1a, match='forbidden'):
        c._start('REPLAY', c.context_sha256)


@pytest.mark.parametrize('scheme', ['single', 'split', 'spread'])
def test_all_cases_live_mode_and_verify_replay_exact(scheme):
    for _, case in catalog_v0():
        f = plan_v1a(case, scheme)
        t = TransportPlanV1a(2)
        p = uniform_causal_service_plan_v1b(f, pe_slots=128,
                                              fabric_slots_per_tick=128)
        m = uniform_causal_memory_plan_v1c(f)
        l = CausalLinkPlanV1d(1, 1, 128, 4096)
        c = ModeControllerV1a(context_fingerprint_v1a(case, f, t, p, m, l))
        c.transition('EXECUTE')
        live = c.run(case, f, t, p, m, l)
        c.transition('VERIFY')
        verified = c.run(case, f, t, p, m, l,
                         expected_sha256=live['result_sha256'])
        assert verified['result_sha256'] == live['result_sha256']
        assert verified['boundary'].status == 'QUIESCENT'
