# SPK Back Validation Contract v0

**Status: RESEARCH CANDIDATE, not a frozen release.**

**Basis:** frozen `spk-architecture-bounded-reference-v1`, commit
`5af99cd1f4d603bf0c8e1557a6561c107765fdb5`; frozen Core, Network,
Compiler and Simulator remain unchanged. This is a **normative proposal** for a
new, hardware-independent experimental layer. It has not passed an integration
gate on `fwork` and does **not** claim learning, improved cognition, or physical
security. The accompanying Python module checks offline trace structure; it
is neither an adaptation algorithm nor an interface to the A3d scheduler.

## 1. Research hypothesis

**H-BV:** Context-conditioned, locally propagated evaluations of *observed
consequences* can guide the search for neuron-local programs, and may improve
held-out task outcomes **after accounting for all costs of exploration**.

The null hypothesis is that such propagation produces no improvement beyond
matched-compute alternatives. A local neighbor's appreciation of a spike is
not evidence of global benefit without further controls.

**Out of scope v0:** changing active Core programs, training policies, weight
updates, online promotion, synchronous neural backpropagation, claiming causal
credit from correlation, and actual communication over the v1 fabric.

## 2. Existing anchors and missing information

- Frozen `spk_network/learning_v0.py` already defines immutable
  `NetworkRouteObservationV0` and `NetworkBatchObservationV0` plus a read-only
  observer protocol. It explicitly **does not define** a learning rule or
  reward. It reports timestamp, endpoints and channels, but *not a unique
  identity for each parallel occurrence nor its consumed-event ancestry*.
- Frozen Core v0: `CoreProgram` and `CoreConfig`, batch semantics and transient
  guard. Programs do not mutate within an execution.
- Frozen Memory Contract v0: P/S/E/O ownership, event multiplicity, bounded
  resources, observer noninterference, and separation of EVENT_TIME and
  SERVICE_TIME.
- Frozen A4a/A4b: mode and epoch authority. Frozen A4c: staged candidate,
  independent verification, explicit operator approval, revision CAS and
  **cold** activation. A4d: snapshot/replay custody, not hot state migration.

The new trace identity fields are **proposed v0 extensions**, not data that
Network v0 already exposes. An integration stage must capture them at the
emission/routing boundary, never reconstruct them from a nonunique tuple
`(timestamp, source, target, channel)`.

## 3. Formal objects

Let `G=(V,E)` be an arbitrary finite *directed multigraph* during one versioned
epoch `e`. Structural cycles and parallel edges are permitted; every delivered
spike occurrence has an unambiguous identity `r` and positive temporal delay.

For each neuron `i`, context snapshot

`C_i^k=(node_i, program_digest_i, extractor_digest_i, feature_digest_i, [t0,t1])`

binds a **local** feature projection over an explicit observation window.
Snapshots may change within an epoch, but the active program digest of
a neuron cannot change during that epoch. A snapshot is only available at
`window_end`: a producing or observing neuron MUST NOT use context features
from its own future. A snapshot may be reused later; freshness policy is a
separate, future contract. No global context vector or privileged
knowledge is assumed. The hashes pin claimed inputs; they do **not** attest
that their underlying measurements are truthful.

The topology is a multigraph with explicit **edge identities**, channels and
positive minimum delays, bound by a canonical digest of the declared nodes and
edges. Structural multiedges must not be collapsed even if their endpoints and
channel labels coincide. The offline validator checks topology membership and
edge-delay lower bounds; a trusted capture adapter must still attest actual
execution.

An emitted-and-routed occurrence is

`r=(id, edge_id, src, dst, src_channel, dst_channel, t_emit, t_deliver, C_src, P_src, parents)`.

`parents(r)` are the *occurrences previously delivered to the producing
neuron's causal batch*. They express **claimed potential causal ancestry**, not proven
marginal influence. This offline verifier checks parent identity, ownership
and temporal admissibility but **cannot attest exact batch membership**.
That stronger property requires independently witnessed consumed-batch receipts
from a future capture adapter. External stimuli need not have a parent. Recurrent graphs
cannot create a provenance cycle if edges have positive delay and causal
batch provenance is faithfully captured.

A destination can issue an assessment

`a=(id, r, observer=dst(r), t_observed, C_observer, metric, policy, evidence, status, value, confidence)`.

`OBSERVED` carries a **local** normalized metric in [-1,+1] and a declared
confidence in [0,1]; this is not a calibrated probability unless separately
validated. `ABSTAIN` has no numeric score and an explicit reason; it must
never be treated as a zero reward or a negative vote. Missing feedback is
`UNKNOWN`, not negative.

Propagation follows a *provenance path*:

`path(a) = (r_0, r_1, ..., r_h)` with `r_0 = assessed(a)` and
`r_{j+1} in parents(r_j)`.

One distinct assessed feedback may be delivered to any ancestor occurrence
at most once. Multiple paths converging on the same ancestor must not inflate
its support. **Paths are recorded evidence, not independently counted votes.**
Distinct paths that terminate at the *same upstream neuron* from the same
assessment must be coalesced into one logical feedback delivery for that
neuron, even if they end on different occurrences. The validator reports
unique recipients; it does **not** send messages. `max_hops`, per-kind record budgets and per-occurrence parent
budgets bound the procedure. Here `max_hops` counts occurrence IDs in a path
(starting at 2 for one explicit upstream hop), not network depth or hardware
cycles. A feedback **never** traverses an arbitrary reverse graph edge without
recorded ancestry.

A proposed change is

`q=(id,node,active_program_digest,candidate_digest,context_snapshot,
    supporting_assessment_ids,supporting_propagation_ids,STAGED_UNVERIFIED)`.

Support is a list of evidence *references*, not a proof of advantage. No
`APPROVED` or `PROMOTED` proposal status exists in this v0 trace.
The `STAGED_UNVERIFIED` token denotes *offline proposal staging*, not an
A4a/A4c verified stage receipt or an authorization to run.

## 4. State machine and authority boundary

```text
CONTEXT_OBSERVED
      |
      v
NEURAL_EVENT_RECORDED -> DESTINATION_OBSERVED / ABSTAIN
                                 |
                                 v
                     ANCESTRY_PROPAGATED (bounded)
                                 |
                                 v
                    LOCAL_HYPOTHESIS (not a verdict)
                                 |
                                 v
                      STAGED_UNVERIFIED
                                 |
                     future verification protocol
                                 v
               A4c-style independent verification
                                 |
               separate trusted authorization + CAS
                                 v
                    cold activation only
```

The last two stages are **existing A4c capabilities** in another domain, not
executed by this v0 verifier. `EXECUTE` and `VERIFY` may observe but must not
mutate P/S/E; `TRAINING`/`REMODEL` may create candidate references only. A
malformed assessment must not change neuron state, event queues or an active
program. Observation records live in logically separate O storage; real
allocation, scheduling and congestion costs will need their own later model.

## 5. Required invariants BV01–BV16

| ID | Normative requirement |
|---|---|
| BV01 | A trace is bound to a topology digest and epoch. No cross-epoch mixing. |
| BV02 | Each routed occurrence has a unique ID, even across identical parallel edges, and refers to a version-pinned topology edge. |
| BV03 | Routing has positive logical delay; parent occurrences were delivered before child emission. |
| BV04 | The source program and context snapshot must match the producing neuron and its time window. |
| BV05 | The observer must be the actual destination of the assessed occurrence. |
| BV06 | Assessment time must not precede delivery or precede the end of its context window. |
| BV07 | No feedback means `UNKNOWN`; `ABSTAIN` has no numeric value. |
| BV08 | Values/confidence are finite and bounded; their calibration is **not** inferred. |
| BV09 | Every propagation follows exact recorded parent-occurrence IDs. |
| BV10 | A given assessment cannot be counted twice at the same ancestor occurrence. |
| BV11 | All loops are bounded by per-kind, parent and hop budgets. |
| BV12 | One node's observations confer no direct write access to another node's S/P memory. |
| BV13 | Proposal evidence must be reachable by its owner and is only `STAGED_UNVERIFIED`. |
| BV14 | No mode or program changes as a side effect of trace verification. |
| BV15 | Score aggregation cannot assert a unique causal allocation or global reward from provenance alone. |
| BV16 | The validity of trace structure does not attest the truth of underlying measurements, identity signatures or utility. |

Most of BV01–BV11 and the referential part of BV13 are checked by the
accompanying pure Python validator. Exact source batch membership (BV03)
and metric/evidence authenticity (BV08/BV16) require future independently
witnessed instrumentation; offline JSON structure cannot prove them. BV12, BV14 and BV15–BV16 are **architectural proof
obligations**, not magically verified by parsing offline JSON.

## 6. Why local credit is **not yet defined**

For a downstream outcome `Y`, a meaningful marginal attribution to program
`Pi_i` would ideally compare counterfactuals

`Delta_i = E[Y | do(Pi_i=pi_new)] - E[Y | do(Pi_i=pi_old)]`.

Neither observation provenance nor a neighbor's feedback supplies this value.
If two parents jointly trigger the same event, recording both as ancestors
**does not justify splitting reward 50:50**, or treating the downstream
neighbor's local metric as the network objective.

v0 therefore propagates *attributed observations with uncertainty*, not
numerical causal credit. A subsequent experimental protocol may use paired
rollouts, randomized interventions, ablations, or controlled delayed
feedback. Credit rules must be explicitly versioned and validated separately.

## 7. Capacity, latency, privacy, and failure

An implementation MUST separately budget: occurrence-ID storage, context
snapshots, O records, feedback transmissions, propagation hops, observation
policy execution, and candidate evaluation. On budget exhaustion it must
return an explicit incomplete/denied outcome; never silently drop a spike,
replace missing feedback with negative reward, or mark a proposal verified.

Feedback is *logically* separate from neuronal spike delivery. The verifier
models no physical feedback bandwidth, scheduling priority or causal latency.
The network topology may be secret or restricted; local nodes need only the
ancestral evidence they are authorized to see. Hash-only contexts reduce
incidental disclosure but are **not a privacy guarantee** or authenticated
provenance; trusted event capture and access policy remain requirements.

`OBSERVED` scores are dimensionless values reported by a metric implementation.
The unit interval does not confer comparability across different `metric_id`
values or extractor versions. Combining incompatible metrics must be rejected
by any future aggregation policy.

## 8. Minimal conformance example

`examples/spk_bv_v0_distributed_feedback.json` contains A->B->C,
with two parallel A->B occurrences. B->C records both as parents. C observes
B->C and two ancestry paths lead from B back to A. They represent **one**
logical delivery of that same assessment to A, not two votes.
A and B can stage separate unverified proposals; no code is learned or
replaced. Both parallel occurrences remain distinct; both routes may be
causally relevant, but no marginal attribution is claimed.

`python -m pytest -q tests/test_spk_back_validation_contract_v0.py`

The test suite includes malformed ancestor paths, forged receivers, future
parents, feedback before delivery, wrong contexts, nonfinite metrics, duplicate
credit via a diamond path, stale proposals, budget overflow and denial of any
`PROMOTED` status. A green test suite **only** certifies this offline trace
validator in its declared domain, not SPK Runtime integration or cognition.

## 9. First controlled experimental design (before any training claims)

Competing conditions use identical seeds, problems, topology, allowed program
primitives, evaluation budget, wall-clock/energy accounting model and held-out
families:

- **F:** fixed neuron-local programs, no candidate search;
- **R:** matched-budget random or centrally chosen program candidates;
- **L:** local search with downstream context observations but no propagation;
- **BV:** local search with provenance-bounded backward propagation;
- **S:** same as BV with shuffled/temporally misaligned feedback (negative control).

Primary outcome: held-out task utility with confidence intervals. Secondary:
valid novel program forms not in the training catalog, program diversity,
change acceptance rate, calibration of local assessment versus global utility,
operation count, memory units, event and feedback traffic, PE/link stalls,
critical-path time, and full candidate-search cost (including failures).

Pre-register task families, intervention policy, acceptance thresholds, and
stop criteria; hold total search cost constant. Programs that merely differ
syntactically but reduce to the same SPK algebraic normal form must **not** be
counted as independent computational novelties.

## 10. Explicit next decisions (not solved by v0)

1. Define metric policies and observational evidence production with
   calibration and no hindsight leakage.
2. Decide whether backward propagation represents informational evidence,
   confidence attenuation, or experimentally estimated causal contribution.
3. Specify how provenance occurrence IDs are emitted in an N-node A3d
   execution without changing frozen v1.
4. Define concurrent context windows, cross-epoch feedback treatment and
   revocation of stale candidates.
5. Define per-node candidate search and controlled approvals with a budget;
   do not assume local and global objectives agree.

**Exit criteria for v0 contract acceptance:** separate review of the formal
invariants, reproducible conformance vectors on `fwork`, an agreed negative
control for the learning experiment, and an integration-design review covering
identifier creation and costs. No frozen reference is modified.
