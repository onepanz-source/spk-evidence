# SPK BV v0t — Source-bound native OFF/ON triad (research only)

## Purpose and source identity

Reconstruct the native `execute_live_v0e(case, fabric, tplan, pplan, mplan, lplan, bv)` contract identified by the v0s API probe. The native fixture is `search.spk_bv_v0e_live_evidence.fixture()` returning `(case, fabric, (tplan, pplan, mplan, lplan))`. No new simulator, scheduler or frozen source is introduced. All three interventions call the same existing native scheduler, on exactly the same in-memory fixture, using a new `LiveBVPlanV0e` per run.

The three configurations are:

1. `off`: `enabled=False, priority='forward-first'`.
2. `on_forward_first`: `enabled=True, priority='forward-first'`.
3. `on_feedback_first`: `enabled=True, priority='feedback-first'`.

The plan's remaining fields are untouched defaults. The intervention comparisons are: toggling `enabled` with priority held at `forward-first`, changing `priority` with `enabled=True`, and the combined OFF→feedback-first change. The third comparison is **not** a single-factor intervention.

## Fail-closed controls

* Require exact hashes of the native scheduler, native fixture producer and native v0e test as observed in the v0s source probe. Also verify actual module `__file__` paths after imports and ensure sources did not change during experiment. These are source-byte custody checks, not proof of semantic independence.
* Build `fixture()` **once** and hash its complete typed dataclass/tuple representation before and after each native execution; reject input mutation. This verifies supplied arguments stay constant, **not** that each run consumes the same effective sequence of events.
* Require OFF to produce no feedback assessments, deliveries, grants, votes, service or memory units, and no timeline feedback sends. Require both ON arms to actually transport feedback.
* Require basic resource accounting and exact integer types. Do not equate reported grant `wait` with hardware transmission latency. Do not infer energy.
* Compare emitted and terminal output payload multisets without timestamps, as well as final neuron state hashes. Differences are *reported*, not automatically declared failures.
* Optional-but-recommended reference: enforce that shared input and BOTH ON results match the previously captured and source-pinned native v0o fixture with SHA-256 `887ad94cc89d91083950d9a99fff10007edc160df370c6bdef5b1d9048167fb4`. The gate requires this reference; it does not infer an OFF run from v0o.
* Emit a bounded JSON report outside the repository, refusing overwrites and symlinks as input. Replay in two separate Python processes with different `PYTHONHASHSEED` values and compare the *entire* reports exactly.
* Architecture v1 and Core/Network/Compiler stay frozen. The gate inherits the existing Architecture v1 source guard from v0n; the native experiment is separate.

## Commands on fwork

```bash
cd ~/workspace/spk-backvalidation-v0
source ~/workspace/spk-algebra/.venv/bin/activate

tar -tzf ~/Scaricati/spk-bv-v0t-three-arm-native-control-research.tar.gz
tar -xzf ~/Scaricati/spk-bv-v0t-three-arm-native-control-research.tar.gz

bash search/spk_bv_v0t_research_gate.sh

bash search/spk_bv_v0t_native_gate.sh \
  /tmp/spk-bv-v0t-native \
  /tmp/spk-bv-v0o-native-importfix-13.json

bash search/spk_bv_credit_v0a_full_regression.sh
```

The native gate writes `/tmp/spk-bv-v0t-native-13.json` and `/tmp/spk-bv-v0t-native-811.json` without overwrites; select a new prefix if needed. Both must be identical, with native `off` and two native `on` replays. Upload the 13 report and gate output for next checkpoint, **not** the full native capture; the report contains counts, hashes and delta tables.

## Interpretation limits

The OFF vs ON-forward-first comparison supports model-internal effects of changing the feedback switch under the **declared identical static input, mapping, budgets and implementation**. It cannot by itself establish whether the information from the feedback improves decisions, because this v0e scheduler has no learning or promotion. Also, changes in `fabric_link_contention` counts describe failed/requeued opportunities in the scheduler, not physical costs; sampled service/memory/link sums are abstract occupancy/work proxies. The network is the pinned three-node reference fixture, not an N-node or distributed-hardware claim. No equivalence with the separate 528-message v0h stress experiment.

## Expected progression

If v0t passes the native gate, the research result is a valid bounded three-arm **intervention on the simulator configuration**, not a validated learning advantage. Separate follow-up should examine matched forward-event completion distributions and feedback cost scaling over multiple controlled source-pinned workloads before designing a learning policy.
