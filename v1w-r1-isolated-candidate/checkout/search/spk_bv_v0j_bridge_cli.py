#!/usr/bin/env python3
"""Explicit mapping only: native BV packet NDJSON -> exact v0i evidence ledger."""
import argparse
import json
from pathlib import Path
from spk_bv_research.native_bridge_v0j import (read_manifest, bridge_packet_ndjson, NativeBridgeError)
from spk_bv_research.evidence_cost_v0i import EvidenceCostContractError, BudgetProfile
from spk_bv_research.pressure_v0j import pressure_report


def main(argv=None):
    p = argparse.ArgumentParser(description="BV research explicit packet mapping (no guesses)")
    p.add_argument("--mapping", type=Path, required=True)
    p.add_argument("--packets", type=Path, required=True)
    p.add_argument("--link-capacity", action="append", default=[], metavar="LINK_ID:UNITS")
    p.add_argument("--global-capacity", type=int)
    a = p.parse_args(argv)
    try:
        mapping = read_manifest(a.mapping)
        caps = {}
        for entry in a.link_capacity:
            link, sep, value = entry.rpartition(":")
            if not sep or link in caps:
                raise NativeBridgeError("invalid/duplicate link capacity")
            caps[link] = int(value)
        snapshot = bridge_packet_ndjson(a.packets, mapping)
        if caps or a.global_capacity is not None:
            snapshot["pressure"] = pressure_report(snapshot, per_link_capacity=caps,
                                                  global_capacity=a.global_capacity)
        print(json.dumps(snapshot, sort_keys=True, separators=(",", ":")))
        return 0
    except (NativeBridgeError, EvidenceCostContractError, OSError, ValueError, KeyError) as exc:
        p.exit(2, f"BV native bridge rejected: {exc}\n")

if __name__ == "__main__":
    raise SystemExit(main())
