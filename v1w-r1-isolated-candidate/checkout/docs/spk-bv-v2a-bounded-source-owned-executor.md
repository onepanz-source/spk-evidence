# SPK BV v2a · Bounded source-owned experimental executor

**Research executable, not a promotion of the frozen SPK scheduler.**

This release introduces a separately versioned Python *micro-executor* at
`spk_backvalidation_v2/observed_scheduler_v2a.py`. The observer is invoked
**inside the execution code** where decisions, emissions, receiver ingress
admissions and closure occur. Unlike v1x post-return projections or v1y Python
line tracing, these records are produced at the *micro-executor's own semantic
callsites*. This assertion refers only to the new bounded runtime, not the
frozen `execute_live_v0e` or its PE instructions.

## Domain restriction

- Three locally named processors A -> B -> C, FIFO message queue; only integer
  stimulus `1`, at most 16 environment inputs.
- Operations `relay` (emit for each ingress), `pair` (emit on every second
  ingress of this node), and `block` (emit nothing). These are **research
  micro-operators, NOT the frozen SPK CMP instruction** and not certified
  algebraic rewrites.
- `bv_enabled` is a scenario label only. There is no BV feedback engine in v2a.
- Logical ticks count *this executor's own recorded phases*. The closure
  record is **not** an independent timing, delivery or silence certificate.
- A frozen dataclass record includes episode, ordinal, logical tick, phase,
  actor, target, decision ID, parent token and emitted event token. Python
  process values do not authenticate external source or recipient identities.
- `ObserverV2a` has bounded storage, persistent overflow/fault flags and
  immutable records. It never gates decisions, routes, returns or SPK feedback.
- Observer messages go to a **research sink**, not to the native B neuron.

### Eight bounded comparisons

Four micro-operator configurations × BV label OFF/ON. Every pair runs the actual
v2a forward function twice, with and without the observer, then compares typed
canonical result bytes. The observer event sequence is cross-checked against
the result's decision ledger, emission counts and routed ingress counts.

| Micro configuration | Expected micro A/B/C emissions | Relation to frozen SPK |
| --- | --- | --- |
| relay_chain | 2 / 2 / 2 | Count-level analogy only |
| block_at_A | 0 / 0 / 0 | Not CMP(2) equivalence |
| pair_at_B | 2 / 1 / 1 | Not CMP(2) equivalence |
| pair_at_C | 2 / 2 / 1 | Not CMP(2) equivalence |

Matching these few counts to older native reports is **not** full forward
parity, control-protocol equivalence, native event authenticity or proof of
neuron-owned feedback. The observer emits no absence witnesses, independent
clock guarantees, local value judgments, updates or learning.

## Chain custody / fail-closed CLI

CLI inputs: canonical v1z, v1y and v1x reports. It recomputes the entire v1z
canonical report from the predecessors, demands **byte-exact** identity and
checks their SHA-256 relationships. It also verifies source pins of the frozen
scheduler and Architecture **on fwork** before and after the bounded v2a runs.
Inputs and output must not be inside the repository or symlinks. Output must
not exist. The v2a executor module's source bytes are hashed and checked for
a change during execution.

For offline research when the frozen modules are not present, `--contract-only`
is available. The report clearly marks
`frozen_native_source_pins_rechecked_in_this_run=false`; do not promote that
report as native custody. On fwork, omit `--contract-only`.

```bash
cd ~/workspace/spk-backvalidation-v0
bash search/spk_bv_v2a_research_gate.sh
python -m search.spk_bv_v2a_versioned_executor \
  --v1z /tmp/spk-bv-v1z-native-observer-admission.json \
  --v1y /tmp/spk-bv-v1y-native-external-probe.json \
  --v1x /tmp/spk-bv-v1x-reference-observation-port.json \
  --out /tmp/spk-bv-v2a-bounded-executor.json
```

Only additively named files, with **zero edits to frozen Core, Network,
Compiler, Architecture v1, scheduler v0e**, or existing BV research modules.

## What remains to demonstrate

1. Faithful full-native/SPK operator and scheduler state parity, beyond count
   coincidences on a bounded three-node example.
2. A source-authenticated independent observation port, plus a distinct
   receiver-control route with actual delivery receipt and fault management.
3. Independent coverage and predecision commitments that support an honest
   silence/absence claim.
4. Receiver-owned declared value function; causal decision identity; native
   feedback judgment, bounded updates and a learning experiment.

Until all such properties are separately verified, the ten v1z native
promotion obligations remain `verified=false`.
