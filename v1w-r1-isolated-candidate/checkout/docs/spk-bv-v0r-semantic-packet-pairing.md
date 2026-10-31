# SPK BV v0r: native structural semantic packet matching

The v0q audit reported `bv2` and `bv3` with changes in assessment, route and evidence fields when joined by the same packet ID across scheduler policies. Those IDs are generated within each run, so they are **not** warranted global identities.

This research-only module reads the two original source-pinned v0o captures (hash-seed 13 and 811) using inherited v0o/v0p/v0q verifiers. It pairs a delivery with its grant and referenced assessment **inside** each run. It then computes a canonical semantic signature from **all non-temporal and non-local-ID fields** across assessment, delivery and grant.

Excluded fields: assessment `id`, `tick`; delivery `packet_id`, `assessment_id`, `tick`; grant `packet_id`, `assessment_id`, `tick`, `delivered_at`, `wait`. No other fields are silently discarded, and evidence ordering/multiplicity is preserved. Reported wait is a native metric, **not** the grant-to-delivery tick difference or hardware latency.

Signatures are compared as multisets. Only signatures occurring exactly once in each run are allowed to produce a specific cross-policy packet association. Duplicate signatures remain ambiguous. The tool does not infer causal equivalence, global event identity, feedback ON/OFF, learning or energy costs, and does not change frozen code.

Run in existing research worktree:

```bash
bash search/spk_bv_v0r_research_gate.sh
python -m search.spk_bv_v0r_semantic_pairing \
  --capture-13 /tmp/spk-bv-v0o-native-importfix-13.json \
  --capture-811 /tmp/spk-bv-v0o-native-importfix-811.json \
  --out /tmp/spk-bv-v0r-semantic-pairing.json
bash search/spk_bv_credit_v0a_full_regression.sh
```

The CLI only creates new files under `/tmp` outside the worktree. On any mismatch in source hashes or independent captures it rejects; no synthesis or execution of the native simulator occurs. This is a record-field equivalence analysis only. If a full semantic signature bijection is verified, the next *different* research activity is to establish a controlled feedback-off run with unchanged input and effective resource constraints.
