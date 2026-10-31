# SPK Architecture A4a: Mode Authority and Quiescent Epochs

**Status: INTEGRATION PASS (2026-10-16, trusted quiescent logical epochs).**

## Contract

A4a introduces a controller-owned **operating mode epoch** over the existing
A3d deterministic PE-local causal engine. It does **not** alter any previously
certified Core, Network, Compiler, Simulator, A1/A2 or A3 source.

| Mode | Authorized A4a action | Explicitly forbidden |
|---|---|---|
| `VERIFY` | `REPLAY` source-bound deterministic A3d run against pinned full output digest | live `RUN`, candidate staging |
| `EXECUTE` | `RUN` full A3d engine with bound context | candidate staging, self-replay override |
| `TRAINING` | `STAGE` candidate reference SHA-256 only | live execution, executable model modification |
| `REMODEL` | `STAGE` candidate reference SHA-256 only | live execution, remapping or neuron program rewrite |

Transitions run only when the controller has established `QUIESCENT` status
following a successful run/replay or a staging operation. Any A3d failure,
unknown expected digest or mismatched replay during an active operation leaves
the controller `FAULTED`: no automatic transition, rollback, retry or restore.
The canonical transition graph is:

- `VERIFY` -> `EXECUTE`, `TRAINING` or `REMODEL`;
- `EXECUTE`, `TRAINING`, `REMODEL` -> `VERIFY` only.

A full context fingerprint binds the exact program+event dataclasses, PE
ownership/static routes, transport latency and capacity, PE service grants,
causal memory permits, and sender link/backpressure limits. A change to any
of these inputs invalidates the current mode epoch **before** the engine runs.
A successful A3d run must have zero remaining in-flight/outbox occurrences,
matched delivered remote routes, and a complete batch transcript.

The controller is **trusted in-process Python code**, not a security boundary
against an adversary who can manipulate Python objects or its private members.
The `VERIFY` action deterministically **re-executes** a pure A3d simulation;
it is not a hardware read-only probe. Its expected digest must be fixed
independently by the caller: a digest chosen by the same attacker is not
cryptographic authentication.

`TRAINING` and `REMODEL` do not train, change any memory values, rebuild a
compiled program, or install candidate programs. They only stage opaque
digests under mode-specific authority and require a return to `VERIFY` before
another live execution can be admitted. Full learning/remodel policies remain
future A4 work.

## Acceptance and limitations

- For each of the 216 pinned networks and all three PE placements, exercise
  six mode transitions, two candidate reference stages, a live **finite-link
  A3d** execution, and an independent verified rerun: 648 of each run type.
- Compare each live result to the existing A3d real Compiler/host-backed
  oracle transcript under the same latency/placement/service limits.
- Reject mid-run transitions, activity elevation, all six context-drift
  dimensions, mismatched/missing replay digest, and failed engine runs.
- Canonical evidence must be byte-identical in independent processes; a
  checksum recomputed on a forged receipt must fail semantic replay.
- All frozen modules and earlier A1/A2/A3 stages are immutable.

Not certified: real training, remodeling, checkpoint resumption, live
synchronization, distributed mode authority, physical transaction enforcement,
or authentication of hostile Python processes.

## Certified A4a gate

- Independent operating-mode tests: 18 PASS.
- Frozen Compiler/host integration: 7 PASS.
- Mode-controlled executions: 648.
- Independent mode replays: 648.
- Staged candidate references: 1296.
- Previous regressions: 39 PASS.
- Full repository regression: 3284 PASS.
- Independent-process canonical replay: PASS.
- Frozen reference and patch hygiene: PASS.

Evidence SHA256:
2bd988fe55ee7092553620c7a133cc457751816c194baad6e47da30f4339d505

Acceptance covers mode authority, trusted logical epochs,
context binding and quiescent mode transitions.

No actual training, candidate promotion, durable recovery,
physical isolation or automatic rollback is certified.
