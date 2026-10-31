# SPK Architecture v1: A2d Bounded Memory Resource Failure Contract

**Status: INTEGRATION PASS (2026-10-16, bounded preflight and aggregate-service domain).**

## 1. Motivation and accepted boundaries

A2a reserves logical P/S/E/O units *before* PE execution; A2b authorizes
aggregate logical access intents *after* independently verified PE execution;
A2c schedules service of those aggregate intents using separate abstract
service ticks. A2d makes failure boundaries and status ownership explicit.

**These are two different failure times.** A rejected A2a admission prevents
A1d execution from being invoked. Insufficient A2c `max_service_ticks` may be
identified only *after* PE work occurred, because aggregate A2b demands are
constructed from a finished execution or a committed PE-fault prefix. It
cannot imply rollback or that an in-flight PE has been stalled.

## 2. Versioned outcomes

- `ADMISSION_REJECTED`: A2a rejected the memory plan and A1d was not invoked.
  The rejection may be due to capacity or malformed plan; diagnostics retain
  the original A2a reason. Only explicitly witnessed one-unit shortages are
  counted as capacity denials.
- `EXECUTED`: the admitted, trusted execution callback ran and yielded its
  *own* `CLOSED` or `PE_FAULT` outcome, without reinterpretation.
- `SERVED`: A2c accounted for **all** authorized logical units under the
  service ceiling. Its `complete_service` is a complete A2c service receipt,
  *not* a claim that the PE computation succeeded.
- `MEMORY_SERVICE_EXHAUSTED`: A2c hit `max_service_ticks`; no complete service
  receipt is returned. The preceding execution status remains available and
  distinct. No partial ledger, recovery, or atomic rollback is asserted.

A2d requires the controller-pinned digest of the independently reconstructed
A2a projection. Changes to that projection after pinning are rejected before
A2b service; a digest selected by an untrusted caller is NOT authentication.

Invalid access authority, epochs and resource-service plans continue to raise
A2b/A2c exceptions rather than being relabeled as exhaustion.

## 3. Boundary verification

For each nonempty authorized aggregate trace, obtain the minimum completion
boundary by rerunning A2c with a sufficient finite ceiling. Test service
at the exact tick boundary and, where strictly positive, one tick below it.
The full A2c run is a *reference computation*, not an independent temporal
oracle. Cases requiring one or zero ticks have no positive one-tick-short
budget; they are counted explicitly, not treated as coverage.

Each P/S/E/O one-unit memory-capacity mutation is admitted through A2a again.
The mutated plan must be rejected before invoking the execution callback.
Demand arithmetic, callback behavior, service states and the original PE
outcome are separately verified.

## 4. Corpus and evidence

The 216-case pinned corpus is exercised with three placements and the
compiled/host reference, 648 nominal A1d traces, 504 reachable PE-fault
prefixes, admission shortfalls and service-boundary probes. Provenance,
counts and canonical results are replayed in separate Python processes.

The source catalog fingerprint remains:
`cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5`.

## 5. Explicit nonclaims

No live memory interposition, access-level transactional isolation, atomic
rollback, physically timed memory controller, distributed resource ownership,
causal backpressure, persistent authority, or recovery is certified. The
priority E/S/P/O remains an experimental controller policy, not algebra.
A2d closes the fourth *bounded A2 rubric criterion*; it does not complete all
future memory-fabric engineering or certify A3.

## 6. Gate

`bash search/spk_arch_a2d_final_gate_v1d.sh`

The gate runs independent resource-failure tests, real Compiler/host
integration, independent-process canonical evidence replay, prior A2
regressions, the full test suite, and frozen-reference/staging hygiene.
No automatic commit or release tag is created.

## Certified A2d gate

- Independent memory exhaustion tests: 13 PASS.
- Frozen Compiler/host integration: 7 PASS.
- Capacity admission rejections: 2592.
- Compiled reference comparisons: 648.
- Nominal exact-service completions: 648.
- Nominal short-budget failures: 540.
- Fault-prefix exact-service completions: 504.
- Fault-prefix short-budget failures: 504.
- Nonprobeable one-tick-short boundaries: 108.
- Previous A2 regressions: 45 PASS.
- Full repository regression: 3157 PASS.
- Cross-process canonical replay: PASS.
- Frozen source and patch hygiene: PASS.

Evidence SHA256:
91d118030af6540bf7261f4dcb547f9edd30a4fd865ae49233544c51a08e13be

Acceptance is limited to pre-execution memory admission
and post-execution aggregate service adjudication.

No live memory interposition, causal stalls, atomic rollback,
durable recovery or physical memory behavior is certified.
