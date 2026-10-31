"""A4d P/S/E/O closed-state capture, reconstructive replay, cold reset denial."""
from dataclasses import replace
import json
import pytest

from search.spk_24n_differential_evidence_v0 import canonical, sha
from search.spk_24o_semantic_corpus_v0 import catalog_v0
from search.spk_arch_a4c_candidate_conformance_v1c import args_v1c
from spk_architecture_v1.operating_modes_v1a import ModeControllerV1a,context_fingerprint_v1a
from spk_architecture_v1.candidate_promotion_v1c import (
    CandidateRegistryV1c, describe_candidate_v1c,
)
from spk_architecture_v1.state_custody_v1d import (
    StateCustodyV1d,StateCustodyDeniedV1d, verify_checkpoint_v1d,
)

CATALOG=catalog_v0()


def setup(index=13, scheme='spread'):
    cid, case=CATALOG[index]
    args=args_v1c(case,scheme)
    context=context_fingerprint_v1a(*args)
    reg=CandidateRegistryV1c(context)
    ctrl=ModeControllerV1a(context)
    ctrl.transition('EXECUTE')
    run=ctrl.run(*args)
    keeper=StateCustodyV1d(reg)
    snapshot=keeper.capture(ctrl,run,args)
    return keeper,snapshot,ctrl,run,args


def promote(index=13, scheme='spread'):
    keeper,cp,ctrl,run,args=setup(index,scheme)
    old=CATALOG[index]
    target=CATALOG[(index+36)%216]
    target_args=args_v1c(target[1],scheme)
    reg=keeper.registry
    producer=ModeControllerV1a(cp.context_sha256)
    producer.transition('TRAINING' if index%2==0 else 'REMODEL')
    manifest=sha('test-candidate-manifest:'+target[0])
    desc=describe_candidate_v1c(target[0],sha('fixed-source-catalog'),manifest,target_args)
    reg.stage(producer,desc)
    verified=reg.verify(ModeControllerV1a(desc.context_sha256),target_args,
                        trusted_ideal_witness={'source_sha256':sha('fixed-source-catalog'),
                                               'manifest_sha256':manifest,
                                               'ideal_result_sha256':sha('separate-ideal-test-witness')})
    approval=reg.approve('local-test-operator',verified,expected_revision=0)
    receipt=reg.promote(producer,verified,approval)
    return keeper,cp,args,target_args,receipt,verified


def test_corpus_648_closed_checkpoints_replay_entire_output():
    total=0
    for _,case in CATALOG:
        for scheme in ('single','split','spread'):
            args=args_v1c(case,scheme)
            context=context_fingerprint_v1a(*args)
            ctrl=ModeControllerV1a(context)
            ctrl.transition('EXECUTE')
            live=ctrl.run(*args)
            keeper=StateCustodyV1d(CandidateRegistryV1c(context))
            cp=keeper.capture(ctrl,live,args)
            assert verify_checkpoint_v1d(cp,args)==live['output']
            recovered=keeper.recover_by_replay(args)
            assert recovered.replay_result_sha256==live['result_sha256']
            assert recovered.method=='REPLAY_FROM_INITIAL_INPUTS'
            total+=1
    assert total==648


def test_capture_is_immutable_after_caller_mutates_run_output():
    keeper,cp,ctrl,run,args=setup()
    ref=cp.output_document
    run['output']['result']['states'][0]['raw']+=1
    assert verify_checkpoint_v1d(cp,args)['result']['states'][0]['raw']!=run['output']['result']['states'][0]['raw']
    assert cp.output_document==ref
    assert keeper.recover_by_replay(args).checkpoint_sha256==cp.checkpoint_sha256


def test_snapshot_tamper_and_recomputed_outer_digest_still_rejected_by_full_replay():
    keeper,cp,_,_,args=setup()
    modified=json.loads(cp.output_document)
    modified['result']['states'][0]['raw'] = (modified['result']['states'][0]['raw']+1) % 256
    with pytest.raises(StateCustodyDeniedV1d):
        verify_checkpoint_v1d(replace(cp,output_document=canonical(modified)),args)
    from spk_architecture_v1 import state_custody_v1d as mod
    fields={k:getattr(cp,k) for k in mod.CheckpointV1d.__dataclass_fields__ if k!='checkpoint_sha256'}
    fields['output_document']=canonical(modified)
    fields['result_sha256']=sha(fields['output_document'])
    fields['states_sha256']=mod._hash(sorted(mod.strict_json(fields['output_document'])['result']['states'], key=lambda x:x['node_id']))
    forged=mod.CheckpointV1d(**fields,checkpoint_sha256=mod._hash(fields))
    # Even a fully recomputed checksum cannot forge the independently executed source.
    keeper.checkpoint=forged
    with pytest.raises(StateCustodyDeniedV1d,match='replay does not reproduce'):
        keeper.recover_by_replay(args)


def test_capture_denies_nonquiescent_and_verifier_mode():
    keeper,cp,ctrl,run,args=setup()
    other=StateCustodyV1d(keeper.registry)
    ctrl.transition('VERIFY')
    with pytest.raises(StateCustodyDeniedV1d):
        other.capture(ctrl,run,args)
    ctrl.transition('EXECUTE')
    ctrl.status='ACTIVE'
    with pytest.raises(StateCustodyDeniedV1d):
        other.capture(ctrl,run,args)


def test_capture_denies_nonempty_link_or_state_trace():
    keeper,cp,ctrl,run,args=setup()
    other=StateCustodyV1d(keeper.registry)
    tampered=dict(run)
    tampered['output']=json.loads(cp.output_document)
    tampered['output']['transport']['outstanding_outbox_occurrences']=1
    with pytest.raises(StateCustodyDeniedV1d):
        other.capture(ctrl,tampered,args)


def test_capture_denies_revision_and_changed_inputs():
    keeper,cp,ctrl,run,args=setup()
    other=StateCustodyV1d(keeper.registry)
    keeper.registry.revision+=1
    with pytest.raises(StateCustodyDeniedV1d):
        other.capture(ModeControllerV1a(cp.context_sha256),run,args)
    with pytest.raises(StateCustodyDeniedV1d):
        keeper.recover_by_replay(args)
    with pytest.raises(StateCustodyDeniedV1d):
        verify_checkpoint_v1d(cp,args_v1c(CATALOG[1][1],'spread'))


def test_duplicate_capture_is_denied():
    keeper,cp,ctrl,run,args=setup()
    with pytest.raises(StateCustodyDeniedV1d):
        keeper.capture(ctrl,run,args)


def test_restore_denies_divergent_result_even_when_state_digest_looks_valid(monkeypatch):
    keeper,cp,ctrl,run,args=setup()
    from spk_architecture_v1 import operating_modes_v1a as mod
    original=mod.execute_causal_transport_v1d
    def wrong(*params):
        r=original(*params)
        r['service']['fabric_stall_incidents'] += 1
        return r
    monkeypatch.setattr(mod,'execute_causal_transport_v1d',wrong)
    with pytest.raises(StateCustodyDeniedV1d,match='replay does not reproduce'):
        keeper.recover_by_replay(args)


def test_exact_changed_candidate_cold_reset_and_stale_snapshot_rejection():
    keeper,cp,args,target,receipt,verified=promote()
    with pytest.raises(StateCustodyDeniedV1d,match='stale checkpoint'):
        keeper.recover_by_replay(args)
    a=keeper.activate_cold(receipt,args,target,policy='COLD_RESET')
    assert a.policy=='COLD_RESET' and a.revision==1
    assert a.result_sha256==verified.execution_sha256
    assert cp.context_sha256!=a.to_context_sha256
    assert cp.states_sha256!='' and cp.event_custody_sha256!=''


def test_altered_promotion_cannot_activate_and_retains_pending_authority():
    keeper,cp,args,target,receipt,verified=promote()
    with pytest.raises(StateCustodyDeniedV1d):
        keeper.activate_cold(replace(receipt,revision_after=2),args,target,policy='COLD_RESET')
    assert keeper.activation is None
    assert keeper.activate_cold(receipt,args,target,policy='COLD_RESET').revision==1


def test_state_migration_hot_activation_and_rollback_are_denied():
    keeper,cp,args,target,receipt,verified=promote()
    for policy in ('MIGRATE_STATE', 'HOT_SWAP', 'ROLLBACK', 'VERIFY', None):
        with pytest.raises(StateCustodyDeniedV1d):
            keeper.activate_cold(receipt,args,target,policy=policy)
    assert keeper.activation is None


def test_cold_activation_denies_wrong_target_and_source():
    keeper,cp,args,target,receipt,verified=promote()
    wrong=args_v1c(CATALOG[0][1],'spread')
    with pytest.raises(StateCustodyDeniedV1d):
        keeper.activate_cold(receipt,args,wrong,policy='COLD_RESET')
    with pytest.raises(StateCustodyDeniedV1d):
        keeper.activate_cold(receipt,wrong,target,policy='COLD_RESET')


def test_activation_is_one_shot_with_no_implicit_restart():
    keeper,cp,args,target,receipt,verified=promote()
    keeper.activate_cold(receipt,args,target,policy='COLD_RESET')
    with pytest.raises(StateCustodyDeniedV1d):
        keeper.activate_cold(receipt,args,target,policy='COLD_RESET')


def test_program_profile_changed_before_only_cold_reset():
    total=0
    for i in range(0,216,6):
        keeper,cp,args,target,receipt,verified=promote(i,'split')
        assert keeper.activate_cold(receipt,args,target,policy='COLD_RESET').result_sha256==verified.execution_sha256
        total+=1
    assert total==36


def test_forged_quiescence_indicators_do_not_enable_capture():
    keeper,cp,ctrl,run,args=setup()
    different=StateCustodyV1d(keeper.registry)
    fake=dict(run)
    fake['result_sha256']='f'*64
    with pytest.raises(StateCustodyDeniedV1d):
        different.capture(ctrl,fake,args)
