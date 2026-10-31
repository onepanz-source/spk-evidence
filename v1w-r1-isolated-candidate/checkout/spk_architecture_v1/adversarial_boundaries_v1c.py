"""A5c: adversarial witnesses of existing logical trust and failure boundaries.

No security boundary against hostile Python code is claimed. All fault tests
operate against the actual A3d/A4a/A4d reference, not an abstract dummy.
"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict, replace

from search.spk_24n_differential_evidence_v0 import canonical, sha
from spk_architecture_v1.causal_transport_v1d import execute_causal_transport_v1d
from spk_architecture_v1.candidate_promotion_v1c import CandidateRegistryV1c
from spk_architecture_v1.metamorphic_v1b import alpha_rename_v1b
from spk_architecture_v1.operating_modes_v1a import (
    ModeControllerV1a, OperatingModeDeniedV1a, context_fingerprint_v1a,
    result_digest_v1a,
)
from spk_architecture_v1.state_custody_v1d import (
    CheckpointV1d, StateCustodyV1d, StateCustodyDeniedV1d,
    verify_checkpoint_v1d, _hash, _images,
)
from search.spk_arch_a5b_conformance_v1b import conservation_v1b


class BoundaryAssertionV1c(AssertionError):
    pass


def _must_reject(action, expected, label):
    try:
        action()
    except expected:
        return
    raise BoundaryAssertionV1c('A5c admitted forbidden ' + label)


def forged_complete_checkpoint_v1c(cp, args):
    """Forge *all* unkeyed digests, not just the outer checkpoint digest.

    This remains a syntactically sound logical snapshot, but cannot replace
    an independently executed, trusted original replay transcript.
    """
    if type(cp) is not CheckpointV1d:
        raise BoundaryAssertionV1c('checkpoint expected')
    from search.spk_24n_differential_evidence_v0 import strict_json
    modified = strict_json(cp.output_document)
    modified['service']['fabric_stall_incidents'] += 1
    doc = canonical(modified)
    program, state, event, observation = _images(args, modified)
    fields = asdict(cp)
    del fields['checkpoint_sha256']
    fields.update(output_document=doc, result_sha256=result_digest_v1a(modified),
                  program_sha256=program, states_sha256=state,
                  event_custody_sha256=event, observations_sha256=observation)
    forged = CheckpointV1d(**fields, checkpoint_sha256=_hash(fields))
    # The attacker has recomputed all hashes consistently. The only valid
    # independent check now is recomputation of the original execution.
    assert verify_checkpoint_v1d(forged, args) == modified
    return forged


def adversarial_case_v1c(cid, case, scheme, *, deep=False):
    from search.spk_arch_a4c_candidate_conformance_v1c import args_v1c
    args = args_v1c(case, scheme)
    output = execute_causal_transport_v1d(*args)
    baseline_doc = canonical(output)
    remote = conservation_v1b(output, len(case.events))

    # Attack one: alter the transport bookkeeping (or local event balance)
    # without tampering with the original outcome held by its caller.
    forged = deepcopy(output)
    if remote:
        forged['transport']['delivered_cross_pe_occurrences'] -= 1
    else:
        forged['result']['processed_events'] += 1
    _must_reject(lambda: conservation_v1b(forged,len(case.events)),
                 AssertionError, 'event custody')
    if canonical(output) != baseline_doc:
        raise BoundaryAssertionV1c('tamper mutated legitimate output')

    context = context_fingerprint_v1a(*args)
    renamed, _ = alpha_rename_v1b(args)
    controller = ModeControllerV1a(context)
    controller.transition('EXECUTE')
    boundary = controller.boundary()
    _must_reject(lambda: controller.run(*renamed), OperatingModeDeniedV1a,
                 'stale cross-placement authority')
    if controller.status != 'QUIESCENT' or controller.boundary() != boundary:
        raise BoundaryAssertionV1c('pre-grant denial changed controller state')

    # Illegal actions are rejected before a RUN lease is granted.
    staging = ModeControllerV1a(context, initial_mode='TRAINING')
    _must_reject(lambda: staging.run(*args), OperatingModeDeniedV1a,
                 'TRAINING execution')
    if staging.status != 'QUIESCENT' or staging.audit:
        raise BoundaryAssertionV1c('denied staging action mutated authority')

    # A semantically incorrect VERIFY digest is discovered *during* the
    # independent execution, so this controller must fault, not close.
    verifier = ModeControllerV1a(context)
    _must_reject(lambda: verifier.run(*args,expected_sha256='0'*64),
                 OperatingModeDeniedV1a, 'forged replay success')
    if verifier.status != 'FAULTED':
        raise BoundaryAssertionV1c('failed semantic replay did not fault')
    _must_reject(lambda: verifier.transition('EXECUTE'),
                 OperatingModeDeniedV1a, 'reusing faulted epoch')

    checkpoint_hash = None
    if deep:
        owned = ModeControllerV1a(context)
        owned.transition('EXECUTE')
        live = owned.run(*args)
        registry = CandidateRegistryV1c(context)
        keeper = StateCustodyV1d(registry)
        cp = keeper.capture(owned,live,args)
        if keeper.recover_by_replay(args).replay_result_sha256 != live['result_sha256']:
            raise BoundaryAssertionV1c('legitimate replay diverged')
        attack = forged_complete_checkpoint_v1c(cp,args)
        keeper.checkpoint = attack
        _must_reject(lambda: keeper.recover_by_replay(args),
                     StateCustodyDeniedV1d, 'fully rehashed counterfeit recovery')
        keeper.checkpoint = cp
        _must_reject(lambda: keeper.capture(verifier,live,args),
                     StateCustodyDeniedV1d, 'faulted controller checkpoint')
        checkpoint_hash=cp.checkpoint_sha256
    return {'id':cid, 'scheme':scheme,
            'baseline_sha256':sha(baseline_doc),
            'remote_occurrences':remote,
            'cross_context_denied':True,
            'staging_execution_denied':True,
            'failed_verify_faulted':True,
            'forged_custody_denied':True,
            'deep_checkpoint_sha256':checkpoint_hash}
