"""A4c: cold promotion with explicit approval and trusted semantic anchor."""
from dataclasses import replace
import pytest
from search.spk_24n_differential_evidence_v0 import sha
from search.spk_24o_semantic_corpus_v0 import catalog_v0
from spk_architecture_v1.pe_fabric_v1a import plan_v1a
from spk_architecture_v1.temporal_transport_v1a import TransportPlanV1a
from spk_architecture_v1.temporal_service_v1b import uniform_causal_service_plan_v1b
from spk_architecture_v1.causal_memory_v1c import uniform_causal_memory_plan_v1c
from spk_architecture_v1.causal_transport_v1d import CausalLinkPlanV1d
from spk_architecture_v1.operating_modes_v1a import ModeControllerV1a, context_fingerprint_v1a
from spk_architecture_v1.candidate_promotion_v1c import (
    CandidateRegistryV1c, CandidatePromotionDeniedV1c,
    describe_candidate_v1c, candidate_digest_v1c,
)

CATALOG = catalog_v0()
SOURCE = 'cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5'


def args_for(case, scheme='spread'):
    f = plan_v1a(case, scheme)
    return (case, f, TransportPlanV1a(2),
            uniform_causal_service_plan_v1b(f, pe_slots=128, fabric_slots_per_tick=128),
            uniform_causal_memory_plan_v1c(f), CausalLinkPlanV1d(1, 1, 128, 4096))


def setup(i=19, scheme='spread', producer_mode='TRAINING'):
    old_args = args_for(CATALOG[i][1], scheme)
    new_id, new_case = CATALOG[(i + 36) % 216]
    new_args = args_for(new_case, scheme)
    producer = ModeControllerV1a(context_fingerprint_v1a(*old_args))
    producer.transition(producer_mode)
    registry = CandidateRegistryV1c(producer.context_sha256)
    desc = describe_candidate_v1c(new_id, SOURCE, sha('manifest:'+new_id), new_args)
    trusted = {'source_sha256': SOURCE, 'manifest_sha256': desc.manifest_sha256,
               'ideal_result_sha256': sha('independent-host:'+new_id)}
    return producer, registry, desc, new_args, trusted


def staged_and_verified(i=19, scheme='spread', producer_mode='TRAINING'):
    producer, registry, desc, args, trusted = setup(i, scheme, producer_mode)
    stage = registry.stage(producer, desc)
    verifier = ModeControllerV1a(desc.context_sha256)
    verified = registry.verify(verifier, args, trusted_ideal_witness=trusted)
    return producer, registry, desc, args, stage, verified


@pytest.mark.parametrize('producer_mode', ['TRAINING', 'REMODEL'])
def test_trusted_cold_promotion_requires_approval_and_new_controller(producer_mode):
    p, r, d, args, staged, verified = staged_and_verified(producer_mode=producer_mode)
    assert verified.stage_sha256 == staged.stage_sha256
    assert verified.execution_sha256 == verified.replay_sha256
    with pytest.raises(CandidatePromotionDeniedV1c):
        r.promote(p, verified, None)
    approval = r.approve('operator:1', verified, expected_revision=0)
    promotion = r.promote(p, verified, approval)
    assert r.active_context_sha256 == d.context_sha256
    assert r.revision == 1 and len(r.history) == 1
    assert promotion.from_context_sha256 != promotion.to_context_sha256
    cold = r.cold_start(promotion)
    assert cold.mode == 'VERIFY' and cold.status == 'QUIESCENT' and cold.epoch == 0
    cold.transition('EXECUTE')
    assert cold.run(*args)['result_sha256'] == verified.execution_sha256
    with pytest.raises(CandidatePromotionDeniedV1c):
        r.promote(p, verified, approval)


def test_staging_never_switches_active_program():
    p, r, d, args, trusted = setup()
    r.stage(p, d)
    assert r.active_context_sha256 == p.context_sha256
    assert r.revision == 0
    with pytest.raises(CandidatePromotionDeniedV1c):
        r.stage(p, d)


def test_execute_and_verify_cannot_stage_candidate():
    for mode in ('VERIFY', 'EXECUTE'):
        p, r, d, args, trusted = setup()
        if mode == 'VERIFY':
            p.transition('VERIFY')
        else:
            p.transition('VERIFY'); p.transition('EXECUTE')
        with pytest.raises(CandidatePromotionDeniedV1c):
            r.stage(p, d)


def test_noop_candidate_is_rejected():
    p, r, d, args, trusted = setup()
    with pytest.raises(CandidatePromotionDeniedV1c):
        r.stage(p, replace(d, context_sha256=p.context_sha256))


def test_invalid_candidate_inputs_denied():
    p, r, d, args, trusted = setup()
    with pytest.raises(CandidatePromotionDeniedV1c):
        describe_candidate_v1c('candidate', 'garbage', d.manifest_sha256, args)
    with pytest.raises(CandidatePromotionDeniedV1c):
        describe_candidate_v1c(d.source_id, SOURCE, d.manifest_sha256, args[:-1])
    with pytest.raises(CandidatePromotionDeniedV1c):
        candidate_digest_v1c({'fake':'candidate'})


def test_verification_requires_fresh_independent_candidate_controller():
    p, r, d, args, trusted = setup()
    r.stage(p, d)
    with pytest.raises(CandidatePromotionDeniedV1c):
        r.verify(p, args, trusted_ideal_witness=trusted)
    changed = list(args)
    changed[2] = TransportPlanV1a(3)
    with pytest.raises(CandidatePromotionDeniedV1c):
        r.verify(ModeControllerV1a(d.context_sha256), tuple(changed), trusted_ideal_witness=trusted)


@pytest.mark.parametrize('key', ['source_sha256','manifest_sha256','ideal_result_sha256'])
def test_corrupted_compiler_source_and_witness_denied(key):
    p, r, d, args, trusted = setup()
    r.stage(p, d)
    corrupted = dict(trusted)
    corrupted[key] = 'oops' if key == 'ideal_result_sha256' else 'f' * 64
    with pytest.raises(CandidatePromotionDeniedV1c):
        r.verify(ModeControllerV1a(d.context_sha256), args, trusted_ideal_witness=corrupted)
    assert r.verification is None and r.active_context_sha256 == p.context_sha256


def test_replay_failure_does_not_issue_verification(monkeypatch):
    p, r, d, args, trusted = setup()
    r.stage(p, d)
    verifier = ModeControllerV1a(d.context_sha256)
    real_run = verifier.run
    calls = []
    def fail_second(*a, **kw):
        calls.append(1)
        if len(calls) == 2:
            raise RuntimeError('replay unavailable')
        return real_run(*a, **kw)
    monkeypatch.setattr(verifier, 'run', fail_second)
    with pytest.raises(RuntimeError, match='unavailable'):
        r.verify(verifier, args, trusted_ideal_witness=trusted)
    assert verifier.status == 'QUIESCENT' or verifier.status == 'FAULTED'
    assert r.verification is None and r.active_context_sha256 == p.context_sha256


def test_unapproved_or_wrong_version_cannot_promote():
    p, r, d, args, stage, verified = staged_and_verified()
    with pytest.raises(CandidatePromotionDeniedV1c):
        r.approve('operator', verified, expected_revision=1)
    approval = r.approve('operator', verified, expected_revision=0)
    with pytest.raises(CandidatePromotionDeniedV1c):
        r.promote(p, verified, replace(approval, expected_revision=1))
    with pytest.raises(CandidatePromotionDeniedV1c):
        r.approve('operator', verified, expected_revision=0)
    assert r.revision == 0


def test_producer_epoch_audit_and_busy_status_must_be_unchanged():
    p, r, d, args, stage, verified = staged_and_verified()
    approval = r.approve('operator', verified, expected_revision=0)
    p.transition('VERIFY')
    with pytest.raises(CandidatePromotionDeniedV1c):
        r.promote(p, verified, approval)
    assert r.revision == 0


def test_replacement_without_approved_descriptor_denied():
    p, r, d, args, stage, verified = staged_and_verified()
    approval = r.approve('operator', verified, expected_revision=0)
    r.descriptor = replace(d, manifest_sha256='f'*64)
    # Even if trusted host mutates registry internals, a production security
    # boundary would be separate. The logical algorithm must reject drift.
    with pytest.raises(CandidatePromotionDeniedV1c):
        r.promote(p, verified, approval)


def test_cold_start_refuses_stale_promotion_receipt():
    p, r, d, args, stage, verified = staged_and_verified()
    approval = r.approve('operator', verified, expected_revision=0)
    receipt = r.promote(p, verified, approval)
    with pytest.raises(CandidatePromotionDeniedV1c):
        r.cold_start(replace(receipt, revision_after=100))


def test_all_216_cases_three_placements_have_cold_replay_without_mutating_active():
    changed = 0
    for i in range(216):
        for scheme in ('single', 'split', 'spread'):
            p, r, d, args, staged, verified = staged_and_verified(i, scheme)
            assert r.active_context_sha256 != d.context_sha256
            assert p.mode == 'TRAINING' and p.status == 'QUIESCENT'
            assert verified.execution_sha256 == verified.replay_sha256
            changed += 1
    assert changed == 648
