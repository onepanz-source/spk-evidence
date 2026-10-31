"""A4c trusted cold candidate promotion, separately witnessed verification.

A candidate has real immutable source data and a bound execution context.  A4a
TRAINING/REMODEL stage its digest, but cannot install it.  A separate A4a
EXECUTE->VERIFY replay proves deterministic A3d execution. A caller-supplied
trusted frozen-Compiler witness pins ideal semantics; this module does not
silently treat two self-replays as an independent Compiler oracle.

Promotion changes a *logical active context pointer* only, with an explicit
operator approval and version CAS. No live neuron memory migration, training,
rollback, process security or durable atomic filesystem update is implemented.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass, is_dataclass
import re

from search.spk_24n_differential_evidence_v0 import canonical, sha
from spk_architecture_v1.operating_modes_v1a import (
    ModeControllerV1a, context_fingerprint_v1a,
)

SCHEMA = 'spk-architecture-candidate-promotion/v1c'
HEX = re.compile(r'[0-9a-f]{64}\Z')


class CandidatePromotionDeniedV1c(ValueError):
    pass


def _hex(value):
    return type(value) is str and HEX.fullmatch(value) is not None


def _hash(x):
    return sha(canonical(x))


@dataclass(frozen=True)
class CandidateDescriptorV1c:
    source_id: str
    source_sha256: str
    context_sha256: str
    manifest_sha256: str
    input_sha256: str


@dataclass(frozen=True)
class StageReceiptV1c:
    candidate_sha256: str
    producer_mode: str
    producer_epoch: int
    producer_audit_sha256: str
    from_context_sha256: str
    from_revision: int
    stage_sha256: str


@dataclass(frozen=True)
class VerificationReceiptV1c:
    stage_sha256: str
    candidate_sha256: str
    context_sha256: str
    manifest_sha256: str
    frozen_ideal_sha256: str
    execution_sha256: str
    replay_sha256: str
    verifier_audit_sha256: str
    verification_sha256: str


@dataclass(frozen=True)
class ApprovalV1c:
    verification_sha256: str
    operator_id: str
    expected_revision: int
    approval_sha256: str


@dataclass(frozen=True)
class PromotionReceiptV1c:
    from_context_sha256: str
    to_context_sha256: str
    revision_before: int
    revision_after: int
    candidate_sha256: str
    verification_sha256: str
    approval_sha256: str
    promotion_sha256: str


def describe_candidate_v1c(source_id, source_sha256, manifest_sha256, args):
    if (type(source_id) is not str or not source_id or len(source_id) > 200
            or not _hex(source_sha256) or not _hex(manifest_sha256)
            or type(args) is not tuple or len(args) != 6
            or any(not is_dataclass(item) or isinstance(item, type) for item in args)):
        raise CandidatePromotionDeniedV1c('invalid candidate source or context')
    return CandidateDescriptorV1c(
        source_id, source_sha256, context_fingerprint_v1a(*args),
        manifest_sha256, _hash([asdict(x) for x in args]))


def candidate_digest_v1c(descriptor):
    if type(descriptor) is not CandidateDescriptorV1c:
        raise CandidatePromotionDeniedV1c('invalid candidate descriptor')
    return _hash({'schema': SCHEMA, 'candidate': asdict(descriptor)})


class CandidateRegistryV1c:
    """In-memory trusted authority with one outstanding cold-start proposal."""
    def __init__(self, active_context_sha256, *, revision=0):
        if not _hex(active_context_sha256) or type(revision) is not int or revision < 0:
            raise CandidatePromotionDeniedV1c('invalid registry state')
        self.active_context_sha256 = active_context_sha256
        self.revision = revision
        self.stage_receipt = None
        self.descriptor = None
        self.verification = None
        self.approval = None
        self.history = []

    def stage(self, producer, descriptor):
        if (type(producer) is not ModeControllerV1a
                or type(descriptor) is not CandidateDescriptorV1c
                or producer.status != 'QUIESCENT'
                or producer.mode not in ('TRAINING', 'REMODEL')
                or producer.context_sha256 != self.active_context_sha256
                or descriptor.context_sha256 == self.active_context_sha256
                or not all(_hex(x) for x in (
                    descriptor.source_sha256, descriptor.context_sha256,
                    descriptor.manifest_sha256, descriptor.input_sha256))
                or self.stage_receipt is not None):
            raise CandidatePromotionDeniedV1c('unqualified or overlapping candidate staging')
        fingerprint = candidate_digest_v1c(descriptor)
        boundary = producer.stage(fingerprint)
        fields = dict(candidate_sha256=fingerprint, producer_mode=boundary.mode,
                      producer_epoch=boundary.epoch,
                      producer_audit_sha256=boundary.audit_sha256,
                      from_context_sha256=self.active_context_sha256,
                      from_revision=self.revision)
        receipt = StageReceiptV1c(**fields, stage_sha256=_hash(fields))
        self.descriptor = descriptor
        self.stage_receipt = receipt
        return receipt

    def verify(self, verifier, args, *, trusted_ideal_witness):
        """A distinct candidate controller must RUN then REPLAY the candidate.

        trusted_ideal_witness must come from a separately established Compiler /
        independent semantic check. A digest alone does not prove that claim.
        """
        st, desc = self.stage_receipt, self.descriptor
        if (type(verifier) is not ModeControllerV1a or st is None
                or self.verification is not None or self.approval is not None
                or verifier is None or verifier.status != 'QUIESCENT'
                or verifier.mode != 'VERIFY' or verifier.epoch != 0
                or verifier.audit != [] or verifier.context_sha256 != desc.context_sha256
                or type(args) is not tuple or len(args) != 6
                or context_fingerprint_v1a(*args) != desc.context_sha256
                or _hash([asdict(x) for x in args]) != desc.input_sha256
                or type(trusted_ideal_witness) is not dict
                or set(trusted_ideal_witness) != {'source_sha256', 'manifest_sha256', 'ideal_result_sha256'}
                or trusted_ideal_witness['source_sha256'] != desc.source_sha256
                or trusted_ideal_witness['manifest_sha256'] != desc.manifest_sha256
                or not _hex(trusted_ideal_witness['ideal_result_sha256'])
                or st.candidate_sha256 != candidate_digest_v1c(desc)
                or st.from_revision != self.revision
                or st.from_context_sha256 != self.active_context_sha256):
            raise CandidatePromotionDeniedV1c('candidate verification preflight rejected')
        # Intentional separate candidate controller. No active-context mutation.
        verifier.transition('EXECUTE')
        live = verifier.run(*args)
        verifier.transition('VERIFY')
        replay = verifier.run(*args, expected_sha256=live['result_sha256'])
        if (replay['result_sha256'] != live['result_sha256']
                or verifier.status != 'QUIESCENT'
                or verifier.boundary().audit_sha256 != replay['boundary'].audit_sha256):
            raise CandidatePromotionDeniedV1c('candidate replay did not close')
        fields = dict(stage_sha256=st.stage_sha256,
                      candidate_sha256=st.candidate_sha256,
                      context_sha256=desc.context_sha256,
                      manifest_sha256=desc.manifest_sha256,
                      frozen_ideal_sha256=trusted_ideal_witness['ideal_result_sha256'],
                      execution_sha256=live['result_sha256'],
                      replay_sha256=replay['result_sha256'],
                      verifier_audit_sha256=replay['boundary'].audit_sha256)
        receipt = VerificationReceiptV1c(**fields,
                                         verification_sha256=_hash(fields))
        self.verification = receipt
        return receipt

    def approve(self, operator_id, verification, *, expected_revision):
        if (type(operator_id) is not str or not 1 <= len(operator_id) <= 64
                or not operator_id.isascii() or not operator_id.isprintable()
                or type(expected_revision) is not int
                or expected_revision != self.revision
                or type(verification) is not VerificationReceiptV1c
                or verification != self.verification or self.approval is not None):
            raise CandidatePromotionDeniedV1c('explicit operator approval denied')
        fields = dict(verification_sha256=verification.verification_sha256,
                      operator_id=operator_id, expected_revision=self.revision)
        approval = ApprovalV1c(**fields, approval_sha256=_hash(fields))
        self.approval = approval
        return approval

    def promote(self, producer, verification, approval):
        """Atomic in-memory logical pointer switch; no running PE is mutated."""
        if (type(producer) is not ModeControllerV1a
                or producer.status != 'QUIESCENT'
                or producer.mode not in ('TRAINING', 'REMODEL')
                or self.stage_receipt is None or self.descriptor is None
                or self.verification is None or self.approval is None
                or self.stage_receipt.candidate_sha256 != candidate_digest_v1c(self.descriptor)
                or self.verification.candidate_sha256 != self.stage_receipt.candidate_sha256
                or self.verification.context_sha256 != self.descriptor.context_sha256
                or self.verification.manifest_sha256 != self.descriptor.manifest_sha256
                or producer.context_sha256 != self.active_context_sha256
                or producer.boundary().audit_sha256 != self.stage_receipt.producer_audit_sha256
                or producer.epoch != self.stage_receipt.producer_epoch
                or type(verification) is not VerificationReceiptV1c
                or verification != self.verification
                or type(approval) is not ApprovalV1c
                or approval != self.approval
                or approval.verification_sha256 != verification.verification_sha256
                or approval.expected_revision != self.revision
                or self.stage_receipt.from_revision != self.revision
                or self.stage_receipt.from_context_sha256 != self.active_context_sha256):
            raise CandidatePromotionDeniedV1c('promotion authority, custody or revision denied')
        before = self.active_context_sha256
        rev = self.revision
        fields = dict(from_context_sha256=before,
                      to_context_sha256=self.descriptor.context_sha256,
                      revision_before=rev, revision_after=rev + 1,
                      candidate_sha256=self.stage_receipt.candidate_sha256,
                      verification_sha256=verification.verification_sha256,
                      approval_sha256=approval.approval_sha256)
        receipt = PromotionReceiptV1c(**fields, promotion_sha256=_hash(fields))
        self.active_context_sha256 = receipt.to_context_sha256
        self.revision = rev + 1
        self.history.append(receipt)
        self.stage_receipt = self.descriptor = self.verification = self.approval = None
        return receipt

    def cold_start(self, receipt):
        """Return a fresh A4a VERIFY controller, with no migrated state."""
        if (type(receipt) is not PromotionReceiptV1c or not self.history
                or receipt != self.history[-1] or receipt.to_context_sha256 != self.active_context_sha256
                or receipt.revision_after != self.revision):
            raise CandidatePromotionDeniedV1c('cold start is not current promotion')
        return ModeControllerV1a(self.active_context_sha256)
