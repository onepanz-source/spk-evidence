# SPK 24q: Corpus-Wide Failure Parity and Observer Boundaries v0

**Status: INTEGRATION PASS (2026-10-16, bounded budget domain).**

Baseline: SPK 24p after its accepted integration gate; 24o corpus ID:
`cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5`.
Core, Network, Compiler, Architecture and prior Simulator modules are frozen.
No changes to those modules are included.

## Objective

Expand 24p's exact successful/failed outcome parity from a two-neuron reference
network to the already accepted 24o **216-case** corpus, while keeping the
independent 24n interpreter responsible for predicting expected outcomes.
The frozen Network runtime supplies only actual outcomes. The passive observer
is run separately, and errors cannot be represented as successful receipts.

## Deterministic budget probes

A pure, frozen-independent planner executes 24n once per case under ample
bounded limits and produces up to three probes per case:

1. `exact_success`: precisely the observed successful work budget, except the
   API minimum of 1 when the corpus contains no work;
2. `event_limit`: 1 less than the successful event count, only if at least 2
   events are processed, with ample `max_batches=128`;
3. `batch_limit`: 1 less than the successful batch count, only if at least 2
   batches are processed, with ample `max_events=4096`.

The resulting fixed plan contains **558 probes**: 216 successes, 174 event-limit
rejections and 168 batch-limit rejections. It contains no zero/negative budgets.
It deliberately excludes simultaneous exhaustion of both budgets, where
error-priority semantics must be specified separately before verification.

The original 24o `guard_overwrite` primitive is retained by the independent
planner and oracle; the frozen adapter continues to apply the previously
accepted Core-IR canonical admission normalization without modifying Core v0.

## Acceptance rule for each probe

Run frozen Network with and without the internal passive observer, and run 24n
independently. Require the same success/limit class for all three runs.

For `CLOSED`, require identical **full** Network results with observer OFF/ON
and the entire independent observable projection, including events, state,
route and batch multisets. The receipt records a digest of the projection.

For `LIMIT_REACHED`, require the exact, single reason (`max_events` or
`max_batches`) to agree across frozen OFF, frozen ON and 24n. Only the status
and reason are recorded. The recorder may contain partial observations, but
they do **not** form a complete successful execution result, nor imply rollback
or durability.

Unexpected runtime errors, invalid case admissions and mismatches must propagate
as failures. Do not turn them into `LIMIT_REACHED` or discard discrepancies.

## Evidence and replay

Evidence envelope schema: `spk-corpus-failure-parity-evidence/v0`.
The payload includes the 24o corpus SHA-256, probe summary and a canonical
per-probe row. Verification rejects duplicate JSON keys, noncanonical encoding,
incorrect digest or replay divergence even after resealing. Replay executes the
entire matrix again; hash equality by itself does not confer authenticity.
Independent-process equality is verified by the gate.

## Test scope and limitations

The full `fwork` gate runs pure oracle tests, real frozen differential tests,
independent-process canonical evidence, previous 24o/24p regressions, complete
repository tests and frozen-source hygiene. Expected counts are not declared
PASS until executed on the authoritative checkout.

The gate does **not** prove semantic equivalence for arbitrary SPK programs,
learning, contention, arbitrary user-provided observers, combined-failure
precedence, persistent exactly-once authority or crash recovery. It also does
not create a new multineuron application host: it strengthens the reference
failure semantics already introduced in 24p.

## Roadmap treatment

24q primarily adds coverage to S4 (observer error noninterference) and S5
(independent failure differential). It does not close S3's full application
host integration. No roadmap percentage should be incremented before 24q
passes, and coverage estimates remain engineering judgements, not proofs.

## Certified fwork gate - 2026-10-16

Baseline: b6025fa.

- Independent probe-plan tests: 7 PASS.
- Frozen failure-parity tests: 13 PASS.
- Exact-budget successes: 216.
- max_events failures: 174.
- max_batches failures: 168.
- Total computational probes: 558.
- Previous 24o/24p regressions: 85 PASS.
- Full repository regression: 2832 PASS.
- Independent-process artifact replay: PASS.
- Frozen-source and patch hygiene: PASS.

Corpus SHA256:
cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5

Evidence SHA256:
1b4eea30bb380ea1c5d682d4b6d2c492806507349de3a3e25ad4a07ed6b63105

Acceptance excludes simultaneous exhaustion of both budgets,
arbitrary observer implementations, recovery and distributed authority.

Roadmap engineering estimates remain:
S1=100%, S2=100%, S3=85%, S4=80%, S5=90%.
Total=91%, equally weighted.
