# SPK S3.7d/3b2b2k/24a — Single-clock Service Admission

**Status: candidate, real-fwork regression gate required.**

## Finding

The current root batch fixtures pre-confirm P/S requests as a **test convenience**. This is not a real P/S read authority. Meanwhile, the finite-bandwidth `Service Quantum` schedules all causally READY work; per-lane owners refuse work belonging to other lanes. Calling the root and P/S owners sequentially double-spends `SERVICE_TIME`.

## Minimal change to the existing service engine

Extend the existing `advance_service_quantum_v0(..., *, owned_service_request_ids: tuple[int, ...] | None = None)` with an explicit **per-boundary service admission** argument:

- `None` preserves *exactly* the legacy automatic ready-request selection (all old callers still work).
- An explicit canonical tuple permits only those requests to spend PE service units in this boundary.
- `()` advances one clock boundary with no new work; previous awaiting-confirmation effects can still be confirmed, but **not automatically**.
- Every ongoing partial request must remain admitted. Silently pausing/handover to an unrelated authority is prohibited.
- Memory grants for excluded requests, unknown/duplicate/unsorted identities, and invalid types fail closed.
- Dependencies, external release times, finite PE bandwidth, and pending-confirmation semantics are unchanged.
- The read-only `frontier` still reports the complete *causally ready* set. Actual service `slices` reflect the **allowed subset**. These are different concepts.

**Warning**: this argument is a caller-supplied selection policy; it is not an authenticated ownership certificate. Do not expose it to independent concurrent owners. A future root execution owner must derive it deterministically from its own immutable state.

## What this is not

This does **not** yet perform a unified root execution, P/S physical reads, neuron STATE_COMMIT, output publication, or deadlock detection. In particular, do not start pre-confirming PROGRAM_REFERENCE/STATE_LOAD. This is the necessary scheduling primitive for the following integration, not a claim that it exists already.

## Integration acceptance for /24b

One owner must: (1) initialize P/S as *unconfirmed*; (2) admit sealed due external events and finite PE work once per SERVICE_TIME; (3) read P/S only after service completion; (4) physically consume root EVENT after completion; (5) execute frozen Core using exactly the consumed channels; (6) commit no-output STATE after STATE_COMMIT service completion; (7) preserve historic witnesses/snapshot versions; (8) compare to Network v0 only after execution; (9) reject all unowned/emitting operations; (10) return TICK_LIMIT without calling it deadlock.

## Regression gate

`python -m pytest -q tests/test_owned_service_admission_v0.py`

`python -m pytest -q tests/test_causal_service_quantum_v0.py tests/test_owned_service_admission_v0.py`

`python -m pytest -q`

Unchanged frozen components: Core v0, Network v0, Compiler v0.
