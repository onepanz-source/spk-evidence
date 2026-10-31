# SPK S3.7c/2: Ownership Consistency Audit v0

Status: DRAFT, test-driven integration checkpoint.

## Scope

This component **does not introduce a new event-buffer model**. The existing
`audit_event_buffers_v0(..., ingress=...)` already accounts for external and
routed events **together**, sharing each destination PE's finite `event_slots`.

S3.7c/1 separately verifies routed spike ownership in finite source
`output_slots` and destination `event_slots`, without external-event occupancy.

S3.7c/2 rebinds every routed occurrence to the completed frozen-Network
observation, runs **both** existing audits, and independently checks that
boundary-level admissions and consumptions agree on the same:

- PE identifiers;
- `SERVICE_TIME` completion boundaries;
- external occurrence count (including explicit ingress boundaries);
- routed `ROUTE_ENQUEUE` multiplicity;
- `BATCH_CONSUME` quantities;
- event-slot cumulative occupancy and final zero conservation;
- ownership OFFER/ADMIT/CONSUME coverage and completion matching.

No silent deduplication of parallel edges; no inferred relationship from
`EVENT_TIME` to `SERVICE_TIME`.

## API

`audit_ownership_consistency_v0(network, observed, placement, architecture,
plan, provenance, initial_events, requests, schedule, *, ingress=None)`

Returns `OwnershipConsistencyAuditV0` with:

- `routing_binding`: validated Network-provenance binding;
- `ownership_replay`: S3.7c/1 replay;
- `event_buffer_audit`: full S3.6b/3 event buffer occupancy;
- `pe_usage`: per-PE peak output, peak routed event, peak total event and final occupancy.

When `ingress` is absent, external events are preloaded at `SERVICE_TIME=0`.
When supplied, it must be a valid bound ingress plan; the full buffer audit
rebinds it to initial occurrences and checks readiness.

## Fail-closed behavior

Either downstream audit can reject the schedule, including by
`RoutedStorageBlockedV0` or `EventBufferOverflowV0`. S3.7c/2 rejects
inconsistent boundary identities, unknown routed transitions, duplicate
transitions, incomplete PE conservation, or conflicting peak occupancy.

## Important non-guarantees

- This is **post-hoc** checking; no producer suspension or rescheduling.
- There is no live atomic reservation protocol, transit buffer, or ingress
  handshake.
- Passing audit certifies this completed trace under its capacity and
  boundary accounting conventions, **not** feasibility of every possible run.
- Validation is not a proof of liveness or absence of deadlock.
- Core, Network, and Compiler v0 contracts are not modified.

## Tests

The S3.7c/2 suite checks observed Network routing, parallel-edge multiplicity,
combined event peaks, deterministic replay, legacy and explicit ingress,
same-PE routing, and fail-closed corruptions.
