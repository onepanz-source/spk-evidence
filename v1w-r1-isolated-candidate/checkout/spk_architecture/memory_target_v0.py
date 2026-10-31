"""SPK architectural memory target identities v0.

Structural identity and reference resolution only.
No access authorization or scheduling.
"""

from dataclasses import dataclass
from enum import Enum

from spk_architecture.access_v0 import (
    MemoryAccessIntentV0,
    MemoryDomainV0,
)


class MemorySpaceV0(str, Enum):
    ACTIVE = "ACTIVE"
    CANDIDATE = "CANDIDATE"
    SNAPSHOT = "SNAPSHOT"


def _identifier(name, value):
    if (
        type(value) is not str
        or not value
        or value.strip() != value
    ):
        raise ValueError(f"invalid {name}")


@dataclass(frozen=True, slots=True)
class MemoryTargetV0:
    target_id: str
    space: MemorySpaceV0
    epoch_id: str
    pe_id: str
    domain: MemoryDomainV0
    owner_node_id: str | None = None

    def __post_init__(self):
        for name in ("target_id", "epoch_id", "pe_id"):
            _identifier(name, getattr(self, name))

        if type(self.space) is not MemorySpaceV0:
            raise TypeError("invalid memory space")

        if type(self.domain) is not MemoryDomainV0:
            raise TypeError("invalid memory domain")

        if self.owner_node_id is not None:
            _identifier(
                "owner_node_id",
                self.owner_node_id,
            )

        if (
            self.domain is MemoryDomainV0.STATE
            and self.owner_node_id is None
        ):
            raise ValueError(
                "state memory requires a node owner"
            )


@dataclass(frozen=True, slots=True)
class MemoryTargetCatalogV0:
    targets: tuple[MemoryTargetV0, ...]

    def __post_init__(self):
        if type(self.targets) is not tuple:
            raise TypeError("targets must be a tuple")

        if not self.targets:
            raise ValueError("empty memory target catalog")

        if any(
            type(target) is not MemoryTargetV0
            for target in self.targets
        ):
            raise TypeError("invalid memory target")

        ids = [target.target_id for target in self.targets]

        if len(ids) != len(set(ids)):
            raise ValueError("duplicate memory target ID")

    def get(self, target_id: str) -> MemoryTargetV0:
        _identifier("target_id", target_id)

        for target in self.targets:
            if target.target_id == target_id:
                return target

        raise KeyError(target_id)


@dataclass(frozen=True, slots=True)
class MemoryTargetReferenceV0:
    intent: MemoryAccessIntentV0
    target_id: str

    def __post_init__(self):
        if type(self.intent) is not MemoryAccessIntentV0:
            raise TypeError("invalid memory access intent")

        _identifier("target_id", self.target_id)


def resolve_memory_target_v0(
    catalog: MemoryTargetCatalogV0,
    reference: MemoryTargetReferenceV0,
) -> MemoryTargetV0:
    """Resolve identity and check domain consistency.

    This function does NOT authorize access.
    Requester PE and target PE may differ.
    Request epoch and target epoch may differ.
    """

    if type(catalog) is not MemoryTargetCatalogV0:
        raise TypeError("invalid memory target catalog")

    if type(reference) is not MemoryTargetReferenceV0:
        raise TypeError("invalid memory target reference")

    target = catalog.get(reference.target_id)

    if reference.intent.domain is not target.domain:
        raise ValueError(
            "memory access domain mismatch"
        )

    return target
