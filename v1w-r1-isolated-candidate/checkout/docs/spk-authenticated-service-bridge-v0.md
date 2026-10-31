# SPK S3.7d/3b2b2f - Authenticated Service Boundary Bridge v0

Status: experimental; not frozen. Does not change SPK Core, Network, Compiler v0.

## Objective

Compose the Service Effect Authority with Causal Service Quantum at exactly
one `SERVICE_TIME` boundary, so storage requests can be confirmed **only**
after actual bounded-storage transitions. Authoritative state comes from a
single immutable snapshot comprising the service state and backpressure driver.

Sequence at boundary `t`:

1. Check continuity of quantum and backpressure boundary snapshots.
2. Replay the requested boundary using Service Effect Authority. The authority
   checks service-finished evidence and derives only witnessed completions.
3. Validate newly submitted routing IDs against the causal DAG, even if memory
   reservation was denied. This prevents a denied early request remaining
   queued indefinitely and later bypassing causality.
4. Confirm witnessed storage effects and grant only actually reserved routing
   IDs in the Causal Service Quantum, which allocates finite PE service units.
5. Return a new immutable aggregate snapshot. A failure returns no snapshot.

## Invariants

- No caller-supplied `confirmed_request_ids` or memory grant lists.
- `ROUTE_ENQUEUE` reservation is not confirmation; `COMMIT` is required.
- `EMISSION_RECORD` blocked by OUTPUT remains unconfirmed.
- `BATCH_CONSUME` requires the full routed/external occurrence set.
- Completions unblock causal descendants in the same boundary only after
  boundary effects have been authenticated; no earlier `SERVICE_TIME` release.
- External ingress bindings must match the driver's actual ingress, and any
  nonempty external arrival set requires explicit release metadata.
- This adapter does not convert or alter `EVENT_TIME`.
- Rejected transitions leave input snapshots unchanged.

## Limitations

This is **not** an autonomous scheduler. Readiness frames are still
caller-supplied, as are the starting quantum state and dependency DAG.
The bridge does not prove that the quantum history was honestly constructed.
Non-storage requests (program/state reads or writes) may finish their service
units but still require an independent confirmation mechanism. Crucially, the
bridge does **not** authorize the initial service start of EMISSION_RECORD:
that needs a finite OUTPUT-capacity grant integrated with the atomic emission
planner. Consequently a work-conserving, live scheduler is still pending.

A finite time limit is not a deadlock finding; wait cycles and independent
progress remain open issues. No extra spike queue/storage is introduced.
