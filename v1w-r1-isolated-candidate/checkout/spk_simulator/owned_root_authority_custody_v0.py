"""SPK k24e: process-local, single-writer custody of a k24b -> k24d handoff.

One registry object represents one trusted installation and supports exactly
one root history. Its lock serializes *all* API calls; caller-supplied revisions
are optimistic preconditions, not authentication capabilities. Neither this
registry nor its snapshots revoke raw k24b references, exclude other registry
instances/processes, or survive host failure. See the accompanying contract.
"""
from dataclasses import dataclass
from enum import Enum
from threading import RLock

from spk_simulator.owned_root_single_clock_v0 import (
    OwnedRootSingleClockStateV0,
    OwnedRootSingleClockStepV0,
    advance_owned_root_single_clock_v0,
)
from spk_simulator.owned_root_terminal_commit_v0 import (
    OwnedRootTerminalCommitStateV0,
    OwnedRootTerminalCommitStepV0,
    handoff_owned_root_terminal_commit_v0,
    advance_owned_root_terminal_commit_v0,
)


class CustodyPhaseV0(str, Enum):
    ROOT_OWNED = 'ROOT_OWNED'
    COMMIT_OWNED = 'COMMIT_OWNED'
    CLOSED = 'CLOSED'


class CustodyActionV0(str, Enum):
    ROOT_STEP = 'ROOT_STEP'
    HANDOFF = 'HANDOFF'
    TERMINAL_STEP = 'TERMINAL_STEP'


class CustodyStaleRevisionV0(ValueError):
    """Caller's expected revision does not match the current owner revision."""


class CustodyPhaseErrorV0(ValueError):
    """A well-formed operation is forbidden in the current custody phase."""


@dataclass(frozen=True, slots=True)
class CustodyRecordV0:
    revision: int
    action: CustodyActionV0
    phase: CustodyPhaseV0
    next_service_tick: int


@dataclass(frozen=True, slots=True)
class CustodyViewV0:
    phase: CustodyPhaseV0
    revision: int
    root: OwnedRootSingleClockStateV0
    terminal: OwnedRootTerminalCommitStateV0 | None
    trace: tuple[CustodyRecordV0, ...]

    @property
    def next_service_tick(self):
        if self.terminal is not None:
            return self.terminal.service.next_service_tick
        return self.root.shared.dynamic.transit.service.next_service_tick


@dataclass(frozen=True, slots=True)
class CustodyStepV0:
    view: CustodyViewV0
    root_step: OwnedRootSingleClockStepV0 | None = None
    terminal_step: OwnedRootTerminalCommitStepV0 | None = None


def _root_tick(root):
    return root.shared.dynamic.transit.service.next_service_tick


def _view(phase, revision, root, terminal, trace):
    return CustodyViewV0(phase, revision, root, terminal, trace)


def replay_custody_trace_v0(initial_root: OwnedRootSingleClockStateV0,
                            trace: tuple[CustodyRecordV0, ...]) -> CustodyViewV0:
    """Independently re-execute accepted operations from a trusted root.

    Replays both owners via their existing deterministic interfaces. This
    proves trace/state consistency *relative to the supplied initial root*,
    not the legitimacy of that root or authorization of the operation list.
    """
    if type(initial_root) is not OwnedRootSingleClockStateV0:
        raise TypeError('custody replay requires a k24b initial root')
    initial_root.__post_init__()
    if type(trace) is not tuple or any(type(x) is not CustodyRecordV0 for x in trace):
        raise TypeError('custody trace must be a tuple of canonical records')
    root = initial_root
    terminal = None
    phase = CustodyPhaseV0.ROOT_OWNED
    for revision, record in enumerate(trace, start=1):
        if type(record.revision) is not int or record.revision != revision:
            raise ValueError('custody trace revision gap, duplicate or forgery')
        if type(record.action) is not CustodyActionV0 or type(record.phase) is not CustodyPhaseV0:
            raise TypeError('noncanonical custody action or phase')
        if record.action is CustodyActionV0.ROOT_STEP:
            if phase is not CustodyPhaseV0.ROOT_OWNED:
                raise CustodyPhaseErrorV0('root service cannot run after handoff')
            root = advance_owned_root_single_clock_v0(root).state
        elif record.action is CustodyActionV0.HANDOFF:
            if phase is not CustodyPhaseV0.ROOT_OWNED:
                raise CustodyPhaseErrorV0('handoff is allowed exactly once')
            prior_tick = _root_tick(root)
            terminal = handoff_owned_root_terminal_commit_v0(root)
            if terminal.service.next_service_tick != prior_tick:
                raise ValueError('handoff spent service or changed clock')
            phase = CustodyPhaseV0.COMMIT_OWNED
        elif record.action is CustodyActionV0.TERMINAL_STEP:
            if phase is not CustodyPhaseV0.COMMIT_OWNED:
                raise CustodyPhaseErrorV0('terminal service requires active commit owner')
            terminal = advance_owned_root_terminal_commit_v0(terminal).state
            if terminal.committed:
                phase = CustodyPhaseV0.CLOSED
        else:
            raise ValueError('unknown custody action')
        next_tick = terminal.service.next_service_tick if terminal is not None else _root_tick(root)
        if record.phase is not phase or type(record.next_service_tick) is not int or record.next_service_tick != next_tick:
            raise ValueError('custody trace outcome not reconstructible')
    return _view(phase, len(trace), root, terminal, trace)


class OwnedRootAuthorityRegistryV0:
    """One installation per in-memory, process-local custody domain.

    All participants must exclusively use this object to operate the root and
    terminal owner. Its lock and check-and-set form the sole linearization
    point *inside this registry instance*. There is intentionally no reset.
    """

    __slots__ = ('_lock', '_installed', '_initial_root', '_root', '_terminal',
                 '_phase', '_revision', '_trace')

    def __init__(self):
        self._lock = RLock()
        self._installed = False
        self._initial_root = None
        self._root = None
        self._terminal = None
        self._phase = None
        self._revision = 0
        self._trace = ()

    def install(self, root: OwnedRootSingleClockStateV0) -> CustodyViewV0:
        with self._lock:
            if self._installed:
                raise CustodyPhaseErrorV0('custody installation already consumed')
            if type(root) is not OwnedRootSingleClockStateV0:
                raise TypeError('custody installation requires k24b root')
            root.__post_init__()
            # No side effects before successful validation.
            self._initial_root = root
            self._root = root
            self._phase = CustodyPhaseV0.ROOT_OWNED
            self._installed = True
            return self._view()

    def _view(self):
        return _view(self._phase, self._revision, self._root, self._terminal, self._trace)

    def snapshot(self) -> CustodyViewV0:
        with self._lock:
            if not self._installed:
                raise CustodyPhaseErrorV0('no custody installation')
            return self._view()

    def _require(self, expected_revision, phase):
        if not self._installed:
            raise CustodyPhaseErrorV0('no custody installation')
        if type(expected_revision) is not int or expected_revision < 0:
            raise TypeError('expected_revision must be a nonnegative exact integer')
        if expected_revision != self._revision:
            raise CustodyStaleRevisionV0('stale custody revision')
        if self._phase is not phase:
            raise CustodyPhaseErrorV0('custody action forbidden in current phase')

    def _record(self, action, phase, tick):
        new_revision = self._revision + 1
        record = CustodyRecordV0(new_revision, action, phase, tick)
        self._trace = self._trace + (record,)
        self._revision = new_revision
        self._phase = phase

    def advance_root(self, *, expected_revision: int) -> CustodyStepV0:
        with self._lock:
            self._require(expected_revision, CustodyPhaseV0.ROOT_OWNED)
            result = advance_owned_root_single_clock_v0(self._root)
            tick = _root_tick(result.state)
            if tick != _root_tick(self._root) + 1:
                raise ValueError('k24b root did not advance exactly one SERVICE_TIME')
            # The owner computation must succeed before custody state changes.
            self._root = result.state
            self._record(CustodyActionV0.ROOT_STEP, CustodyPhaseV0.ROOT_OWNED, tick)
            return CustodyStepV0(self._view(), root_step=result)

    def handoff(self, *, expected_revision: int) -> CustodyViewV0:
        with self._lock:
            self._require(expected_revision, CustodyPhaseV0.ROOT_OWNED)
            terminal = handoff_owned_root_terminal_commit_v0(self._root)
            tick = _root_tick(self._root)
            if terminal.service.next_service_tick != tick:
                raise ValueError('handoff cannot advance SERVICE_TIME')
            self._terminal = terminal
            self._record(CustodyActionV0.HANDOFF, CustodyPhaseV0.COMMIT_OWNED, tick)
            return self._view()

    def advance_terminal(self, *, expected_revision: int) -> CustodyStepV0:
        with self._lock:
            self._require(expected_revision, CustodyPhaseV0.COMMIT_OWNED)
            result = advance_owned_root_terminal_commit_v0(self._terminal)
            tick = result.state.service.next_service_tick
            if tick != self._terminal.service.next_service_tick + 1:
                raise ValueError('terminal did not advance exactly one SERVICE_TIME')
            phase = CustodyPhaseV0.CLOSED if result.state.committed else CustodyPhaseV0.COMMIT_OWNED
            self._terminal = result.state
            self._record(CustodyActionV0.TERMINAL_STEP, phase, tick)
            return CustodyStepV0(self._view(), terminal_step=result)

    def verify(self) -> CustodyViewV0:
        with self._lock:
            if not self._installed:
                raise CustodyPhaseErrorV0('no custody installation')
            result = replay_custody_trace_v0(self._initial_root, self._trace)
            if result != self._view():
                raise ValueError('custody state differs from reconstructed trace')
            return result
