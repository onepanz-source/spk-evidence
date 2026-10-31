# SPK 24t: Diagnostic Equivalence Host v0

**Status: INTEGRATION PASS (2026-10-16, bounded reference host scope).**

Baseline: accepted SPK 24s checkpoint. 24n oracle, 24p reference host,
Core v0, Network v0 and Compiler v0 are not changed.

## Problem and decision

24s shows 336/336 singleton-failure parity results, but 168/168
simultaneous failures have a frozen selection of `max_events` and an
independent interpreter selection of `max_batches`.

24p requires exact equality of *selected diagnostic* for all failures,
so it can incorrectly reject a genuinely dual-eligible failure.
This package introduces a **separate versioned reference contract** and
reference host, without altering or silently changing 24p receipts.

For budget exhaustion at the **first batch where processing is disallowed**:

- no violated conditions: both engines must finish with equal full projection;
- exactly one violated condition: both must fail with that exact reason;
- two simultaneously violated conditions: both must fail, but either reason
  may be selected, provided it belongs to the independently derived eligible set;
- the passive observer must preserve the *same chosen reason* as the frozen
  unobserved run, even when the choice is implementation-dependent;
- any other exception propagates: it is never masked as a successful receipt.

This is a **diagnostic equivalence policy for this versioned reference host**.
It is not a new Core algebra axiom, nor a retroactive promise about older
receipts. The selected reason is retained in the receipt, not normalized away.

## Independently bounded proof

The pure module `search/spk_24t_diagnostic_contract_v0.py` imports no frozen
Core, Network, Compiler or runtime components. It admits a case only if the
independent interpreter can complete it under the declared fixed reference
ceiling (128 batches, 4096 events). From that complete trace, it computes
prefix event and batch counts and identifies the first rejected logical batch.
It checks the independent interpreter's actual limited execution is consistent.

A program exceeding this ceiling, a nonterminating cycle, unknown opcode or
invalid Core-state execution **fails closed**, even if a smaller caller limit
would have stopped the frozen runtime earlier. This deliberate coverage
restriction is necessary because the proof requires a complete finite trace.

The 24t manifest host source-pins and decodes an existing Compiler manifest;
uses the actual frozen Network through the already defined 24p `_attempt`;
performs ON/OFF observer comparison; checks its independently derived
eligibility proof; and verifies successful full projections by the 24n oracle.
No alternate scheduler, Core canonicalizer or frozen-module change is added.

## Signed? No. Replayed? Yes.

Receipt schema: `spk-diagnostic-equivalence-reference-host/v0`.
The receipt retains the exact original manifest, pinned digest, both caller
budgets, selected frozen reason, eligible-reasons set, independent choice,
reference adjudication and complete result only in successful executions.
Canonical JSON and digest allow reproducible replay. Verification recomputes
every value from the pinned manifest and frozen runtime, not just its SHA-256.

Digests are not cryptographic source authority or a signature. The
single-shot object is cooperative, in-process and not persistent exactly-once.
Partial work in a limited execution is neither rolled back nor published as a
completed result. Arbitrary observer callbacks are not certified.

## Acceptance gate

1. Independent 24q/24s plan classification and falsification controls.
2. Real frozen Compiler manifest + Network/OFF/ON tests, including dual tie.
3. Separate Python process receipts for success, isolated and dual failures.
4. Earlier 24p/24q/24r/24s contract regressions.
5. Complete pytest repository suite.
6. Frozen-boundary, workspace and archive hygiene.

No percentage increase is assigned before the authoritative gate. Baseline
S1=100%, S2=100%, S3=85%, S4=80%, S5=90%, total 91% equally weighted.

## Certified fwork gate - 2026-10-16

Baseline commit: e16a280.

- Independent diagnostic contract tests: 13 PASS.
- Frozen Compiler/Network host tests: 12 PASS.
- Previous 24p/24q/24r/24s regressions: 100 PASS.
- Complete repository regression: 2902 PASS.
- Cross-process canonical receipt verification: PASS.
- Frozen-source and patch hygiene: PASS.

Certified reference outcomes:
- CLOSED: EXACT_PASS.
- Isolated max_events: EXACT_PASS.
- Isolated max_batches: EXACT_PASS.
- Simultaneous violations: AMBIGUOUS_TIE_PASS.

Reference evidence SHA256 for simultaneous violation:
acb90f9078092b57e9f804700eac59532d2461c5e035271ee764187eb3c19d11

The host preserves the selected frozen diagnostic and accepts
either independently eligible reason on a simultaneous violation.

Scope limitations:
- Host integration is tested on a bounded compiled reference network.
- Corpus-wide diagnostic adjudication is tested independently.
- No universal observer noninterference is asserted.
- Receipts are reproducible, not signed or externally authenticated.
- Single-shot execution is cooperative, not persistent exactly-once.
- No atomic rollback is provided.

Roadmap estimates remain:
S1=100%, S2=100%, S3=85%, S4=80%, S5=90%.
Total=91% (equal weighting), unchanged.
