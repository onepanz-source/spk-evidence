"""Independent A4b mode/epoch capabilities and post-run logical service."""
from dataclasses import replace
import pytest

from search.spk_24o_semantic_corpus_v0 import catalog_v0
from spk_architecture_v1.pe_fabric_v1a import plan_v1a
from spk_architecture_v1.pe_service_v1c import uniform_service_plan_v1c
from spk_architecture_v1.pe_fault_v1d import execute_failstop_v1d
from spk_architecture_v1.memory_projection_v1a import (
    uniform_memory_plan_v1a, admit_memory_v1a, project_execution_memory_v1a,
)
from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
from spk_architecture_v1.temporal_service_v1b import uniform_causal_service_plan_v1b
from spk_architecture_v1.causal_memory_v1c import uniform_causal_memory_plan_v1c
from spk_architecture_v1.causal_transport_v1d import CausalLinkPlanV1d
from spk_architecture_v1.operating_modes_v1a import (
    ModeControllerV1a, context_fingerprint_v1a,
)
from spk_architecture_v1.mode_memory_v1b import (
    ModeMemoryDeniedV1b, ModeMemoryPermitV1b, issue_mode_memory_permit_v1b,
    serve_mode_memory_v1b,
)
from spk_architecture_v1.memory_service_v1c import MemoryServiceExhaustedV1c


def setup(case=None, scheme='spread'):
    if case is None:
        case = next(c for ident, c in catalog_v0()
                    if ident == 'relays/parallel/at_zero')
    f = plan_v1a(case, scheme)
    ps = uniform_service_plan_v1c(f, pe_slots=4096, fabric_slots_per_tick=4096)
    a = admit_memory_v1a(case, f, ps, uniform_memory_plan_v1a(f))
    outcome = execute_failstop_v1d(case, f, ps)
    proj = project_execution_memory_v1a(case, f, a, outcome)
    t = TransportPlanV1a(2)
    p = uniform_causal_service_plan_v1b(f, pe_slots=128, fabric_slots_per_tick=128)
    m = uniform_causal_memory_plan_v1c(f)
    l = CausalLinkPlanV1d(1, 1, 128, 4096)
    args = (case, f, t, p, m, l)
    c = ModeControllerV1a(context_fingerprint_v1a(*args))
    return c, args, a, proj


def completed(c, args, mode):
    if mode == 'EXECUTE':
        c.transition('EXECUTE')
        return c.run(*args)
    if c.mode != 'VERIFY':
        c.transition('VERIFY')
    # VERIFY replay must be compared to an independent pinned actual RUN.
    raise AssertionError('VERIFY needs a prior EXECUTE run')


def test_execute_and_verify_policies_do_not_promote_candidates():
    c, args, a, proj = setup()
    live = completed(c, args, 'EXECUTE')
    grant = issue_mode_memory_permit_v1b(c, a, proj)
    served = serve_mode_memory_v1b(c, grant, a, proj)
    assert served['scope'] == 'EXECUTION_LEDGER'
    assert served['priority_order'] == ['E', 'S', 'P', 'O']
    assert served['service']['execution_status'] == 'CLOSED'
    c.transition('VERIFY')
    replay = c.run(*args, expected_sha256=live['result_sha256'])
    assert replay['result_sha256'] == live['result_sha256']
    verify_grant = issue_mode_memory_permit_v1b(c, a, proj)
    verify_served = serve_mode_memory_v1b(c, verify_grant, a, proj)
    assert verify_served['scope'] == 'ISOLATED_REPLAY_LEDGER'
    assert verify_served['priority_order'] == ['P', 'S', 'E', 'O']
    assert verify_served['service']['logical_units'] == served['service']['logical_units']
    assert verify_grant.request_sha256 == grant.request_sha256
    assert verify_grant.authority_sha256 == grant.authority_sha256
    assert verify_grant != grant
    assert c.status == 'QUIESCENT'
    assert all(x['kind'] != 'STAGE' for x in c.audit)


def test_training_and_remodel_can_stage_but_never_get_memory_service():
    c, args, a, proj = setup()
    for mode in ('TRAINING', 'REMODEL'):
        if c.mode != 'VERIFY':
            c.transition('VERIFY')
        c.transition(mode)
        assert c.stage('a' * 64).status == 'QUIESCENT'
        with pytest.raises(ModeMemoryDeniedV1b, match='stage candidates'):
            issue_mode_memory_permit_v1b(c, a, proj)


def test_no_grant_before_completed_run_or_during_lease():
    c, args, a, proj = setup()
    with pytest.raises(ModeMemoryDeniedV1b, match='completed'):
        issue_mode_memory_permit_v1b(c, a, proj)
    c.transition('EXECUTE')
    lease = c._start('RUN', c.context_sha256)
    with pytest.raises(ModeMemoryDeniedV1b, match='quiescent'):
        issue_mode_memory_permit_v1b(c, a, proj)
    c._fault()
    with pytest.raises(ModeMemoryDeniedV1b, match='quiescent'):
        issue_mode_memory_permit_v1b(c, a, proj)
    assert lease == 1


def test_stale_grant_revoked_on_mode_transition():
    c, args, a, proj = setup()
    completed(c, args, 'EXECUTE')
    grant = issue_mode_memory_permit_v1b(c, a, proj)
    c.transition('VERIFY')
    with pytest.raises(ModeMemoryDeniedV1b):
        serve_mode_memory_v1b(c, grant, a, proj)


def test_stale_grant_revoked_on_new_completed_action_same_epoch():
    c, args, a, proj = setup()
    completed(c, args, 'EXECUTE')
    grant = issue_mode_memory_permit_v1b(c, a, proj)
    c.run(*args)
    with pytest.raises(ModeMemoryDeniedV1b, match='stale'):
        serve_mode_memory_v1b(c, grant, a, proj)


@pytest.mark.parametrize('field,value', [
    ('mode', 'REMODEL'), ('epoch', -1), ('context_sha256', 'x'*64),
    ('scope', 'EXECUTION_LEDGER_UNRESTRICTED'),
    ('priority_order', ('O','E','S','P')),
    ('authority_sha256', 'f'*64), ('projection_sha256', 'e'*64),
    ('request_sha256', '0'*64),
])
def test_altered_grant_is_denied(field, value):
    c, args, a, proj = setup()
    completed(c, args, 'EXECUTE')
    grant = issue_mode_memory_permit_v1b(c, a, proj)
    assert type(grant) is ModeMemoryPermitV1b
    with pytest.raises(ModeMemoryDeniedV1b, match='stale'):
        serve_mode_memory_v1b(c, replace(grant, **{field:value}), a, proj)


def test_changed_projection_and_admission_rejected():
    c, args, a, proj = setup()
    completed(c, args, 'EXECUTE')
    grant = issue_mode_memory_permit_v1b(c, a, proj)
    modified = dict(proj)
    modified['limitations'] = ['forged']
    with pytest.raises(ModeMemoryDeniedV1b, match='stale'):
        serve_mode_memory_v1b(c, grant, a, modified)
    changed_admission = dict(a)
    changed_admission['max_batches'] += 1
    with pytest.raises(ModeMemoryDeniedV1b, match='stale'):
        serve_mode_memory_v1b(c, grant, changed_admission, proj)


def test_low_service_tick_budget_has_no_succeeded_verdict():
    c, args, a, proj = setup()
    completed(c, args, 'EXECUTE')
    grant = issue_mode_memory_permit_v1b(c, a, proj)
    with pytest.raises(MemoryServiceExhaustedV1c):
        serve_mode_memory_v1b(c, grant, a, proj,
                              pe_slots=1, fabric_slots_per_tick=1,
                              domain_slots_per_tick=1, max_service_ticks=1)


@pytest.mark.parametrize('scheme', ('single', 'split', 'spread'))
def test_all_216_networks_two_mode_profiles_conserve_logical_units(scheme):
    for _, case in catalog_v0():
        c, args, a, proj = setup(case, scheme)
        live = completed(c, args, 'EXECUTE')
        e = issue_mode_memory_permit_v1b(c, a, proj)
        er = serve_mode_memory_v1b(c, e, a, proj)
        c.transition('VERIFY')
        c.run(*args, expected_sha256=live['result_sha256'])
        v = issue_mode_memory_permit_v1b(c, a, proj)
        vr = serve_mode_memory_v1b(c, v, a, proj)
        assert vr['service']['logical_units'] == er['service']['logical_units']
        assert vr['service']['request_count'] == er['service']['request_count']
        assert vr['priority_order'] != er['priority_order']
        assert vr['service']['status'] == er['service']['status'] == 'SERVED'
        assert c.status == 'QUIESCENT'
