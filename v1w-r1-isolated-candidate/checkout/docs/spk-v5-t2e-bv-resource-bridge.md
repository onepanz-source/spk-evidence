# SPK V5-T2e | BV resource bridge and semantic feedback boundary

**Status:** research-only. 21 October 2026. No frozen source changes. The inherited V5-T2d gate on fwork passed 120 tests and returned SHA-256 `b2171ec498497b96e83d6a92a51c9bff5c7b8a1ddc91db7737530289cb48395f`.

## What is tested

Use the unchanged SPK BV v0e live dual-event *research scheduler* against the actual V5-T2c A–B–C demand/closure cases. In the 42-cell factorial (seven temporal input templates, two synthetic exogenous C-demand bits, three fixed candidate A programs) execute **one original source run per mode**:

1. `disabled`: BV off;
2. `forward_first`: native v0e *echo* feedback priority after forward;
3. `feedback_first`: native v0e echo feedback priority before forward;
4. `closure_only`: terminal channel 9 at C as assessor instead of terminal channel 7.

The comparison is made within v0e (enabled/disabled). A1b's independently executed C-demand reward is **shadow-only** and must never be copied into v0e feedback. C's reward is positive/negative/abstain only when demand observation and closure exist, whereas v0e terminal-channel-7 feedback is ancestry-bound to *emitted spikes*, not to their usefulness for the island.

## Source-executed accounting and logical costs

Source v0e actually grants reverse links, consumes one abstract PE service unit and two abstract O/E memory units per reverse link grant, and shares the cross-PE link quota (one per tick in this fixture). The source's per-tick grant/resource ledger, closure count, causal delivery timestamps and conserved counters are checked. **These are simulator-owned abstract costs, not hardware watt-hours or true paid semantic-C reward delivery.** There is no measured PE/S consumer charge for the T2c semantic reward.

Results on 42 cells:

| v0e mode | Forward link grants | Reverse link grants | Abstract PE units for reverse | Abstract O/E units for reverse | Cells with reverse grants |
|---|---:|---:|---:|---:|---:|
| off | 32 | 0 | 0 | 0 | 0 |
| forward-first | 32 | 32 | 32 | 64 | 14 |
| feedback-first | 32 | 32 | 32 | 64 | 14 |
| assessor on C closure, channel 9 | 32 | 0 | 0 | 0 | 0 |

Feedback-first changes the v0e C-terminal timing/batching in **2/42** cells relative to v0e with BV off, even though the total grant count matches forward-first. The absence of extra feedback in the channel-9 case is **not** proof of no value in a silent decision. C closure is an exogenous event: it has no upstream A spike ancestry with which to route a semantic reward back to A.

A negative T2c reward can occur when A stays silent while C's exogenous demand is true; in that case v0e's reverse credit is zero. A positive v0e reverse ACK can occur when A over-emits on an episode in which C would judge the action negative. Both counterexamples are asserted against the original source, not a reimplementation.

## Gate decision

- **GO (narrow):** establish source-owned, budget-charged echo transport and report its effect on temporal island computation; retain native parity/authority guardrails.
- **NO-GO:** interpreting v0e reverse ACK as objective reward or claiming T2c reward has been charged and delivered.
- **BLOCKED:** T3 blind RL, external/independent task truth, a legal reverse reward for an un-emitted action, native learning and program promotion.

## Required future contract, not an implementation

A semantic reward needs an episode/counterfactual action identity and causal binding *even if A remained silent*, C's closed and authenticated local objective observation, an explicit abstention state, paid PE/S/O/E/link service and a custody/authorization policy for sending it to A. It must not be forged from a lack of ACKs. An island objective is a logical domain; this milestone does not decide physical placement, mesh, source weights, topology or physical hardware.

The next valid scientific test is a source-independent evaluator/holdout, plus a separately authorized reverse semantic-reward service. A V5 shadow learner cannot be promoted on synthetic truth. The old S1/S2/S3/S4/S5 roadmap remains 100/100/60/0/0 (52% equally weighted, no release gate change).
