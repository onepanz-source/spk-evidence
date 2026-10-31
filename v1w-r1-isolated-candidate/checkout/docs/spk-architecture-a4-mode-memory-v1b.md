# SPK Architecture A4b: Mode-Bound P/S/E/O Logical Memory Authority

**Status: INTEGRATION PASS (2026-10-16, trusted logical replay scope).**

## Scope and authorities

Builds exclusively on the frozen A4a `ModeControllerV1a`, A2a projection,
A2b logical access authority, and A2c finite *aggregate* service. It introduces
no new access intent, neuron instruction or mutable deployed program. The
controller's **completed** current action and quiescent A4a boundary are
required before a memory service permit can be issued.

| Mode | Last completed A4a action | Logical memory scope | Service priority |
| --- | --- | --- | --- |
| `EXECUTE` | `RUN` | `EXECUTION_LEDGER` | E, S, P, O |
| `VERIFY` | `REPLAY` | `ISOLATED_REPLAY_LEDGER` | P, S, E, O |
| `TRAINING` | `STAGE` only | none | none |
| `REMODEL` | `STAGE` only | none | none |

Both EXECUTE and VERIFY require the same independently checked A2a/A2b
logical access intents because replay has **private simulated state** rather
than accessing the deployed program. The difference is controller-assigned
priority and a tagged logical scope. These tags do **not** establish physical
memory protection, sandboxing or principal authentication.

## Epoch-bound permit

`issue_mode_memory_permit_v1b()` binds mode, epoch, context digest, audit
digest, A4a result digest, A2a admission/projection, A2b controller authority,
request list and mode-specific policy. `serve_mode_memory_v1b()` reissues
and compares the entire permit against the live trusted controller state.
A transition, new action, forged priority, altered projection, stale epoch or
unclosed activity fails closed. The A2c service plan is created by the
controller based on its fixed mode policy, not supplied by an access request.

Services are applied to **A2a/A2b post-execution aggregates**, with A2c's
independent service clock. Exhaustion propagates and must not produce a
successful service verdict. No A4a or A3d source is changed.

## Full differential witness and limits

The adapter checks 216 frozen-source cases x 3 PE schemes. Each case is
witnessed through two distinct frozen Compiler/host paths: A4a/A3d and
A2b/A1d/A2a. It checks the exact compiled manifest identity, A4a context
and audit digest, A2b authorization digest, then performs two mode-scoped
logical service runs and two explicit staging-mode denials.

The A1d memory-reference trace is not a trace of A3d physical accesses.
This experiment cannot claim that the A2c post-run memory service caused
A3d's observed neuronal timestamps. The service is authorization and
priority conformance, not live memory interposition.

No candidate promotion, learned update, checkpoint migration, rollback,
physical RAM access, hardware isolation or secure hostile-host boundary
is implemented. Changing `MODE_POLICY` is a new architecture policy and
requires renewed conformance evidence; its orders are not Core algebra laws.

## Gate

`bash search/spk_arch_a4b_final_gate_v1b.sh`

Six sections: independent mode-rights/priority tests; real frozen Compiler
integration; two-process canonical replay; prior A4a/A2b/A2c tests; full
repository regression; annotated v0 tag and immutable predecessor checks.
No automatic commit or tag is created.

## Certified A4b gate

- Independent mode-memory authority tests: 18 PASS.
- Frozen Compiler/host integration: 8 PASS.
- Compiled host comparisons: 648.
- Mode logical service runs: 1296.
- Staging memory denials: 1296.
- Previous A4a/A2 regressions: 51 PASS.
- Full repository regression: 3310 PASS.
- Independent-process evidence replay: PASS.
- Frozen source and patch hygiene: PASS.

Evidence SHA256:
f6960f1af5d335d97072dc8ac90299637f392bb81011c9a24ebe3c2266348df8

Acceptance covers mode-scoped logical P/S/E/O
authority, priority, epoch binding and permit revocation.

No candidate promotion, program modification,
physical isolation, durable recovery or live
memory enforcement is certified.
