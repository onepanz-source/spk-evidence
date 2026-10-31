# BV v0v: link capacity × cross-PE in-flight limit

This experimental module extends the v0u link scan, without modifying frozen SPK Architecture, Compiler, Core, Network, or the v0e simulator.

## Experimental question

When link fabric capacity `fabric_slots_per_tick` increases from 1 to 2, do the benefits depend on having sufficient simultaneous in-flight cross-PE occurrences (`max_inflight_occurrences`)? This tests **resource interaction** in the bounded 3-neuron v0e model, not hardware topology.

## Design

Six cells: `(fabric, max_inflight)` = `(1,4)`, `(2,4)`, `(1,1)`, `(1,2)`, `(2,1)`, `(2,2)`. Each executes 3 arms: feedback OFF, ON/forward-first, ON/feedback-first. Exactly **18 native executions per process**, repeated in separate processes with `PYTHONHASHSEED` 13 and 811. The direction link capacity remains at 1. Network, stimuli, placement, service, memory, all other transport fields and controls are held constant within each cell. Original input and each altered input are hashed before and after every run, with failures propagated. No partial or silently dropped cells.

The first two cells must replay all metrics, terminal ticks and full-result hashes of v0u `(fabric,direction)=(1,1)` and `(2,1)` respectively, on exactly the same fixture bytes and source pins, through the pre-existing v0t/v0o verification chain. The scan checks that recorded peak in-flight occupancy never exceeds the imposed limit.

## Interpretation constraints

Within-cell OFF/ON differences can be interpreted as model interventions. Between-cell resource alterations change the realized dynamic schedules; never assert identical *effective* workloads. A maximum in-flight count is an abstract transport quota, **not a buffer measured in bytes**. A low quota can increase deferrals, change ordering or trigger bounded-horizon rejection. Every rejection must fail the scan; none is classified automatically as zero throughput or converted into a success.

This experiment does not measure informational gain, causal learning, hardware power, physical latency, n-node scalability, architecture promotion, nor v0h 528-record stress equivalence.

## fwork commands

```bash
cd ~/workspace/spk-backvalidation-v0
# extract archive first
bash search/spk_bv_v0v_research_gate.sh
bash search/spk_bv_v0v_native_gate.sh /tmp/spk-bv-v0v-native /tmp/spk-bv-v0u-native-13.json
bash search/spk_bv_credit_v0a_full_regression.sh
```

Upload the resulting `/tmp/spk-bv-v0v-native-13.json` after native replay gate PASS. Do not claim success based only on this package's synthetic tests.
