# SPK Native Learning v1v: provenance exception hotfix

The original v1v gate passed its frozen SHA and file-manifest checks and
reached 47/48 tests. The last test deliberately patches the ORIGINAL
`pe_execution_v1b._compute_local`, which is correctly rejected by the
frozen `pin_sources` guard, but emits `AssertionError:
FROZEN_PE_COMPUTATION_IDENTITY_MISMATCH`. v1v promised a typed
`SensorReject: ORIGINAL_PE_PROVENANCE_DENIED` instead.

This hotfix corrects **only that exact exception boundary**. Other frozen
SHA failures, absent modules, memory-identity mismatches, or unexpected
errors still propagate untouched and fail the gate. Original frozen SPK,
BV-v0e, v1u, and v1t files are not modified.

Use the provided single gate wrapper; it verifies the exact original v1v
source and manifest before replacing those two **mutable research files**
with pinned corrected copies, runs 9 adversarial tests, and then invokes
the **existing complete 8-stage v1v release gate**.

The complete original gate remains mandatory. No skip, xfail, or weaker
assertion has been introduced. Install is idempotent and refuses drift.
