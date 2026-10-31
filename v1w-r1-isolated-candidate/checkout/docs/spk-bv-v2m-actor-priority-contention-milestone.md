# SPK/* Back Validation v2m — Derived actor-first priority and PE contention

## Decision

**New source-backed research priority gate PASS; frozen-native actor event
policy and actor credit consumption remain BLOCKED.** This checkpoint makes
the first intentional timing divergence between a *derived* actor-aware
scheduler and its independently executed frozen native v0e baseline. It does
not alter Core, Network, Algebra, Architecture, Compiler, v0e scheduler,
instruction set, native neuron state or operator weights.

v2l proved an ordered, actor-addressed acknowledgement journal after
resource service. v2m inserts a source-audited hook **just before native
forward batch arbitration at line 158**. It offers two explicit policies:

- `forward-first`: same order as v2l; native forward batching and BV are
  processed first, and only residual capacity serves derived actor controls.
  The full frozen native result is recovered **exactly** by removing only
  audited research control resource costs/tail rows.
- `actor-first`: due delivered, causally valid controls with available
  credit enter a bounded service slot **before** forward batching. These
  events actually decrement the derivative's running `service_used`,
  `pe_total`, `mem_pe_used`, `mem_dom_used`, `mem_total` budgets. Forward
  candidates subsequently see the remaining capacity. The unchanged
  native-derived batch scheduler then decides what can execute this tick.

As in v2k/v2l, resource audit and closure hooks are source-pinned to lines
**296** and **307**, with inherited receiver/clock/emission/ingress and
callsite anchors. All work happens in a separately compiled AST-derived
function. Native source and Python module globals stay intact.

**Important parity distinction:** under `actor-first`, subtracting the
audited control resource costs recovers the derivative's *counterfactual
resource-only result*, not necessarily the independent original native
result. Forward timing, BV link arbitration and the logical tick sequence
may already have changed. Such real contention is not "repaired" or
misreported as native whole-result equality.

## Explicit budget and contention experiment

The same 15 workload recipes x three BV modes are run under two separately
chosen legal native PE plans:

| Source-backed property | Original capacity | Contended capacity |
|---|---:|---:|
| Global PE service units/tick | 3 | **1** |
| Independent native workload/BV cells | 45 | 45 |
| `forward-first`: whole native-result parity | **45/45** | **45/45** |
| `actor-first`: whole native-result parity | 38/45 | **0/45** |
| `actor-first`: forward timing changed | 6/45 | **45/45** |
| `actor-first`: final actor states identical | **45/45** | **45/45** |
| `actor-first`: terminal payload multiset identical | **45/45** | **45/45** |
| `actor-first`: event and batch counts identical | **45/45** | **45/45** |
| Actual actor-control grants placed before forward | 140 | **141** |
| Forward opportunities immediately PE-blocked by those pre-grants | 0 | **162** |
| Causally acknowledged derived actor controls | 156 | **156** |

At normal capacity, **6** cells change forward timing even though the
specific *immediate PE-block* probe is zero; early control charges can
also affect later resource service/BV arbitration. Of the **7** cells that
lose whole native-result equality, one has a difference outside the exact
forward payload. We do not label every normal-capacity difference as a
direct PE block.

The contended-capacity result is sharper: in **every one** of 45 cells,
actor-first changes forward timing, and **every one** contains at least one
direct ready-forward PE block caused by a pre-forward actor-control grant.
Yet all complete without changing final values or number/type of terminal
emissions in this *finite pinned corpus*.

For the reference workload under a single PE service slot globally, its
two terminal spikes move from ticks **4 and 6** under frozen v0e to ticks
**5 and 9** under derived actor-first. The trace witnesses **4** forward
opportunities blocked by real pre-forward resource charges. This is a
bounded scheduling/latency effect, not a computation/learning improvement.

### Causal null interventions: 45 cells each

The following controls differ only in the derived actor-control path;
native workload, BV parameters, capacities, and original execution remain
the same.

| Intervention with 1 PE global service slot | Full original native equality |
|---|---:|
| Lose all actor feedback in the transport | **45/45** |
| Transport callback always fails closed | **45/45** |
| Deliver actor controls but deny all credit/resource grants | **45/45** |

Thus the schedule change is not an artefact of the AST compilation itself:
it disappears when the additional pre-forward resource charge disappears.
The third variant demonstrates again that *control delivery alone* does
not imply actor service, credit or a native state transition.

### Bounds, custody and adverse evidence

- Every combined native-derived resource row respects original global,
  per-PE and memory-domain limits; there are no fabricated extra PE slots.
- A stricter `max_ticks=11` scenario has an accepted original native result
  but rejects the actor-first derivative after exhausting the bounded
  horizon. **No successful outcome or silence certificate is fabricated.**
- Changed source bytes, unsupported priorities, reordered/altered pressure
  probes, unexplained resource-counter mutations, forged mailbox records,
  replay and wrong actor ownership fail closed.
- In the separately replayed real-negative-B fixture, two genuine negative
  receiver judgments are acknowledged by A with derived credit `−2`, also
  under PE contention. This is **not native actor learning**.
- One abstract PE service unit and two O/E memory units per control remain
  *chosen research costs*. A pre-grant can defer whole atomic forward
  batches but cannot interrupt an already running batch. No fairness or
  starvation-free theorem is asserted for other workloads or quotas.

## Reproducibility

- Canonical signed v2l predecessor SHA-256:
  `b77f257adc6cb6c888e6cef44e67d39e54bf328ed6e9ee4d434eb7eea3bdf3d7`.
- Frozen scheduler v0e SHA-256:
  `2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9`.
- **18 dedicated stdlib unittests**, all required PASS.
- New full runtime replays: **91** original native + **91** derived
  forward-first + **91** derived actor-first + **135** causal nulls =
  **408 executions**. These counts include separately replayed real-negative
  evidence in the three main execution categories.
- Reports contain pinned workload recipes, per-tick competing-service
  probes, actor credit journals and explicit native-vs-derived differences.
  All source SHA pins and canonical predecessor bytes are rechecked after
  running. Report determinism requires an identical rerun into a fresh file.

```bash
cd ~/workspace/spk-backvalidation-v0
tar --keep-old-files -xzf \
  ~/Scaricati/SPK_BV_v2m_Derived_Actor_Priority_Contention_Milestone.tar.gz

bash search/spk_bv_v2m_actor_priority_contention_gate.sh \
  /tmp/spk-bv-v2l-actor-credit-protocol.json \
  /tmp/spk-bv-v2m-actor-priority-contention.json

bash search/spk_bv_v2m_inherited_regression_gate.sh
```

The output report must be absent before invocation, and both reports must
live outside the checkout. Extract the additive archive only once. Run
the inherited pytest regressions separately on `fwork`.

## Next gate

v2m proves a priority scheduling effect under the selected bounded
three-actor research workload, but does **not** establish the frozen-native
actor event contract. The next step is an explicit fairness/liveness and
native-admission policy review: starvation treatment, priority budgets,
oldest-due control backlog, forward progress, bounded horizon and safe
credit consumption. Only after independently proving that contract should
we consider a frozen-native integration path, and still without changing
the future SPK algebra/semantic-weight roadmap prematurely.
