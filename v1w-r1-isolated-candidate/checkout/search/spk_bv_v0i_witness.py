#!/usr/bin/env python3
"""Reproducible standalone 64-node stress witness with 528 observed receptions."""
import json
from spk_bv_research.evidence_cost_v0i import BudgetProfile, EvidenceCostLedger, Reception


from spk_bv_research.stress_v0i import fixture


def main():
    ledger = EvidenceCostLedger(BudgetProfile(
        max_transmissions=528, max_votes=33,
        max_units_per_tick=250,
        per_link_units_per_tick={"link-0": 60},
    ))
    ledger.ingest_all(fixture())
    result = ledger.snapshot()
    assert result["physical_transmissions"] == 528
    assert result["distinct_contextual_votes"] == 33
    assert result["additional_transmissions_over_vote_count"] == 495
    assert result["transport_units"] == 528
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
