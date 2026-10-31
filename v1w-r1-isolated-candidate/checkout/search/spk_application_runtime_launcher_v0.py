"""SPK 24k: explicit offline consumer of the 24j application host.

Run: python -m search.spk_application_runtime_launcher_v0 \\
    --provider trusted_local_module:build_epoch --epoch-id E0 \\
    --max-actions 100 --chunk-size 8

Importing a provider executes trusted local Python code. Not a sandbox,
authentication protocol or deployment entrypoint accepting network requests.
All mutations go through the 24j host -> 24g dispatcher; no second clock.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from importlib import import_module
import json
import sys
from typing import Callable, Sequence

from spk_simulator.application_epoch_provider_v0 import SingleUseSealedEpochProviderV0
from spk_simulator.application_runtime_host_v0 import (
    ApplicationRuntimeHostV0, HostPhaseV0, HostStatusV0,
)
from spk_simulator.owned_root_execution_dispatch_v0 import (
    DispatchOperationV0, DispatchRequestV0,
)
from spk_simulator.owned_shared_event_cycle_v0 import OwnedSharedEventCycleStateV0

EXIT_COMPLETED = 0
EXIT_FAILURE = 2
EXIT_INCOMPLETE = 3


class OfflineSessionErrorV0(RuntimeError):
    """Failure after admission; preserve the last observable progress boundary.

    The status is *diagnostic*, not proof that every prior step rolled back or
    that the epoch can be recovered after process exit.
    """

    def __init__(self, cause: Exception, status: HostStatusV0):
        super().__init__(f'{type(cause).__name__}: {cause}')
        self.phase = status.phase.value
        self.revision = None if status.view is None else status.view.revision
        self.next_service_tick = None if status.view is None else status.view.next_service_tick
        self.observation_error = status.observation_error


@dataclass(frozen=True, slots=True)
class OfflineEpochResultV0:
    provider_id: str
    epoch_id: str
    phase: str
    completed: bool
    revision: int
    next_service_tick: int
    actions: int
    service_ticks_spent: int
    handoffs: int
    old_version: int | None
    new_version: int | None


def resolve_local_epoch_factory_v0(spec: str) -> Callable[[], OwnedSharedEventCycleStateV0]:
    """Resolve an explicitly trusted, no-argument LOCAL Python factory.

    The `module:function` string is a *configuration*, not an authority token.
    Only import modules from a caller-controlled trusted Python environment.
    """
    if (type(spec) is not str or spec.count(':') != 1
            or not spec.split(':')[1].isidentifier()
            or not all(x.isidentifier() for x in spec.split(':')[0].split('.'))):
        raise ValueError('provider must be module.path:factory')
    module_name, function_name = spec.split(':')
    factory = getattr(import_module(module_name), function_name)
    if not callable(factory):
        raise TypeError('selected epoch factory is not callable')
    return factory


def run_offline_epoch_v0(
    *, factory: Callable[[], OwnedSharedEventCycleStateV0],
    provider_id: str, epoch_id: str, max_actions: int, chunk_size: int,
) -> OfflineEpochResultV0:
    """One bounded, non-resumable launcher process session.

    Resumption across *chunks* is explicit through the actual returned revision.
    This method never retries stale commands or begins another epoch.
    Rerunning the process is NOT crash recovery and might duplicate authority.
    """
    if not callable(factory):
        raise TypeError('factory must be callable')
    if type(epoch_id) is not str or not epoch_id:
        raise TypeError('epoch_id must be a nonempty exact string')
    for name, n in (('max_actions', max_actions), ('chunk_size', chunk_size)):
        if type(n) is not int or n < 1:
            raise ValueError(f'{name} must be an exact positive integer')
    if type(provider_id) is not str or not provider_id or provider_id.strip() != provider_id:
        raise TypeError('provider_id must be a nonempty trimmed string')

    # A single canonical snapshot is acquired once, then issued once to 24j.
    epoch = factory()
    source = SingleUseSealedEpochProviderV0(epoch, source_id=provider_id)
    host = ApplicationRuntimeHostV0(provider=source, provider_id=provider_id)
    status = host.admit(epoch_id=epoch_id)
    actions = ticks = handoffs = 0
    try:
        while actions < max_actions and status.phase is HostPhaseV0.ACTIVE:
            requested = min(chunk_size, max_actions - actions)
            result = host.dispatch(DispatchRequestV0(
                epoch_id, DispatchOperationV0.RUN,
                expected_revision=status.view.revision, max_actions=requested,
            ))
            if result.run is None:
                raise RuntimeError('RUN missing execution record')
            steps = result.run.steps
            if not steps or len(steps) > requested:
                raise RuntimeError('RUN violated finite progress bound')
            consumed = sum(s.service_ticks_spent for s in steps)
            handoff_count = sum(s.action.value == 'HANDOFF' for s in steps)
            if (consumed != result.view.next_service_tick - status.view.next_service_tick
                    or consumed + handoff_count != len(steps)):
                raise RuntimeError('RUN disagrees with unique SERVICE_TIME')
            if result.view.revision != status.view.revision + len(steps):
                raise RuntimeError('RUN revision advance not accounted for')
            actions += len(steps)
            ticks += consumed
            handoffs += handoff_count
            status = host.status()
            if status.observation_error is not None or status.view != result.view:
                raise RuntimeError('host snapshot differs from executed RUN')
        # Final replay verification is read-only and cannot fabricate success.
        audit = host.dispatch(DispatchRequestV0(epoch_id, DispatchOperationV0.AUDIT))
        status = host.status()
        if audit.view != status.view or status.observation_error is not None:
            raise RuntimeError('custody replay audit disagrees with host snapshot')
        receipt = status.view.commit_receipt
        if status.completed and (handoffs != 1 or receipt is None or receipt.candidate_outputs):
            raise RuntimeError('completed run lacks unique output-free commit')
        if not status.completed and receipt is not None:
            raise RuntimeError('incomplete run exposes commit receipt')
        return OfflineEpochResultV0(
            provider_id, epoch_id, ('CLOSED' if status.completed else 'INCOMPLETE'), status.completed,
            status.view.revision, status.view.next_service_tick,
            actions, ticks, handoffs,
            None if receipt is None else receipt.old_version,
            None if receipt is None else receipt.new_version,
        )
    except Exception as exc:
        # The underlying accepted RUN may have progressed before failing.
        # Inspect authoritative status before the final fail-stop shutdown.
        raise OfflineSessionErrorV0(exc, host.status()) from exc
    finally:
        # An incomplete one-shot session is *not* preserved or recoverable.
        # No state serialization or second host installation is attempted.
        if host.status().phase is HostPhaseV0.ACTIVE:
            host.shutdown()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='SPK offline single-epoch launcher (trusted local provider only)')
    parser.add_argument('--provider', required=True, help='trusted.module:factory; imports and executes local code')
    parser.add_argument('--epoch-id', required=True)
    parser.add_argument('--max-actions', type=int, required=True)
    parser.add_argument('--chunk-size', type=int, default=8)
    args = parser.parse_args(argv)
    try:
        factory = resolve_local_epoch_factory_v0(args.provider)
        result = run_offline_epoch_v0(factory=factory, provider_id=args.provider,
                                      epoch_id=args.epoch_id, max_actions=args.max_actions,
                                      chunk_size=args.chunk_size)
    except Exception as exc:
        # Failure is explicit; NEVER output a fabricated success result.
        error = {'status': 'ERROR', 'type': type(exc).__name__, 'detail': str(exc)}
        if isinstance(exc, OfflineSessionErrorV0):
            error.update(phase=exc.phase, revision=exc.revision,
                         next_service_tick=exc.next_service_tick,
                         observation_error=exc.observation_error)
        print(json.dumps(error, sort_keys=True))
        return EXIT_FAILURE
    print(json.dumps(asdict(result), sort_keys=True))
    return EXIT_COMPLETED if result.completed else EXIT_INCOMPLETE


if __name__ == '__main__':
    sys.exit(main())
