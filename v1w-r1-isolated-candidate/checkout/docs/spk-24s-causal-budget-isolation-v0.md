# SPK 24s: Causal Budget Isolation & Ambiguous-Tie Evidence v0

**Status: INTEGRATION PASS (2026-10-16, bounded diagnostic scope).**

Baseline: accepted 24r checkpoint, after the 24q and 24p reference gates.
SPK Core v0, Network v0, Compiler v0, and the earlier simulator remain frozen.

## Motivation

24q demonstrated exact-reason parity on unambiguous failures. 24r then proved
that both limits were eligible at the same pending batch in 168 bounded corpus
cases. Frozen Network v0 reported `max_events` in all 168; the independent 24n
interpreter reported `max_batches`, following its own guard order.

This is a **difference in tie-break diagnostics**, not yet a contradiction of
a documented normative priority. A failure gate that equates these reasons
unconditionally would falsely label an implementation choice as semantics.

## Causal triplets

For every 24r eligible prefix, independently determine the number of already
processed batches `B`, processed events `E`, and events in the next batch `k`.
Construct exactly three probes at the SAME next batch:

| Condition | max_batches | max_events | Required violated conditions |
|---|---:|---:|---|
| both | B | E | batch and event |
| events_only | B + 1 | E | event only |
| batches_only | B | E + k | batch only |

All three must reach `LIMIT_REACHED`, never publish a successful full result,
and produce no claim of rollback. `events_only` must diagnose `max_events`,
`batches_only` must diagnose `max_batches`. For `both`, the frozen reason must
be one of the independently proven simultaneously violated constraints; record
its exact value but do not require equality to 24n's arbitrary tie choice.

The passive observer must not change the selected reason for any of the three.
The 168 eligible prefixes yield **504 paired (observed/unobserved) probes**.
This is not 504 distinct network fixtures; all probes derive from the bounded
216-case corpus and are evaluated at the identical causal boundary.

## Independence and admissibility

The planner imports only the primitive 24n interpreter and the 24o corpus,
not frozen Core/Network/Compiler. It first verifies that both budgets are
insufficient at the selected pending batch and then checks the individual
relaxations via the independent engine. The frozen evaluator is in a separate
module and does not use its reported reason to select budgets.

The engine's choice for the ambiguous tie is retained as an observable datum.
The exact-reason differential is **normative only for singleton violations**
in this test contract. Changing that policy requires an explicit reviewed
SPK specification decision; do not adjust frozen code to satisfy the test.

## Evidence

Receipt schema: `spk-causal-budget-failure-evidence/v0`.
The receipt records each probe's case, budgets, independently justified set
of violated constraints, chosen independent and frozen diagnostic reasons,
limit status, and absence of any successful result. It includes the unchanged
corpus fingerprint, isolated exact-parity totals, observed tie counts, and
counts of disagreements with the independent engine's diagnostic choice.

Rechecking a checksum is insufficient: verification recomputes every probe
against both engines. JSON has unique keys and canonical bytes. Modifying
an observed reason and regenerating the digest must fail on replay.
Two separate Python processes must produce byte-identical receipts.

Checksums provide reproducibility and integrity relative to the submitted
artifact, not proof of authenticated sensor provenance or source authority.

## Acceptance and limits

Gate stages: (1) independent triplets, (2) frozen/observer differential,
(3) two-process evidence replay, (4) 24q/24r regressions,
(5) full suite, (6) frozen-module and workspace hygiene.

The accepted gate would strengthen S4 and S5 evidence for causal failure
classification without automatically increasing completion percentages.
Roadmap remains S1=100%, S2=100%, S3=85%, S4=80%, S5=90%; total 91%.

**Not established:** general precedence law for all SPK executions, ordering
of simultaneous errors beyond these two budgets, arbitrary observer safety,
partial-result rollback, persistent exactly-once execution, distributed
ownership, or universal semantic equivalence.

## Decision left open

A future normative review may specify one global winner (`max_events` or
`max_batches`), or instead declare exact failure reasons implementation-defined
on simultaneous eligible limits while preserving the violated-condition set.
24s observes and isolates the alternatives. It does **not** choose one by
changing the specification silently.

## Certified fwork gate - 2026-10-16

Baseline: 2246949.

- Independent causal-triplet tests: 10 PASS.
- Frozen and observer tests: 13 PASS.
- Causal triplets: 168; conditions: 504.
- Singleton exact agreements: 336/336.
- Simultaneous frozen max_events: 168/168.
- Simultaneous independent max_batches: 168/168.
- Previous failure-contract regression: 42 PASS.
- Full repository regression: 2877 PASS.
- Cross-process canonical replay: PASS.
- Frozen-source and patch hygiene: PASS.

Evidence SHA256:
bbf336a945043c6e4dcb603c7d60cc7c144247adbb691670653f9f5bee29e864

The difference in simultaneous diagnostic selection is observed,
not classified as a semantic violation without a normative rule.

Roadmap S1=100%, S2=100%, S3=85%, S4=80%, S5=90%.
Total=91%, equally weighted, unchanged.
