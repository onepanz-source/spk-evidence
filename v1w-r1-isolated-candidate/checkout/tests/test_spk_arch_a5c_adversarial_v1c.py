"""A5c independently exercised adversarial boundaries over the full corpus."""
from dataclasses import replace
import pytest
from search.spk_24o_semantic_corpus_v0 import catalog_v0
from search.spk_arch_a4c_candidate_conformance_v1c import args_v1c
from search.spk_arch_a5a_conformance_v1a import sampled_indices_v1a
from spk_architecture_v1.pe_fabric_v1a import SCHEMES
from spk_architecture_v1.adversarial_boundaries_v1c import (
    adversarial_case_v1c, forged_complete_checkpoint_v1c,
)
from spk_architecture_v1.causal_transport_v1d import CausalLinkHorizonV1d
from spk_architecture_v1.operating_modes_v1a import (
    ModeControllerV1a, OperatingModeDeniedV1a, context_fingerprint_v1a,
)
from spk_architecture_v1.candidate_promotion_v1c import CandidateRegistryV1c
from spk_architecture_v1.state_custody_v1d import (
    StateCustodyV1d, StateCustodyDeniedV1d, verify_checkpoint_v1d,
)

CATALOG=catalog_v0()


@pytest.mark.parametrize('scheme',SCHEMES)
def test_216_adversarial_transcripts_each_placement(scheme):
    rows=[adversarial_case_v1c(cid,c,scheme) for cid,c in CATALOG]
    assert len(rows)==216
    assert len({r['id'] for r in rows})==216
    assert all(r['cross_context_denied'] and r['failed_verify_faulted'] for r in rows)


def test_108_stratified_independently_replayed_forged_snapshots():
    indices=sampled_indices_v1a()
    rows=[adversarial_case_v1c(CATALOG[i][0],CATALOG[i][1],scheme,deep=True)
          for i in indices for scheme in SCHEMES]
    assert len(rows)==108 and all(r['deep_checkpoint_sha256'] for r in rows)


def test_failed_runtime_horizon_faults_controller_before_any_checkpoint():
    cid,case=dict(CATALOG).get('relays/chain/separated') and (
        'relays/chain/separated',dict(CATALOG)['relays/chain/separated']) or CATALOG[0]
    args=args_v1c(case,'spread')
    too_short= args[:-1]+(replace(args[-1],max_link_span_ticks=1),)
    ctx=context_fingerprint_v1a(*too_short)
    ctrl=ModeControllerV1a(ctx)
    ctrl.transition('EXECUTE')
    with pytest.raises(CausalLinkHorizonV1d):
        ctrl.run(*too_short)
    assert ctrl.status=='FAULTED'
    keeper=StateCustodyV1d(CandidateRegistryV1c(ctx))
    with pytest.raises(StateCustodyDeniedV1d):
        keeper.capture(ctrl,{'mode':'EXECUTE'},too_short)
    with pytest.raises(OperatingModeDeniedV1a):
        ctrl.transition('VERIFY')


def test_forged_complete_checkpoint_is_structurally_valid_but_not_recoverable():
    cid,case=CATALOG[26]
    args=args_v1c(case,'split')
    ctx=context_fingerprint_v1a(*args)
    ctrl=ModeControllerV1a(ctx)
    ctrl.transition('EXECUTE')
    run=ctrl.run(*args)
    keeper=StateCustodyV1d(CandidateRegistryV1c(ctx))
    cp=keeper.capture(ctrl,run,args)
    forged=forged_complete_checkpoint_v1c(cp,args)
    verify_checkpoint_v1d(forged,args)
    keeper.checkpoint=forged
    with pytest.raises(StateCustodyDeniedV1d,match='replay does not reproduce'):
        keeper.recover_by_replay(args)


def test_bad_incomplete_checkpoint_never_accepted():
    cid,case=CATALOG[0]
    args=args_v1c(case,'single')
    ctrl=ModeControllerV1a(context_fingerprint_v1a(*args))
    ctrl.transition('EXECUTE')
    run=ctrl.run(*args)
    keeper=StateCustodyV1d(CandidateRegistryV1c(ctrl.context_sha256))
    forged=dict(run)
    forged['output']=dict(run['output'])
    forged['output']['transport']=dict(run['output']['transport'])
    forged['output']['transport']['remaining_inflight_occurrences']=1
    with pytest.raises(StateCustodyDeniedV1d):
        keeper.capture(ctrl,forged,args)
