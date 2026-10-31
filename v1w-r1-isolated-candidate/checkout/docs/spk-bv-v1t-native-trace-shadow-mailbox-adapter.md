# SPK BV v1t · Native posthoc trace to isolated receiver mailbox adapter

## Purpose and scope

Use **native producer-owned evidence** from the already attested v1m 4-arm
execution (original / variant, BV OFF / ON) as an input to a **new, isolated,
in-process, read-only experiment** that delivers disclosure packets to a shadow
B mailbox. The native forward scheduler, Core, Network, Architecture and
Compiler remain frozen. This is NOT a native B input port, a native two-port
sensor, a native message transport, independent witness/coverage, or learning.

The exact distinction under test is between:

* `experimenter_posthoc_counts_not_receiver_visible`: the experimenter's
  source-side copy of the native trace, NOT attached to B;
* `receiver_view`: B's locally projected ingress count and the verified
  *laboratory packets actually delivered* to its mailbox. The B object has no
  reference to the native producer trace or to any factorial/alternative world;
* the shadow episode labels `shadow.native-trace.<arm>.<mode>`: bookkeeping of
  independent **lab** experiments. They are NOT identities pairing events
  between two counterfactual worlds.

Even when B sees a `sender_count` message it is a *fabricated lab disclosure
of a genuine posthoc count*, not producer-authenticated communication. Python
role-specific object seals are a closed-process test assumption, not native or
cryptographic sender authentication.

## Inputs and bounded reconciliation

Source documents: canonical `spk-bv-v1s-receiver-disclosure-channel.json` and
`spk-bv-v1m-native-passive-trace-projection.json`; the full predecessor chain
from v1r to v0w is also required by the CLI. The report-only analyzer validates
exact metadata, source hashes, completeness and native edge count consistency:

| Native v1m arm | A emitted (A→B) | B received | B consumed | Source of evidence |
|---|---:|---:|---:|---|
| original, BV OFF | 2 | 2 | 2 | Native scheduler posthoc trace |
| original, BV ON | 2 | 2 | 2 | Native scheduler posthoc trace |
| variant, BV OFF | 0 | 0 | 0 | Native scheduler posthoc trace |
| variant, BV ON | 0 | 0 | 0 | Native scheduler posthoc trace |

It checks B→C is the **distinct** direct edge and does not grant C direct
A→C authority. The original has two native ingress occurrence identifiers, but
v1t **does not invent cross-world occurrence pairing**, and aggregates only
bounded per-run counts (not fabricated event-specific receipts). There are 58
closed-world laboratory sessions, using two arms, two modes, and 15 plans,
except that an ingress-contradiction case requires positive original ingress.

## Delivery experiment

The `BShadowMailbox` possesses only the projected local ingress count,
process-local role seals and delivered packets. It checks episode, direct edge,
issuer, immutable type, timing, replay protection and content. Five packet
kinds are supported: pre-episode expectation, sender-port count, sender
coverage, receiver coverage, and experimenter-labelled decision. Expectation
and coverage messages are **illustrations**, not read from the frozen scheduler.

A sender count is a **declared posthoc producer count**, never a standalone
coverage certificate. Control loss, missing expectation or either coverage
record fails closed to an unknown classification. A genuine positive B ingress
stays just a posthoc receiver projection, without independent origin/utility.
If the sender count contradicts the local ingress count, classification is
`CONFLICTING_EVIDENCE_UNKNOWN`.

Even with all five kinds, a variant's empty source port is classified
`LAB_DISCLOSED_ZERO_SENDER_COUNT_NO_NATIVE_AUTHORITY`. It is not a B-native
absence witness or a decision-causal statement. Omitting decision disclosure
cannot alter the sender-port/transport classification; visibility of a chosen
operator does not show that it caused the absent emission.

Adversarial scenarios cover forged role seal, replay, late delivery, wrong
episode, wrong edge/issuer, source count contradiction, mismatched source
records and fail-closed CLI inputs/output. Cross-episode source evidence cannot
enter another shadow mailbox.

## CLI chain and attestations

1. `bash search/spk_bv_v1t_research_gate.sh` (separate full inherited gate).
2. `python -m search.spk_bv_v1t_native_trace_mailbox_adapter` with `--v1s`
   plus **all arguments required by v1s** (`--v1r`, `--v1q`, `--v1p`, `--v1o`,
   `--v1n`, `--v1m`, `--v1l`, `--v1k`, `--v1j`, `--v1i`, `--v1h`, `--v1g1`,
   `--v1f`, `--v1e`, `--v1d`, `--v1c`, `--v1b1`, `--v1a`, `--v0w`, `--out`).
3. Rebuild **v1s** using its CLI, including its source-bound v1r/v1q/v1m
   native replay chain. Reject unless the rebuilt v1s bytes match the
   supplied v1s **byte for byte**. Reject aliases, repository output writes,
   output overwrite and mutated evidence during replay.
4. Only this verified CLI can set
   `inherited_native_v1s_recomputation_verified_in_this_run=true`.
   The report-only analyzer and local preview set **false**. This flag attests
   inherited native provenance only, NOT that shadow B or a new native channel
   exists.

There are NO new native scheduler runs attributable to v1t itself. Its
`source_native_scheduler_runs_in_v1m=4` concerns already observed native traces.

## Interpretation / next requirements

The exercise demonstrates a **data-path adapter** between a finite native
posthoc report and a lab actor model; it does not yet demonstrate an
independent runtime tap or receiver-visible transmission. Before requesting
any receiver-originated value judgment, future research must specify genuinely
provenance-bearing producer messages, independent coverage witnesses, control
channel backpressure and drop semantics, tamper-resistant receiver acknowledgments,
a receiver-local predeclared criterion, and decision-causal bindings.

This module provides no certified algebra rewrite, no scored feedback, no
operator commit/rollback, and no learning. It is deliberately incremental and
research-only.
