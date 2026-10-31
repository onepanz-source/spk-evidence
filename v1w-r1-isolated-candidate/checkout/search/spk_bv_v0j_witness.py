#!/usr/bin/env python3
"""Synthetic witness only; checks pressure invariance and counts, NOT native BV v0h."""
import json
from spk_bv_research.evidence_cost_v0i import EvidenceCostLedger
from spk_bv_research.stress_v0i import fixture
from spk_bv_research.pressure_v0j import pressure_report


def main():
    l = EvidenceCostLedger()
    l.ingest_all(fixture())
    d = l.snapshot()
    p = pressure_report(d, per_link_capacity={f"link-{i}": 60 for i in range(4)},
                        global_capacity=200)
    assert d["physical_transmissions"] == 528
    assert d["distinct_contextual_votes"] == 33
    assert d["additional_transmissions_over_vote_count"] == 495
    assert p["transport_units"] == 528
    print(json.dumps({"status": p["status"], "physical_sha256": p["physical_sha256"],
                      "total_units": p["transport_units"],
                      "peak_global_backlog": max(x["peak_end_of_tick_backlog_units"]
                                                 for x in p["global_curves"]),
                      "total_link_backlog_peaks": sum(x["peak_end_of_tick_backlog_units"]
                                                      for x in p["link_curves"]),
                      "native_v0h_verified": False}, sort_keys=True))

if __name__ == "__main__":
    main()
