# SPK S3.7d/3b2b2k/22 · Owned Root Batch Consumption v0

Status: **candidate; validate on the real fwork SPK suite before commit**.

## Scope

This is the first **physical consumption of a sealed, complete root input batch** in the joint EVENT ledger. Unlike `Owned Sealed Root Batch v0`, it spends `BATCH_CONSUME` service through the existing `Service Quantum`, and at a **subsequent** `SERVICE_TIME` boundary moves *all* associated external input identities from `resident` to persistent `consumed` tombstones, simultaneously confirming the service request. The finite EVENT occupancy per PE is recalculated from current residents, dynamic routed residents, and route reservations. The input plan remains immutable for the epoch. No Network v0 functional trace is consulted.

### One-batch example

At service boundary 4, external input #0 with `EVENT_TIME=3` is due; it enters EVENT. If the complete sealed root batch is ready, request `BATCH_CONSUME` consumes PE service units and may finish at boundary 5. **No physical consumption occurs yet**. At boundary 5, the authenticated finished request is confirmed, input #0 is moved to the consumed ledger, and its EVENT slot is released atomically. `EVENT_TIME` remains 3 throughout.

## Modified pre-existing contracts

`OwnedSharedEventCycleStateV0` gains a trailing, optional `external_consumed_input_indices=()` field. Old constructors and the existing shared EVENT cycle retain their behavior. State validation checks canonical identities, disjoint residents/tombstones, exact partition of all external inputs due *before* the current service boundary, batch-complete tombstones, positive `BATCH_CONSUME` service confirmation, root-only ownership, and the order of logical batches. Its capacity audit counts only resident events, not tombstones. `advance_owned_shared_event_cycle_v0` retains tombstones while performing its legacy route/external-admission cycle.

`analyze_owned_sealed_root_batches_v0` now classifies physically consumed historical batches as `ROOT_INPUT_SET_CONSUMED` and considers later batches ready only when *all* earlier batches for the same neuron have been consumed. Its `supports_consume_confirmation=False` remains unchanged: merely auditing readiness is not a consumption authority.

## Ownership and restrictions

`advance_owned_root_batch_consumption_v0()` is an **exclusive service-boundary owner**, not a general scheduler. It may admit mandatory external arrivals before serving a complete root batch, but spends PE service units **only for root `BATCH_CONSUME` requests** and only when its ingress-release/causal conditions are met. Other P/S operations, STATE_COMMIT, emissions and dynamic route service are not executed by this function; if a quantum would schedule them, the call fails closed. The future scheduler must select the correct owner and ensure it never advances two owners at the same logical `SERVICE_TIME` boundary.

For deliberately conservative service accounting, a boundary spent confirming physical batch consumption does not spend further PE service. The input resident set and service state are updated in a **single immutable successor**; errors return no successor. Mandatory new external arrivals due at that boundary are also accounted for before returning the successor, or the transaction fails with the established overflow exception.

The registry must contain matching static requests and releases; this limited function does not generate requests for later batches and does not infer an open ingress source is closed. An initial caller-authored snapshot is **not independently authenticated** merely by constructing it. It cannot validate the content of a preceding CORE computation; it supplies a physical consumption receipt for a later owner.

## Tests and acceptance

- Positive ingress -> one or many service slices -> physical consumption -> tombstone + freed slot.
- Exact preservation of multiplicity for equal-channel arrivals.
- Later arrivals block service until complete.
- No early confirmation, no duplicate consumption and no forged time travel.
- Canonical identities, non-overlap, capacity, and exclusive-service restrictions.
- Regression: legacy shared EVENT cycle and sealed root batch tests must stay green.

This milestone does **not** claim a complete dynamic-network `BATCH_CONSUME`, integrated Core execution, global scheduler or deadlock detector. These remain blockers for S3.
