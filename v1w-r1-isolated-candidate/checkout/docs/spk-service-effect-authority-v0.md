# SPK S3.7d/3b2b2e: Storage Service Effect Authority v0

Status: **DRAFT / integration candidate**. Requires full SPK repository validation.

## Purpose

Connect a `ServiceQuantumStateV0` at boundary `s` to the actual bounded storage
transitions produced at `s` by `advance_bounded_backpressure_v0`. An effect is
confirmed only if (1) the matching service work has finished no later than `s`,
(2) a correctly typed, provenance-bound storage operation succeeds, and (3)
when a batch consumes multiple events, **all** its routed and external
occurrences are consumed together at the same boundary.

This stage is not a complete owner-scheduler. It does not infer `SERVICE_TIME`
from `EVENT_TIME`, and it never modifies either frozen semantic layer.

## Public API

`authenticate_service_storage_effects_v0(architecture, manifest, admission, requests, service_state, driver_state, frame)`

Returns `ServiceEffectAuthorityResultV0` with immutable fields:

- `driver_state`: the state returned by a **real invocation** of the bounded
  driver, not an ad hoc fabricated acknowledgment;
- `driver_step`: the corresponding full boundary result;
- `confirmed_request_ids`: canonical, distinct request identities for proven
  `EMISSION_RECORD`, `ROUTE_ENQUEUE`, and nonempty `BATCH_CONSUME` effects;
- `effects`: explicit boundary witnesses with **separate** routed request IDs and external input indices (different identity namespaces);
- `granted_route_request_ids`: actual event reservations (not delivery
  confirmations, and not standalone causal permission to start service).

## Authority conditions

- The quantum state's next boundary must equal the driver's frame boundary.
- A storage-effect request must be in the quantum state's
  `awaiting_confirmation` with a `finish_boundary <= frame.service_boundary`.
  `partial` service or mere causal readiness is not enough.
- Request kind and destination/source PE must match the routing and emission
  bindings. External input identities must match the consuming request.
- An emission is confirmed only if admitted atomically by the bounded driver;
  a blocked/retried emission remains unconfirmed. For zero fanout, the driver's
  explicit admission record is the witness.
- Route delivery is confirmed only after a `COMMIT` operation by the bounded
  reservation ledger, never by an earlier `RESERVE`/`WAIT` decision.
- A `BATCH_CONSUME` is confirmed only if **all** bound routed and external
  occurrences assigned to that request are consumed together. This version
  deliberately rejects partial batch consumption.
- The function is pure with respect to caller-owned snapshots. If its checks
  or a driver transition fail, it does not return a modified state.

## Explicit exclusions

- The `ServiceQuantumStateV0` supplied to the function is assumed to have
  been produced and retained by a **trusted single owner**. This stage does
  not independently prove every service slice in its history. A forged
  snapshot cannot be distinguished from a trusted caller's legitimate one.
- `frame.new_ready_route_ids` and the *initial memory-grant* phase are not
  independently authorized by this gate. The future scheduler must derive
  them from dependency readiness and actual reservation state.
- Internal/non-storage service kinds are NOT auto-confirmed by this function.
  They require a separate rule and authority boundary.
- No deadlock conclusion, fairness guarantee, live PE concurrency protocol,
  or active rescheduling follows from a successful storage effect witness.
- No hidden ingress buffer is implied; non-backpressurable arrivals retain
  their explicit finite-capacity, fail-closed semantics.

## Acceptance checks

Real driver transitions for offers, commits and consumes; blocked emissions
are not confirmed; route reservation is not delivery; mixed external and routed
batch completeness; partial/premature/unknown effects are rejected;
`SERVICE_TIME` and profile/epoch consistency; immutable result, no input-state
mutation on error; deterministic repeated evaluation.

Only add files in `docs/`, `spk_simulator/` and `tests/`. Do not change frozen
Core, Network, Compiler, PE Architecture or previously validated simulator
modules in this checkpoint.
