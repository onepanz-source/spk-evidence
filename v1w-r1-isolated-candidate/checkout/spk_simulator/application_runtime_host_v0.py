"""SPK 24j: offline, cooperative, one-epoch reference application host.

Every accepted mutation passes through the existing 24g dispatcher. The caller
supplies a named in-process epoch provider. The name and epoch seal are NOT
proof of source authenticity. This is not a deployed host, security sandbox,
cross-process writer lock, or restart/durability protocol.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from threading import RLock
from typing import Callable

from spk_simulator.owned_shared_event_cycle_v0 import OwnedSharedEventCycleStateV0
from spk_simulator.owned_root_execution_dispatch_v0 import (
    CustodyPhaseV0, CustodyStaleRevisionV0, OwnedRootExecutionViewV0,
    DispatchOperationV0, DispatchRequestV0, DispatchResultV0,
    DispatchEpochMismatchV0, OwnedRootExecutionDispatcherV0,
)


class HostPhaseV0(str, Enum):
    NEW = 'NEW'
    ACTIVE = 'ACTIVE'
    CLOSED = 'CLOSED'
    FAILED = 'FAILED'


class HostLifecycleErrorV0(ValueError):
    """Operation disallowed by host lifecycle; no mutation attempted."""


class HostAdmissionErrorV0(ValueError):
    """The selected in-process epoch provider could not admit an epoch."""


class HostExecutionErrorV0(RuntimeError):
    """The installed dispatcher failed during an accepted operation."""


@dataclass(frozen=True, slots=True)
class HostStatusV0:
    phase: HostPhaseV0
    provider_id: str
    epoch_id: str | None
    view: OwnedRootExecutionViewV0 | None
    diagnostic: str | None
    observation_error: str | None = None

    @property
    def completed(self) -> bool:
        return (self.phase is HostPhaseV0.CLOSED and self.view is not None
                and self.view.phase is CustodyPhaseV0.CLOSED
                and self.view.commit_receipt is not None
                and not self.view.commit_receipt.candidate_outputs)


class ApplicationRuntimeHostV0:
    """One admitted epoch, single dispatcher, finite offline execution.

    `provider` is a trusted-for-this-test *callable* chosen by the embedding
    application. No source authentication or global uniqueness follows from
    its name, the shared seal, or the installed dispatcher.

    No raw dispatcher/runner/owner is exposed through the public methods.
    Concurrent requests are serialized across the entire host lifetime.
    """

    __slots__ = (
        '_lock', '_provider', '_provider_id', '_phase', '_dispatcher',
        '_epoch_id', '_last_view', '_diagnostic',
    )

    def __init__(self, *, provider: Callable[[], OwnedSharedEventCycleStateV0], provider_id: str):
        if not callable(provider):
            raise TypeError('provider must be an in-process callable')
        if type(provider_id) is not str or not provider_id.strip():
            raise TypeError('provider_id must be a nonempty exact string')
        self._lock = RLock()
        self._provider = provider
        self._provider_id = provider_id
        self._phase = HostPhaseV0.NEW
        self._dispatcher: OwnedRootExecutionDispatcherV0 | None = None
        self._epoch_id: str | None = None
        self._last_view: OwnedRootExecutionViewV0 | None = None
        self._diagnostic: str | None = None

    @staticmethod
    def _committed(view: OwnedRootExecutionViewV0) -> bool:
        if type(view) is not OwnedRootExecutionViewV0:
            raise HostExecutionErrorV0('noncanonical 24g observation')
        if view.phase is not CustodyPhaseV0.CLOSED:
            if view.commit_receipt is not None:
                raise HostExecutionErrorV0('premature terminal receipt')
            return False
        receipt = view.commit_receipt
        if (receipt is None or receipt.candidate_outputs
                or receipt.new_version != receipt.old_version + 1):
            raise HostExecutionErrorV0('closed state lacks genuine output-free S receipt')
        return True

    def _promote_locked(self, view: OwnedRootExecutionViewV0) -> None:
        self._last_view = view
        if self._committed(view):
            self._phase = HostPhaseV0.CLOSED

    def _status_locked(self) -> HostStatusV0:
        if self._dispatcher is None:
            return HostStatusV0(self._phase, self._provider_id, self._epoch_id,
                                self._last_view, self._diagnostic)
        try:
            result = self._dispatcher.dispatch(
                DispatchRequestV0(self._epoch_id, DispatchOperationV0.SNAPSHOT)
            )
            # Even FAILED hosts may inspect authoritative progress; never
            # infer completion from a failed host's retained last view.
            if type(result) is not DispatchResultV0:
                raise ValueError('noncanonical diagnostic snapshot')
            self._last_view = result.view
            if self._phase is HostPhaseV0.ACTIVE:
                self._promote_locked(result.view)
            return HostStatusV0(self._phase, self._provider_id, self._epoch_id,
                                result.view, self._diagnostic)
        except Exception as exc:
            return HostStatusV0(
                self._phase, self._provider_id, self._epoch_id,
                None, self._diagnostic,
                f'{type(exc).__name__}: {exc}',
            )

    def status(self) -> HostStatusV0:
        """Best-effort observation, without reporting stale state as current."""
        with self._lock:
            return self._status_locked()

    def admit(self, *, epoch_id: str) -> HostStatusV0:
        """Admit exactly one shared epoch from the chosen provider.

        Any failure before successful 24g installation leaves this host NEW.
        The provider may be invoked again *only* after failed admission.
        """
        with self._lock:
            if self._phase is not HostPhaseV0.NEW:
                raise HostLifecycleErrorV0('epoch already admitted or host ended')
            if type(epoch_id) is not str or not epoch_id:
                raise TypeError('epoch_id must be a nonempty exact string')
            try:
                shared = self._provider()
            except Exception as exc:
                raise HostAdmissionErrorV0('epoch provider failed') from exc
            if type(shared) is not OwnedSharedEventCycleStateV0:
                raise TypeError('provider must return canonical shared EVENT epoch')
            # Structural evidence and expected identity, not source proof.
            if shared.seal.epoch_id != epoch_id:
                raise DispatchEpochMismatchV0('provider epoch does not match expectation')
            candidate = OwnedRootExecutionDispatcherV0()
            view = candidate.install(shared, epoch_id=epoch_id)
            # 24g performs validation before publication. Do the same here.
            if (type(view) is not OwnedRootExecutionViewV0
                    or view.phase is not CustodyPhaseV0.ROOT_OWNED
                    or type(view.revision) is not int or view.revision != 0
                    or view.commit_receipt is not None):
                raise HostAdmissionErrorV0('not a fresh root execution')
            self._dispatcher = candidate
            self._epoch_id = epoch_id
            self._last_view = view
            self._phase = HostPhaseV0.ACTIVE
            return HostStatusV0(self._phase, self._provider_id, self._epoch_id,
                                view, None)

    def dispatch(self, request: DispatchRequestV0) -> DispatchResultV0:
        """Reject invalid commands before invoking 24g; fail-stop on error.

        A rejected wrong-epoch, stale-revision or malformed request is *not*
        an execution failure. Any other exception during an accepted 24g
        call transitions this host to FAILED, possibly after partial progress.
        """
        with self._lock:
            if self._phase is HostPhaseV0.NEW:
                raise HostLifecycleErrorV0('host has no installed epoch')
            if type(request) is not DispatchRequestV0:
                raise TypeError('host requires canonical dispatch request')
            request.__post_init__()  # check forged dataclass instances
            if request.epoch_id != self._epoch_id:
                raise DispatchEpochMismatchV0('host epoch mismatch')
            mutate = request.operation in (
                DispatchOperationV0.ADVANCE, DispatchOperationV0.RUN,
            )
            if mutate and self._phase is not HostPhaseV0.ACTIVE:
                raise HostLifecycleErrorV0('host not active for mutation')
            if self._dispatcher is None:
                raise HostLifecycleErrorV0('host has no dispatcher')
            try:
                reply = self._dispatcher.dispatch(request)
            except CustodyStaleRevisionV0:
                # The underlying 24g checks revisions before mutation.
                raise
            except Exception as exc:
                self._phase = HostPhaseV0.FAILED
                self._diagnostic = f'{type(exc).__name__}: {exc}'
                raise HostExecutionErrorV0('dispatcher execution failed; host is fail-stop') from exc
            try:
                if type(reply) is not DispatchResultV0 or reply.epoch_id != self._epoch_id:
                    raise HostExecutionErrorV0('invalid dispatcher response')
                if reply.operation is not request.operation:
                    raise HostExecutionErrorV0('dispatcher returned wrong operation')
                if self._phase is HostPhaseV0.ACTIVE:
                    self._promote_locked(reply.view)
                elif self._phase is HostPhaseV0.CLOSED and not self._committed(reply.view):
                    raise HostExecutionErrorV0('closed host lost underlying commit')
                # FAILED diagnostic commands never resurrect the host.
                return reply
            except Exception as exc:
                self._phase = HostPhaseV0.FAILED
                self._diagnostic = f'{type(exc).__name__}: {exc}'
                raise HostExecutionErrorV0('invalid dispatcher result; host is fail-stop') from exc

    def shutdown(self) -> HostStatusV0:
        """Irreversibly halt an incomplete host; never synthesize commit."""
        with self._lock:
            if self._phase is HostPhaseV0.CLOSED:
                return self._status_locked()
            if self._phase is not HostPhaseV0.FAILED:
                self._phase = HostPhaseV0.FAILED
                self._diagnostic = 'shutdown without verified terminal completion'
            return self._status_locked()
