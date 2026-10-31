# SPK S3.7d/3b2b1 — Atomic Emission Offer Plan v0

Status: **EXPERIMENTAL / admission-only**. Does not modify Core, Network, Compiler or S3.5.

## Motivation

A statically admissible `EMISSION_RECORD` can still be dynamically blocked if
its entire routed fan-out cannot fit in the source PE's currently free `OUTPUT`
slots. Replaying a completed emission into full storage is too late to make a
scheduling decision. This planner selects which *causally ready* emission
groups are eligible to complete/publish on this boundary.

## Preconditions

The caller has independently proved that `ready_emission_ids` refer to
`EMISSION_RECORD`s whose causal predecessors are complete. The planner does
**not** check DAG or service readiness; it checks finite ownership capacity.

`AtomicEmissionAdmissionV0` must be built using the validated plan, requests,
routing manifest and architecture. The module independently checks group
coverage and available OUTPUT occupancy. A previously published or partially
published group is rejected, not silently republished.

## Decision

Groups are examined in ascending emission request-ID order, consistently and
reproducibly. The candidate is admitted as a whole if its complete fan-out
fits current free OUTPUT capacity; otherwise it is `blocked` without reserving
any slot. Distinct routed occurrences remain distinct. Different PE capacities
are tracked independently (Architecture v0 itself requires homogeneous PEs).
Zero-fanout emission groups require no output slots.

The planner returns a **proposal** `routed_offers` to be passed into
`BackpressureBoundaryActionsV0` on the same boundary. It does not mutate
storage or complete `EMISSION_RECORD`. The future scheduler must recheck
capacity at commit time through the single-owner boundary controller.

## Exclusions / next steps

- No route EVENT slot arbitration; the existing arbiter handles that.
- No automatic retry or suspended SERVICE_TIME scheduler yet.
- No external-arrival simulation; the boundary controller remains the authority.
- No proof of fairness, eventual progress, or absence of deadlock.
- No change to EVENT_TIME or hidden event buffer.
- Priority by emission ID is v0 policy, not a hardware law.

## Acceptance

Finite capacity, atomic groups, duplicate protection, exact route coverage,
no state mutation, deterministic ordering, independent PEs, already-published
and partial-group rejection, zero-fanout acceptance, future blocked-retry.
