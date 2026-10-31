# SPK Memory Access Model v0

Status: DRAFT
Baseline: spk-core-network-v0
Parent: spk-memory-contract-v0.md

## 1. Architectural principle

SPK distinguishes three independent concepts:

1. Logical computational action.
2. Architectural resource transaction.
3. Physical implementation of that transaction.

The architecture specifies the first two.

The physical implementation remains independent.

One Core instruction does not necessarily correspond
to one memory transaction.

## 2. Memory domains

P - Program
S - State
E - Events and outputs
O - Observation

Memory domains define logical ownership,
capacity and access protection.

They do not require separate physical memory banks.

## 3. Logical access intents

The following operations describe computational
dependencies and resource requirements:

PROGRAM_REFERENCE
- A node requires its active Core program.

STATE_LOAD
- A batch requires the node persistent state.

STATE_COMMIT
- The completed batch updates persistent state.

BATCH_CONSUME
- The complete input batch is consumed.
- Input multiplicity must be preserved.

EMISSION_RECORD
- A Core emission becomes observable.

ROUTE_ENQUEUE
- A routed event is created for a destination.
- Parallel edges preserve multiplicity.

OBSERVATION_RECORD
- Diagnostic information is recorded separately.

OBSERVATION_READ
- Authorized learning or analysis reads observation data.
- Reading does not modify active computational state.

SNAPSHOT_READ
- An authorized activity reads a stable snapshot.

CANDIDATE_PROGRAM_WRITE
- An isolated candidate configuration is updated.

These are logical access intents, not ISA opcodes.

## 4. Access accounting

Logical quantities and architectural memory
transactions must not be conflated.

A batch may require one logical state load and
one logical state commit, regardless of the number
of Core instructions.

An implementation may retain the state locally
for the entire batch.

Instruction fetching, caching, buffering,
prefetching and memory transaction aggregation
belong to the selected architecture profile.

No fixed transaction cost is assigned to an
individual Core instruction in this version.

## 5. Transaction mapping

Future architecture profiles must explicitly define
the conversion from logical access intents into
resource-service requests.

The mapping must specify:

- target Processing Element;
- memory domain;
- resource units consumed;
- access service demand;
- latency or scheduling constraints;
- buffering requirements.

Mappings must be deterministic under a declared
deterministic architecture policy.

No default physical-memory mapping is implied.

## 6. Two independent temporal domains

EVENT_TIME:
- Logical timestamp of the neuronal event.
- Governed by SPK Core and Network semantics.

SERVICE_TIME:
- Architectural resource service cycle.
- Governed by the selected memory scheduler.

A delay in SERVICE_TIME must not implicitly
change EVENT_TIME.

A future coupling between these domains
requires a separately versioned semantic contract.

## 7. Arbitration

Access permissions, scheduling priority and
service guarantees are independent properties.

The scheduler must preserve admitted resource
reservations and configured access permissions.

Scheduling must not alter the logical causal
ordering or multiplicity of SPK events.

Simulated contention must be observable.

Deadlock, starvation and priority inversion
require explicit detection or policy guarantees.

## 8. Execution epochs

Every active operation belongs to a coherent
execution epoch.

Candidate programs remain isolated.

Program activation is a control transition,
not an ordinary memory transaction.

No in-flight hot-swap exists in Network v0.

## 9. Observation

The architectural simulator must eventually
expose machine-readable records containing:

- access identity and activity;
- execution epoch;
- Processing Element;
- memory domain;
- logical operation;
- logical quantity;
- EVENT_TIME, when applicable;
- SERVICE_TIME, when applicable;
- arbitration outcome;
- resulting resource occupancy.

Missing timing information must remain explicitly
unspecified rather than fabricated.

## 10. Version boundaries

This document defines a preliminary logical
access vocabulary.

It does not yet define:
- physical instruction fetch counts;
- memory latency;
- service scheduling;
- PE-level buffer allocation;
- memory banking;
- instruction encoding;
- hardware concurrency.

Those capabilities require further contracts.

## 11. Acceptance

The model remains DRAFT until:

- logical intents have validated representations;
- resource transaction mapping is defined;
- permission rules are executable;
- architectural timing is independently tested;
- behavior is compared against Network v0.

## 12. Authorization trust boundary

Access grants are architectural authority descriptors.

They must be issued by a trusted machine controller,
not derived from untrusted access request fields.

A matching request activity does not authenticate
the requesting principal.

Memory authorization does not prove that a routed
spike corresponds to a valid Network edge.

Routing provenance must be validated separately.

Priority never grants access permission.

Authorization occurs before resource arbitration.

The current implementation models authorization
decisions but does not implement a security boundary
against arbitrary host-language object construction.

## 13. Transaction activity provenance

A mapped service request retains the activity
established by its authorization context.

The activity must not be inferred solely from
the memory domain or operation kind.

Service priority is assigned separately by
the architectural arbitration policy.

A service request does not carry caller-selected
priority or scheduling privilege.

The transaction mapping layer is trusted
simulator infrastructure, not an authentication
mechanism by itself.
