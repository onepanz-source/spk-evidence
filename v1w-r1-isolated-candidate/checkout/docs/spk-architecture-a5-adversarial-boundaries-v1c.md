# SPK Architecture A5c: cross-system adversarial boundaries v1c

**Status: INTEGRATION PASS (2026-10-16, trusted logical fault domain).**

## Purpose

Test adversarial boundary conditions across A3d causal transport, A4a epoch
and mode authority, A4d snapshot custody and A5b event-conservation laws.
Do not conflate invalid input rejection before a lease with failure during a
lease: the former leaves a controller QUIESCENT, the latter makes it FAULTED.

## Tested contracts

- All 216 semantic cases and 3 placements: verify delivery and event
  accounting cannot be falsified without a discrepancy; do not mutate the
  legitimate output.
- All 648 placements: deny stale PE-context authority, RUN during TRAINING,
  and any attempt to reuse an epoch after a failed VERIFY replay.
- For 36 stratified cases times 3 placements: capture, recover, and forge a
  genuine quiescent A4d P/S/E/O checkpoint, including recalculated hashes;
  recomputed unkeyed hashes must not defeat independent source replay.
- A too-short A3d link horizon must fault the executing A4a controller,
  without generating a CLOSED result or reusable checkpoint.
- Seal evidence and replay it in separate processes. Reject tampered content
  even when the attacker recalculates the outer SHA-256.
- Check Git custody of 18 committed predecessor phases and frozen ancestry.

## Explicit nonclaims

- Trusted in-process authority is not authentication against malicious host code.
- Checkpoint recovery is full replay, not a hot continuation.
- Fault injection is logical; hardware faults and distributed crashes are excluded.
- The campaign covers bounded finite corpus cases, not all architectures.

## Acceptance gate

`bash search/spk_arch_a5c_final_gate_v1c.sh`

The gate runs 6 stages and makes no commit or tag.

## Certified A5c gate

- Independent adversarial tests: 7 PASS.
- Frozen Compiler/host integration: 5 PASS.
- Adversarial executions: 648.
- Cross-context denials: 648.
- Staging execution denials: 648.
- Failed replay faults: 648.
- Event custody tamper denials: 648.
- Fully rehashed snapshot replay denials: 108.
- Certified predecessor phases: 18.
- Protected regressions: 31 PASS.
- Complete repository regression: 3396 PASS.
- Independent-process evidence replay: PASS.
- Frozen source and patch hygiene: PASS.

Evidence SHA256:
60b8ab0d078257c64fabad9264c50df519e4fd6743b47eb17fba35538fea1aa7

Acceptance covers bounded adversarial authority,
event custody and state reconstruction boundaries.

No physical fault recovery, hostile-process security,
durable checkpoint continuation or automatic rollback
is certified.
