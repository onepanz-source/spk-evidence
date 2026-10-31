# SPK S3.7d/3b2b2k/24b: Owned Root Single Clock v0

## Purpose

The **first restricted common `SERVICE_TIME` owner** for sealed finite external
root batches and the neuron's P/S accesses. This is a deliberately incremental
integration, NOT the general autonomous SPK scheduler and NOT a `STATE_COMMIT`
owner.

`initialize_owned_root_single_clock_v0(shared)` admits only a fresh owner:
no preconfirmed P/S/EVENT service, no dynamic registrations, no resident or
consumed historical events, no in-flight work and no routed output. It derives
a versioned Core image from the frozen `NetworkV0`; **no fake P/S confirmations**.

`advance_owned_root_single_clock_v0(state)` advances exactly one `SERVICE_TIME`
by using the existing `advance_service_quantum_v0` once with `owned_service_request_ids`
computed **inside the owner**. It:

1. Revalidates the immutable state, service history, P/S receipts and root
   EVENT consumption witnesses.
2. For P/S work that finished at a previous boundary, reads the active
   `NetworkV0` program and the current neuron image and records a real P/S
   receipt in the same step as the service confirmation.
3. For a root `BATCH_CONSUME` whose work finished previously and whose full
   sealed multiplicity remains physically resident, consumes the exact
   external input indices and records a `WitnessedCoreInputBatchV0`.
4. Admits **all** external arrivals due at the current boundary, failing
   atomically on `EVENT` capacity overflow. No invisible external queue.
5. Prepares frozen Core transitions only from **both** actual P/S reads and
   exact physically consumed input witnesses. Candidate outputs are not
   published, and `STATE_COMMIT` is not scheduled.
6. Selects P/S and eligible root `BATCH_CONSUME` requests from the newly
   admitted ledger, retaining partial service identity across boundaries,
   and invokes one `ServiceQuantumV0` for the whole PE budget.

This preserves distinct `EVENT_TIME` and `SERVICE_TIME` dimensions.

## Invariants

- No service-quantum call from a second owner in the same step.
- No P/S preconfirmation; reads must cover **exactly** confirmed P/S IDs.
- A root `BATCH_CONSUME` must finish service before a later-boundary physical
  consumption; its witness must match the exact historical tombstones.
- No P/S/STATE_COMMIT work is fabricated. Neither an uncommitted Core result
  nor a candidate emission updates OUTPUT or the neuron state version.
- Multi-occurrence and repeated-channel batches preserve multiplicity.
- All state is immutable: failed capacity/causal checks produce no successor.
- The request DAG must already satisfy the serialized Core dependency graph;
  static requests must describe root batches exclusively.

## Limits and trust

The sealed external epoch, PE mapping and initially fresh snapshot are trusted
installation roots. A caller who fabricates the entire initial registry cannot
be authenticated by this module. A physically distinct mutable P-memory store
is **not** modeled: P reads refer to the active frozen `NetworkV0` image.

**Not covered:** `STATE_COMMIT`, STATE/OUTPUT atomic publication, nonroot
batches, routed-event consumption, dynamic service, general multiple-lane
arbitration, bounded tombstone retention or autonomous deadlock classification.
The owner intentionally refuses `STATE_COMMIT` already active in its history.

The next step is a no-output `STATE_COMMIT` integration under this same clock,
followed by atomic OUTPUT and root-to-nonroot causal propagation. Do not use
this component to declare a complete neuron execution cycle.

## Tests

On fwork:

```bash
python -m pytest -q tests/test_owned_root_single_clock_v0.py
python -m pytest -q tests/test_causal_service_quantum_v0.py tests/test_owned_service_admission_v0.py tests/test_owned_root_single_clock_v0.py
python -m pytest -q
```

35 dedicated tests and 88 combined tests passed in a reconstructed local
bench, some underlying models of which are substitutes. The real fwork
repository is the acceptance authority. Prior validated full suite: 2,309.
Expected full suite after adding these tests: **2,344**, subject to real
repository results.
