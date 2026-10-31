# SPK/* Back Validation v2n — Forward opportunity fairness and actor backlog

## Gate decision

**Derived actor/forward fairness research PASS. Frozen-native actor event,
fairness, liveness, admission and credit-consumption contracts remain BLOCKED.**
All implementation files are strictly additive. The scheduler
`spk_backvalidation_v0/live_dual_scheduler_v0e.py`, Core, Network, Algebra,
Architecture, Compiler, instruction weights and native operator state were
not modified.

v2m's source-pinned pre-forward hook (line **158**) can consume global/per-PE
service and O/E memory counters before the atomic forward batching loop.
v2n reuses the same audited source hooks at **158, 296 and 307**, semantic
receiver/clock/emission/batch hooks and callsite inventory, but inserts a
bounded reservation **only in the independently compiled derived executor**.

### Explicit finite policy

`FairnessPlanV2n(max_consecutive_actor_ticks_with_ready_forward=k,
protected_forward_pe_slots=1)` permits up to `k` consecutive actor-control
pregrant ticks when a forward batch is ready. At the next such tick, a
protected window caps actor-control pregrants to
`global_PE_slots_per_tick - protected_forward_pe_slots`. With a single global
PE service slot, **zero** pre-forward actor grants may occur on a protected
window. A ready batch then has a budget opportunity to advance. No actor
control can interrupt an already executing atomic forward batch.

An actor-control grant is registered only after causal delivery, matching
actor ownership, resource service and an exactly-once actor-addressed v2l
credit ACK. Oldest-due service and credit constraints remain in effect;
transport loss, callback failures, overdue backlog and credit refusal never
become silent negative learning certificates. The fairness window is inactive
on the explicitly labelled post-native control tail.

This is deliberately a **conditional budget opportunity**, not a theorem
that arbitrary ready forward work can execute: local PE caps, memory domain
availability, outbox pressure, output-dependent control/feedback timing and
finite event horizons are separate constraints.

## Source-pinned 15 recipes × 3 BV modes × 2 PE capacities

Every cell executes the independent unchanged v0e native baseline; all three
fairness windows execute new AST-derived variants. The predecessor's original
native SHA, all actor ACK journals and pre-forward priority probes are
rechecked against the exact signed-off v2m report. A separate adversarial
no-control matrix is also executed. The three finite windows are:

- `always_protect` (`k=0`): reserve one forward PE slot whenever work is ready;
- `one_actor_turn` (`k=1`): allow one competing actor tick before protection;
- `legacy_window_16` (`k=16`): intentionally recover the historical v2m
  actor-first trace on this bounded corpus; no protected window is reached.

### Tight capacity: exactly one global PE service unit per tick

| Checked property (45 cells per policy) | Protect always | One actor turn | v2m reference |
|---|---:|---:|---:|
| Exact forward temporal trace against native | **45/45** | 0/45 | 0/45 |
| Exact final state + event/terminal payload | **45/45** | **45/45** | **45/45** |
| Native whole result after resource-cost projection | 15/45 | 0/45 | 0/45 |
| Protected forward budget opportunities | **234** | 111 | 0 |
| Protected opportunities with observed forward progress | **234** | 111 | 0 |
| Ready forward batches PE-blocked by early actor service | **0** | 162 | 162 |
| Pre-forward actor-control resource grants | 106 | 141 | 141 |
| Exactly-once actor-credit ACKs | **156** | **156** | **156** |
| Total ACK wait after due tick, across cells | **537 ticks** | 0 | 0 |
| Maximum individual ACK wait | 9 ticks | 0 | 0 |
| Sum of last-terminal delay vs frozen native | **0 ticks** | 105 ticks | 105 ticks |

The tradeoff is real: continuous forward protection restores temporal forward
parity in all **45** tight-capacity cells, but defers source-issued actor
judgment consumption (537 aggregate ACK wait ticks). Those waits are **not**
lost feedback. The one-turn policy has protected windows and actual progress,
but does **not** eliminate the early conflicts: its forward timestamps still
drift in all 45 cells. This falsifies a superficial "any fair turn is enough"
claim on the tested corpus.

### Original capacity: three global PE service units per tick

At original capacity, all policies preserve terminal payloads in 45/45 cells.
All three show 6/45 different forward traces, 43/45 identical terminal
timestamps and 38/45 exact whole-result projections. An extra protected
global PE slot does not necessarily resolve per-PE, memory and causal link
coupling. Actor-credit ACK count is 156 for each policy; only 2 aggregate
wait ticks are observed. Thus **do not extrapolate** tight-capacity temporal
parity to every resource regime.

## Adversarial nulls, timeout and controls

Three full independent tight-capacity causal-null matrices, 45 cells each,
restore **45/45 exact native whole-result parity**:

- all actor-control feedback lost;
- receiver callback fault -> transport loss, not negative credit;
- zero admissible actor credit -> no service, even when delivered.

A real negative-B fixture separately confirms two real negative receiver
judgments addressed to actor A, journal responses `[-1,-1]`, actor-A credit
`-2` and **no frozen-native learning**. Deliberate mailbox forgery, source
drift, unsupported plans, changed forward-computation counters, altered
resource charges and fairness-probe tampering are rejected.

**Hard deadline counterexample.** Under one global PE slot and `max_ticks=11`,
the frozen native baseline completes 11 native ticks. A derived v2m
`forward-first` run also completes and projects exactly to the original
native result. In contrast, both `always_protect` and the v2m-like large
window **raise the actual bounded-horizon rejection**, rather than silently
manufacturing a completed result. Matching forward terminal ticks is not
enough to satisfy a full closed causal/feedback horizon.

Therefore:

- No universal forward liveness, feedback liveness, absence proof, deadline
  guarantee, fairness optimality or native actor event priority is established.
- Hash chains verify internal trace custody, not remote cryptographic
  authentication or distributed mesh replay resistance.
- Abstract PE/memory charges do not establish hardware power, latency or
  energy cost guarantees, and the current three-actor bounded experiment is
  not an N-node compiler/hardware promotion certificate.

## Validation and release

- Signed predecessor v2m canonical SHA-256:
  `97f023c54198e05fcf8dc63f3602ec955acad0ea83a34544be7ef6f5e2311177`.
- Pinned frozen scheduler SHA-256:
  `2fc273f16f685d85ec0492637728fc835884a11741615912d2a7ea4d8c0c7ee9`.
- **16 dedicated adversarial stdlib tests**.
- **90** independent native matrix executions + **270** finite-window
  derived executions + **135** causal-null derived executions = **495**
  completed source-backed matrix executions. The separate horizon witness
  adds **4** execution attempts (two intentional bounded rejections).
- The 90 long-window derived cells must match all signed-off v2m
  actor-first credit journals and pre-forward priority probes.
- Run the same command into a second fresh output to compare byte-identical
  canonical reports. Existing output paths are rejected fail-closed.
- Selected inherited regressions call the entire prior v2m regression gate;
  the 413 pytest cases must be run on the user's `fwork` environment.

```bash
cd ~/workspace/spk-backvalidation-v0

tar --keep-old-files -xzf \
  ~/Scaricati/SPK_BV_v2n_Actor_Forward_Fairness_Milestone.tar.gz

bash search/spk_bv_v2n_actor_forward_fairness_gate.sh \
  /tmp/spk-bv-v2m-actor-priority-contention.json \
  /tmp/spk-bv-v2n-actor-forward-fairness.json

bash search/spk_bv_v2n_inherited_regression_gate.sh
```

**Never concatenate** two shell commands without a newline. The output
report must not already exist. `tar --keep-old-files` is for a one-time
additive extraction, not an upgrade that overwrites previous sources.

## Next research gate

**v2o:** Explicit admissible native-facing actor event contract proposal,
conditional liveness witness (including global deadline and backlog),
policy-optimality counterexamples, consumer/journal handoff model and
source-pinned adversarial integration. This remains a research design and
must not mutate/promote the frozen native actor scheduler without a separately
proved contract.
