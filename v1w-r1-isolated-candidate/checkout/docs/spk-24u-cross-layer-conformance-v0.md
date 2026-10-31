# SPK 24u: Cross-Layer Conformance Audit v0

**Status: INTEGRATION PASS (2026-10-16, finite reference scope).**

Baseline: `cd7071d`, accepted SPK 24t. The frozen `spk_core`, `spk_network`,
`spk_compiler`, `spk_architecture`, `spk_simulator`, and the existing 24m–24t
modules MUST NOT be changed by this package.

## Why this audit is necessary

Earlier checkpoints establish **distinct bounded capabilities**, not a single
universal end-to-end theorem:

| Phase / claim | Existing evidence | Remaining limitation |
| --- | --- | --- |
| S3: source→Compiler→manifest→Network | 24m accepted 2-node/3-edge compiled scenario; 24p/24t use that reference manifest | The 216-case, 3-node 24o corpus was not compiled and passed through 24t |
| S4: observer noninterference | 24o on 216 Network v0 cases; 24q–24s on bounded failure corpus | Certified recorder is passive; arbitrary observers and effects before exceptions remain out of scope |
| S5: independent differential | 24n independent interpreter; 24o 216 cases; 24q 558 probes; 24s 504 causal conditions | Finite primitive IR only; no general liveness, concurrency, durable authority, or arbitrary exception taxonomy |

New checkpoints should distinguish **covered through all layers** from
**covered separately in different test environments**. This is not remedied
merely by adding more probes of the same runtime.

## 24u integration experiment

A single new adapter takes the **exact fixed 24o corpus** (SHA-256
`cda4f44b66f208ca9f14b3c77067b4f5aa208c1a02022e1cdc36648769f19ee5`),
containing 6 instruction profiles × 6 topologies × 6 input patterns.

For **every one of the 216 three-neuron source programs**, it must:

1. Convert to the runtime-normalized Network IR using the existing 24o
   admission boundary. The original, unnormalized primitive program remains
   the independent semantic reference, including `guard_overwrite`.
2. Round-trip the source Network IR using the frozen serialization API.
3. Compile using the frozen Compiler and a *three-PE reference profile*, one
   node per PE, with resources matching 24m's proven per-PE fixture.
4. Round-trip and source-pin the Compiler manifest, preserving event
   multiplicities. Neither compile-time acceptance nor rejection may be
   silently skipped or recorded as success.
5. Execute the compiled manifest through the **existing 24t host** and compare
   the complete, observed, terminal and state projection with a fresh
   independent 24n interpretation of the **original** primitive source.
6. Fail on all unexpected differences. The Compiler is allowed to perform
   semantics-preserving rewrites: structural equality of source graph and
   compiled graph is not asserted as an unproved architectural rule.

**Additional integrated boundary checks:** on all 36 `duplicate` input cases
(6 profiles × 6 graphs), run the 102 pre-existing 24q exact/isolated-budget
probes through the compiled host. On the 30 cases eligible for a dual limit,
run all 90 24s causal controls via the compiled host. Both conditions require
`AMBIGUOUS_TIE_PASS`, while isolated failures require `EXACT_PASS`.

The resulting declared test plan has **216 full executions + 102 boundary runs
+ 90 causal runs = 408 versioned host executions**. These counts describe the
workload to be certified on `fwork`; they are NOT results of that certification.

## Admission is evidence, not a loophole

All 216 cases are mandatory. If a case is rejected by source IR, resource
admission, compiler, manifest loader, bounded independent interpreter or
reference host, the gate **fails with that case identified**. A follow-up must
explain whether it is a valid intended rejection and revise the explicit
acceptance domain, or correct the new adapter; the gate must not count rejected
cases as integrated passes.

Failure receipts have no successful result; a dual-budget diagnostic may be
either independently eligible reason, preserving the actual frozen choice.
No new diagnostic precedence is claimed.

## Evidence and verification

Receipt schema `spk-cross-layer-conformance-evidence/v0`. It includes a
source-plan SHA-256, every compiled manifest digest, every complete-result
digest, exact counts, and per-case receipt/status checks. Canonical, strict
JSON is re-executed from the fixed corpus during verification. Re-sealing a
mutated payload does not confer authority.

SHA-256 is a consistency check, NOT a signature or an external trust root.
The recorder is passive. A failed or rejected execution does not promise
atomic rollback, persistent exactly-once, distributed transactions, learning,
or an application-level recovery procedure.

## Release gate

1. Independently generated and source-pinned 216-case plan (no frozen imports).
2. Actual frozen Compiler→manifest→24t host→observer→independent source proof
   across all 216 cases, including 192 additional budget/cause runs.
3. Independent-process deterministic report and full replay, with adversarial
   re-sealed forgery detection.
4. Original 24m / 24o / 24p / 24t regression gates.
5. Full repository pytest regression.
6. Strict frozen-source, staging and whitespace boundary; three known
   unrelated untracked files must not be staged.

## Roadmap before certification

S1=100%, S2=100%, S3=85%, S4=80%, S5=90%, total **91%** equally weighted.
No numerical promotion is authorized before the authoritative gate. Even after
passing, broader properties remain uncovered: arbitrary observers, non-budget
failures, hardware/PE temporal contention, learning, and persistent authority.
Percentages are engineering estimates, not mathematical probabilities.

## Certified fwork gate - 2026-10-16

Baseline: cd7071d.

- Independent conformance plan tests: 8 PASS.
- Integrated cross-layer tests: 11 PASS.
- Three-node compiled manifests admitted: 216/216.
- Versioned host executions: 408.
- Exact adjudications: 378.
- Ambiguous dual-budget adjudications: 30.
- Prior bounded regressions: 112 PASS.
- Full repository regression: 2921 PASS.
- Independent-process canonical replay: PASS.
- Frozen-source and patch hygiene: PASS.

Plan SHA256:
25e3fffb5b33dc38f525cded4c43c8aa82460eb1142677350dc1b30ad809b579

Evidence SHA256:
e2ce01b440d019c0b33316c67858102310d889c92d71faa04a5e873540119099

Acceptance is limited to the declared finite reference corpus.

Arbitrary observers, non-budget exception families, PE contention,
learning, durable authority, general liveness, and universal
semantic equivalence remain outside this certification.

Updated engineering roadmap:
S1=100%, S2=100%, S3=90%, S4=80%, S5=90%.
Total=92%, equally weighted; previous 91%, delta +1 pp.

These percentages represent engineering acceptance estimates,
not mathematical probabilities of correctness.
