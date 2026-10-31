# SPK V5/T11: Macro-checkpoint for owned memory authority V1

**Classification:** additive experimental/new versioned runtime. No modification of frozen Core, Network, Compiler, PE, BV-v0e or original Memory Contract. No native SPK learning claim.

## Reason to consolidate

Previous T6–T10 checkpoints individually demonstrated semantic feedback, transactional reference P, an asynchronous reference scheduler, concurrency, causal stale-credit quarantine, resource quotas, store fences and an independent admission provider. The repeated 48/84/88/88 results are reproducibility tests, **not new learning benchmarks**.

This macro-checkpoint combines six workstreams in one source release, one cumulative gate and one published report:

1. **Owned Memory Contract V1:** a new-runtime versioned `OwnedMemoryV1` with explicit C/P/execute/PE-C-RESEARCH scope and a dedicated persisted grant ledger.
2. **Event-time integration:** at the actual `SEM_B_C` tick, the SQLite BEFORE UPDATE provider callback checks the V1 contract. The new-runtime authority grant is recorded by an AFTER INSERT trigger on the provider receipt, inside the *same SQLite transaction* as the reference P CAS. Direct P writes remain forbidden.
3. **Resource admission:** separate global/context V1 budget with revision-CAS, verify/execute mode, no retroactive quota contraction or partial commits.
4. **Concurrent credit:** three in-flight episodes, stale-version veto, one grant per contextual P version, comparison against context-affinity and serial.
5. **Durability/adversarial:** crash-style close/reopen, pending events, duplicate prevention, trigger tamper detection, wrong owner/domain/mode/PE requests, zero-budget rollback, false native receipt rejection.
6. **Full lineage and honest boundary:** replay byte-exact of T10JKL source report, pinned T10STU `fwork` report, all inherited manifests/suites, frozen 12 original source pins, independent two-run report and a read-only native API inventory.

## Acceptance criteria and observed local results

- Fixed/naive-three/context-affinity/serial = **48/84/88/88** successes out of 96. Concurrency-control is not assumed physically clock-accurate.
- New runtime V1 authority: **8 grants and P commits** on the adapting task. This is *more* than a mere renamed reference receipt: V1 admission is checked by a separate callback policy and persists in its own typed grant ledger. The underlying implementation still shares a privileged host and SQLite transaction.
- Frozen original SPK Memory Contract: **0 grants / 0 P writes / 0 semantic BV native deliveries**.
- Reopened affinity output is byte-for-byte equivalent to uninterrupted affinity output. Two full local reports are byte identical.
- All 47 new tests PASS; inherited T10STU/T10JKL/T10ABC 25/32/53 PASS locally. Source-specific full historical regressions must run on `fwork` before publishing.
- User's `fwork` SHA for preceding T10STU: `8e06cd938024ccfaf63ad43f3c9b5e02d1b1d4f34fa4fccc5b201135a824f36c`. The launcher fails if it differs.

## Known limits (blocking native promotion)

- This module lives in `research/spk_v5_t11_macro_memory_v1`, not an adopted SPK native Memory Contract version. The original native API is only surveyed via AST, not invoked or patched.
- No independent issuer or trusted A sensor; a privileged host can fabricate and reseal the entire database, event log, callback or policy.
- The resource model covers C/P only, not actual native S/E/O occupancy or full hardware PE allocation.
- This exercise uses predeclared synthetic two-context goals; its positive results do not show generalization to new tasks.
- All grants are logically owned by **new reference runtime V1**, never the original frozen SPK runtime.

## Next macro milestones, not micro-gates

**Macro-II: Actual SPK memory interface adoption**: identify an explicitly authorized Memory Contract API on `fwork` from the read-only inventory; create a *versioned* implementation with tests for ownership, permissions, capacity, transaction mapping and frozen backward compatibility. Where no stable source API exists, fail closed and define the API rather than guessing it.

**Macro-III: Native-v1 semantic BV runtime and learning**: integrate A verdict into a versioned SPK runtime event with explicit source/evidence authority; credit the correct C decision; apply P through the admitted interface on tick; use asynchronous concurrency, independent receiver and held-out interventions. A privileged host can still forge a non-attested source; do not promote until that scope is explicitly accepted or solved.

Progress percentages from the historic S1–S5 rubric are unchanged, **not** native readiness evidence. Adopt new measurable completion gates rather than raising 94% merely from more research files.
