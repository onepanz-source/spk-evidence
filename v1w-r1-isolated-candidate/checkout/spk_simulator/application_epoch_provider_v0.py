"""SPK 24k: single-use, offline adapter for a caller-supplied sealed EVENT epoch.

Structural validity is NOT source authentication. The embedding application
chooses and vouches for the source within the one-process cooperation scope.
No persisted ownership, cross-host fencing, transport or global uniqueness.
"""
from __future__ import annotations

from threading import Lock

from spk_simulator.owned_shared_event_cycle_v0 import OwnedSharedEventCycleStateV0


class EpochAlreadyIssuedV0(ValueError):
    """This provider has already issued its one snapshot."""


class SingleUseSealedEpochProviderV0:
    """One callable handoff of one canonical immutable sealed epoch.

    Reusing the supplied snapshot in a different provider is still possible.
    Do not mistake this process-local one-shot consumption for a security token.
    """

    __slots__ = ('_lock', '_epoch', '_issued', 'source_id')

    def __init__(self, epoch: OwnedSharedEventCycleStateV0, *, source_id: str):
        if type(epoch) is not OwnedSharedEventCycleStateV0:
            raise TypeError('epoch must be a canonical shared EVENT snapshot')
        if type(source_id) is not str or not source_id or source_id != source_id.strip():
            raise TypeError('source_id must be a nonempty trimmed string')
        # Re-run constructors' structural checks on an externally supplied object.
        epoch.__post_init__()
        self._lock = Lock()
        self._epoch = epoch
        self._issued = False
        self.source_id = source_id

    def __call__(self) -> OwnedSharedEventCycleStateV0:
        with self._lock:
            if self._issued:
                raise EpochAlreadyIssuedV0('sealed epoch was already issued')
            self._issued = True
            return self._epoch

    @property
    def issued(self) -> bool:
        with self._lock:
            return self._issued
