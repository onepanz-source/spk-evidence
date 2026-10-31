# BV v1l · Isolated two-port observer and noninterference boundary

## Scope and facts carried forward

BV v1k on fwork reexecuted v1j and preserved the native v1h result: A's
`CMP(1) -> CMP(2)` intervention stops A→B and B→C on the bounded fixture.
B has a direct A→B route; C has only an A→B→C ancestry. In v1k, the
`shadow.missing` example contains a declared expectation, not an authenticated
absence witness. No native scored judgments or learned operator updates exist.

The **new research-only** v1l laboratory uses exactly one hypothetical hop
A→B, not a new SPK link or a modification of the frozen scheduler. It never
claims to observe the native receiver. The experiment is not a full native
network counterfactual and cannot promote any `shadow` witness to `native`.

## Protocol conditions, as implemented in an in-process sandbox

The model provides a bounded predecision expectation, a receiver acknowledgement
before the decision, an independently controlled observation-coverage flag for
both sender **output port** and receiver **input port**, and a deadline. It
uses matched event identity at the two ports. These are **laboratory controls**;
passing a JSON dictionary with the same fields does not make it an authentic
producer-signed witness. No external signature verification or native observer
exists in this prototype. The in-process typed `Episode` is a test stimulus,
not a credential.

The contract classifies one expected event:

| Result | Observable preconditions in the lab | Meaning |
|---|---|---|
| `DELIVERED` | Both ports observed the same event | Delivery in the lab |
| `SENDER_PORT_SILENCE` | Complete independent coverage, no event at either port | No observed sender-port emission in the lab; **not** proof of the neuron's internal decision |
| `TRANSPORT_GAP` | Sender output-port event, no receiver input-port event | Missing transport across this measured hop |
| `COVERAGE_LOSS` | Either port or independent control coverage missing | No conclusion about absence |
| `PENDING` | Deadline not reached | No conclusion about absence |
| `NO_EXPECTATION` | No predecision commitment | No conclusion about a promised event |
| `LATE_ACK` | Acknowledgement missing before decision | No authorized expectation |
| `MISMATCHED_INGRESS` | Receiver observes an unmatched event | No proof of delivery of expected ID |

The sender-port silence world and the transport-gap world produce the **same
receiver ingress projection** (empty). The independent sender-side port
observation makes them distinguishable *in the closed-world model*. If the
independent coverage channel fails, v1l refuses to call the absence witnessed.
A silent sender cannot disable the coverage channel by suppressing the event
under test, by construction of the laboratory transition system. Real-world
trust in such a channel is a *future* proof obligation.

Note: an expected event is a promise about a source/output. An observer at the
link **cannot identify why the neuron did not emit**. Differentiating an
internal computation that suppressed emission from an upstream input that never
occurred needs a separately attested causal decision record. And comparing B's
feedback to C's feedback as independent votes remains unjustified.

## Important negative claims

- No v1l laboratory event is evidence of a native absence in SPK v0e.
- No native sender decision, control heartbeat, receiver acknowledgement or
  coverage certificate is introduced by v1l.
- The experimental observer's access to both ports is an explicit stronger
  observation model than the v1j ingress-only native receiver.
- No external utility, neuron-produced judgment, causal credit, state update,
  learned performance, hardware metric, or architecture promotion is identified.

## fwork installation and source-bound verification

Extract the incremental archive at the root of `~/workspace/spk-backvalidation-v0`.
Run:

```bash
bash search/spk_bv_v1l_research_gate.sh
```

For the reference v1k produced **with `--demo-shadow`**, the following CLI
reexecutes v1k and all its inherited native verifications, checking the v1k
bytes. The `--demo-lab` flag adds ten *synthetic* controlled laboratory worlds.

```bash
python -m search.spk_bv_v1l_two_port_observer \
  --v1k /tmp/spk-bv-v1k-receiver-witness-authority.json \
  --v1j /tmp/spk-bv-v1j-receiver-silence-observability.json \
  --v1i /tmp/spk-bv-v1i-native-feedback-silence.json \
  --v1h /tmp/spk-bv-v1h-isolated-network-counterfactual.json \
  --v1g1 /tmp/spk-bv-v1g1-native-original-route-lineage.json \
  --v1f /tmp/spk-bv-v1f-receiver-preference-polarity.json \
  --v1e /tmp/spk-bv-v1e-conditional-receiver-impact.json \
  --v1d /tmp/spk-bv-v1d-native-declared-criterion-13.json \
  --v1c /tmp/spk-bv-v1c-native-sensitivity.json \
  --v1b1 /tmp/spk-bv-v1b1-native-operator-replay.json \
  --v1a /tmp/spk-bv-v1a-symbolic-holdout.json \
  --v0w /tmp/spk-bv-v0w-native-13.json \
  --demo-lab \
  --out /tmp/spk-bv-v1l-two-port-observer.json
```

If the v1k reference contains a custom non-demo `--shadow-protocol`, v1l
rejects it rather than guessing input provenance. A v1k reference without a
shadow protocol is also supported.

The CLI never replaces an existing output and refuses symlink/alias input
paths and reference files inside the repository. Validation of the native
lineage is inherited from v1k and performed before the laboratory audit.

## Next scientific step

Design a native-instrumentable **observation API** whose commitments and
coverage are not sourced from the monitored spike path. Prove whether the
receiver can access and verify that API without replacing its epistemic state
with global simulator knowledge. Separately define an independently attested
neuron decision and a receiver-valued objective before any learning experiment.
