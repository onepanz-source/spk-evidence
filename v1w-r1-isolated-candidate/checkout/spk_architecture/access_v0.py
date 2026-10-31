"""SPK logical memory access intents v0.

No physical memory operations or scheduling.
"""

from dataclasses import dataclass
from enum import Enum


class MemoryDomainV0(str, Enum):
    PROGRAM = "P"
    STATE = "S"
    EVENT = "E"
    OBSERVATION = "O"


class ActivityV0(str, Enum):
    EXECUTE = "EXECUTE"
    ROUTER = "ROUTER"
    VERIFY = "VERIFY"
    LEARN = "LEARN"
    REMODEL = "REMODEL"
    OBSERVER = "OBSERVER"


class AccessIntentKindV0(str, Enum):
    PROGRAM_REFERENCE = "PROGRAM_REFERENCE"
    STATE_LOAD = "STATE_LOAD"
    STATE_COMMIT = "STATE_COMMIT"
    BATCH_CONSUME = "BATCH_CONSUME"
    EMISSION_RECORD = "EMISSION_RECORD"
    ROUTE_ENQUEUE = "ROUTE_ENQUEUE"
    OBSERVATION_RECORD = "OBSERVATION_RECORD"
    OBSERVATION_READ = "OBSERVATION_READ"
    SNAPSHOT_READ = "SNAPSHOT_READ"
    CANDIDATE_PROGRAM_WRITE = "CANDIDATE_PROGRAM_WRITE"


_INTENT_DOMAINS = {
    AccessIntentKindV0.PROGRAM_REFERENCE:
        MemoryDomainV0.PROGRAM,
    AccessIntentKindV0.STATE_LOAD:
        MemoryDomainV0.STATE,
    AccessIntentKindV0.STATE_COMMIT:
        MemoryDomainV0.STATE,
    AccessIntentKindV0.BATCH_CONSUME:
        MemoryDomainV0.EVENT,
    AccessIntentKindV0.EMISSION_RECORD:
        MemoryDomainV0.EVENT,
    AccessIntentKindV0.ROUTE_ENQUEUE:
        MemoryDomainV0.EVENT,
    AccessIntentKindV0.OBSERVATION_RECORD:
        MemoryDomainV0.OBSERVATION,
    AccessIntentKindV0.OBSERVATION_READ:
        MemoryDomainV0.OBSERVATION,
    AccessIntentKindV0.SNAPSHOT_READ:
        MemoryDomainV0.STATE,
    AccessIntentKindV0.CANDIDATE_PROGRAM_WRITE:
        MemoryDomainV0.PROGRAM,
}

_NODE_REQUIRED = {
    AccessIntentKindV0.PROGRAM_REFERENCE,
    AccessIntentKindV0.STATE_LOAD,
    AccessIntentKindV0.STATE_COMMIT,
    AccessIntentKindV0.BATCH_CONSUME,
    AccessIntentKindV0.EMISSION_RECORD,
    AccessIntentKindV0.ROUTE_ENQUEUE,
}


@dataclass(frozen=True, slots=True)
class MemoryAccessIntentV0:
    request_id: int
    epoch_id: str
    pe_id: str
    activity: ActivityV0
    kind: AccessIntentKindV0

    node_id: str | None = None
    event_time: int | None = None
    quantity: int = 1

    def __post_init__(self):
        if (
            type(self.request_id) is not int
            or self.request_id < 0
        ):
            raise ValueError("invalid request_id")

        for name in ("epoch_id", "pe_id"):
            value = getattr(self, name)

            if (
                type(value) is not str
                or not value
                or value.strip() != value
            ):
                raise ValueError(f"invalid {name}")

        if type(self.activity) is not ActivityV0:
            raise TypeError("invalid activity")

        if type(self.kind) is not AccessIntentKindV0:
            raise TypeError("invalid access intent kind")

        if self.node_id is not None:
            if (
                type(self.node_id) is not str
                or not self.node_id
                or self.node_id.strip() != self.node_id
            ):
                raise ValueError("invalid node_id")

        if self.kind in _NODE_REQUIRED:
            if self.node_id is None:
                raise ValueError("node_id required")

        if self.event_time is not None:
            if (
                type(self.event_time) is not int
                or self.event_time < 0
            ):
                raise ValueError("invalid event_time")

        if (
            type(self.quantity) is not int
            or self.quantity <= 0
        ):
            raise ValueError("invalid quantity")

    @property
    def domain(self) -> MemoryDomainV0:
        return _INTENT_DOMAINS[self.kind]
