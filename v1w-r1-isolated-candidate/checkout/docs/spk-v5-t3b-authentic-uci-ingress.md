# SPK V5-T3b: Original UCI indexed CSV ingestion hotfix

## Root cause

Actual UCI Occupancy Detection files use a seven-column header naming `date,Temperature,Humidity,Light,CO2,HumidityRatio,Occupancy` but **eight data cells**. The first data cell is an unnamed, sequential one-based row index. T3a's `csv.DictReader` interpreted that as the `date` field and treated the last cell as an extra field under `None`, correctly refusing unexpected rows but not accounting for this authentic format. T3a's synthetic selftest used exactly seven cells, so it did not catch this format error.

## Remediation

Add `read_authentic_uci` in a separate research module. It parses original bytes, checks exact header, eight cells, monotonic sequential record indices, monotonic timestamps, bounded finite physical sensor readings, binary external occupancy, and resource bounds. Index and occupancy **never enter A's input**. T3a's feature thresholds, bounded A1b execution, explore-then-commit pilot, public split and evaluator remain **unchanged**. The SHA-256 is computed from **the unmodified original UCI file**, not normalized CSV. T3a's 49 existing source pins stay exactly pinned.

## Scientific interpretation

The open public dataset supports a **public external-task** comparison, not a third-party-blinded held-out test. Selection among three predefined fixed programs is a small shadow bandit, not general reinforcement learning, endogenous BV reward or neural program mutation. Snapshot data was downloaded and provided by the researcher, without cryptographically authenticated acquisition. No production release, runtime promotion, or frozen architecture edits.

## Local usage

```bash
cd ~/workspace/spk-backvalidation-v0
tar --keep-old-files -xzf ~/Scaricati/SPK_V5_T3b_Authentic_UCI_CSV_Ingress_Hotfix.tar.gz
bash search/spk_v5_t3b_authentic_uci_gate.sh
python search/spk_v5_t3b_authentic_uci.py pilot --data ~/Scaricati/occupancy/datatraining.txt --out /tmp/spk-v5-t3b-uci-pilot.json
sha256sum /tmp/spk-v5-t3b-uci-pilot.json
python search/spk_v5_t3b_authentic_uci.py evaluate --data ~/Scaricati/occupancy/datatest2.txt --pilot /tmp/spk-v5-t3b-uci-pilot.json --pilot-sha256 <PILOT_SHA_64_HEX> --out /tmp/spk-v5-t3b-uci-public-eval.json
```

Do not copy labels into the feature input and do not use `datatest.txt` as a post-training test: it occurs **before** the training interval.
