# SPK S3.7d/3b2b2k/10 · Owned Computed Emission Allocation v0

Status: **candidate** until full `fwork` regression.

## Purpose

The previous `Computed Topology Routing v0` could compute a fan-out without a replay trace, but accepted the first event identity as a caller-controlled argument. This component owns and persists a *global epoch-scoped request identity cursor* across successive Core-produced emission candidates.

Entry points:

- `initialize_computed_emission_allocation_v0(architecture, network, placement, image, *, existing_request_ids=(), first_dynamic_request_id=None)`
- `allocate_computed_emission_v0(architecture, image, prepared, ledger)`

An accepted allocation consumes one `EMISSION_RECORD` request ID plus one ID for each `ROUTE_ENQUEUE`. In existing SPK routing, each routed occurrence must have `occurrence.event_id == route_request_id`. Both are assigned from the same owner-controlled monotonically advancing cursor. Terminal-only emission consumes one emission request ID and no route/event IDs.

The ledger retains allocation history to reject duplicate emission allocation for the same neuronal node and state version, reject regression to older versions, and validate cursor/identity continuity after snapshot and restoration. Existing request IDs must be canonical and accounted at initialization. Earlier owner state is immutable; a rejected attempt cannot advance the cursor. At initialization the placement must cover every network node exactly once. Parallel physical edges are assigned distinct IDs. Both EVENT_TIME and physical PE placement come from the computed plan, not from SERVICE_TIME.

## Important limitations

1. This module **does not construct `MemoryServiceRequestV0` objects**. Its IDs are reserved namespaces only. The scheduler must still create validated service requests with correct costs, determine the destination batch and its `BATCH_CONSUME` ownership, extend the causal graph, and admit memory transactions.
2. It **does not reserve physical OUTPUT slots, run service, issue actual buffer offers, confirm terminal outputs, or commit the Core state**. An allocated ID is not a published spike. Do not treat this immutable allocation as an effect receipt.
3. A source node cannot allocate a second emission from the *same or an older* Core state version, but can allocate after a genuine versioned commit. An owner cannot be reconstructed from scratch mid-epoch without the saved cursor/history; otherwise IDs could be reused.
4. As with every purely immutable snapshot, branching from an **old** snapshot can fork the identity namespace. Exactly one outer scheduler owner must persist and advance the *latest* ledger; this module cannot cryptographically authenticate that caller-side ownership.
5. Retained allocation history is currently **unbounded host-side metadata**, not physical event capacity. Explicit epoch retirement and bounded-history policy remain open.
6. This is not a general dynamic scheduler and is not yet integrated with `Atomic Neuronal Commit v0`, which still consumes a preconstructed routing/service manifest.

## Next acceptance

Create `MemoryServiceRequestV0` + causal dependencies from owned IDs; bind delivery to destination batch only when that batch is actually formed from admitted events; couple this same owner to OUTPUT reservation, authenticated publication, and atomic STATE commit. Then validate independent network outputs against frozen Network v0 without consulting its trace during execution.

## Test

```bash
python -m pytest -q tests/test_owned_computed_emission_allocation_v0.py
python -m pytest -q
```
