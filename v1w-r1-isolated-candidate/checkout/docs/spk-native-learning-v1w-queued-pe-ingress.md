# SPK Native Learning v1w: queued PE sensory admission to contextual BV-v1 learning

## Decision and scope

v1v computed the PE context **before** entering the episode and its optional API could be bypassed by invoking v1u's direct context entry point. v1w is a new *versioned cooperative admission coordinator*. Neither the frozen BV-v0e nor any previous v1 module is changed.

The host queues only raw channels, initial program, target and timing, with **no context ID**. The durable coordinator consumes the queue, runs the genuine original `_compute_local` PE classification, associates the PE signature with a persistent context, and admits the existing v1u native learning episode. The BV feedback and P program change continue to execute inside the v1 versioned PE/BV scheduler. The selected P is checked against the **actual first C PE read**.

Five journal stages, each with a causal hash and replayed verification:

1. `OBSERVED`: queued raw channels, with no contextual assignment.
2. `PE_CLASSIFIED`: exact PE emissions and original source pin.
3. `P_SELECTED`: signature, persistent context, and cooperative permit for BV episode creation.
4. `BV_COMPLETED`: same-scheduler A→B→C P update, C actual PE reads, verified SQLite result.
5. `CLOSED`: terminal journal receipt; next episode permitted only after complete closure.

## Gate and evidence

`search/spk_native_learning_v1w_queued_ingress_macro_gate.sh` requires the exact v1v PASS SHA-256 `172b2a1c72a526ca3cc49d9792d4d765b606f7d4b346f43a46ddc2ef50fdd59c` and the true frozen source SHA pins. It checks the six prior versioned manifests plus v1w manifest, runs the dedicated and inherited tests, generates two full-checkout independent reports, compares exact bytes, and publishes a new immutable report only on success.

Precommitted reference: five episodes, PE signals `s71,s72,s71,s72,s71`, contexts `ctx0,ctx1,ctx0,ctx1,ctx0`, 325 BV tick rows + 25 ingress stage rows, P versions `2,1,2,1,3`, P grants `2,1,0,0,1` (total 4). No new BV tick upon exact replay. Reversed first-observation order reverses the internal context numeric IDs while retaining learned policies by PE signature.

Eleven recovery cuts: 4 between ingress journal stages and 7 inside BV episode ticks. Adversarial: invalid cues do not permit P, mutated stage/PE/source/context/permit fails closed on audit, direct v1u API on a v1w-managed database fails at a SQLite trigger before allocating the episode, and two cooperating processes do not duplicate a P grant.

## Explicit boundaries, not waived

- **This does not classify inside a BV neuron tick**. `PE_CLASSIFIED` is a durable ingress event *before* original-v1 BV scheduler ticks. Carrying raw sensor occurrences through the actual BV network is further work.
- The test uses two **predeclared** cue classes `(40,42)` and `(41,43)` (plus admitted noise `99`), three programs `11,12,15`, and host-authored goals. There is no open-world context discovery or authentic independent sensor.
- A legacy caller may still use v1u/v1v on another database. The SQLite trigger fences direct calls **only on v1w-managed databases**, for cooperative callers; the host can bypass or rewrite SQLite and reseal evidence.
- A denied queued observation occupies its sequential epoch; this is **fail-stop**, not a generalized quarantine/dead-letter queue. Manual recovery of such invalid ingress is not implemented.
- Replay is deterministic original-computation reexecution, not heap restoration, distributed consensus, or safe physical action replay.
- **The frozen BV-v0e remains unchanged and learning-free.** Any native learning claim in this report refers strictly to versioned SPK v1 runtime.
