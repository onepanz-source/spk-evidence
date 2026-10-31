# SPK 24v: Cross-Layer Negative Admission & Observer Fault Isolation v0

**Status: INTEGRATION PASS (2026-10-16, bounded injection scope).**

Baseline: commit `4e6d5f8`, the accepted SPK 24u cross-layer conformance.
Frozen `spk_core`, `spk_network`, `spk_compiler`, `spk_architecture`, and
`spk_simulator` are **not** modified. Nor are any 24m–24u modules modified.

## 1. Rationale and deliberately narrow claims

SPK 24u certified full source-to-Compiler-to-host conformance on 216 three-node
cases (408 host executions). That proved successful operation and resource
budget handling on a bounded corpus, but not rejection of malformed requests or
failure isolation for unexpected observer behavior.

24v tests the **negative execution boundary** of the existing 24t reference host.
It is a deterministic fault-injection audit, not a new compiler, scheduler,
observer API, recoverable transaction protocol, or exception taxonomy for Core.

The word *isolation* means **fail-closed evidence publication**: an observer
fault must not cause an affirmative `CLOSED` receipt. It does NOT mean callbacks
cannot affect intermediate runtime execution, nor that a failed run is rolled
back. Observer callback errors are deliberately visible to callers.

## 2. Source-pinned admission rejection matrix

Original 24o corpus identity:
`cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5`.

For every one of the **216 already-compilable sources**, 24v generates a
manifest and submits **seven malformed requests** to the 24t host:

| Negative request | Expected boundary |
| --- | --- |
| Wrong 64-digit manifest pin | Hash source-pin mismatch |
| Malformed non-hex manifest pin | Digest format rejection |
| `max_batches=0` | Positive-integer budget validation |
| `max_events=True` | Type-strict budget validation (bool is not int) |
| Truncated source-pinned JSON (`{`) | Manifest JSON decoding |
| Wrong source-pinned root type (`[]`) | Manifest schema decoding |
| Non-text manifest (`42`) | Input type validation |

**1,512 admission attempts** must be rejected without reaching `_attempt`,
which is guarded by an injected fail-stop sentinel. If ANY request reaches the
execution boundary, or receives a success receipt, the gate fails. Malformed
manifest tests use the digest of the malformed content, so they cannot pass
solely because an earlier source-pin check rejects the request.

Additionally, for the **36 `duplicate` input cases**, compilation is attempted
with a syntactically malformed Network IR string. The frozen Compiler must
reject it; no source mutation is treated as a valid compiled program.

## 3. Observer fault evidence

For the 36 `at_zero` cases (6 profiles × 6 topologies), test the observer's
`on_batch` behavior using the real frozen Network and the actual versioned
host. For each case:

- A callback raising an injected exception must abort the host, leaving its
  cooperative single-shot phase `FAILED`, with no successful receipt.
- A callback that **silently drops** an observation must be caught by the
  existing independent comparison. A matching neuron result alone is not enough.
- After restoring the callback, a **new** host instance must be able to close.
  This does not imply rollback of the poisoned instance.

For 5 emitting relay topologies, repeat both faults for `on_route`.
This yields **82 observer callback fault attempts**.

For 36 duplicate cases, independently inject an incorrect observed failure
reason (`max_batches` instead of actual `max_events`, with `max_events=1`).
The host must detect the observer diagnosis change, reject publication, and
retain phase `FAILED`.

For six representative profiles, a test-only patch raises an unexpected
non-budget `RuntimeError` from the frozen execution entry. The host must
propagate it and consume the one-shot instance without a receipt. This tests
**host fail-closed wiring**, not a real Core exception mechanism.

## 4. Evidence and authenticity limitations

All planned source IDs and corruption kinds are deterministic and hashed. The
receipt contains the rejection **exception class** and all fault rows. Two
independent Python processes must produce exactly the same canonical JSON and
SHA-256. Verification recomputes the full audit; a payload changed and then
rehashed must still fail replay.

The digest provides **consistency**, not signature or external authenticity.
The injection harness temporarily monkeypatches *test-process* objects:
run it only in an isolated, single-threaded test context. It is not suitable
for production process instrumentation. No modified source file is committed.

## 5. Release gate

1. Independently pinned corpus and pure fault harness tests.
2. Real-fwork Compiler negative IR, host admission, callback and diagnostic
   fault test suite on frozen Compiler/Network and existing 24t host.
3. Canonical artifact equality and replay in separate Python processes.
4. Previous 24o, 24t and 24u bounded regressions.
5. Complete repository pytest regression.
6. Frozen source/staging/patch hygiene.

**Any real-fwork failure is a diagnostic result, not permission to relax the
contract silently.** In particular, a callback error which the frozen runtime
suppresses must be characterized before an adapter policy can be designed.

## 6. Outside certified scope

24v makes **no** claim of arbitrary observer noninterference, observer
sandboxing, pre-failure state rollback, event persistence, exactly-once across
process restarts, authenticated receipts, distributed authority, PE contention,
learning, or semantic completeness for programs outside the original corpus.

The previously accepted engineering roadmap stays at S1=100%, S2=100%,
S3=90%, S4=80%, S5=90%; mean **92%**, unchanged pending the authoritative gate.
No percentage increase follows merely from the number of negative attempts.

## 7. Certified integration gate - 2026-10-16

Baseline: 4e6d5f8.

- Independent plan and fault protocol tests: 23 PASS.
- Frozen Compiler/Network negative tests: 8 PASS.
- Manifest admission rejections before executor: 1512.
- Observer callback faults: 82.
- Observer diagnostic corruptions: 36.
- Malformed Compiler source rejections: 36.
- Injected unexpected runtime aborts: 6.
- Prior 24o/24t/24u regressions: 50 PASS.
- Full repository regression: 2952 PASS.
- Canonical cross-process replay: PASS.
- Frozen-source and patch hygiene: PASS.

Plan SHA256:
9d12b3d1662766d145de6f1df0b642a278d24fea32ff75e1ff71fa3396874f8c

Evidence SHA256:
a5f23f7cf402bbc8289cb04d56ec0d66784bb4b713799da94b69c85ee0b4da3e

Acceptance is limited to the declared negative admission
and fault-injection domains.

Fail-closed receipt publication is verified. Arbitrary observer
isolation, transaction rollback, durable recovery, authenticated
receipts and distributed authority are not certified.

Roadmap engineering estimates:
S1=100%, S2=100%, S3=90%, S4=85%, S5=90%.
Total=93%, equally weighted; previous 92%, delta +1 pp.
