# SPK Back Validation v2p — derived actor ACK consumer handoff

## Research verdict

`DERIVED_ACTOR_CONSUMER_ACK_HANDOFF_EXACTLY_ONCE_NATIVE_PARITY`

v2p adds a **separate derived actor consumer** after the independently
resource-charged v2l ACK event. An ACK is an entitlement and a journal entry;
it is **not** identical to application into the consumer's actor-local credit
register. The consumer has its own state, per-actor sequence, SHA-linked
receipts, source/owner/ACK binding, FIFO replay audit, bounded throughput,
explicit backlog and optional consumer-only tail ticks.

The consumer borrows the v2l ACK entitlement and claims **zero additional**
PE/memory budget; no native physical consumer service cost is established.
Consumer-only tail turns are not added to the native resource timeline.
No frozen native scheduler/actor, network, algebra, compiler or operator is
modified. The credit applications are **derived actor-scoped research state**,
not proof of native actor learning, weight updates or native intake.

## Reproduction on `fwork`

Extract the release from the existing `~/workspace/spk-backvalidation-v0`
directory, with the existing signed v2o predecessor report retained:

```bash
cd ~/workspace/spk-backvalidation-v0

tar --keep-old-files -xzf \
  ~/Scaricati/SPK_BV_v2p_Actor_Consumer_Handoff_Milestone.tar.gz

bash search/spk_bv_v2p_actor_consumer_handoff_gate.sh \
  /tmp/spk-bv-v2o-native-causal-admission.json \
  /tmp/spk-bv-v2p-actor-consumer-handoff.json

bash search/spk_bv_v2p_inherited_regression_gate.sh
```

All gates are **fail-closed**: changed pinned code, changed canonical v2o
predecessor bytes, altered resource/ACK provenance, receiver mailbox forgery,
actor/owner mismatch, replay, FIFO violation, invalid capacity, invalid
consumer tick or backlog tampering cause rejection. A successful run requires
a **new, non-existing, repository-external** output path; reruns should use a
different filename, not overwrite the signed report.

## Source-backed results (local v2p report)

The 15 recipes × 3 native BV modes × 2 PE capacity regimes establish
90 exact entire-result frozen-native projections. Each PE regime has:

| Capacity | Native parity | ACKs | Applied actor credits | Pending | Pre-forward actor grants | Native-tick applications | Consumer-tail applications |
|:--|--:|--:|--:|--:|--:|--:|--:|
| Original (3 slots) | 45/45 | 156 | 156 | 0 | 88 | 61 | 95 |
| Contended (1 slot) | 45/45 | 156 | 156 | 0 | 32 | 32 | 124 |

Further 45-cell interventions under contended capacity:

| Consumer policy | ACKs retained | Applied | Visible pending | Native parity |
|:--|--:|--:|--:|--:|
| Total quota 1 | 156 | 45 | 111 | 45/45 |
| Total quota 0 | 156 | 0 | 156 | 45/45 |
| Consumer tail disabled | 156 | 32 | 124 | 45/45 |
| Throughput 0/tick | 156 | 0 | 156 | 45/45 |

The independent negative fixture records two real negative B judgments
as exactly two derived actor-A applications, producing actor-A credit −2;
neither transport silence nor quota refusal manufactures a negative judgment.

- 90 independent native executions, 90 derived normal executions,
  180 derived quota/throughput/tail intervention runs and 2 negative-fixture
  executions.
- 20/20 dedicated v2p adversarial unittests passed locally.
- 17 predecessor v2o unittests executed locally (one skipped because the
  older v2n signed report was absent in this environment).
- Original v2o signed predecessor SHA-256:
  `778a38f312d1e5403f0106015214cec924fe4f284e4cdbf107422f8b76c0716c`.
- Generated v2p JSON SHA-256:
  `1c3f2b0010f6a0470ac2b5be021838b8e1992e85760e367a532d5e5dfe8f9ef3`.
- A second independent output was byte-identical (`cmp` exit 0).

The inherited 413-test pytest suite **must be rerun on `fwork`**, which
provides pytest; this current local environment does not.

## Scientific boundary / next gate

**BLOCKED:** frozen native actor event intake, learning/operator update,
independent physical cost of consumer processing and general causal-ready
arbitrary-workload liveness. v2p evidence does not promote any of these
contracts. The next candidate research step is **v2q independent bounded
consumer resource charging** with a source-backed budget, retaining native
projection where feasible and exposing resource-contention counterexamples.
