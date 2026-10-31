# SPK 24p: Multineuron Reference Host, Observer and Failure Differential v0

**Status: INTEGRATION PASS (2026-10-16, bounded reference scope).**

Baseline Git: `5630388` (24o accepted). No source code from the frozen Core,
Network, Compiler, Architecture, 24j single-root host or 24n oracle is changed.

## 1. Objective and boundary

This is a **separate, single-process, single-shot multineuron reference host**.
It accepts a compiled SPK manifest and an explicit operator-pinned SHA-256 of
that manifest. It is *not* an extension to 24j's single-root, output-free
custody contract, and it does not claim process-global ownership, exactly-once
processing or crash durability. There is no second scheduler or clock.

The caller must provide a compiled manifest. The host verifies the literal
manifest's digest before using the frozen manifest decoder. The demo CLI uses
the 24m declarative scenario and the frozen Compiler to create a real network
of two neurons and three positive-delay routes, including parallel edges.
A digest supplied by the same untrusted caller is only a consistency check,
not proof of the publisher's identity. The trusted approval/pin must be
established outside the host.

## 2. Full successful execution

The host executes the compiled manifest twice with identical budgets:
(1) the frozen Network without an observer; (2) the same frozen Network with
an internal passive recorder using `on_batch` / `on_route`. Full Network
results must be equal. The 24n independent interpreter predicts the entire
canonical observable result and the batch/route observation multisets; a
mismatch causes a hard failure, never a success receipt.

The accepted `CLOSED` receipt records the manifest, digest, budgets, projected
network result, observation counts and independent-oracle status. It is
canonical JSON with a payload SHA-256, and the verifier recomputes execution,
not merely the digest. It does not contain a public mutable runtime handle.

## 3. Failed execution, authority and observation

When the frozen Network raises **`NetworkExecutionLimitV0`** for exactly one of
`max_events` or `max_batches`, both observed and unobserved runs must fail
with the **same reason**. The independent 24n interpreter must also raise
`OracleLimitV0` for that same reason. The emitted receipt has
`status=LIMIT_REACHED`, `reason` set to the exact limiter and `result`,
`comparison` and `observations` all `null`. It cannot be mistaken for CLOSED.

The limit may be reached **after partial computational work**. This contract
makes no claim about rollback of already-executed operations, nor does it
conclude that arbitrary observers are noninterfering. The only admitted
observer is the passive recorder internal to the host. Unexpected runtime or
observer exceptions propagate, leave the host in `FAILED` and issue **no**
receipt. If a budget-limited run is non-deterministic, changes its error class,
or produces an unclassified reason, the host fails closed.

Single-host calls are serialized by `RLock`. Once an execution is attempted
an instance transitions from `NEW` to `CLOSED`, `LIMIT_REACHED`, or `FAILED`.
It cannot be reset or reused; this is an intra-instance guarantee, not
cross-process fencing or persistent deduplication.

## 4. Versioned evidence and limitations

Schema: `spk-multineuron-reference-host-evidence/v0`.

The verification function checks canonical encoding, unique JSON keys,
nonfinite-value rejection, schema, payload shape and digest, then reruns
both frozen and independent execution to compare full output or exact limit
classification. Recomputing the outer digest after tampering must not permit
altered results or error reasons to pass. SHA-256 does not authenticate an
arbitrary external producer or assure immutable local source code.

**Declared test domain:** 24m reference network with two neurons and three
parallel/positive-delay routes; exact success at four events and three batches;
negative limits at three events and two batches. Broader networks already
receive differential verification from 24o, but this host is not certified for
all networks merely because 24o has 216 examples.

## 5. Test and gate

Run `bash search/spk_24p_final_gate_v0.sh` on the authoritative `fwork` repo.
The six stages cover reference-host tests, 24m/24n/24o regression, independent
process success receipts, exact limit receipts, full regression and frozen
source/working-tree hygiene.

Acceptance requirements:

- Compiler→manifest→multineuron host uses actual frozen public APIs.
- Successful full-result observer equivalence and independent-oracle equality.
- Frozen/observer/oracle agree on `max_events` and `max_batches` failures.
- No successful result or spurious rollback guarantee on a limit.
- Mutation, digest, re-sealing and double-run negative tests fail closed.
- Frozen Core, Network, Compiler and existing host remain unchanged.

The local environment may run syntax and synthetic-contract checks, but they
do not replace authoritative `fwork` regression. No commit/tag before PASS.

## 6. Roadmap rubric

Previously accepted engineering estimates: S1=100%, S2=100%, S3=80%,
S4=75%, S5=85%, total **88%** (equally weighted).

24p targets the previously open S3 host consumer by admitting a **separate
multineuron reference host**, and strengthens S4/S5 through error-outcome
and observer parity. This does not itself close the broader production host,
authenticated ingress, general observer noninterference, other error classes,
resource contention, learning or unbounded semantic equivalence.

The estimated percentages remain unchanged until the real 24p gate passes
and its evidence is scored against an explicit acceptance rubric. Test counts
are not correctness percentages.

## 7. Certified integration gate

Baseline: 5630388.

- Reference-host tests: 35 PASS.
- Compiler/Network/observer regressions: 139 PASS.
- Independent-process CLOSED replay: PASS.
- max_events exact failure reason: PASS.
- max_batches exact failure reason: PASS.
- Full regression: 2812 PASS.
- Frozen-source boundary: PASS.

Acceptance scope: finite multineuron reference execution.

No distributed ownership, persistent exactly-once guarantee,
general observer noninterference or atomic rollback is claimed.

Engineering roadmap estimates:
S1=100%, S2=100%, S3=85%, S4=80%, S5=90%.
Total=91%, equally weighted.

These estimates are not mathematical correctness measures.
