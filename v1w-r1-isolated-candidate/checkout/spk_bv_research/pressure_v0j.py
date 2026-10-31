"""Hypothetical capacity-pressure accounting over BV v0i snapshots.

This is an ideal work-conserving fluid/unit service reference, not a simulator
schedule, credit assignment, measured latency, physical timing, or compression.
No spike arrivals are present: feedback-only pressure can be an underestimate.
"""
from __future__ import annotations
from .evidence_cost_v0i import EvidenceCostContractError


def _capacity(x):
    if type(x) is not int or x <= 0 or x > 2**63 - 1:
        raise EvidenceCostContractError("capacity must be a positive bounded int")
    return x


def _curve(epoch, link, timeline, capacity):
    capacity = _capacity(capacity)
    backlog = 0
    peak = 0
    max_tick = None
    instant_over = 0
    last_tick = None
    for tick, arrivals in timeline:
        if last_tick is not None:
            # Consume during empty intermediate ticks without iterating them.
            backlog = max(0, backlog - capacity * (tick - last_tick - 1))
        backlog = max(0, backlog + arrivals - capacity)
        if backlog > peak:
            peak, max_tick = backlog, tick
        if arrivals > capacity:
            instant_over += 1
        last_tick = tick
    trailing = (backlog + capacity - 1) // capacity if last_tick is not None else 0
    return {"epoch": epoch, "link_id": link, "capacity_units_per_tick": capacity,
            "recorded_tick_count": len(timeline), "arrival_units": sum(n for _, n in timeline),
            "peak_end_of_tick_backlog_units": peak,
            "peak_backlog_tick": max_tick,
            "instant_overload_recorded_ticks": instant_over,
            "last_arrival_tick": last_tick,
            "idealized_clear_tick": last_tick + trailing if last_tick is not None else None,
            "trailing_clearance_ticks": trailing}


def pressure_report(snapshot, *, per_link_capacity, global_capacity=None):
    if not isinstance(snapshot, dict) or snapshot.get("schema") != "spk-bv-evidence-transport-cost/v0i":
        raise EvidenceCostContractError("expected v0i snapshot")
    if not isinstance(per_link_capacity, dict):
        raise EvidenceCostContractError("link capacity map required")
    if global_capacity is not None:
        _capacity(global_capacity)
    for name, val in per_link_capacity.items():
        if not isinstance(name, str) or not name:
            raise EvidenceCostContractError("invalid link_id")
        _capacity(val)
    link_data = {}
    global_data = {}
    # Validate schema and chronology even for reports read from JSON files.
    for item in snapshot["per_link_tick_units"]:
        epoch, tick, link, units = (item[k] for k in ("epoch", "tick", "link_id", "units"))
        if type(epoch) is not int or epoch < 0 or type(tick) is not int or tick < 0 \
                or not isinstance(link, str) or not link or type(units) is not int or units <= 0:
            raise EvidenceCostContractError("malformed per-link tick accounting")
        if (epoch, tick, link) in link_data:
            raise EvidenceCostContractError("duplicate link tick accounting")
        link_data[(epoch, tick, link)] = units
        global_data[(epoch, tick)] = global_data.get((epoch, tick), 0) + units
    if sum(link_data.values()) != snapshot["transport_units"]:
        raise EvidenceCostContractError("per-link totals disagree with transport_units")
    declared = {}
    for item in snapshot["per_tick_units"]:
        epoch, tick, units = (item[k] for k in ("epoch", "tick", "units"))
        if (type(epoch) is not int or epoch < 0 or type(tick) is not int
                or tick < 0 or type(units) is not int or units <= 0):
            raise EvidenceCostContractError("malformed per-tick accounting")
        if (epoch, tick) in declared:
            raise EvidenceCostContractError("duplicate global tick accounting")
        declared[(epoch, tick)] = units
    if declared != global_data:
        raise EvidenceCostContractError("per-tick totals disagree with per-link accounting")
    if global_capacity is not None:
        global_groups = {}
        for (epoch, tick), units in global_data.items():
            global_groups.setdefault(epoch, []).append((tick, units))
        global_curves = [_curve(epoch, "ALL_LINKS", sorted(groups), global_capacity)
                         for epoch, groups in sorted(global_groups.items())]
    else:
        global_curves = []
    link_curves = []
    groups = {}
    for (epoch, tick, link), units in link_data.items():
        groups.setdefault((epoch, link), []).append((tick, units))
    for (epoch, link), entries in sorted(groups.items()):
        if link not in per_link_capacity:
            raise EvidenceCostContractError(f"missing capacity for observed link: {link}")
        link_curves.append(_curve(epoch, link, sorted(entries), per_link_capacity[link]))
    return {"schema":"spk-bv-idealized-pressure/v0j", "status":"COUNTERFACTUAL_CAPACITY_ONLY",
            "transport_units":snapshot["transport_units"],
            "physical_sha256":snapshot["physical_sha256"],
            "link_curves":link_curves, "global_curves":global_curves,
            "excluded_claims":["scheduling-equivalence", "hardware-capacity", "actual-delay",
                               "energy", "spike-contention", "causal-credit", "learning", "compression"]}
