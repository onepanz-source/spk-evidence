# SPK S3.7d/3b2b2g — OUTPUT Start Reservation v0

Status: EXPERIMENTAL / admission component; NOT a complete scheduler.

## The missing grant

`ServiceQuantumV0` refuses to start an `EMISSION_RECORD` unless it receives
an authenticated memory grant. The authenticated service bridge currently
supplies only reservations for `ROUTE_ENQUEUE`, not an `OUTPUT` start grant.
Checking instantaneous free OUTPUT slots would be unsound: an emission may
require multiple SERVICE_TIME quanta, and another emission could consume the
same capacity before the first one has published its fan-out.

This component introduces **bounded OUTPUT capacity claims** held from
admission to atomic publication. Claims do not contain spikes. A claim is
neither evidence of completed service nor an emission effect.

## Inputs and invariants

- `ArchitectureProfileV0`: source PE output capacities, homogeneous in v0.
- `AtomicEmissionAdmissionV0`: group identity and full atomic fan-out size.
- `RoutedStorageStateV0`: actual resident routed occurrences in OUTPUT.
- `OutputStartLedgerV0`: active emission reservations plus completed IDs.
- All inputs must use the same profile and epoch.
- Each emission has at most one outstanding reservation; no replays after
  completion. Parallel routes remain distinct occurrences.
- For every PE:

  `pending_output + reserved_output_start_slots <= output_slots`

- Reservation grants for independent emissions are chosen in ascending
  emission request-ID order. Input tuple ordering cannot change the result.
- There is no partial admission of an individual atomic emission bundle.
- Cancellation is allowed only before any occurrence is published.
- Publication settlement requires all newly created route identities to
  appear in OUTPUT with their expected source PE. New tombstones or events
  already delivered to EVENT do not constitute evidence of OUTPUT publication.
- A settlement checks before/after immutable storage states and releases all
  settled reservations **atomically**, permitting multiple fan-outs at one
  boundary. A failed check leaves all caller-owned snapshots unchanged.
- The ledger cannot create or erase an event; the storage controller remains
  the physical occupancy owner.

## Public API

- `output_start_usage_v0(architecture, admission, storage, ledger)`
- `reserve_output_starts_v0(architecture, admission, storage, ledger, ready_emission_ids)`
- `cancel_output_start_v0(architecture, admission, storage, ledger, emission_request_id)`
- `confirm_output_publications_v0(architecture, admission, storage_before,
  storage_after, ledger, emission_request_ids)`

`reserve_output_starts_v0` returns `OutputStartDecisionV0` with granted and
blocked emission identities. Blocked IDs are *not* retained as spikes; a
future owner scheduler must explicitly retain and retry the causal work
request. The returned ledger is immutable and can be persisted as part of
that scheduler's state.

## Explicit trust boundary

This module's publication-confirmation method checks before/after storage
consistency but **does not prove the caller supplied a genuine boundary
transition**. The future single-owner scheduler must invoke the bounded
controller itself, validate `ServiceEffectAuthorityV0` receipts, and only then
settle the associated OUTPUT claims. The current authenticated bridge is not
modified. No arbitrary memory-start grants may yet be passed to it as proof.

This is serialized, single-owner accounting. It is not an atomic CPU lock
or a hardware implementation of concurrent reservation. Completion of a
quantum still does not imply `EMISSION_RECORD` publication. No guarantee of
progress, deadlock detection, or network functional equivalence follows from
this component in isolation. EVENT_TIME never changes and is never derived
from SERVICE_TIME.

Historical `completed_emission_ids`, like routed consumption tombstones,
are host-side reconciliation metadata and require explicit retention or
retirement rules before a bounded runtime can be claimed.

## Future integration / acceptance

1. The owner scheduler starts `EMISSION_RECORD` only after a genuinely
   reserved OUTPUT claim, not after an unprotected instantaneous free-space
   check.
2. While the request consumes partial service, its claim remains active.
3. On a witnessed complete `OFFER` set, settle all affected claims atomically.
4. A failed offer never confirms the service request and does not free a claim.
5. Route reservations, external ingress, service bandwidth and dependency DAG
   remain under the existing separate contracts; combine them in a single
   owner cycle before claiming an active backpressure scheduler.
