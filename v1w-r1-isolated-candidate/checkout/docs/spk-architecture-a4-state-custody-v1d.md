# SPK Architecture A4d: quiescent P/S/E/O state custody v1d

**Status: INTEGRATION PASS (2026-10-16, trusted replay recovery and cold reset domain).**

## Scope

A4d extends the frozen A1/A2/A3 bounded logical reference through A4a mode
authority and A4c explicit cold candidate promotion. A trusted A4a EXECUTE
controller captures a canonical immutable A3d output only after RUN closes
and returns to QUIESCENT. The checkpoint binds the exact six-part execution
context, A4c active revision, source mode epoch and audit, source program image
(P), final per-neuron values and last timestamps (S), consumed and routed
occurrences with zero in-flight/outbox remainder (E), observations and
memory/compute ledgers (O). Every image is hashed independently, as well as
the complete canonical execution document.

A checkpoint is *not* proof of authentication against a malicious Python host:
SHA-256 is an integrity/checking primitive, and the trusted A4a controller and
source-pinned independent witnesses supply its provenance.

## Two recovery policies, carefully separated

**REPLAY_FROM_INITIAL_INPUTS (same context, same active revision).** A fresh
A4a controller re-runs exactly the immutable original case and the original
execution plans. A4d compares the complete canonical A3d outcome to the
captured checkpoint, including state, event and observation evidence. Success
returns an auditable recovery receipt. This is reconstruction by complete
re-execution, *not* injection of a saved state into a running PE and *not*
continuation from the final timestamp. Modified inputs, source state or active
revision deny recovery. No persisted file, disk journal or automatic recovery
agent is implemented.

**COLD_RESET (changed-program A4c promotion).** The original closed checkpoint
remains in custody, but cannot be replay-restored as the new active context.
A4d requires an exact current A4c promotion receipt, previous revision and
source context match, fresh candidate context match, and an explicit COLD_RESET
policy. The new A4a controller must start VERIFY, epoch zero, with an empty
audit; it enters EXECUTE and computes from the candidate's declared initial
state and events. An activation receipt binds snapshot, promotion revision,
new result and audit boundary. The same custody authority permits at most one
cold activation. Migration, hot swap, implicit rollback, stale receipt or
repeated activation fail closed.

A4d does **not** implement a live S/E/O migration, continuation/resume API,
state-space conversion across changed programs, user program training, durable
crash-atomic commit, recovery after a partly executed A3d batch, or physical
hardware isolation. Those remain separate future design problems.

## Planned coverage

- 216 pinned source cases x 3 PE placements = 648 closed source snapshots.
- 648 full same-context causal A3d reconstructive replays.
- 648 stale-revision recovery rejections after changed-program A4c promotion.
- 648 changed-program A4c cold activations under explicit COLD_RESET.
- 648 baseline A4b frozen Compiler/host witnesses and 648 changed-candidate
  frozen Compiler/host witnesses with independent ideal semantic parity.
- TRAINING and REMODEL staging both covered, 324 cases each.
- Distinct negative tests for noncanonical/tampered images, recomputed SHA
  forgeries exposed by independent replay, wrong current context, invalid
  active revision, nonquiescent controller, forged boundary, uncaptured inflight
  activity, disallowed migration, wrong target and double activation.

## Release gate

`bash search/spk_arch_a4d_final_gate_v1d.sh`

Six sections: pure custody tests, real frozen dual Compiler witnesses, canonical
source-pinned two-process replay, A4a/A4b/A4c regressions, full repository
regression, reference freeze and patch hygiene. Gate does not commit or tag.

## Certified A4d gate

- Independent state custody tests: 15 PASS.
- Frozen Compiler/host integration: 8 PASS.
- Closed state snapshots: 648.
- Same-context replay recoveries: 648.
- Stale-revision recovery denials: 648.
- Cold-reset activations: 648.
- Frozen baseline and candidate witnesses: 648 each.
- Previous A4 regressions: 52 PASS.
- Full repository regression: 3357 PASS.
- Independent-process evidence replay: PASS.
- Frozen source and patch hygiene: PASS.

Evidence SHA256:
8b4ada449fa0521dc9b3045776c36183a7d5fa7f14156d21d2b6815a0e4d91d5

Acceptance covers quiescent P/S/E/O custody,
same-context reconstruction by complete replay
and explicit COLD_RESET after authorized promotion.

No hot state migration, continuation from checkpoint,
durable crash recovery or automatic rollback is certified.
