# SPK/* Back Validation v2h — Pinned native-derived actor semantics

## Release decision

**Research gate PASS; frozen native actor-feedback integration BLOCKED.**

This release does not change Core/Network/Compiler/Architecture or the pinned
`live_dual_scheduler_v0e.py`. It reads that source only after its SHA-256 and
v2g callsite inventory are verified, compiles a separate `execute_live_v0e`
function in memory and installs an isolated research `ReceiverPortV2h`.

This is not equivalent to a new frozen native sender/receiver protocol.
The research port is scoped to actors in one Python process; original actor
state, program operators and scheduling/transport resources are untouched.

## Runtime-owned causal boundary

Four semantic anchors in the frozen function are pinned by SHA and AST line:

| Anchor | Native v0e line | Research intervention |
|---|---:|---|
| Native tick | 125 | Deliver due, separately queued control to actor-scoped mailbox |
| Spike ingress | 136 | Verify that a real inflight occurrence reached its target |
| Committed batch | 194 | Compute receiver-local judgment from that actor's actual outputs |
| Source occurrence | 217 | Register true derived-runtime emission identity and provenance |

The four v2g callsite wrappers (`_admit`, `_admit_plan`, two `offer_feedback`)
are retained and independently counted, not treated as actor-level evidence.

Source occurrence identity, actual target/channel, emitted tick and lineage
are captured when the scheduler creates the forward occurrence. An ingress
must match this source-owned record; a receiver batch must admit that same
occurrence before a judgment can be issued. The negative criterion is explicit:
the receiving actor's committed batch had no emitted outputs. This criterion
is *chosen for research* and is **not** a theorem of the SPK algebra or a
trained notion of a beneficial decision.

Control is put in a bounded, deterministic, separate queue. A causally
validated packet can only reach its sender-scoped mailbox; loss, callback
failure, queue saturation and mailbox overflow never imply a negative vote or
an absence certificate. After the last native tick, the research-only control
queue is drained explicitly; that delivery is counted as `post_native_deliveries`
and is **not** passed into the frozen scheduler or neuron program.

## Actual release gate (2026-10-19 local isolated source snapshot)

- v0e source hash: `2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9`.
- v2g report hash: `eb108df313fb705f6a6b54a08edfa10abc0df170bf98f45249f1068243d703f0`.
- 15 native workloads x 3 BV policy modes.
- 45 fresh original-native runs; 45 fresh semantic-port derived-native runs;
  135 additional derived runs (loss, fault + observer fault, overflow + observer
  overflow). The negative-source experiment adds 1 original + 1 derived run.
  Total explicit runtime runs: **227**.
- 45/45 native/derived full-result summaries and result SHA-256 match the
  historical v2g report, with source custody rechecked after the matrix.
- Source occurrence events: 156. Target ingress events: 156. Receiver-local
  judgments: 156. Normal sender-mailbox deliveries: 156. Negative judgments in
  this historical relay-only matrix: zero. Control-only post-native deliveries:
  15. Original frozen actor-feedback state updates: zero.
- Additional native-backed negative B fixture: 2 actual ingresses, 2 actual
  receiver-side negative judgments, A sender score -2, no causal absence claim,
  native/derived result equality.
- Nine new stdlib unittest methods PASS including native/derived work, forged
  lineage, wrong target, duplicate/replay, time order, source drift, bounded
  overflow, loss, callback fault, negative judgment and predecessor tamper.

## Reproduction on `fwork`

Extract the new v2h release tarball at the root of the existing SPK checkout.
Keep all existing files untouched (the release only adds versioned files).

```bash
bash search/spk_bv_v2h_derived_receiver_port_gate.sh \
  /tmp/spk-bv-v2g-derived-native-callsite-parity.json \
  /tmp/spk-bv-v2h-derived-actor-feedback.json
```

The output file must not already exist. Inputs and outputs must be outside the
repository, must not be symlinks, and the original v2g bytes must match the
pinned SHA-256. Follow with inherited selected regressions:

```bash
bash search/spk_bv_v2h_inherited_regression_gate.sh
```

The isolated execution environment provided for preparing this release did
not contain `pytest`; therefore **inherited pytest regressions are not claimed
as locally executed**. They remain a distinct required fwork gate. The new
unittest/native replay gate above did run to completion.

## Excluded claims and next functional gate

No cryptographic producer authentication; no native PE-level isolated mailbox
or actor event-loop intake; no hardware/network trust or N-node equivalence;
no universal timing-independent parity; no algebra-derived reward criterion;
no automatic causal learner update, operator adaptation, commit or rollback;
no cold promotion or alteration to frozen SPK contracts.

The next functional checkpoint must route feedback through an *actor-owned
runtime intake* with custody at the receiving source actor, preserve frozen
forward semantics under resource pressure, and establish an explicit contract
for credit consumption before any learning is claimed.
