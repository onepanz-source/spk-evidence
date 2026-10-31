"""A4d quiescent state custody and explicitly cold activation.

A closed A3d execution is captured as immutable canonical JSON, pinned to a
trusted A4a RUN boundary and to an A4c active-context revision. Same-context
recovery *reexecutes* the original inputs and verifies the entire output;
there is no A3d continuation API. After a changed-program A4c promotion,
only a fresh, initial-state candidate controller may activate; S/E/O state
migration, hot swap, implicit rollback and durable crash recovery are denied.
"""
from __future__ import annotations
from dataclasses import dataclass

from search.spk_24n_differential_evidence_v0 import canonical, sha, strict_json
from spk_architecture_v1.operating_modes_v1a import (
    ModeControllerV1a, context_fingerprint_v1a, result_digest_v1a,
)
from spk_architecture_v1.candidate_promotion_v1c import (
    CandidateRegistryV1c, PromotionReceiptV1c,
)

SCHEMA = 'spk-architecture-state-custody/v1d'


class StateCustodyDeniedV1d(ValueError):
    pass


@dataclass(frozen=True)
class CheckpointV1d:
    context_sha256: str
    revision: int
    mode_epoch: int
    boundary_sha256: str
    result_sha256: str
    source_inputs_sha256: str
    program_sha256: str
    states_sha256: str
    event_custody_sha256: str
    observations_sha256: str
    output_document: str
    checkpoint_sha256: str


@dataclass(frozen=True)
class RecoveryReceiptV1d:
    context_sha256: str
    revision: int
    checkpoint_sha256: str
    replay_result_sha256: str
    replay_boundary_sha256: str
    method: str
    recovery_sha256: str


@dataclass(frozen=True)
class ActivationReceiptV1d:
    checkpoint_sha256: str
    promotion_sha256: str
    from_context_sha256: str
    to_context_sha256: str
    revision: int
    result_sha256: str
    activation_boundary_sha256: str
    policy: str
    activation_sha256: str


def _hash(item):
    return sha(canonical(item))


def _inputs(args):
    if type(args) is not tuple or len(args) != 6:
        raise StateCustodyDeniedV1d('expected exact six-part context')
    try:
        fingerprint = context_fingerprint_v1a(*args)
    except Exception as exc:
        raise StateCustodyDeniedV1d('invalid execution context') from exc
    return fingerprint, _hash([repr(type(a)) + ':' + canonical(__import__('dataclasses').asdict(a)) for a in args])


def _images(args, output):
    case = args[0]
    if type(output) is not dict or output.get('schema') != 'spk-architecture-causal-transport-backpressure/v1d':
        raise StateCustodyDeniedV1d('invalid bounded causal output')
    result = output.get('result')
    transport = output.get('transport')
    if type(result) is not dict or type(transport) is not dict:
        raise StateCustodyDeniedV1d('missing execution custody')
    nodes = case.nodes
    states = result.get('states')
    if (type(states) is not list or len(states) != len(nodes)
            or {x['node_id'] for x in states} != {n.node_id for n in nodes}
            or any(type(x.get('raw')) is not int or not 0 <= x['raw'] < (1 << n.state_bits)
                   or type(x.get('last_timestamp')) is not int or x['last_timestamp'] < 0
                   for n in nodes for x in states if x.get('node_id') == n.node_id)
            or transport.get('remaining_inflight_occurrences') != 0
            or transport.get('outstanding_outbox_occurrences') != 0
            or transport.get('cross_pe_occurrences') != transport.get('delivered_cross_pe_occurrences')
            or result.get('processed_events') != len(case.events) + len(result.get('observations', {}).get('routes', []))):
        raise StateCustodyDeniedV1d('unsettled or inconsistent P/S/E/O custody')
    images = (
        _hash([{'node_id':n.node_id, 'instructions':n.instructions,
                'width':n.state_bits,'fractional_bits':n.fractional_bits} for n in nodes]),
        _hash(sorted(states, key=lambda x:x['node_id'])),
        _hash({'external_events': len(case.events), 'consumed_events': result['processed_events'],
               'routed': result['observations']['routes'],
               'transfers': transport['transfers'],
               'deliveries': transport['delivery_log'],
               'inflight_remaining': 0, 'outbox_remaining':0}),
        _hash({'observations': result['observations'],
               'memory': output['memory'], 'service': output['service']}),
    )
    return images


def _checkpoint_fields(cp):
    return {key: getattr(cp, key) for key in CheckpointV1d.__dataclass_fields__
            if key != 'checkpoint_sha256'}


def verify_checkpoint_v1d(checkpoint, args):
    if type(checkpoint) is not CheckpointV1d:
        raise StateCustodyDeniedV1d('invalid checkpoint type')
    context, input_sha = _inputs(args)
    if (checkpoint.context_sha256 != context
            or checkpoint.source_inputs_sha256 != input_sha
            or type(checkpoint.revision) is not int or checkpoint.revision < 0
            or type(checkpoint.mode_epoch) is not int or checkpoint.mode_epoch < 0
            or _hash(_checkpoint_fields(checkpoint)) != checkpoint.checkpoint_sha256):
        raise StateCustodyDeniedV1d('checkpoint integrity or source mismatch')
    try:
        output = strict_json(checkpoint.output_document)
        if canonical(output) != checkpoint.output_document:
            raise ValueError('noncanonical')
        semantic_hash = result_digest_v1a(output)
        program, state, event, observation = _images(args, output)
    except (ValueError, TypeError, KeyError, AssertionError) as exc:
        raise StateCustodyDeniedV1d('invalid state/evidence image') from exc
    if (semantic_hash != checkpoint.result_sha256
            or (program, state, event, observation) != (
                checkpoint.program_sha256, checkpoint.states_sha256,
                checkpoint.event_custody_sha256, checkpoint.observations_sha256)):
        raise StateCustodyDeniedV1d('P/S/E/O image mismatch')
    return output


class StateCustodyV1d:
    """Trusted in-memory authority for one quiescent snapshot and activation.

    No signatures or durable storage. The state cannot be forged by untrusted
    code *relative to the trusted controller*; SHA alone is not authentication.
    """
    def __init__(self, registry):
        if type(registry) is not CandidateRegistryV1c:
            raise StateCustodyDeniedV1d('requires A4c registry authority')
        self.registry = registry
        self.checkpoint = None
        self.activation = None

    def capture(self, controller, run_receipt, args):
        registry = self.registry
        if (self.checkpoint is not None or self.activation is not None
                or type(controller) is not ModeControllerV1a
                or type(run_receipt) is not dict
                or controller.status != 'QUIESCENT' or controller.mode != 'EXECUTE'
                or not controller.audit or controller.audit[-1].get('kind') != 'RUN'
                or registry.stage_receipt is not None):
            raise StateCustodyDeniedV1d('capture requires a settled approved RUN')
        context, inputs = _inputs(args)
        boundary = controller.boundary()
        if (context != registry.active_context_sha256
                or context != controller.context_sha256
                or run_receipt.get('boundary') != boundary
                or run_receipt.get('mode') != 'EXECUTE'
                or run_receipt.get('epoch') != controller.epoch
                or run_receipt.get('result_sha256') != controller.audit[-1]['result_sha256']):
            raise StateCustodyDeniedV1d('RUN boundary or revision provenance mismatch')
        output = run_receipt.get('output')
        program, state, event, observation = _images(args, output)
        digest = result_digest_v1a(output)
        if digest != run_receipt['result_sha256']:
            raise StateCustodyDeniedV1d('output drift from run authority')
        fields = dict(context_sha256=context, revision=registry.revision,
                      mode_epoch=controller.epoch,
                      boundary_sha256=boundary.audit_sha256,
                      result_sha256=digest, source_inputs_sha256=inputs,
                      program_sha256=program, states_sha256=state,
                      event_custody_sha256=event, observations_sha256=observation,
                      output_document=canonical(output))
        cp = CheckpointV1d(**fields, checkpoint_sha256=_hash(fields))
        verify_checkpoint_v1d(cp, args)
        self.checkpoint = cp
        return cp

    def recover_by_replay(self, args):
        cp, registry = self.checkpoint, self.registry
        if (cp is None or self.activation is not None
                or cp.revision != registry.revision
                or cp.context_sha256 != registry.active_context_sha256):
            raise StateCustodyDeniedV1d('stale checkpoint: recovery denied')
        verify_checkpoint_v1d(cp, args)
        controller = ModeControllerV1a(cp.context_sha256)
        controller.transition('EXECUTE')
        replay = controller.run(*args)
        if (replay['result_sha256'] != cp.result_sha256
                or canonical(replay['output']) != cp.output_document):
            raise StateCustodyDeniedV1d('independent P/S/E/O replay does not reproduce checkpoint')
        fields = dict(context_sha256=cp.context_sha256,
                      revision=cp.revision, checkpoint_sha256=cp.checkpoint_sha256,
                      replay_result_sha256=replay['result_sha256'],
                      replay_boundary_sha256=replay['boundary'].audit_sha256,
                      method='REPLAY_FROM_INITIAL_INPUTS')
        return RecoveryReceiptV1d(**fields, recovery_sha256=_hash(fields))

    def activate_cold(self, promotion, source_args, target_args, *, policy):
        cp, registry = self.checkpoint, self.registry
        if (self.activation is not None or cp is None or policy != 'COLD_RESET'
                or type(promotion) is not PromotionReceiptV1c
                or not registry.history or promotion != registry.history[-1]
                or cp.revision != promotion.revision_before
                or registry.revision != promotion.revision_after
                or cp.context_sha256 != promotion.from_context_sha256
                or registry.active_context_sha256 != promotion.to_context_sha256
                or promotion.from_context_sha256 == promotion.to_context_sha256):
            raise StateCustodyDeniedV1d('cold activation policy or promotion custody denied')
        verify_checkpoint_v1d(cp, source_args)
        target_context, _ = _inputs(target_args)
        if target_context != promotion.to_context_sha256:
            raise StateCustodyDeniedV1d('target input/context mismatch')
        controller = registry.cold_start(promotion)
        if (controller.status != 'QUIESCENT' or controller.mode != 'VERIFY'
                or controller.epoch != 0 or controller.audit):
            raise StateCustodyDeniedV1d('candidate must begin from pristine controller')
        controller.transition('EXECUTE')
        activation = controller.run(*target_args)
        fields = dict(checkpoint_sha256=cp.checkpoint_sha256,
                      promotion_sha256=promotion.promotion_sha256,
                      from_context_sha256=cp.context_sha256,
                      to_context_sha256=target_context,
                      revision=registry.revision,
                      result_sha256=activation['result_sha256'],
                      activation_boundary_sha256=activation['boundary'].audit_sha256,
                      policy='COLD_RESET')
        receipt = ActivationReceiptV1d(**fields, activation_sha256=_hash(fields))
        self.activation = receipt
        return receipt
