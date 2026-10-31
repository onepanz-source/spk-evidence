# SPK BV v0p: native policy identity audit (research)

Read-only diagnostic over the **existing** v0o native fixture: 2 feedback-enabled runs with a shared setup, `forward-first` and `feedback-first`. No scheduler invocation. Does not add ON/OFF experiments. It does not write to the SPK frozen packages.

## Safety / provenance
- Loads both independent fixture snapshots with the inherited native capture validator.
- Requires fixed witnessed fixture digest, equal payload in both captures, equal source pins, and current source digest matching the repository.
- Requires both run `enabled=true`; named `forward-first` and `feedback-first` as in the observed native fixture.
- Preserves duplicated event signatures as *multisets* rather than pairing events by list position.
- Matches feedback packets by `packet_id` only when all non-temporal payload fields agree; matches forward occurrences by native `id` only with immutable payload agreement.
- Separates timestamp distributions from identity-aligned changes. If an ID has different immutable fields, reports mismatch and does not count it as matched.
- Conserved terminal/emission content + final state are reported; discrepancies do not silently turn into a claim of equal output.

## Non-claims
No causal benefit, no true feedback-on/off comparison, no true per-packet energy, no guaranteed equality of effective inputs, no hardware profile, no architecture promotion, no learning.

## Run

```bash
cd ~/workspace/spk-backvalidation-v0
python -m pytest -q tests/test_spk_bv_v0p_policy_identity.py
python -m search.spk_bv_v0p_policy_identity \
  --capture-13 /tmp/spk-bv-v0o-native-importfix-13.json \
  --capture-811 /tmp/spk-bv-v0o-native-importfix-811.json \
  --out /tmp/spk-bv-v0p-native-policy-identity.json
```

Read the output JSON before deciding on the next experiment. The next distinct phase will require a true ON/OFF workload pair, not these two feedback-enabled policies.
