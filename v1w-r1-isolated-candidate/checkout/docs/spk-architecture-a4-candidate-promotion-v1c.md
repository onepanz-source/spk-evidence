# SPK Architecture A4c: verified cold candidate promotion v1c

**Status: INTEGRATION PASS (2026-10-16, trusted logical pointer domain).**

## Scope and boundary

A4c introduces an explicit, versioned, trusted in-memory *logical deployment
pointer*, and a two-stage promotion workflow: staged candidate from A4a
TRAINING/REMODEL, independently compiled ideal candidate reference, A3d
EXECUTE/VERIFY replay on a fresh candidate controller, separate operator
approval and revision-CAS cold promotion. The baseline and candidate contexts
use distinct three-neuron programs from the pinned 216-case corpus. Each source
program maps to the same graph/input with the next frozen profile, so the
change is real and deterministic, not a fabricated arbitrary digest. It does
**not** implement a neural training algorithm.

Every candidate is bound to its full dataclass execution context (program,
placement, transport, PE and memory grants, link policy), pinned corpus SHA,
source ID and real frozen Compiler manifest SHA. The A4b baseline witness
independently invokes frozen Compiler/host paths A4a and A2b. The candidate
witness invokes the frozen Compiler/host separately and checks ideal A3a
zero-latency PE-local semantic parity. A3d timed execution is replayed in a
separate candidate-mode controller. A digest of an arbitrary local replay is
**not** a substitute for the frozen ideal semantic witness.

The staging authority may only be in TRAINING or REMODEL at a QUIESCENT
boundary of the currently active context. Staging does not alter the active
pointer; verification does not alter it either. An approval with explicit
operator identity, exact verification receipt and expected revision is required.
Promotion requires the source controller to remain in the same trusted epoch
and quiescent boundary. It performs a single in-memory switch of the pointer,
records a receipt and consumes staging/verification/approval. Replaying a
consumed approval or attempting a stale revision fails closed. A fresh A4a
controller can run the target context after promotion. It **starts cold**.

## Coverage

- 216 frozen three-neuron cases x 3 PE placements = 648 actual candidate changes.
- Each candidate comes from another pre-existing frozen source profile.
- 648 previous A4b baseline Compiler/host authority witnesses.
- 648 independent frozen candidate Compiler/host witnesses and zero-latency
  semantic parity projections.
- 648 candidate mode EXECUTE/VERIFY pairs plus 648 fresh cold executions.
- 324 staged TRAINING and 324 staged REMODEL promotions.
- Wrong source/manifest, changed context, altered verifier state, forged
  permission, stale operator approval, modified descriptor, replay failure,
  noncanonical evidence and recomputed-digest forgery are tested.

## Limitations

A4c does **not** swap running neuronal instructions or migrate live S/E/O
memory; A4d will address custody, activation and recovery conditions. The
registry is in-memory, not durable or fault-tolerant. The operator ID is an
explicit logical approval, not a cryptographic signature or authenticated
identity. This is not a security boundary against a malicious Python process
or mutable host internals. Frozen compiler semantically anchors *ideal*
behavior only; the bounded A3d timed variant is confirmed by deterministic
replay, not falsely equated to the zero-latency compiled host. No new Core,
Network, Compiler, Simulator or frozen Architecture source is modified.

## Gate

`bash search/spk_arch_a4c_final_gate_v1c.sh`

Six sections: independent controller/candidate tests, full real Compiler
cross-witness, two independent-process source-pinned canonical replays,
previous A4b/A4a/A3d regressions, complete repository regression and
frozen-tag/source/patch hygiene. The gate performs no commit or tag.

## Certified A4c gate

- Independent candidate promotion tests: 16 PASS.
- Frozen Compiler/host integration: 8 PASS.
- Compiled baseline witnesses: 648.
- Compiled candidate witnesses: 648.
- Independent candidate verifications: 648.
- Explicit promotions: 648.
- Cold executions: 648.
- Previous regressions: 56 PASS.
- Full repository regression: 3334 PASS.
- Independent-process evidence replay: PASS.
- Frozen source and patch hygiene: PASS.

Evidence SHA256:
29703896c4861f4905f1847a58157110a0eaa8144ae7aec14aebd83e0ecfd739

Acceptance covers verified, explicitly authorized,
version-controlled cold candidate promotion.

No live neuronal state migration, hot replacement,
durable recovery or automatic rollback is certified.
