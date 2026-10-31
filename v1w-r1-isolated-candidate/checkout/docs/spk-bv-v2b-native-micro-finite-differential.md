# SPK BV v2b | Finite native/micro differential boundary

**Falsification-focused research artifact. No alteration to frozen SPK source.**

## What is compared, and what is not

V2b receives three previously attested reports, **v2a**, **v1q** (16 frozen
native factorial executions) and **v1m** (post-return native route traces),
plus v1z/v1y/v1x predecessors to reconstruct v2a. It does **not** repeat a
native scheduler execution. On fwork the CLI rechecks frozen source hashes
while the micro-executor executes, but a source-hash check is not a new native
semantic event or independently trusted emission.

The comparison runs 8 intervention masks `none,A,B,C,AB,AC,BC,ABC` × BV mode
`off/on`, each as a *fresh* v2a micro-executor instance twice, with observer
OFF and ON. This means 16 distinct micro cases and 32 micro executions, not 32
new SPK native runs. For each case it checks exact finite projections:
`emissions_by_neuron`, edges A→B and B→C, and terminal emission count.
Every micro event ledger is checked against its executed decision ledger.

The **deliberately count-fitting representation** is:
- For A changed by native `CMP(1)→CMP(2)`: research `block` at A.
- For B or C changed by native `CMP(1)→CMP(2)`: research `pair` there.
- Unmodified nodes: research `relay`.

These are not native `CMP` implementations. Matching all 16 counts on one
fixed two-input fixture does not imply that their transition systems, states,
causal provenance, scheduler, timestamps, BV propagation, event identity,
operator semantics or behavior on other inputs agree. Native BV ON produces
assessments in its own scheduler; v2a BV ON is only a label. Native assessment
counts are preserved separately, explicitly **not reproduced** by v2a.

## Explicit observable mismatch

For the **original** native program, the independently produced v1m post-return
source traces give:

- A→B: sender emission timestamps `[1,3]`
- B→C: sender emission timestamps `[2,4]`
- Therefore source order `ABAB` over these two edges.

In the bounded FIFO executor v2a on `relay_chain`, emission observations occur
in source order `AABB` (all initial A inputs precede B dequeues).
The resulting counts are still `A=2,B=2,C=2` for either BV label.

Thus the temporal sender-order projections are **unequal on the original
fixture**. This is a *counterexample to trace-order equivalence of these two
finite executions*, not proof that the native runtime's timestamps and v2a
logical ticks share a metric, and not an event-ID pairing. V1m is producer-side
posthoc evidence and not receiver-local evidence.

Any changed, ambiguous or tied timestamp trace causes a **fail-closed** audit;
v2b does not interpolate a convenient ordering. Inputs must be canonical,
source-bound, non-aliased and external to the repository. Native references
are matched across q/m/y and v2a is **fully rerun** and compared byte-for-byte
to the input v2a report, using the exact source hash and its predecessors.

## On fwork

```bash
cd ~/workspace/spk-backvalidation-v0
bash search/spk_bv_v2b_research_gate.sh
python -m search.spk_bv_v2b_differential_boundary \
  --v2a /tmp/spk-bv-v2a-bounded-executor.json \
  --v1q /tmp/spk-bv-v1q-native-factorial-interactions.json \
  --v1m /tmp/spk-bv-v1m-native-passive-trace-projection.json \
  --v1z /tmp/spk-bv-v1z-native-observer-admission.json \
  --v1y /tmp/spk-bv-v1y-native-external-probe.json \
  --v1x /tmp/spk-bv-v1x-reference-observation-port.json \
  --out /tmp/spk-bv-v2b-native-micro-differential.json
```

`--contract-only` supports an **offline** review with
`frozen_native_source_pins_rechecked_in_this_run=false`. On fwork omit it. The
output must not already exist. No symlinks, overwrites or in-repo input/output.

## Promotion status

Count projection equality is a **verified finite result**; a temporal
counterexample **rejects any full trace-equivalence claim on this fixture**.
No native `CMP` mapping, BV feedback semantics, receiver knowledge, independent
absence witness, local value criterion, scored feedback or operator learning
has been established. No amount of observer instrumentation overrides that
boundary. The next research activity should address **the actual SPK
instruction/transition semantics and scheduler interleaving** on a separately
versioned executor, rather than tuning counts further.
