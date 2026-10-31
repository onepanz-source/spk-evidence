# SPK Native Learning v1s: one cumulative serialization and replay macro

## Purpose

Extend the **new versioned native v1** scheduler, which already showed `A PE judgment → native BV delivery → C P0→P1 → subsequent C PE executes P1`, and the v1r SQLite replay discipline. The frozen BV-v0e, original PE and original memory sources remain untouched.

## Contract and acceptance

1. A single cooperative POSIX `flock` protects each database during genesis replay, durable tick commits, inherited P use, and post-commit verification. Independent processes cannot each create a duplicate grant while using this API.
2. A series of epochs retains C's owned P across changes of goal and between complete invocations. A repeated identical series writes zero new tick rows and produces the same chain digest.
3. Seven crash points in a tick journal are recovered by deterministic re-execution and comparison with *each* earlier committed tick.
4. An audit refuses corrupted tick snapshots, hash-chain rows, parent P versions or terminal-result digests. Audit itself never appends tick rows.
5. Tests explicitly lock the journal from a different process, including two racing writers. Symlinked DB/lock paths and malformed requests fail closed.
6. Two independently reconstructed conformance reports must be identical. Tests of original PE/BV, the prior versioned scheduler, v1r durability, and T17–T14 are inherited.

## Boundaries

This is **not** global consensus, a distributed lease, an authenticated host, or immunity against processes that bypass the coordinator. `flock` is advisory. The runtime still uses bounded deterministic binary 11/12 PE programs and A 21/22 judgements. Recovery replays a local pure simulation: never replay external physical actuator side effects. `run_sequence` commits a recoverable prefix; it is not a transaction spanning epochs. The prior v1r full gate MUST PASS before running this cumulative gate.

## Recommended future architecture

Do not extrapolate this result to N-node or arbitrary programs. The next scientific gate should first define a **versioned, typed P intent** and more than two PE program alternatives, while preserving the proof that the updated P is actually read by the PE in the *same* scheduler. Avoid new observational wrapper layers that cannot affect C's execution.
