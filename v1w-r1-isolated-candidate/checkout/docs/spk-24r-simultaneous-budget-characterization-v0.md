# SPK 24r: Simultaneous Budget Eligibility Characterization v0

**Status: INTEGRATION PASS (2026-10-16, bounded observational scope).**

Baseline: accepted SPK 24q after commit. This contract adds evidence about a
previously excluded budget boundary. Core v0, Network v0, Compiler v0 and all
previous simulator components remain unchanged.

## Purpose

24q established agreement for 216 exact-budget successful executions, 174
single `max_events` limits and 168 single `max_batches` limits. Those probes
avoid simultaneous exhaustion. The 24r extension asks which reason the frozen
Network v0 actually reports **when both constraints become unsatisfied on the
same pending batch**. An observational answer is not automatically a normative
priority rule.

## Independent eligibility construction

For a completed 24n execution containing at least two batches, choose the
last batch as the first one denied by both budgets. Set `max_batches` to the
number of earlier batches and `max_events` to the number of earlier processed
events. These budgets are positive. For the next pending batch, both hold:

- `processed_batches >= max_batches`
- `processed_events + pending_batch_size > max_events`

The proof uses only the independent 24n event interpreter and 24o primitive
corpus. It neither consults nor executes frozen Network v0 to derive the probe.
The 216-case corpus yields **168 dual-eligible probes**; cases with zero or one
batch have no valid positive `max_batches` preceding a later batch.

24n currently checks `max_batches` first. This is recorded as the independent
engine's **implementation choice**, not a specification of the frozen engine.

## Frozen experimental characterization

For every dual-eligible probe, run frozen Network v0 twice: observer OFF and
with the existing passive observer ON. Both must terminate by typed
`NetworkExecutionLimitV0`; the reported reason must be one of `max_events` and
`max_batches` and must be identical with observer OFF and ON.

A reason that differs from the independent interpreter's selected reason is
recorded transparently instead of being disguised as a normal differential
PASS or silently corrected. If the frozen engine consistently gives a
particular precedence, that is **observed bounded behavior**, not yet a
priority guarantee across all admitted programs. If the frozen reasons vary,
the counts must expose that variation rather than normalize it away.

Errors other than the typed limit propagate. No complete result, successful
receipt, atomic rollback, or complete partial observer trace is claimed on
an exhausted execution.

## Evidence and adversarial replay

Canonical schema: `spk-dual-limit-characterization-evidence/v0`.
Each row states the case identifier, budgets, independent prefix counters,
proof of simultaneous eligibility, selected independent and frozen reasons,
and `LIMIT_REACHED` with `result_sha256=null`.

The summary includes the original corpus fingerprint and counts of both frozen
failure reasons. Verification checks JSON uniqueness and canonical encoding,
the document checksum and an **entire recomputation of the probe matrix**.
Rehashing a forged priority cannot make it pass replay. Two independent Python
processes must produce byte-identical documents.

## Acceptance boundary and follow-up

An accepted 24r gate provides an empirical characterization of combined
budget failures for the bounded 216-case semantic corpus and 168 applicable
cases. It does not establish normative priority, which must be separately
specified and reviewed before a cross-engine exact-reason requirement is
added. In particular, we do not silently modify 24n or Network v0 to make
both report the same winner in a tie.

This extension is relevant to S4 (passive-observer failure noninterference)
and S5 (failure evidence and negative replay). It does not independently close
S3's broader application-host or the untested semantic fragments. Do not
increment roadmap estimates solely for passing the gate.

## Certified fwork gate - 2026-10-16

Baseline: dfd822a.

- Independent prefix tests: 10 PASS.
- Frozen dual-limit tests: 12 PASS.
- Dual-eligible probes: 168.
- Frozen max_events: 168.
- Frozen max_batches: 0.
- Previous budget/host regressions: 55 PASS.
- Full repository regression: 2854 PASS.
- Independent-process artifact replay: PASS.
- Frozen-source and patch hygiene: PASS.

Evidence SHA256:
d37b0161d3555c2f99f2d0cd8d7b172ce4e15101f048485f4510413de751e564

The frozen runtime consistently selected max_events in this corpus.
The independent 24n implementation selects max_batches in ties.

This records observed behavior, not normative error precedence.
No general SPK error-priority rule is established.

Roadmap: S1=100%, S2=100%, S3=85%, S4=80%, S5=90%.
Total=91% (equal weighting), unchanged.
