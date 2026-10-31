# SPK BV v0w: temporal workload sensitivity, native bounded v0e

Research-only layer. Frozen `spk_architecture_v1/`, Core/Network/Compiler and
`spk_backvalidation_v0/live_dual_scheduler_v0e.py` are **not** modified.

## Experimental design

Five external stimulus profiles are constructed deterministically from the
pinned native v0e fixture with exactly two original externally injected events
at ticks `(1,3)`. All have **the same three-neuron topology and programs**.

1. `baseline`: original `(1,3)`.
2. `coincident`: move second event to tick 1, `(1,1)`.
3. `second_plus_1`: `(1,4)`.
4. `second_plus_3`: `(1,6)`.
5. `repeated_episode`: repeat both external events after eight ticks,
   `(1,3,9,11)`.

For each profile, we test capacity pairs `(fabric, in-flight)` of
`(1,4)`, `(2,1)`, `(2,4)` while directional grants remain 1.
This distinguishes a fabric constraint from an in-flight constraint.
Each cell reuses *one immutable input instance* for three explicit interventions:
`OFF`, `ON forward-first`, `ON feedback-first`. This gives **45 executions per
Python process**, rerun under two distinct hash seeds. Any rejected execution
fails the gate without omitting the cell. The event count is NOT kept constant
across all profiles (particularly repeated_episode): contrasts are valid only
**within** cells, not as a single all-load causal effect.

### Custody and reference anchors

- Pin original runtime and fixture source bytes to known SHA-256 values before
  importing the native modules; verify imported module locations and recheck.
- Hash original fixture before/after all runs and each mutated cell before/after
  every arm; verify the only case changes are in `events`.
- Compare all three baseline capacity profiles against
  full native **v0v** report records, including whole-result hashes and metrics.
- Verify v0v has inherited v0u → v0t → v0o chain.
- Abort on unknown fixture shape, unsupported quota, changes to sources,
  any hidden mutation, mismatched output anchor, overwritten report, or
  report inside the repository.
- Include the full native `resources.contention` dictionary by reason in every
  arm; fabric-link-only aggregates cannot identify in-flight blocking.

### Interpretation

This study measures model-internal scheduling, contention and budget proxies.
It DOES NOT infer learning, causal value of neighbor judgments, physical energy,
N-node scalability, universal bandwidth thresholds, or hardware timing.
The original bounded v0e scheduler does not modify neuron programs. No results
should be promoted into frozen Architecture v1 on these data alone.

## On fwork

```bash
cd ~/workspace/spk-backvalidation-v0
tar -xzf ~/Scaricati/SPK_BV_v0w_Temporal_Workload_Research.tar.gz
bash search/spk_bv_v0w_research_gate.sh
bash search/spk_bv_v0w_native_gate.sh /tmp/spk-bv-v0w-native /tmp/spk-bv-v0v-native-13.json
bash search/spk_bv_credit_v0a_full_regression.sh
```

Upload `/tmp/spk-bv-v0w-native-13.json`; a second process report can be
retained locally if the native gate prints PASS. Never overwrite reports.
