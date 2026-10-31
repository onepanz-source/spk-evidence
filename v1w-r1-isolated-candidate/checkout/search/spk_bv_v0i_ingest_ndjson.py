#!/usr/bin/env python3
"""Offline normalized NDJSON adapter endpoint; maps NO BV v0h API implicitly."""
import argparse
import json
from pathlib import Path
from spk_bv_research.evidence_cost_v0i import (
    BudgetProfile, EvidenceCostLedger, EvidenceCostContractError, Reception,
)


def main(argv=None):
    parser=argparse.ArgumentParser(description="Validate and account for normalized BV v0i receptions")
    parser.add_argument("--input", type=Path, required=True,
                        help="Newline-delimited JSON, exactly one Reception object per line")
    parser.add_argument("--max-transmissions", type=int, default=100_000)
    parser.add_argument("--max-votes", type=int, default=100_000)
    parser.add_argument("--max-units-per-tick", type=int)
    parser.add_argument("--link-budget", action="append", default=[], metavar="LINK_ID:CAPACITY",
                        help="Offline link capacity per tick; may repeat for multiple links")
    args=parser.parse_args(argv)
    link_caps={}
    for item in args.link_budget:
        try:
            key, val=item.rsplit(":", 1)
            if key in link_caps:
                raise ValueError("duplicate link budget")
            link_caps[key] = int(val)
        except ValueError as exc:
            parser.error(f"invalid --link-budget {item}: {exc}")
    try:
        ledger=EvidenceCostLedger(BudgetProfile(
            max_transmissions=args.max_transmissions, max_votes=args.max_votes,
            max_units_per_tick=args.max_units_per_tick,
            per_link_units_per_tick=link_caps))
        with args.input.open(encoding="utf-8") as lines:
            for num, line in enumerate(lines, 1):
                if not line.strip():
                    continue
                try:
                    ledger.ingest(Reception.from_dict(json.loads(line)))
                except (EvidenceCostContractError, ValueError, TypeError, json.JSONDecodeError) as exc:
                    raise EvidenceCostContractError(f"line {num}: {exc}") from exc
        print(json.dumps(ledger.snapshot(), sort_keys=True, separators=(",", ":")))
        return 0
    except (EvidenceCostContractError, OSError) as exc:
        parser.exit(2, f"BV v0i input rejected: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
