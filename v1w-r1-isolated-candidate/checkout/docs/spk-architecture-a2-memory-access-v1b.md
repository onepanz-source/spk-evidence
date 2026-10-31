# SPK Architecture v1: A2b Logical Memory Access Authorization

**Status: INTEGRATION PASS (2026-10-16, bounded logical access domain).**

Baseline: frozen simulator tag `spk-simulator-bounded-reference-v0` at
`a76ebaae49373a4c6b66f94465d78dbf1cf19f80`.
A2a source projection evidence fingerprint:
`c7164a8abdf27e747f3522ec29b0449574aee219ab525b7f9cc1aff4acc80082`.

## 1. Design boundary

The pre-existing `docs/spk-memory-contract-v0.md` and
`docs/spk-memory-access-model-v0.md` distinguish *logical access intent* from
*authorized resource transaction* and physical memory implementation.
Permissions, access priority and arbitration are independent dimensions.

A2b adds an executable **simulator authorization policy for existing A2a
logical access aggregates**. A2a reconstructs real A1d committed batch and
route traces; A2b checks which controller-issued activity has the right to
account each logical intent in an admitted execution epoch and target PE.
Neither module simulates physical RAM access or enforces grants inside the
A1d batch scheduler. Runtime enforcement is future work.

## 2. Authorized activities and logical intents

| Domain | Intent | Controller activity |
|---|---|---|
| P | PROGRAM_REFERENCE | EXECUTE |
| S | STATE_LOAD, STATE_COMMIT | EXECUTE |
| E | BATCH_CONSUME, EMISSION_RECORD | EXECUTE |
| E | ROUTE_ENQUEUE | ROUTER |
| O | OBSERVATION_RECORD | OBSERVER |

`EXECUTE`, `ROUTER`, and `OBSERVER` are distinct logical activities. The
admitted principal is deterministically scoped to `activity/pe_id/epoch`;
permissions never derive from the request's self-proclaimed activity.
`issue_authority_v1b(admission)` creates a fixed controller policy for all
admitted PE identities and domains before execution; the subsequent request
set must equal the one reconstructed from A2a. The request has no priority
field and cannot appoint itself a more privileged role.

`EMISSION_RECORD` may be present in A2a with quantity zero when a guarded
batch emits no output. This is accepted as *zero accounting*, not a memory
request. Zero quantities for all other intents are rejected. Parallel routed
occurrences are counted with full multiplicity.

## 3. Failing closed

The versioned `AccessAuthorityV1b` must exactly match controller policy.
Missing or enlarged grants, unknown PE, mismatched epoch, unknown domains,
wrong activity, duplicated/omitted/reordered requests and forged quantities
fail before an authorization verdict. The admitted A2a ledger is the only
permitted input to the logical access mapper. Grant identity is procedural,
not cryptographic: **arbitrary Python object construction is outside the
security boundary**. This is a conformance property, not user authentication.

A2a pre-execution memory admission must precede A1d execution. A2b authority
is then issued before the A1d execution. Authorization of actual recorded
access occurrences happens on the post-execution independently verified
A2a ledger, not in the live Core execution loop. Fault prefixes are
explicitly `PE_FAULT`, not `CLOSED`, and are audited only for committed work.

## 4. Scope and evidence

Pinned source catalog SHA256:
`cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5`.

- 216 canonical networks, three admitted A1 PE placements: 648 frozen
  Compiler/host comparisons and corresponding nominal A2b decisions.
- Exactly 504 additional fault prefixes admitted and projected via A2a.
- Negative tests for wrong epoch, ownership, role, domain, grant augmentation,
  missing or inserted requests, unknown intent, boolean quantities,
  illicit priority claims and tampered A2a ledger.
- Deterministic canonical attestation, independent-process replay and
  digest recomputation forgery tests.

The Compiler and frozen Network run only through the integration adapter.
The A2b domain module does not import frozen Core, Network or Compiler code.

## 5. Explicit non-claims

- No authentication, signed grants or host-language memory isolation.
- No enforcement *during* actual PE-local memory operations.
- No candidate program writes, SNAPSHOT_READ, OBSERVATION_READ or activation
  privileges; those require separate mode and candidate-store contracts.
- No resource bandwidth, memory service scheduling, SERVICE_TIME or
  architectural transaction count. A2c will address the service mapping.
- No dynamic epoch changes, routing revalidation beyond A2a, persistence,
  atomic rollback, hot-swap or PE failover.

This bounded contract does not imply the full A2 Memory Fabric is complete.

## 6. Final gate

`bash search/spk_arch_a2b_final_gate_v1b.sh`

Six stages: pure access tests, real Compiler/host integration, independent
process replay, A2a/A1d regression, entire repository regression and frozen
component/patch hygiene. No commit or tag is created by the gate.

## Certified A2b gate

- Independent authorization tests: 15 PASS.
- Frozen Compiler/host integration: 7 PASS.
- Authorized nominal executions: 648.
- Authorized fail-stop prefixes: 504.
- Previous A2a/A1d regressions: 26 PASS.
- Full repository regression: 3112 PASS.
- Independent-process evidence replay: PASS.
- Frozen-source and patch hygiene: PASS.

Evidence SHA256:
22564bbdde8c5a3e1a358735498eb274d3e6c4eee3f1cbcc358a0b1a31bebacc

Acceptance covers authorization of independently verified
P/S/E/O logical access aggregates.

No live memory access enforcement, memory bandwidth
arbitration, physical memory isolation or causal timing
is certified.
