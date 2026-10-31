# SPK S3.7d/3b2b2j: Autonomous Storage Execution Loop v0

Status: **experimental simulator component** (not a frozen contract).

## Purpose

`run_autonomous_storage_v0` advances a single persistent owned state through
successive `SERVICE_TIME` boundaries. Unlike the older multi-boundary driver,
it does **not** receive caller-authored frames, proposed completions, or memory
grants. Instead, it calls `advance_autoframed_owned_tick_v0`, which derives
storage-effect frames from the current bounded storage state, OUTPUT start
reservations, routing binding and causally finished service work.

This is a real autonomous **storage subset** execution loop, not yet a
complete SPK Core/Network runtime. It supports exactly:

- `EMISSION_RECORD`
- `ROUTE_ENQUEUE`
- `BATCH_CONSUME`

It rejects any other request kind before executing its first tick. In
particular, no instruction/program/state/observation request is silently
accepted or automatically declared complete. Such requests require their
own independently verified effect authority.

## Inputs and ownership

The caller supplies an already-constructed, previously validated immutable
`OwnedServiceTickStateV0`, architecture, routed binding, emission admission,
service requests, dependency DAG and optional external ingress binding.
That initial snapshot is a trust boundary. This runner does not independently
rebuild or attest the complete initial provenance history.

The loop itself owns every subsequent snapshot and frame. It does not call
the original functional Network engine or modify the frozen Core, Network,
or Compiler v0 interfaces. Outputs are immutable dataclass values.

## Time semantics

Each iteration handles one consecutive `SERVICE_TIME` boundary. The loop
never derives service time from `EVENT_TIME`, changes a neuronal timestamp,
or silently skips a future external arrival. `max_service_ticks` is a
strictly positive limit on additional serviced boundaries for this invocation.
The runner can resume from a returned snapshot without replaying completed
work; the new limit applies to the resumed invocation.

## Results

- `COMPLETED`: every request has an authenticated service completion,
  every routed occurrence and bound external occurrence is consumed, and
  no live OUTPUT/EVENT reservations or unconsumed event slots remain.
- `TICK_LIMIT`: some requests remain incomplete after the permitted number
  of ticks. This is **not** a deadlock classification. The result retains
  the immutable state, accepted frames, unfinished identities and future
  external arrival boundaries.

The host-side execution history is observation data bounded by
`max_service_ticks`, **not** an additional SPK physical event buffer.

A trace that declares everything complete while retaining live resources,
or omits a routed/external occurrence, is rejected instead of reported as
success. A rejected transition leaves the caller's immutable input unchanged.

## Scope / remaining work

The runner does not automatically complete non-storage operations. There is
no general instruction-effect authority, no full Network v0 end-to-end
comparison, and no rigorous deadlock certificate. A repeated lack of progress
or reaching `max_service_ticks` does **not** prove that no other valid schedule
could complete. Explicit wait-for analysis and future ingress semantics remain
necessary for deadlock and progress guarantees.

## Validation

Run the 33 new tests and the complete regression suite on the real SPK
repository. The local integration bench uses the actual recent SPK modules,
but some older architecture definitions remain substituted: its passing tests
are **not** a substitute for checking on fwork.
