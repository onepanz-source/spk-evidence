"""SPK BV v0i: offline evidence/transport separation.

This module neither grants causal credit nor estimates truth, energy or utility.
A 'distinct vote' is only a distinct contextual observation key, NOT proof
of causal independence. Resource units are supplied abstract transport units.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
import re
from typing import Iterable, Mapping


class EvidenceCostContractError(ValueError):
    """Invalid evidence-cost trace. Fail closed, never repair provenance."""


_TOKEN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,95}\Z")
_FIELDS = frozenset((
    "transmission_id", "epoch", "observed_tick", "batch_tick",
    "origin", "batch_id", "receiver", "context_id", "evidence_code",
    "link_id", "path_id", "transport_units",
))


def _token(v: object, name: str) -> str:
    if not isinstance(v, str) or not _TOKEN.fullmatch(v):
        raise EvidenceCostContractError(f"{name}: expected nonempty bounded ASCII token")
    return v


def _nonnegative_int(v: object, name: str) -> int:
    if type(v) is not int or v < 0 or v > 2**63 - 1:
        raise EvidenceCostContractError(f"{name}: expected bounded nonnegative integer")
    return v


def _positive_int(v: object, name: str) -> int:
    x = _nonnegative_int(v, name)
    if x == 0:
        raise EvidenceCostContractError(f"{name}: must be positive")
    return x


def _sha(document: object) -> str:
    return sha256(json.dumps(document, sort_keys=True, ensure_ascii=True,
                             separators=(",", ":")).encode("ascii")).hexdigest()


@dataclass(frozen=True, slots=True)
class Reception:
    transmission_id: str
    epoch: int
    observed_tick: int
    batch_tick: int
    origin: str
    batch_id: str
    receiver: str
    context_id: str
    evidence_code: str
    link_id: str
    path_id: str
    transport_units: int

    def __post_init__(self) -> None:
        for name in ("transmission_id", "origin", "batch_id", "receiver",
                     "context_id", "evidence_code", "link_id", "path_id"):
            _token(getattr(self, name), name)
        for name in ("epoch", "observed_tick", "batch_tick"):
            _nonnegative_int(getattr(self, name), name)
        _positive_int(self.transport_units, "transport_units")
        if self.observed_tick < self.batch_tick:
            raise EvidenceCostContractError("observed_tick precedes batch_tick")

    @classmethod
    def from_dict(cls, document: Mapping[str, object]) -> "Reception":
        if not isinstance(document, Mapping) or set(document) != _FIELDS:
            raise EvidenceCostContractError("reception fields missing or unrecognized")
        return cls(**document)

    def as_dict(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in sorted(_FIELDS)}

    def vote_key(self) -> tuple[int, str, str, str, str]:
        return (self.epoch, self.origin, self.batch_id, self.receiver, self.context_id)

    def batch_key(self) -> tuple[int, str, str]:
        return (self.epoch, self.origin, self.batch_id)


@dataclass(frozen=True, slots=True)
class BudgetProfile:
    """Offline capacity hypotheses; NOT runtime reservations/admission."""
    max_transmissions: int = 100_000
    max_votes: int = 100_000
    max_units_per_tick: int | None = None
    per_link_units_per_tick: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _positive_int(self.max_transmissions, "max_transmissions")
        _positive_int(self.max_votes, "max_votes")
        if self.max_units_per_tick is not None:
            _positive_int(self.max_units_per_tick, "max_units_per_tick")
        for link, capacity in self.per_link_units_per_tick.items():
            _token(link, "link_id")
            _positive_int(capacity, "per_link capacity")


class EvidenceCostLedger:
    """Order-independent, exact offline ledger with replay-safe transmission IDs."""

    def __init__(self, profile: BudgetProfile | None = None) -> None:
        self.profile = profile or BudgetProfile()
        self._transmissions: dict[tuple[int, str], Reception] = {}
        self._votes: dict[tuple[int, str, str, str, str], Reception] = {}
        self._batch_ticks: dict[tuple[int, str, str], int] = {}

    def ingest(self, receipt: Reception) -> bool:
        """Return True only for an unseen physical transmission ID.

        Entire input batch is consistent or an error is raised; a rejected
        record causes no state change. Ingest repeats with identical ID are
        audit replays, NOT additional observed packets.
        """
        if not isinstance(receipt, Reception):
            raise EvidenceCostContractError("expected Reception")
        tx_key = (receipt.epoch, receipt.transmission_id)
        prior_tx = self._transmissions.get(tx_key)
        if prior_tx is not None:
            if prior_tx != receipt:
                raise EvidenceCostContractError("transmission ID reused with altered envelope")
            return False
        batch_key = receipt.batch_key()
        prior_tick = self._batch_ticks.get(batch_key)
        if prior_tick is not None and prior_tick != receipt.batch_tick:
            raise EvidenceCostContractError("identified batch has inconsistent birth tick")
        vote_key = receipt.vote_key()
        prior_vote = self._votes.get(vote_key)
        if prior_vote is not None and prior_vote.evidence_code != receipt.evidence_code:
            raise EvidenceCostContractError("contextual vote carries conflicting evidence_code")
        if len(self._transmissions) >= self.profile.max_transmissions:
            raise EvidenceCostContractError("transmission-memory bound reached")
        if prior_vote is None and len(self._votes) >= self.profile.max_votes:
            raise EvidenceCostContractError("vote-memory bound reached")
        self._transmissions[tx_key] = receipt
        self._batch_ticks[batch_key] = receipt.batch_tick
        if prior_vote is None:
            self._votes[vote_key] = receipt
        return True

    def ingest_all(self, receipts: Iterable[Reception]) -> None:
        for receipt in receipts:
            self.ingest(receipt)

    def snapshot(self) -> dict[str, object]:
        physical = [r.as_dict() for _, r in sorted(self._transmissions.items())]
        votes = [{
            "epoch": epoch, "origin": origin, "batch_id": batch_id,
            "receiver": receiver, "context_id": context,
            "batch_tick": self._batch_ticks[(epoch, origin, batch_id)],
            "evidence_code": self._votes[key].evidence_code,
        } for key in sorted(self._votes)
            for epoch, origin, batch_id, receiver, context in (key,)]
        per_tick: dict[tuple[int, int], int] = {}
        per_link: dict[tuple[int, int, str], int] = {}
        units = 0
        for r in self._transmissions.values():
            tick_key = (r.epoch, r.observed_tick)
            link_key = (r.epoch, r.observed_tick, r.link_id)
            per_tick[tick_key] = per_tick.get(tick_key, 0) + r.transport_units
            per_link[link_key] = per_link.get(link_key, 0) + r.transport_units
            units += r.transport_units
        overloads: list[dict[str, object]] = []
        for (epoch, tick), actual in sorted(per_tick.items()):
            cap = self.profile.max_units_per_tick
            if cap is not None and actual > cap:
                overloads.append({"kind": "tick", "epoch": epoch, "tick": tick,
                                  "observed_units": actual, "capacity_units": cap})
        for (epoch, tick, link), actual in sorted(per_link.items()):
            cap = self.profile.per_link_units_per_tick.get(link)
            if cap is not None and actual > cap:
                overloads.append({"kind": "link", "epoch": epoch, "tick": tick,
                                  "link_id": link, "observed_units": actual,
                                  "capacity_units": cap})
        physical_n = len(physical)
        logical_n = len(votes)
        return {
            "schema": "spk-bv-evidence-transport-cost/v0i",
            "status": "RESEARCH_OBSERVATION_ONLY",
            "physical_transmissions": physical_n,
            "distinct_contextual_votes": logical_n,
            "additional_transmissions_over_vote_count": physical_n - logical_n,
            "transport_units": units,
            "physical_per_vote_numerator": physical_n,
            "physical_per_vote_denominator": logical_n,  # 0 means undefined
            "observed_neurons": len({n for r in self._transmissions.values()
                                     for n in (r.origin, r.receiver)}),
            "identified_batches": len(self._batch_ticks),
            "per_tick_units": [{"epoch": epoch, "tick": tick, "units": value}
                               for (epoch, tick), value in sorted(per_tick.items())],
            "per_link_tick_units": [{"epoch": epoch, "tick": tick, "link_id": link,
                                     "units": value}
                                    for (epoch, tick, link), value in sorted(per_link.items())],
            "budget_overloads": overloads,
            "physical_sha256": _sha(physical),
            "contextual_vote_sha256": _sha(votes),
            "excluded_claims": ["causal-credit", "evidence-independence", "truth",
                                "utility", "learning", "energy", "compression",
                                "runtime-admission", "hardware-performance"],
        }
