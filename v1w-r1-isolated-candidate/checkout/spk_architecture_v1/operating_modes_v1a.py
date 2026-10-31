"""A4a: trusted in-process operating mode authority and quiescent epochs.

A3d remains the actual causal engine. This layer gates actions and binds a
mode epoch to a complete immutable logical execution context. TRAINING and
REMODEL only stage candidate *digests*; neither trains nor changes a program.
Python objects are not a security boundary against malicious host code.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass
import re

from search.spk_24n_differential_evidence_v0 import canonical, sha
from spk_architecture_v1.causal_transport_v1d import execute_causal_transport_v1d

SCHEMA = 'spk-architecture-operating-modes/v1a'
MODES = ('VERIFY', 'EXECUTE', 'TRAINING', 'REMODEL')
ACTIONS = {'VERIFY': frozenset({'REPLAY'}),
           'EXECUTE': frozenset({'RUN'}),
           'TRAINING': frozenset({'STAGE'}),
           'REMODEL': frozenset({'STAGE'})}
TRANSITIONS = {'VERIFY': frozenset({'EXECUTE', 'TRAINING', 'REMODEL'}),
               'EXECUTE': frozenset({'VERIFY'}),
               'TRAINING': frozenset({'VERIFY'}),
               'REMODEL': frozenset({'VERIFY'})}
_HEX = re.compile(r'[0-9a-f]{64}\Z')


class OperatingModeDeniedV1a(ValueError):
    pass


class OperatingModeFaultV1a(RuntimeError):
    pass


@dataclass(frozen=True)
class ModeBoundaryV1a:
    epoch: int
    mode: str
    context_sha256: str
    status: str
    audit_sha256: str


def context_fingerprint_v1a(case, fabric, transport, pe, memory, link):
    """Bind exact source programs, placement and service plans to the epoch."""
    parts = (case, fabric, transport, pe, memory, link)
    if any(not is_dataclass(x) or isinstance(x, type) for x in parts):
        raise OperatingModeDeniedV1a('non-dataclass execution context')
    return sha(canonical({'schema': SCHEMA, 'inputs': [asdict(x) for x in parts]}))


def result_digest_v1a(output):
    """Full A3d result including ownership, grants and transcripts."""
    if type(output) is not dict or output.get('schema') != (
            'spk-architecture-causal-transport-backpressure/v1d'):
        raise OperatingModeDeniedV1a('unknown A3d output')
    result, routed = output.get('result'), output.get('transport')
    if type(result) is not dict or type(routed) is not dict:
        raise OperatingModeDeniedV1a('missing result or transport')
    if (routed.get('remaining_inflight_occurrences') != 0
            or routed.get('outstanding_outbox_occurrences') != 0
            or routed.get('cross_pe_occurrences') != routed.get('delivered_cross_pe_occurrences')):
        raise OperatingModeDeniedV1a('nonquiescent A3d execution')
    # Batch count is not event count: check batches, not one event per batch.
    if result.get('processed_batches') != len(result.get('observations', {}).get('batches', [])):
        raise OperatingModeDeniedV1a('invalid batch transcript')
    if result.get('processed_events') is None or result['processed_events'] < 0:
        raise OperatingModeDeniedV1a('invalid event accounting')
    return sha(canonical(output))


class ModeControllerV1a:
    """Single logical authority; phase changes only under its own run lease."""
    def __init__(self, context_sha256, initial_mode='VERIFY'):
        if (type(context_sha256) is not str or not _HEX.fullmatch(context_sha256)
                or type(initial_mode) is not str or initial_mode not in MODES):
            raise OperatingModeDeniedV1a('invalid initial authority')
        self.context_sha256 = context_sha256
        self.mode = initial_mode
        self.epoch = 0
        self.status = 'QUIESCENT'
        self.audit = []
        self._nonce = 0

    def boundary(self):
        return ModeBoundaryV1a(self.epoch, self.mode, self.context_sha256,
                               self.status, sha(canonical(self.audit)))

    def transition(self, next_mode):
        if self.status != 'QUIESCENT':
            raise OperatingModeDeniedV1a('nonquiescent mode transition denied')
        if type(next_mode) is not str or next_mode not in TRANSITIONS[self.mode]:
            raise OperatingModeDeniedV1a('unsupported operating mode transition')
        old = self.mode
        self.mode = next_mode
        self.epoch += 1
        self.audit.append({'kind': 'TRANSITION', 'from': old, 'to': next_mode,
                           'epoch': self.epoch, 'context_sha256': self.context_sha256})
        return self.boundary()

    def _start(self, action, current_context):
        if self.status != 'QUIESCENT':
            raise OperatingModeDeniedV1a('controller is not quiescent')
        if action not in ACTIONS[self.mode]:
            raise OperatingModeDeniedV1a('activity forbidden in current mode')
        if current_context != self.context_sha256:
            raise OperatingModeDeniedV1a('epoch context drift')
        self.status = 'ACTIVE'
        self._nonce += 1
        return self._nonce

    def _finish(self, nonce, action, result_sha):
        if self.status != 'ACTIVE' or nonce != self._nonce:
            raise OperatingModeFaultV1a('invalid live mode lease')
        self.audit.append({'kind': action, 'mode': self.mode, 'epoch': self.epoch,
                           'context_sha256': self.context_sha256,
                           'result_sha256': result_sha})
        self.status = 'QUIESCENT'
        return self.boundary()

    def _fault(self):
        # Deliberately no rollback or unproven restart from a partial A3d run.
        self.status = 'FAULTED'

    def run(self, case, fabric, transport, pe, memory, link, *, expected_sha256=None):
        """RUN invokes A3d in EXECUTE; REPLAY invokes it in VERIFY.

        REPLAY must supply a previously expected full-result digest; the digest
        does not authenticate its origin, but a forged result cannot pass a
        fixed expected digest without a matching deterministic execution.
        """
        action = 'REPLAY' if self.mode == 'VERIFY' else 'RUN'
        context = context_fingerprint_v1a(case, fabric, transport, pe, memory, link)
        if action == 'REPLAY' and (type(expected_sha256) is not str or
                                   not _HEX.fullmatch(expected_sha256)):
            raise OperatingModeDeniedV1a('VERIFY requires pinned expected digest')
        if action == 'RUN' and expected_sha256 is not None:
            raise OperatingModeDeniedV1a('RUN cannot supply expected replay digest')
        nonce = self._start(action, context)
        try:
            outcome = execute_causal_transport_v1d(case, fabric, transport, pe, memory, link)
            digest = result_digest_v1a(outcome)
            if action == 'REPLAY' and digest != expected_sha256:
                raise OperatingModeDeniedV1a('independent mode replay mismatch')
            boundary = self._finish(nonce, action, digest)
            return {'schema': SCHEMA, 'mode': self.mode, 'epoch': self.epoch,
                    'result_sha256': digest, 'boundary': boundary, 'output': outcome}
        except Exception:
            self._fault()
            raise

    def stage(self, candidate_sha256):
        """TRAINING/REMODEL can only record a candidate reference, not install it."""
        if type(candidate_sha256) is not str or not _HEX.fullmatch(candidate_sha256):
            raise OperatingModeDeniedV1a('invalid candidate fingerprint')
        nonce = self._start('STAGE', self.context_sha256)
        return self._finish(nonce, 'STAGE', candidate_sha256)
