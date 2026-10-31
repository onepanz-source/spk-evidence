# SPK Architecture A3c: Causal Memory Permits v1c

**Status: INTEGRATION PASS (2026-10-16, conservative transaction-envelope domain).**

## Scope and assumptions

A3c is a new execution engine composed from frozen A1b PE-local arithmetic,
A3a inter-PE transport, A3b finite PE grants, A2a per-PE P/S/E/O admission,
and A2b controller-issued access policy. All frozen v0 components are unchanged.

The engine acquires **conservative, finite memory permits for a whole neuron
batch before executing it**. The cost is causal: a PE has to wait for all
permits and is then executed at the actual later logical tick. The computed
output is not merely time-shifted after the event.

## Resource envelope

For each PE-local batch, the controller constructs these intent quantities:

- `PROGRAM_REFERENCE` on P: number of program instructions.
- `STATE_LOAD` and `STATE_COMMIT` on S: one each.
- `BATCH_CONSUME` on E: number of pending input occurrences.
- `EMISSION_RECORD` on E: one per syntactic EMIT upper bound.
- `ROUTE_ENQUEUE` on E **at each destination PE**: one per syntactic
  possible route occurrence, including duplicated parallel edges.
- `OBSERVATION_RECORD` on O: one batch record plus one for every possible route.

A guarded EMIT that produces no output consumes no actual emission or route
record. Therefore `reserved_units >= actual_units` and the two counts are
**intentionally not equal**. Grant ledgers are recorded separately from
actual access intents. No instruction is executed during partial reservation.

Memory quotas are finite per PE, per domain and per shared fabric tick. Domain
precedence `E,S,P,O` is a controller policy for this experiment; it is not a
mathematical priority of the algebra. Partial reservations may span ticks;
only after completion can the A3b PE arbiter grant compute service.

## Key invariants

1. A2a capacity is admitted before execution, and A2b controller authority
   authorizes every reserve intent without caller-supplied privilege.
2. Actual access-intent count never exceeds its authorized reservation.
3. A3b is reproduced **exactly** with abundant memory permits, with both ideal
   and finite PE slots and both zero and positive additional route latency.
4. With finite memory permits, neuronal computation, timestamps, decay, and
   downstream routes are genuinely executed at the later grant timestamp.
5. Events, duplicated routes and cross-PE delivery occurrences are conserved.
6. Quota errors and causal horizon exhaustion fail explicitly; no completed
   result, rollback, recovery or backpressure is falsely claimed.
7. Evidence is pinned to the 216-case source fingerprint, compared with the
   actual frozen Compiler/host for 648 ideal zero-latency programs, and sealed
   with independently replayable canonical SHA-256.

## Known limits

This is an **atomic logical batch reservation model**, not instrumentation of
individual Python reads/writes, RAM cycles, lock contention or physical banks.
The intent quantities are conservative envelopes checked against observed
post-compute intent counts, not proofs of bytewise memory execution. A global
arbiter remains; link bandwidth, queue backpressure, asynchronous failures and
distributed clocks are not implemented. Additional A3 work is needed before
claiming full live memory transaction interposition.

The v1c architecture layer is kept separate from immutable Core, Network,
Compiler, bounded Simulator v0 and Architecture v0.

## Acceptance

Run `bash search/spk_arch_a3c_final_gate_v1c.sh` in the dedicated architecture
worktree after committing accepted A3b. The gate contains six independent
sections and does not automatically stage or commit new files.

## Certified A3c gate

- Independent causal memory tests: 19 PASS.
- Real frozen Compiler/host integration: 8 PASS.
- Causal memory executions: 2592.
- A3b ideal comparisons: 1296.
- Frozen compiled-host comparisons: 648.
- Memory-limited temporal changes: 1080.
- Previous regressions: 65 PASS.
- Full repository regression: 3232 PASS.
- Independent-process evidence replay: PASS.
- Frozen reference and patch hygiene: PASS.

Evidence SHA256:
47879a87837f19cd1b7994eb471c64cbb2ad5eb958c6c96f9fef5df39141c662

Acceptance covers conservative PE-owned causal memory
permits before neuronal batch execution.

No individual physical RAM transactions, causal link
backpressure, recovery or distributed clock is certified.
