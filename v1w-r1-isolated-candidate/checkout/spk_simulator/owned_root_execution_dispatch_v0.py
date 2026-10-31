"""SPK 24g: opt-in single-epoch dispatch boundary for k24f.

The dispatcher is an in-memory cooperating host adapter, NOT a retrofit of
legacy callers or a security sandbox. It owns exactly one k24f runner and never
returns it; all mutation submitted to this adapter passes through that runner.
No second scheduling clock, cross-process fencing or epoch authentication.
"""
from dataclasses import dataclass
from enum import Enum
from threading import RLock

from spk_simulator.owned_shared_event_cycle_v0 import OwnedSharedEventCycleStateV0
from spk_simulator.owned_root_authority_custody_v0 import (
    CustodyPhaseV0, CustodyPhaseErrorV0, CustodyStaleRevisionV0,
    CustodyRecordV0,
)
from spk_simulator.owned_root_custody_execution_v0 import (
    OwnedRootCustodyExecutionV0,
    OwnedRootExecutionViewV0,
    OwnedRootExecutionStepV0,
    OwnedRootExecutionRunV0,
)


class DispatchOperationV0(str, Enum):
    SNAPSHOT = 'SNAPSHOT'
    ADVANCE = 'ADVANCE'
    RUN = 'RUN'
    AUDIT = 'AUDIT'
    TRACE = 'TRACE'


class DispatchAdmissionErrorV0(ValueError):
    """Invalid or duplicate single-epoch installation."""


class DispatchEpochMismatchV0(ValueError):
    """Request epoch does not match the installed epoch."""


class DispatchNotInstalledV0(ValueError):
    """No epoch installed in the dispatcher."""


@dataclass(frozen=True, slots=True)
class DispatchRequestV0:
    """Typed command with strict per-operation argument shape.

    A request carries a checked epoch identity and optimistic control revision.
    Neither is an unforgeable token or an authentication credential.
    """
    epoch_id: str
    operation: DispatchOperationV0
    expected_revision: int | None = None
    max_actions: int | None = None

    def __post_init__(self):
        if type(self.epoch_id) is not str or not self.epoch_id:
            raise TypeError('epoch_id must be a nonempty exact string')
        if type(self.operation) is not DispatchOperationV0:
            raise TypeError('noncanonical dispatch operation')
        mutate = self.operation in (DispatchOperationV0.ADVANCE, DispatchOperationV0.RUN)
        if mutate:
            if type(self.expected_revision) is not int or self.expected_revision < 0:
                raise TypeError('mutating dispatch requires exact nonnegative revision')
        elif self.expected_revision is not None:
            raise TypeError('read-only dispatch cannot specify revision')
        if self.operation is DispatchOperationV0.RUN:
            if type(self.max_actions) is not int or self.max_actions <= 0:
                raise TypeError('RUN requires exact positive max_actions')
        elif self.max_actions is not None:
            raise TypeError('non-RUN dispatch cannot specify max_actions')


@dataclass(frozen=True, slots=True)
class DispatchResultV0:
    """Observation-only reply; no root, registry, terminal, or runner."""
    epoch_id: str
    operation: DispatchOperationV0
    view: OwnedRootExecutionViewV0
    step: OwnedRootExecutionStepV0 | None = None
    run: OwnedRootExecutionRunV0 | None = None
    trace: tuple[CustodyRecordV0, ...] | None = None


class OwnedRootExecutionDispatcherV0:
    """One installation, one k24f runner, no reset or owner-choice API.

    All methods are serialized by the dispatcher lock. `install` is a one-shot
    admission transaction: the runner must initialize successfully before it
    becomes visible. The identity is read from the trusted shared epoch, not
    minted or signed by this object. CLOSED remains readable/auditable but
    rejects mutating dispatch requests, including zero-action RUN.

    An external host must explicitly route all its cooperative client traffic
    through this object. Legacy pure functions and other dispatchers remain
    callable outside this boundary.
    """

    __slots__ = ('_lock', '_runner', '_epoch_id')

    def __init__(self):
        self._lock = RLock()
        self._runner = None
        self._epoch_id = None

    def install(self, shared: OwnedSharedEventCycleStateV0, *, epoch_id: str):
        with self._lock:
            if self._runner is not None:
                raise DispatchAdmissionErrorV0('dispatcher already installed; no reset')
            if type(shared) is not OwnedSharedEventCycleStateV0:
                raise TypeError('dispatcher requires fresh shared EVENT epoch')
            if type(epoch_id) is not str or not epoch_id:
                raise TypeError('epoch_id must be a nonempty exact string')
            if shared.seal.epoch_id != epoch_id:
                raise DispatchEpochMismatchV0('installation epoch mismatch')
            runner = OwnedRootCustodyExecutionV0(shared)
            view = runner.snapshot()
            if (view.phase is not CustodyPhaseV0.ROOT_OWNED
                    or view.revision != 0 or view.commit_receipt is not None):
                raise DispatchAdmissionErrorV0('installation must start at fresh root')
            # No publication until after all validation succeeds.
            self._runner = runner
            self._epoch_id = epoch_id
            return view

    def dispatch(self, request: DispatchRequestV0) -> DispatchResultV0:
        if type(request) is not DispatchRequestV0:
            raise TypeError('dispatch requires canonical request')
        request.__post_init__()  # reject forged dataclass created without validation
        with self._lock:
            if self._runner is None:
                raise DispatchNotInstalledV0('dispatcher has no installed epoch')
            if request.epoch_id != self._epoch_id:
                raise DispatchEpochMismatchV0('dispatch epoch mismatch')
            runner = self._runner
            op = request.operation
            if op is DispatchOperationV0.SNAPSHOT:
                return DispatchResultV0(self._epoch_id, op, runner.snapshot())
            if op is DispatchOperationV0.AUDIT:
                return DispatchResultV0(self._epoch_id, op, runner.audit())
            if op is DispatchOperationV0.TRACE:
                return DispatchResultV0(self._epoch_id, op, runner.snapshot(), trace=runner.trace())

            current = runner.snapshot()
            # Compare revision before checking CLOSED, including a stale
            # command arriving after closure.
            if request.expected_revision != current.revision:
                raise CustodyStaleRevisionV0('stale dispatch revision')
            if current.phase is CustodyPhaseV0.CLOSED:
                raise CustodyPhaseErrorV0('dispatcher epoch closed')
            if op is DispatchOperationV0.ADVANCE:
                step = runner.advance(expected_revision=request.expected_revision)
                return DispatchResultV0(self._epoch_id, op, step.after, step=step)
            if op is DispatchOperationV0.RUN:
                run = runner.run(
                    expected_revision=request.expected_revision,
                    max_actions=request.max_actions,
                )
                return DispatchResultV0(self._epoch_id, op, run.after, run=run)
            raise TypeError('unsupported dispatch operation')
