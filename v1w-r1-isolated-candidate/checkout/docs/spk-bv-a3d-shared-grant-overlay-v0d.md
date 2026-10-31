# SPK BV v0d: A3d-anchored shared-grant overlay

**Status: RESEARCH CANDIDATE; `fwork` gate required.**

## Objective

Bridge the independently replayed v0c causal feedback packets to **real execution
ledgers** of frozen `spk_architecture_v1/causal_transport_v1d.py` (A3d), so
forward spikes and feedback draw against the *same declared finite link, PE
service and logical memory credit budgets*. Observe actual contention, causal
feedback dependencies, and finite starvation limits before implementing a live
BV-aware event scheduler.

## Immutable baselines

`spk-architecture-bounded-reference-v1` at
`5af99cd1f4d603bf0c8e1557a6561c107765fdb5` remains untouched. The
research module imports and executes frozen A3d, but never monkeypatches its
scheduler or modifies its source. The comparison never claims an extension of
the 3,411-test bounded release to BV.

## Experimental domain

- Exactly A -> B -> C, spread over PE0, PE1, PE2; one uniquely witnessed causal
  parent per forwarded B -> C route. No general topology support.
- Candidate and baseline have the same operator sets as BV v0b/v0c. Two
  independently injected source events at ticks 1 and 4; the A3d candidate
  emits two C terminals. The baseline does not emit terminal outputs.
- Frozen A3d produces four authoritative **forward** inter-PE link grants.
  Each real grant is cross-checked against the actual transfer ledger.
- Each terminal creates an `OBSERVED` (not utility-certified) assessment. Its
  source event and causal parent are reconstructed from actual executed A3d
  batches and transfers. Ambiguous batching is **rejected**, not guessed.
- v0c computes four feedback packet intents (C -> B -> A twice). Feedback
  scheduling consumes residual A3d link credits, with **absolute priority to
  frozen forward grants**. No forward spike can be rescheduled by the overlay.
- All feedback packet injections require one global/PE service credit, two
  logical memory credits (sender O + receiver E), one fabric and directional
  link slot, and one shared in-flight slot throughout transport.
- Finite `max_feedback_wait_ticks` and A3d logical horizon: deny without a
  `CLOSED` result when feedback cannot be granted in time.
- The independent-process replay reconstructs actual A3d and feedback from
  source and compares canonical sealed evidence, rejecting even rehashed
  modifications to the report.

## Trial result expected

For ticks `(1, 4)` and `link.fabric_slots_per_tick=1`:

- Four actual forward link grants; four feedback link grants.
- Feedback grants cannot occupy ticks containing forward grants.
- Nonzero contention reported in both `fabric_link` and `pe_service`.
- Exact preservation of frozen A3d forward execution digest.
- Explicit denial if the feedback grant wait limit is too small.

## Formal boundary

**This is a post-execution shared-credit overlay, not a live joint scheduler.**
It demonstrates finite-resource compatibility with observed A3d grants under a
forward-first reservation policy, but **not** feedback-induced spike delays,
execution interleaving, async PE concurrency, fairness, programmable learning,
or physical energy/memory measurement.

The remaining blocker to live BV integration is not a missing UI control: A3d
never exposes an extension point for inserting a new feedback event class
*inside* its `while` service loop. A live research replacement must admit
joint forward/BV traffic, preserve per-occurrence causal identities under
coalesced batches, charge domain memory before state changes, and demonstrate
parity with frozen A3d when BV is disabled.

This phase deliberately does **not** patch A3d to fabricate such behavior.

## Acceptance gate

`bash search/spk_bv_v0d_research_gate.sh` runs 22 new research tests, 106
inherited selected functional tests, frozen-Git ancestry protection and a
separate-process replay. The broader functional regression can use
`bash search/spk_bv_credit_v0a_full_regression.sh`: its six branch-specific
historic Git release tests remain intentionally deselected, not counted as PASS.

No commit or release tag should be created until `fwork` results are reviewed.
