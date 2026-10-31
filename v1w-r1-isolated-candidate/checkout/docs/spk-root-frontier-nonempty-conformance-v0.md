# SPK S3.7d/3b2b2k/16: nonempty root emission frontier conformance v0

## Purpose

The previously validated `owned_root_emission_frontier_v0.py` exercises the
positive frontier chiefly for **empty** root input prefixes. A root source
with a nonempty sealed input plan needs a real end-to-end positive proof before
its certificate is trusted as a premise of causal induction.

This checkpoint adds **no production logic**. It is an integration/conformance
gate and does not change Core v0, Network v0, Compiler v0 or the already
validated SPK simulator modules.

## Positive proof path

The fixture derives an output-free, root-only, finite-epoch execution by
restricting an existing architecture test context to one or two neuronal
batches on node B. It starts from the actual empty storage ledger:

1. Seal the finite external ingress plan at initialization.
2. Register `BATCH_CONSUME`, `PROGRAM_REFERENCE`, `STATE_LOAD`, `STATE_COMMIT`
   with serialized causal dependencies and real resource requests.
3. Use the existing owned internal read advance, which advances the physical
   `EVENT` controller and spends service quantum.
4. Consume external input occurrences; obtain Core preparation only from
   consumed events and owned P/S reads.
5. Complete real `STATE_COMMIT` through `commit_owned_internal_state_v0`.
6. Re-audit the resulting *same* immutable owned snapshot with
   `analyze_owned_root_emission_frontier_v0`.

The positive case with an external input at `EVENT_TIME=4` yields consumed
index `(0,)`, committed request `(80,)`, neuron version `1`, and a certified
source prefix through logical time 4. A two-batch variant reaches version 2,
and a two-occurrence batch checks spike multiplicity rather than set semantics.

No `ObservedExecutionV0` or Network runtime result supplies future emissions.
No receipts or tombstones are manually installed in the positive path.

## Negative controls

Pending input, resident-only input, consumed but uncommitted input, late
`SERVICE_TIME` admission, altered input seal, removed commit receipts,
removed consumption tombstones, and stale snapshots must not gain the same
certificate. The gate also checks snapshot immutability/determinism and that
a positive source prefix *never* implies permission for `BATCH_CONSUME`.

## What this proves and does not prove

**Proved under the frozen finite-input seal and single-owner snapshot
assumption:** For root nodes with no incoming edges, a nonempty external-input
prefix can be actually consumed, processed by Core, committed and certified.
This closes a previously untested *positive integration path*.

**Not proved:** frontier induction for non-root nodes, exhaustiveness of
in-flight routed events, dynamic destination batch closure, open/live ingress,
autonomous end-to-end network execution, general deadlock detection, or
independent tamper-evident storage. The fixture deliberately uses a Core
program that produces no candidate output, to isolate root prefix validity.

## Verification

```bash
bash search/root_frontier_nonempty_gate_v0.sh
bash search/root_frontier_nonempty_gate_v0.sh --full
```

Expected: 17 new tests; existing root (34), external prefix (44), and
output-free state commit (33) tests unchanged. Full suite grows from
2,005 to 2,022 tests if no unrelated changes exist.

## Next independent gate

Use the newly exercised nonempty root certificate as an input to an
**authenticated one-hop source-exhaustion check**. That check must still
account for already produced routes that remain in OUTPUT/EVENT/in transit;
source exhaustion alone never closes a destination batch.
