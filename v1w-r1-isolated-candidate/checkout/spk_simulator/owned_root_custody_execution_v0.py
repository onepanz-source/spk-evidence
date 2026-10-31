"""SPK k24f: opt-in custody-enforced execution entrypoint for one root epoch.

Within *this entrypoint*, all progress is routed through the k24e registry:
ROOT_STEP -> HANDOFF (no SERVICE_TIME) -> TERMINAL_STEP -> CLOSED.

No raw owner/registry is returned by the public interface. This is API
encapsulation, NOT a security barrier against arbitrary in-process Python,
other runners, retained raw snapshots, or host crashes. See the contract.
"""
from dataclasses import dataclass
from threading import RLock

from spk_simulator.owned_shared_event_cycle_v0 import OwnedSharedEventCycleStateV0
from spk_simulator.owned_root_single_clock_v0 import initialize_owned_root_single_clock_v0
from spk_simulator.owned_root_authority_custody_v0 import (
    CustodyActionV0, CustodyPhaseV0, CustodyPhaseErrorV0,
    CustodyStaleRevisionV0, CustodyRecordV0, OwnedRootAuthorityRegistryV0,
)
from spk_simulator.versioned_core_transition_v0 import (
    NeuronVersionV0, CoreStateCommitReceiptV0,
)


@dataclass(frozen=True, slots=True)
class OwnedRootExecutionViewV0:
    """Observation-only projection: no root, owner, service, or registry reference."""
    phase: CustodyPhaseV0
    revision: int
    next_service_tick: int
    neurons: tuple[NeuronVersionV0, ...]
    commit_receipt: CoreStateCommitReceiptV0 | None

    @property
    def completed(self) -> bool:
        return self.phase is CustodyPhaseV0.CLOSED


@dataclass(frozen=True, slots=True)
class OwnedRootExecutionStepV0:
    action: CustodyActionV0
    before_revision: int
    after: OwnedRootExecutionViewV0
    service_ticks_spent: int


@dataclass(frozen=True, slots=True)
class OwnedRootExecutionRunV0:
    steps: tuple[OwnedRootExecutionStepV0, ...]
    after: OwnedRootExecutionViewV0

    @property
    def completed(self) -> bool:
        return self.after.completed


class OwnedRootCustodyExecutionV0:
    """A single-root, process-local *cooperating* execution boundary.

    The driver owns its registry and does not offer owner-choice operations.
    `advance` is an atomic control-plane action (not always a service tick).
    `run` is bounded and may finish with incomplete work. No global
    exclusivity, unforgeable capabilities, or crash durability is implied.
    """

    __slots__ = ('_lock', '_registry')

    def __init__(self, shared: OwnedSharedEventCycleStateV0):
        # Initialize from a fresh external EVENT/P/S epoch, not from a
        # caller-supplied prepared owner or a forged successful transition.
        root = initialize_owned_root_single_clock_v0(shared)
        registry = OwnedRootAuthorityRegistryV0()
        registry.install(root)
        self._lock = RLock()
        self._registry = registry

    @staticmethod
    def _project(view):
        image = view.root.image if view.terminal is None else view.terminal.image
        receipt = None
        if view.phase is CustodyPhaseV0.CLOSED:
            # k24d owns receipt production and has already replay-validated it.
            receipt = view.terminal.quanta[-1].receipt
            if receipt is None or receipt.candidate_outputs:
                raise ValueError('closed terminal must have output-free S receipt')
        return OwnedRootExecutionViewV0(
            view.phase, view.revision, view.next_service_tick,
            image.neurons, receipt,
        )

    def snapshot(self) -> OwnedRootExecutionViewV0:
        with self._lock:
            return self._project(self._registry.snapshot())

    def audit(self) -> OwnedRootExecutionViewV0:
        """Replay under k24e custody and return only an observation."""
        with self._lock:
            return self._project(self._registry.verify())

    def trace(self) -> tuple[CustodyRecordV0, ...]:
        """Untrusted as an independent authentication proof; replayable in k24e."""
        with self._lock:
            return self._registry.snapshot().trace

    def _advance_locked(self, expected_revision: int):
        before = self._registry.snapshot()
        # Check stale revision *before* deciding which action to take.
        if type(expected_revision) is not int or expected_revision < 0:
            raise TypeError('expected_revision must be a nonnegative exact integer')
        if expected_revision != before.revision:
            raise CustodyStaleRevisionV0('stale execution revision')
        if before.phase is CustodyPhaseV0.ROOT_OWNED:
            # A prepared root MUST attempt handoff. Failed admission is fatal
            # to this step; never resume P/S/EVENT as an implicit fallback.
            if before.root.prepared:
                after = self._registry.handoff(expected_revision=expected_revision)
            else:
                after = self._registry.advance_root(expected_revision=expected_revision).view
        elif before.phase is CustodyPhaseV0.COMMIT_OWNED:
            after = self._registry.advance_terminal(expected_revision=expected_revision).view
        elif before.phase is CustodyPhaseV0.CLOSED:
            raise CustodyPhaseErrorV0('execution already closed')
        else:
            raise CustodyPhaseErrorV0('unknown execution phase')
        if after.revision != before.revision + 1:
            raise ValueError('accepted custody action must increment revision once')
        record = after.trace[-1]
        spent = after.next_service_tick - before.next_service_tick
        if spent not in (0, 1) or (record.action is CustodyActionV0.HANDOFF) != (spent == 0):
            raise ValueError('custody action violates single SERVICE_TIME')
        return OwnedRootExecutionStepV0(
            record.action, before.revision, self._project(after), spent,
        )

    def advance(self, *, expected_revision: int) -> OwnedRootExecutionStepV0:
        with self._lock:
            return self._advance_locked(expected_revision)

    def run(self, *, expected_revision: int, max_actions: int) -> OwnedRootExecutionRunV0:
        """Run at most max_actions accepted custody operations, never fake finish.

        The same driver lock protects the entire bounded run. The caller must
        inspect `completed`; exhaustion is NOT an execution success or error.
        Previously accepted operations are not rolled back if an owner fails.
        """
        if type(max_actions) is not int or max_actions <= 0:
            raise TypeError('max_actions must be an exact positive integer')
        with self._lock:
            before = self._registry.snapshot()
            if type(expected_revision) is not int or expected_revision < 0:
                raise TypeError('expected_revision must be a nonnegative exact integer')
            if before.revision != expected_revision:
                raise CustodyStaleRevisionV0('stale execution revision')
            steps = []
            for _ in range(max_actions):
                if self._registry.snapshot().phase is CustodyPhaseV0.CLOSED:
                    break
                view = self._registry.snapshot()
                steps.append(self._advance_locked(view.revision))
            return OwnedRootExecutionRunV0(tuple(steps), self._project(self._registry.snapshot()))
