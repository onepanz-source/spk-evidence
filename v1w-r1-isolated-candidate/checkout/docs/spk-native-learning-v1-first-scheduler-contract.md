# SPK Native Learning Runtime v1: first same-scheduler proof

## Architectural discontinuity closed (bounded reference)

Original frozen `spk_backvalidation_v0/live_dual_scheduler_v0e.py` transports reverse judgments but has no P update. T17 updates P, but in a different staged SQLite application. This release introduces a **new versioned live scheduler** descended from the exact original BV-v0e source, keeping `_admit`, `_compute_local` and resource admission backed by unmodified frozen SPK modules. **It is not a modification of the frozen scheduler.**

The new scheduler embeds one *native-to-this-v1-runtime* P transition at actual BV delivery to C. C's next PE batch uses the revised P program, not a post-run Python report or a host-side choice. The bounded contract is intentionally narrow: A/B/C placement, choices 11/12, A judgments 21/22, terminal 7, goal compiled into original A program, and binary flip on verified negative feedback.

## Necessary evidence chain

1. `C_PE` executes choice 12 at logical tick 10 using `P_version=0`.
2. Original `_compute_local` at B relays the spike to A with acknowledged source occurrence ancestry.
3. At A, original `_compute_local` emits `22` (negative) plus structural `7`. The new scheduler binds the semantic verdict to the **actual A emission** and A assessment (BV-v0e transported assessment ID but not verdict).
4. The real two-hop BV arbitration carries that verdict A→B→C, preserving causal occurrence IDs and consuming original BV resource grants.
5. On **arrival at C**, the scheduler checks assessor, actual A emission, C→B causal parents, original P read version, assessment uniqueness, verify/execute mode, budget, and current PE/P resource headroom.
6. The scheduler atomically revises its owned P program and records one PE service unit and one P memory unit at that tick.
7. A second C input at tick 30 (or the actual delivery tick 14) computes **choice 11 using `P_version=1`** within the same live scheduler. A consequently emits positive `21` and no new P grant.

Symmetric evidence is required for 11→12. With BV disabled, feedback unavailable, execute mode disabled, quota=0, or initial positive assessment, no P transition may occur. Replay, stale P versions and unsupported verdicts fail closed. With learning disabled, all original forward batches, spikes, BV grants, resource timelines and final states must match the frozen v0e, except version-only report fields removed for comparison.

## Resource model

Each admitted P write uses one extra PE service unit on C's owner and one logical P-memory unit. It is accounted in exactly the same tick as the BV arrival, before regular forward batch scheduling. This is a **bounded logical** resource model, not a physical write/transaction measurement and not the full Architecture Memory Contract v1 authorization.

## Declared limitations

- Narrow binary negative-feedback learning rule, not generic neuromorphic gradient/credit attribution.
- Original BV-v0e stays frozen and does **not** learn. This is a *new v1 native scheduler*, not a claim of retroactive native learning in v0e.
- A's goal is still compiled into a synthetic A program by the test harness; no independent physical sensor.
- The versioned P state lives within one run. Crash recovery, durable memory, N-node arbitrary topology, multi-receiver credit, source authentication, generalization and actual hardware costs **remain open**.
- The `fwork` gate must load original pinned source modules, not simulated Python substitutes. Isolated local unit testing of the scheduler with test-only resource fixtures **does not substitute** for this gate.

## Release acceptance

The **same native v1 scheduler** must produce: `C@10 v0 choice12 → BV C delivery + P grant v1 → C@30 v1 choice11`, plus symmetric 11→12. All controls deny credit, original v0e parity holds when disabled, source SHA-256 pins stay unchanged, and two independent reports have identical bytes. Anything less is BLOCKED, not PASS.
