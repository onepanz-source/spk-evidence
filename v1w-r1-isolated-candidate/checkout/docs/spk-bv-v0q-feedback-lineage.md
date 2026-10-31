# SPK BV v0q: native feedback lineage divergence audit

Goal: Diagnose non-temporal feedback payload mismatches for packet IDs `bv2` and `bv3` observed in the v0p audit. This is a **read-only** postprocessing module, not a changed network execution.

Inputs: two matching, independently captured native v0o typed fixtures, whose shared fixture SHA-256 is `887ad94cc89d91083950d9a99fff10007edc160df370c6bdef5b1d9048167fb4`, with producer source hashes independently rechecked against the local worktree.

Scope: validate per-run delivery–grant pairing and assessment references; compare each packet's fields across the two policies; report non-temporal field changes separately from timestamps and reported waits; corroborate the v0p mismatch set. No merge of contexts or identities and no inference that two same-named packet IDs represent equivalent causal facts across runs.

Excluded: feedback ON/OFF, causal treatment effect, v0h 528-packet equivalence, energy, hardware latency, cost of learning, system improvement, frozen Architecture v1 changes.

Run:

```bash
bash search/spk_bv_v0q_research_gate.sh
python -m search.spk_bv_v0q_lineage_differential \
 --capture-13 /tmp/spk-bv-v0o-native-importfix-13.json \
 --capture-811 /tmp/spk-bv-v0o-native-importfix-811.json \
 --out /tmp/spk-bv-v0q-feedback-lineage.json
```

The CLI refuses existing destinations. The gate is a focused local regression, and cannot replace the full inherited Architecture v1 custody gate or the full 3892+ suite. Inspect `packet_diagnostics` and `assessment_non_temporal_changes` to determine whether the mismatch is a payload identity shift or an underlying assessment/route difference. Next experimental block should create feedback OFF using the native v0e API after confirming treatment isolation in the same scenario.
