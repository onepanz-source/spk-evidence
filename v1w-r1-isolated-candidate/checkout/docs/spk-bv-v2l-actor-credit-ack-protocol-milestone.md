# SPK/* Back Validation v2l — Derived actor credit/ack protocol

## Gate decision

**Source-pinned derived research gate PASS; frozen-native actor credit and
event-priority contract remain BLOCKED.** This milestone adds no changes to
frozen Core, Network, Architecture, Compiler or scheduler v0e, and proves
neither native actor learning nor adaptive weight/activation behavior.

v2k demonstrated **156** control-service grants charged to *derived*
resource counters, together with exact reconstruction of the complete
original native result. v2l adds a separate derived **per-actor credit
event register**: a receiver judgment must be transported, delivered to its
source actor, admitted into bounded service and charged against derived
resources **before** it may receive an actor-addressed acknowledgement.

Acknowledgements are bound to all of:

- The actor ID and PE assignment from the pinned native `_admit` result.
- The original emitted spike, actual receiver/issuer, receiver-local batch
  decision and positive or negative response.
- Control creation/due ticks and service tick, including whether service
  occurred during a native-loop residual slot or derived control-only tail.
- The actor's strictly increasing event epoch, credit before/after, and
  previous acknowledgement root.

The event is acknowledged **exactly once** and counted as `+1` or `-1` in a
bounded, separately held research register. A deterministic SHA-256 digest
links successive acknowledgements for each actor; audit rejects reordering,
replay, altered credit, changed identity, bad digest and inconsistency with
resource grants. This is **in-process audit integrity**, not signature,
external identity proof or cryptographic authentication. The native neuron
has not yet consumed the control event.

## Explicit semantic admission rules

| Condition | Derived actor credit outcome |
|---|---|
| Authenticated-by-source-code receiver judgment delivered and resource serviced | Ack, once, in its source actor's journal |
| Positive receiver judgment (`outputs` nonempty) | `+1`, only after admitted resource grant |
| Negative receiver judgment (`outputs` empty) | `−1`, only after admitted resource grant |
| Transport loss, callback fault or overflow | No ack; no inference from missing data |
| Full credit register or acknowledgement quota | Delivered but *withheld*, no resource grant or negative certificate |
| Strict per-actor due-order head blocked | Newer records for that actor cannot bypass it |
| Tail disabled or resource pressure | Unconsumed delivered records are explicit, not renamed into silence proofs |

For reproducibility v2l chooses a policy of maximum absolute credit **256**
per actor, maximum **512** acks over the run, strict per-actor FIFO by
`(due_tick, judgment_id)`, and the previously chosen v2k cost model
(**1 abstract PE unit + 2 abstract local O/E memory units** per event).
One event per actor per tick is permitted. These are **research policies**,
not canonical SPK algebraic rules or hardware specifications. Alternative
policy interventions exercise zero/one credit capacity, one global ack,
loss/fault, mailbox overflow and no tail.

The v2l completion code retains the pinned v2k inline and tail resource
bookkeeping and uses an admission-aware tail termination. When every
delivered record is explicitly disallowed by the credit policy, it does
**not** manufacture up to 32 empty control-only ticks. Future-due control
events still have bounded opportunities to mature. Native scheduler time
and state are always unchanged.

## Actual experiment — 15 workloads x three native BV modes

| Source-backed measurement | Result |
|---|---:|
| Original native executions, including negative fixture | 46 |
| Normal derived actor-credit executions, including negative fixture | 46 |
| Derived policy/loss/pressure variants, including capped negative fixture | 316 |
| **All new executable replays** | **408** |
| Exact full native projection parity | **45/45** |
| Exact v2k derived resource-ledger parity under default policy | **45/45** |
| Receiver-authored controls delivered in normal matrix | 156 |
| Service grants booked to derived counters | 156 |
| Distinct causally linked actor-credit acknowledgements | **156/156** |
| Inline derived control service / research tail service | 140 / 16 |
| Abstract PE / O+E memory units booked | 156 / 312 |
| Normal delivered but unacknowledged | 0 |
| Native neuron state, weights, operator changes | **0** |

### Source-backed intervention differences

These totals sum 45 paired workload/BV cells; variants are independent
runs over otherwise equivalent original native workloads.

| Policy intervention | Controls delivered | Actor acks | Explicit withheld/pending |
|---|---:|---:|---:|
| Normal bounded derived admission | 156 | 156 | 0 |
| Transport loss | 0 | 0 | 0 |
| Callback fault | 0 | 0 | 0 |
| Bounded queue/mailbox overflow | 45 | 45 | 0 |
| Credit capacity = 0 | 156 | 0 | **156 withheld** |
| Credit capacity = 1 per actor | 156 | 90 | **66 withheld** |
| Global ack quota = 1 per run | 156 | 45 | **111 withheld** |
| Tail disabled | 156 | 138 | **18 pending** |

In the zero-credit intervention, all 156 controls *were delivered* but no
one had permission to apply their credit: zero resource grants, zero
acknowledgements and zero synthetic idle tail ticks. This separation rules
out an easy but invalid inference that a packet's mere delivery proves
actor-local credit application.

The separate real-negative-B native fixture produces **two genuine
receiver-negative judgments**, both acknowledged to source actor A under
normal limits, giving A `−2` in its *derived* credit register. Under a
one-credit bound, only one can be admitted: A's register is `−1`, and the
other still exists as delivered but withheld evidence. It is **not**
silence, forgotten error, native learning or a command to mutate a neuron.

## Reproduction and evidence pinning

- Canonical predecessor v2k report SHA-256:
  `774758196caeefd0d8ff629d8c4aca2d543b6e3dee8c2f2fda51eb236afe6ad4`.
- Frozen scheduler source SHA-256:
  `2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9`.
- The CLI verifies canonical exact predecessor bytes, v2h/v2i/v2j/v2k
  inherited source hashes, new v2l source hashes, and source integrity
  again after replay. Unsafe inputs, existing outputs, symlinks, drift,
  replay and forged mailbox entries fail closed.
- New `unittest` count: **19** (must all pass on `fwork`).
- Inherited selected `pytest` regressions run separately on `fwork`;
  `pytest` need not be installed in the research preparation sandbox.

Apply the additive release to the checkout once:

```bash
cd ~/workspace/spk-backvalidation-v0
tar --keep-old-files -xzf \
  ~/Scaricati/SPK_BV_v2l_Derived_Actor_Credit_Ack_Protocol_Milestone.tar.gz

bash search/spk_bv_v2l_actor_credit_protocol_gate.sh \
  /tmp/spk-bv-v2k-integrated-actor-resource-admission.json \
  /tmp/spk-bv-v2l-actor-credit-protocol.json

bash search/spk_bv_v2l_inherited_regression_gate.sh
```

Both report paths must be outside the checkout; output must not already
exist. Repeat replays use a *fresh* output filename and must produce the
same report hash. Do not re-extract the same additive archive: it contains
files with exactly one v2l name and is designed for clean checkpoints.

## Deliberately unresolved native contract

The next gate is a **native actor event priority and credit-consumption
contract**: define the native scheduler's event acceptance point, resource
charge before/against forward service (including starvation), message
ownership and acknowledgement semantics, queue ordering, bounded liveness,
and a **separate** opt-in native actor credit register or handler. Test
observable native effects and safety under contention, not only derived
projection parity. Even after this work, source-dependent synaptic
weights and adaptation remain a future topic, not a v2l promotion.
