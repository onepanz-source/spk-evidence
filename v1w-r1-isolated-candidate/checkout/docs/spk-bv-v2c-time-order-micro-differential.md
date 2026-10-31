# SPK/* Back Validation v2c - finite causal-time micro scheduling differential

**Research extension only.** No changes to frozen Core, Network, Compiler, Architecture v1,
`spk_backvalidation_v0/live_dual_scheduler_v0e.py`, or the existing v2a executor.

## Accepted input and custody

- `--v2b`: byte-canonical, native-source-pinned **v2b** differential document.
- `--v2a`, `--v1q`, `--v1m`, `--v1z`, `--v1y`, `--v1x`: the exact source reports used by v2b.
- v2c fully recomputes v2b against these reports, including the 16 finite count
  comparisons and the *prior* original-order counterexample. All source-linked
  SHA-256 references and no-authority exclusions remain in force.
- v2a executor source must match the `v2b`/`v2a` source pin. The **new v2c** executor
  has a separately reviewed SHA-256 embedded in the CLI. On fwork the read-only
  frozen-source custody is checked again before/after the experiment.
- Outputs are new paths outside the checkout and cannot overwrite existing files;
  symlinks and aliases are rejected. `--contract-only` permits an honest offline
  rehearsal without claiming a fresh native custody check.

## Bounded micro-runtime, not native semantics

`time_order_executor_v2c.py` adds a new *independent* heap-based event loop.
Input occurrences for A are scheduled at `1 + i * stimulus_gap`. When a new
micro-operator emits on a route, the next node gets a work item at
`emission_tick + hop_delay`. Work with equal ticks is ordered by creation
sequence. These are deliberately stipulated operational semantics, **not**
a reconstruction of the hidden/entire scheduling rule of `execute_live_v0e`.

The emitter generates immutable source-owned `ObservationV2a` records while
processing arrivals, decisions and emissions. Recipient ingress is emitted
when the destination actually dequeues its event, rather than immediately
when the source enqueues it. A local `predecision_expectation` denotes an
immediate local preparation, **not** a sender commitment received ahead of
a native decision. The close record is logical only, not an independent
clock/certification of silence. The observer may fail/overflow without
changing the executor's returned forward result. Python in-process object
identity is not authentication. **No control evidence reaches native B**.

`relay`, `pair`, `block` are the same research-only micro rules as in v2a,
not aliases for SPK `CMP`. `bv_enabled` is only a label, without reverse
feedback, native state or an endogenous receiver value criterion.

## Results and falsification discipline

The *experimental* policy `(stimulus_gap=2, hop_delay=1)` on two stimuli
at ticks 1 and 3 yields the **micro** A/B emission timestamps:

| Sender | Original native posthoc (v1m) | New v2c micro-live |
|---|---|---|
| A | [1, 3] | [1, 3] |
| B | [2, 4] | [2, 4] |

This gives the relative A/B emitter order `ABAB`, unlike FIFO v2a `AABB`.
The same fixture matches 16 previously native-attested **count projections**
under the *experimenter-chosen count-fitting operator mapping*. Only
original/variant in BV OFF/ON possess the native A/B timestamp projections
in v1m; the other 12 factorial cells have **no matching native timing evidence**.

**Essential limitation:** gap=2, hop=1 were selected with knowledge of the
existing native trace. This is an *in-sample fit*, not an inferred rule,
independent validation, operational isomorphism, scheduler equivalence,
state equivalence, native timestamps certified to B, or real-time correctness.
The negative control with `stimulus_gap=3` gives A `[1,4]` and B `[2,5]`
while retaining `2/2/2` counts: matching counts do not identify timestamps
or the correct scheduler. Also `stimulus_gap=1` produces `AABB` again.
No cross-runtime token/event identity is inferred.

## Test and gate

```sh
cd ~/workspace/spk-backvalidation-v0
bash search/spk_bv_v2c_research_gate.sh

python -m search.spk_bv_v2c_temporal_differential \
  --v2b /tmp/spk-bv-v2b-native-micro-differential.json \
  --v2a /tmp/spk-bv-v2a-bounded-executor.json \
  --v1q /tmp/spk-bv-v1q-native-factorial-interactions.json \
  --v1m /tmp/spk-bv-v1m-native-passive-trace-projection.json \
  --v1z /tmp/spk-bv-v1z-native-observer-admission.json \
  --v1y /tmp/spk-bv-v1y-native-external-probe.json \
  --v1x /tmp/spk-bv-v1x-reference-observation-port.json \
  --out /tmp/spk-bv-v2c-time-order-differential.json
```

No native scheduler executions occur in this v2c CLI. Tests cover
source-identity/recomputation, event ordinals and parent tokens, arrival
latency, bounded queue capacity, observer faults, identity and timeline
falsification, all eight factorial interventions with BV OFF/ON, and
negative perturbations of the chosen temporal parameters.

## Unmet native proof obligations

No: full forward-state equivalence, BV reverse equivalence, native `CMP`
semantics, complete event-trace equivalence, independent clock and coverage,
recipient-local value criterion, native control packet delivery, authenticated
source/episode or absence certificate, causal credit, operator updates or learning.

Next bounded research step: derive an independent, testable **native
instruction/scheduler semantic witness** from the frozen source, then use
held-out schedules and perturbations for out-of-sample validation.
Do not promote source-owned *micro* evidence to native recipient knowledge.
